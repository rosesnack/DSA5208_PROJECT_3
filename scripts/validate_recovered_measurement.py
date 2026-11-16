"""Independently verify retained ranks/timings; never fabricate missing history."""
from array import array
import csv
import json
import math
from pathlib import Path
import statistics
import sys

source=Path(sys.argv[1]);reference=Path(sys.argv[2]);edge_path=Path(sys.argv[3]);output=Path(sys.argv[4])
settings=json.loads((reference/'summary.json').read_text());n=settings['nodes'];alpha=settings['alpha']
ranks=array('d');indegree=array('I');outdegree=array('I')
with (source/'ranks.csv').open() as f:
    for i,row in enumerate(csv.DictReader(f)):
        assert int(row['node_id'])==i
        r=float(row['rank']);assert math.isfinite(r) and r>=0
        ranks.append(r);indegree.append(int(row['in_degree']));outdegree.append(int(row['out_degree']))
assert len(ranks)==n and abs(math.fsum(ranks)-1)<=1e-10
actual_in=array('I',[0])*n;actual_out=array('I',[0])*n;incoming=array('d',[0])*n
contribution=array('d',(r/d if d else 0 for r,d in zip(ranks,outdegree)))
edges=0
with edge_path.open() as f:
    for line in f:
        line=line.split('#',1)[0].strip()
        if not line:continue
        u,v=map(int,line.split());actual_out[u]+=1;actual_in[v]+=1;incoming[v]+=contribution[u];edges+=1
assert edges==settings['edges'] and actual_in==indegree and actual_out==outdegree
base=((1-alpha)+alpha*math.fsum(r for r,d in zip(ranks,outdegree) if d==0))/n
residual=math.fsum(abs(base+alpha*x-r) for x,r in zip(incoming,ranks));assert residual<=1e-8+1e-12
errors=[]
with (reference/'ranks.csv').open() as f:
    for i,row in enumerate(csv.DictReader(f)):
        assert int(row['node_id'])==i
        errors.append(abs(ranks[i]-float(row['rank'])))
assert len(errors)==n and math.fsum(errors)<=1e-8
with (source/'timings.csv').open() as f:timings=list(csv.DictReader(f))
assert len(timings)==5 and [int(x['run']) for x in timings]==list(range(1,6))
assert all(x['converged']=='true' and int(x['processes'])==128 and int(x['iterations'])==12 for x in timings)
assert all(float(x['residual_l1'])<=1e-8 and abs(float(x['rank_sum'])-1)<=1e-10 for x in timings)
times=[float(x['solve_s']) for x in timings];assert all(math.isfinite(t) and t>0 for t in times)
report={'numerical_and_timing_checks_passed':True,'canonical_validation_complete':False,
        'missing_original_artifacts':['history.csv','summary.json'],
        'explanation':'Output failed after ranks and five timings were saved. No missing history or original summary was manufactured.',
        'source':str(source),'vertices':n,'edges':edges,'independent_residual_l1':residual,
        'rank_sum_error':abs(math.fsum(ranks)-1),'serial_l1_error':math.fsum(errors),
        'solve_median_s':statistics.median(times),'solve_repeats_s':times}
output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
