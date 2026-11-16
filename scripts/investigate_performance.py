"""Targeted Vanda reproduction using existing binaries and separate outputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def run(command, env, log):
    with log.open('a') as stream:
        stream.write(json.dumps(command)+'\n'); stream.flush()
        subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['compute','validate'])
    parser.add_argument('kind',choices=['google','mpi128'])
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    dest=args.destination.resolve(); dest.mkdir(parents=True,exist_ok=True)
    graph='google' if args.kind=='google' else 'strong_uniform'
    env=os.environ.copy()
    env.update(PAGERANK_ENVIRONMENT='vanda-gcc13-release',PAGERANK_REPEATS='5',PAGERANK_WARMUPS='1')
    data=Path(env['DATA_ROOT'])
    manifest=data/'manifests/strong_scaling.tsv'
    line=next(x for x in manifest.read_text().splitlines() if x.split()[0]==graph)
    (dest/'dataset.tsv').write_text(line+'\n')
    env['PAGERANK_DATASET_MANIFEST']=str(dest/'dataset.tsv')
    log=dest/(args.mode+'.log')
    cases=[]
    if args.kind=='google':
        for policy in ['unbound_default','spread_active','spread_passive']:
            cases.append((policy,'openmp',None))
            for t in [16,32]:cases.append((policy,'kokkos',t))
    else:cases=[('p128','mpi',128)]
    if args.mode=='compute':
        assert len(os.sched_getaffinity(0))>=32, 'Fewer than 32 usable CPUs on this node'
        run(['bash','scripts/record_vanda_allocation.sh',str(dest/'cpu_hosts.jsonl')],env,log)
        hosts=[json.loads(x) for x in (dest/'cpu_hosts.jsonl').read_text().splitlines()]
        assert all('Platinum 8452Y' in h['cpu_model'] for h in hosts)
        assert len({h['host'] for h in hosts})==(1 if args.kind=='google' else 4)
        metadata={'job':env['PBS_JOBID'],'allowed_cpus':sorted(os.sched_getaffinity(0)),
                  'original_omp_environment':{k:v for k,v in env.items() if k.startswith(('OMP_','GOMP_','KMP_'))},
                  'binaries':{n:hashlib.sha256(Path('build-vanda-matrix-cpu',n).read_bytes()).hexdigest()
                              for n in ['pagerank_openmp','pagerank_kokkos','pagerank_mpi']}}
        (dest/'environment.json').write_text(json.dumps(metadata,indent=2)+'\n')
    for policy,method,t in cases:
        case=dest/(policy+'_'+method+(str(t) if t else ''))
        case.mkdir(exist_ok=True)
        reference=case/'serial';reference.mkdir(exist_ok=True)
        target=reference/graph
        if not target.exists():target.symlink_to(data/'results/serial_grid'/graph/'serial'/graph,target_is_directory=True)
        current=env.copy();current['PAGERANK_RESULTS_ROOT']=str(case)
        current.update(OMP_NUM_THREADS=str(t or 32),OMP_DYNAMIC='FALSE',OMP_DISPLAY_ENV='VERBOSE',OMP_DISPLAY_AFFINITY='TRUE')
        for key in ['OMP_PROC_BIND','OMP_PLACES','OMP_WAIT_POLICY','GOMP_CPU_AFFINITY','GOMP_SPINCOUNT','KMP_AFFINITY']:
            current.pop(key,None)
        current['PAGERANK_OPENMP_THREADS']='1 2 4 8 16 32' if policy=='unbound_default' else '16 32'
        if policy.startswith('spread'):
            current.update(OMP_PROC_BIND='spread',OMP_PLACES='cores',OMP_WAIT_POLICY=policy.split('_')[1].upper())
        if args.mode=='compute':
            if method=='mpi':
                prefix=['mpiexec','-x','LD_LIBRARY_PATH','--map-by','ppr:32:node','--bind-to','core','-n','128']
                mapping=subprocess.check_output(prefix+['python3','scripts/report_core_group_affinity.py'],env=current,text=True)
                records=[json.loads(x) for x in mapping.splitlines()]
                assert len(records)==128 and len({x['host'] for x in records})==4
                assert all(len(x['cpus'])==1 for x in records)
                assert len({(x['host'],x['cpus'][0]) for x in records})==128
                (case/'mapping.jsonl').write_text(mapping)
                command=prefix+['./build-vanda-matrix-cpu/pagerank_mpi','--communication=halo']
            else:command=['./build-vanda-matrix-cpu/pagerank_'+method]
            run(command,current,log)
        else:
            command=['python3','scripts/validate_openmp.py'] if method=='openmp' else (
                ['python3','scripts/validate_gpu.py','kokkos','OpenMP'] if method=='kokkos' else
                ['python3','scripts/validate_mpi.py','halo','--processes','128'])
            run(command,current,log)
    (dest/(args.mode+'_complete.txt')).write_text(env['PBS_JOBID']+'\n')


if __name__=='__main__':main()
