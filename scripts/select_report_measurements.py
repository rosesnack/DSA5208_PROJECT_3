"""Select complete validated measurements deterministically, preserving provenance."""
import json
from pathlib import Path
from analyze_report_results import ROOT, INVENTORY, read_csv, dimensions


def main():
    inventory=read_csv(INVENTORY/'experiment_manifest_20700.csv')
    lookup={}
    for r in inventory:
        if '512' in r['stage']:continue
        s=json.loads((ROOT/r['summary']).read_text())
        if 'a40' in s['environment']:continue
        n,p,t=dimensions(r['stage'],s,r['canonical_summary'])
        mode='none' if 'processes' not in s else s['communication'].replace('allgatherv','allgather')
        lookup[r['graph'],s['implementation'],n,p,t,mode]=r
    selected={}
    def add(path,n,t,marker,performance,validation):
        if not path.exists() or not marker.exists():return
        proof=json.loads(marker.read_text()) if marker.suffix=='.json' else None
        if proof is not None and (proof.get('failed')!=0 or proof.get('passed')!=1):return
        host_file=next(parent/'cpu_hosts.jsonl' for parent in path.parents if (parent/'cpu_hosts.jsonl').is_file())
        hosts=[json.loads(x) for x in host_file.read_text().splitlines()]
        assert len({x['host'] for x in hosts})==n
        assert all('Platinum 8452Y' in x['cpu_model'] for x in hosts)
        s=json.loads(path.read_text());mode=s.get('communication','none').replace('allgatherv','allgather')
        r=lookup[s['dataset'],s['implementation'],n,s.get('processes',1),t,mode]
        selected[r['canonical_summary']]={'summary':str(path.relative_to(ROOT)),'marker':str(marker.relative_to(ROOT)),
             'performance_job':performance,'validation_job':validation}
    base=ROOT/'results/updated_vanda_scaling/performance_investigation_20261116'
    google=base/'google'
    # The OpenMP validator covers all six configurations in one report.
    report=google/'unbound_default_openmp/openmp/validation.json'
    if report.exists():
        proof=json.loads(report.read_text())
        if proof['failed']==0 and proof['passed']==6:
            for t in [1,2,4,8,16,32]:
                path=google/f'unbound_default_openmp/openmp/google/t{t}/summary.json'
                r=lookup['google','openmp',1,1,t,'none']
                selected[r['canonical_summary']]={'summary':str(path.relative_to(ROOT)),'marker':str(report.relative_to(ROOT)),
                    'performance_job':'1567277.stdct-mgmt-02','validation_job':'1567278.stdct-mgmt-02'}
    for t in [16,32]:
        folder=google/f'unbound_default_kokkos{t}/kokkos/OpenMP'
        add(folder/'google/summary.json',1,t,folder/'validation.json','1567277.stdct-mgmt-02','1567278.stdct-mgmt-02')
    for graph,perf,val in [('strong_uniform','1567383','1569220'),('strong_hub','1567385','1567386'),('strong_controlled','1567387','1567388')]:
        for path in (base/'hongxinran'/graph).rglob('summary.json'):
            s=json.loads(path.read_text());t=s.get('requested_threads',s.get('actual_threads',1))
            parent=path.parents[2]
            if s['implementation']=='mpi_kokkos':
                if t>1:parent=parent/f'threads_{t}'
            validation_job=val+'.stdct-mgmt-02'
            if graph=='strong_uniform':
                case=path.relative_to(base/'hongxinran'/graph).parts[0]
                parallel=base/'validation_parallel_20261117.json'
                if parallel.exists():
                    receipt=json.loads(parallel.read_text())
                    validation_job=next((x['validation_job'] for x in receipt['jobs'] if x['case']==case),validation_job)
                resume=base/'validation_resume_20261117.json'
                if resume.exists():
                    old=json.loads(resume.read_text())
                    if any('/'+case+'/' in x['path'] for x in old['existing_reports']):validation_job='1567384.stdct-mgmt-02'
            add(path,8,t,parent/'validation.json',perf+'.stdct-mgmt-02',validation_job)
    folder=base/'final128/results'
    marker=folder/'validate_complete.txt'
    if marker.exists():
        for path in folder.rglob('summary.json'):
            if '/serial/' not in str(path):add(path,4,1,marker,'1569195.stdct-mgmt-02','1569196.stdct-mgmt-02')
    dest=ROOT/'reports/non512/measurement_selection.json'
    dest.write_text(json.dumps(selected,indent=2)+'\n')
    print('Selected validated cells:',len(selected))


if __name__=='__main__':main()
