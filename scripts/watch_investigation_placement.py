"""Refresh only queued diagnostic host bindings; keep queue and experiment layout."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import time
from refresh_vanda_cpu_placement import refresh_queued, physical_capacity


def poll(receipt, proof, state):
    rows=json.loads(receipt.read_text())['jobs']
    ids=[r['performance_job'] for r in rows]
    jobs=json.loads(subprocess.check_output(['qstat','-x','-f','-F','json',*ids],text=True))['Jobs']
    assert set(ids)<=set(jobs), 'Missing PBS history; inspect before changing assignments'
    before={i:j['queue'] for i,j in jobs.items()}
    updates=refresh_queued(rows,jobs,proof,256)
    nodes=json.loads(subprocess.check_output(['pbsnodes','-av','-F','json'],text=True))['nodes']
    capacity=physical_capacity(nodes,json.loads(proof.read_text()))
    if updates:
        after=json.loads(subprocess.check_output(['qstat','-x','-f','-F','json',*ids],text=True))['Jobs']
        assert all(j['queue']==before[i] for i,j in after.items())
        with (state/'changes.jsonl').open('a') as f:
            for update in updates:f.write(json.dumps(update)+'\n')
    active=[i for i,j in jobs.items() if j['job_state'] in ['Q','H','R','E','B']]
    status={'observed_at':datetime.now().astimezone().isoformat(),'pid':os.getpid(),
            'states':{i:j['job_state'] for i,j in jobs.items()},'queues':before,
            'placement_updates':len(updates),'active_jobs':active,
            'eligible_known_hosts_32cores_222GiB':{pool:sum(x['cpu']>=32 and x['memory']>=222*1024**3 for x in hosts.values()) for pool,hosts in capacity.items()}}
    (state/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    return active


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('receipt',type=Path);p.add_argument('proof',type=Path)
    p.add_argument('state',type=Path);p.add_argument('--until',required=True)
    p.add_argument('--once',action='store_true');args=p.parse_args()
    args.state.mkdir(exist_ok=True,parents=True)
    deadline=datetime.fromisoformat(args.until)
    while datetime.now().astimezone()<deadline and not (args.state/'STOP').exists():
        try:
            active=poll(args.receipt,args.proof,args.state)
            if not active or args.once:break
        except (subprocess.CalledProcessError,ValueError,OSError) as error:
            (args.state/'last_error.txt').write_text(datetime.now().astimezone().isoformat()+' '+str(error)+'\n')
            if args.once:raise
        time.sleep(60)


if __name__=='__main__':main()
