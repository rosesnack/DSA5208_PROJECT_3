"""Independent 256-core controls; outputs never replace the fixed matrix."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from investigate_performance import run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['compute','validate'])
    parser.add_argument('graph',choices=['strong_uniform','strong_hub','strong_controlled'])
    parser.add_argument('destination',type=Path)
    args=parser.parse_args();dest=args.destination.resolve();dest.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();data=Path(env['DATA_ROOT'])
    env.update(PAGERANK_ENVIRONMENT='vanda-gcc13-release',PAGERANK_REPEATS='5',PAGERANK_WARMUPS='1',
               OMP_DYNAMIC='FALSE',OMP_PROC_BIND='spread',OMP_PLACES='cores',
               PAGERANK_HYBRID_MAX_TOTAL_THREADS='256')
    line=next(x for x in (data/'manifests/strong_scaling.tsv').read_text().splitlines() if x.split()[0]==args.graph)
    manifest=dest/'dataset.tsv';manifest.write_text(line+'\n');env['PAGERANK_DATASET_MANIFEST']=str(manifest)
    layouts=[('mpi',1)]
    if args.graph=='strong_uniform':layouts += [(m,t) for m in ['hybrid','mpi_kokkos'] for t in [1,16,32]]
    log=dest/(args.mode+'.log')
    if args.mode=='compute':
        run(['bash','scripts/record_vanda_allocation.sh',str(dest/'cpu_hosts.jsonl')],env,log)
        hosts=[json.loads(x) for x in (dest/'cpu_hosts.jsonl').read_text().splitlines()]
        assert len({h['host'] for h in hosts})==8 and all('Platinum 8452Y' in h['cpu_model'] for h in hosts)
        binaries=['pagerank_'+m for m,t in layouts]
        (dest/'environment.json').write_text(json.dumps({'job':env['PBS_JOBID'],
            'binaries':{n:hashlib.sha256(Path('build-vanda-matrix-cpu',n).read_bytes()).hexdigest() for n in binaries}},indent=2)+'\n')
    for method,t in layouts:
        p=256//t
        for mode in ['allgather','halo']:
            folder=dest/f'{method}_p{p}_t{t}_{mode}';folder.mkdir(exist_ok=True)
            ref=folder/'serial';ref.mkdir(exist_ok=True)
            if not (ref/args.graph).exists():(ref/args.graph).symlink_to(data/'results/serial_grid'/args.graph/'serial'/args.graph,target_is_directory=True)
            current=env.copy();current.update(PAGERANK_RESULTS_ROOT=str(folder),OMP_NUM_THREADS=str(t),
                PAGERANK_HYBRID_THREADS=str(t),PAGERANK_KOKKOS_THREADS=str(t))
            if args.mode=='compute':
                prefix=['mpiexec','-x','LD_LIBRARY_PATH','--map-by',f'ppr:{p//8}:node','--bind-to','core' if t==1 else 'none','-n',str(p)]
                if t>1:prefix+=['python3','scripts/mpi_affinity_exec.py',str(t)]
                records=[json.loads(x) for x in subprocess.check_output(prefix+['python3','scripts/report_core_group_affinity.py'],text=True,env=current).splitlines()]
                assert len(records)==p and len({x['host'] for x in records})==8
                assert all(len(x['cpus'])==t for x in records)
                assert len({(x['host'],c) for x in records for c in x['cpus']})==256
                (folder/'mapping.jsonl').write_text('\n'.join(map(json.dumps,records))+'\n')
                run(prefix+['./build-vanda-matrix-cpu/pagerank_'+method,'--communication='+mode],current,log)
            else:
                if method=='mpi':cmd=['python3','scripts/validate_mpi.py',mode,'--processes',str(p)]
                elif method=='hybrid':cmd=['python3','scripts/validate_hybrid.py',mode,'--processes',str(p)]
                else:cmd=['python3','scripts/validate_mpi_device.py','mpi_kokkos','OpenMP',mode,'--processes',str(p)]
                run(cmd,current,log)
    (dest/(args.mode+'_complete.txt')).write_text(env['PBS_JOBID']+'\n')


if __name__=='__main__':main()
