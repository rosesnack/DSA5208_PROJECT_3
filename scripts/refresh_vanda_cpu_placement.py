"""Rebind queued CPU requests to available, previously validated physical hosts."""
import json
import re
import subprocess
from pathlib import Path


def memory_bytes(value):
    if not value:
        return 0
    match = re.fullmatch(r'([0-9.]+)([a-z]+)', str(value).lower())
    return float(match[1]) * {'b': 1, 'kb': 1024, 'mb': 1024**2,
                             'gb': 1024**3, 'tb': 1024**4}[match[2]]


def physical_capacity(nodes, allowed_hosts):
    """A PBS chunk can use multiple NUMA vnodes on the same physical host."""
    pools = {}
    for node in nodes.values():
        available = node.get('resources_available', {})
        assigned = node.get('resources_assigned', {})
        host = available.get('host')
        if host not in allowed_hosts or 'cpu_node' not in available.get('node_pool', ''):
            continue
        if any(state in node.get('state', '') for state in ('offline', 'down')):
            continue
        cores = int(available.get('ncpus', 0)) - int(assigned.get('ncpus', 0))
        memory = memory_bytes(available.get('mem', 0)) - memory_bytes(assigned.get('mem', 0))
        for pool in (available.get('switch') or '').split(','):
            if pool not in ('cpu_all', 'gpu_all'):
                continue
            host_capacity = pools.setdefault(pool, {}).setdefault(host, {'cpu': 0, 'memory': 0})
            host_capacity['cpu'] += cores
            host_capacity['memory'] += memory
    return pools


def placement_changes(rows, jobs, capacity, max_total_cores):
    """Keep node/core/memory/walltime requests; change only their host bindings."""
    proposals = []
    for row in sorted(rows, key=lambda item: (int(item['cores']), item['performance_job'])):
        job_id = row['performance_job']
        job = jobs.get(job_id, {})
        if job.get('job_state') != 'Q' or job.get('queue') != 'batch_cpu':
            continue
        resources = job['Resource_List']
        cores, nodes = int(resources['ncpus']), int(resources['nodect'])
        if cores > max_total_cores or int(resources.get('ngpus', 0)):
            continue
        per_node, memory = cores // nodes, memory_bytes(resources['mem']) / nodes
        old_hosts = re.findall(r'(?:^|:)host=([^:+]+)', resources['select'])
        old_pool = re.search(r'(?:^|:)switch=([^:+]+)', resources['select'])
        pools = [old_pool[1]] if old_pool else ['cpu_all', 'gpu_all']
        for pool in pools:
            choices = capacity.get(pool, {})
            eligible = {host for host, free in choices.items()
                        if free['cpu'] >= per_node and free['memory'] >= memory}
            if len(eligible) < nodes:
                continue
            if len(set(old_hosts)) == nodes and set(old_hosts) <= eligible:
                hosts = old_hosts
            else:
                hosts = sorted(eligible, key=lambda host: (-choices[host]['cpu'], host))[:nodes]
                chunk = resources['select'].split('+')[0].split(':', 1)[1]
                chunk = re.sub(r':host=[^:]+', '', chunk)
                if not old_pool:
                    chunk += ':switch=' + pool
                select = '+'.join('1:' + chunk + ':host=' + host for host in hosts)
                proposals.append({'job': job_id, 'before': resources, 'select': select, 'hosts': hosts})
            # Reserve the slots for this scheduler pass; PBS handles actual allocation.
            for available in capacity.values():
                for host in hosts:
                    if host in available:
                        available[host]['cpu'] -= per_node
                        available[host]['memory'] -= memory
            break
    return proposals


def refresh_queued(rows, jobs, allowed_path, max_total_cores):
    allowed = json.loads(Path(allowed_path).read_text())
    nodes = json.loads(subprocess.check_output(['pbsnodes', '-av', '-F', 'json'], text=True))['nodes']
    proposals = placement_changes(rows, jobs, physical_capacity(nodes, allowed), max_total_cores)
    updates = []
    for proposal in proposals:
        job_id = proposal['job']
        current = json.loads(subprocess.check_output(
            ['qstat', '-x', '-f', '-F', 'json', job_id], text=True))['Jobs'][job_id]
        if current['job_state'] != 'Q':
            continue
        before = current['Resource_List']
        subprocess.check_call(['qalter', '-l', 'select=' + proposal['select'], job_id])
        after = json.loads(subprocess.check_output(
            ['qstat', '-x', '-f', '-F', 'json', job_id], text=True))['Jobs'][job_id]['Resource_List']
        assert all(before.get(key) == after.get(key) for key in
                   ('ncpus', 'nodect', 'mem', 'walltime', 'ngpus', 'place', 'mpiprocs'))
        updates.append({'job': job_id, 'before': before, 'after': after,
                        'hosts': {host: allowed[host] for host in proposal['hosts']}})
    return updates
