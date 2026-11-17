"""Check the residual certificate and rejection paths on temporary toy artifacts; no benchmark results are produced."""
import sys,tempfile,os,json,csv,math,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from validate_collective_controls import validate_group
from investigate_collectives import folder_for
os.environ['PBS_JOBID']='local-validator-check'
with tempfile.TemporaryDirectory(prefix='collective-certificate-') as td:
 root=Path(td);graph='tiny';edges=root/'tiny.edges';nodes=root/'tiny.nodes';edges.write_text('0 1\n1 0\n1 2\n');nodes.write_text('0\n1\n2\n')
 alpha=.85;out=[1,2,0];ind=[1,1,1]
 def F(x):
  base=((1-alpha)+alpha*x[2])/3
  return [base+alpha*x[1]/2,base+alpha*x[0],base+alpha*x[1]/2]
 x=[1/3]*3;history=[]
 while True:
  y=F(x);delta=math.fsum(abs(a-b) for a,b in zip(x,y));history.append(delta);x=y
  if delta<=1e-8:break
 residual=math.fsum(abs(a-b) for a,b in zip(x,F(x)))
 meta=dict(dataset=graph,environment='validator-test',build_type='Release',nodes=3,edges=3,alpha=alpha,tolerance_l1=1e-8,max_iterations=1000,fixed_iterations=0,warmup_runs=1,repeat_runs=5,iterations=len(history),converged=True,solve_median_s=3.,solve_min_s=1.,solve_max_s=5.,max_residual_l1=residual,max_rank_sum_error=abs(math.fsum(x)-1))
 def write(folder,implementation):
  folder.mkdir(parents=True,exist_ok=True);s={**meta,'implementation':implementation}
  if implementation=='mpi':s.update(processes=1,communication='halo')
  (folder/'summary.json').write_text(json.dumps(s))
  with (folder/'ranks.csv').open('w') as f:
   f.write('node_id,rank,in_degree,out_degree\n')
   for i,value in enumerate(x):f.write(f'{i},{value:.17g},{ind[i]},{out[i]}\n')
  with (folder/'timings.csv').open('w') as f:
   f.write('run,processes,iterations,converged,solve_s,residual_l1,rank_sum\n')
   for i in range(1,6):f.write(f'{i},1,{len(history)},true,{i},{residual:.17g},{math.fsum(x):.17g}\n')
  with (folder/'history.csv').open('w') as f:
   f.write('iteration,delta_l1\n')
   for i,d in enumerate(history,1):f.write(f'{i},{d:.17g}\n')
 ref=root/'serial_grid'/graph/'serial'/graph;write(ref,'serial')
 cell=dict(id='case',graph=graph,implementation='mpi',processes=1,threads=1,communication='halo',policy='default')
 g=dict(output=str(root/'results/c1'),serial_root=str(root/'serial_grid'),cores=1,cells=[cell],datasets={graph:f'{graph} {edges} {nodes}'})
 case=Path(g['output'])/'case';write(case/folder_for(cell),'mpi');(case/'measurement_complete.txt').write_text('test-performance\n')
 validate_group(g);assert json.loads((case/'validation.json').read_text())['passed']
 # A mass-preserving but wrong vector must fail the independent certificate.
 (case/'validation_complete.txt').unlink();rankfile=case/folder_for(cell)/'ranks.csv';saved=rankfile.read_text();lines=saved.splitlines();a=lines[1].split(',');b=lines[2].split(',');a[1]=str(float(a[1])+.01);b[1]=str(float(b[1])-.01);lines[1]=','.join(a);lines[2]=','.join(b);rankfile.write_text('\n'.join(lines)+'\n')
 try:validate_group(g)
 except AssertionError:pass
 else:raise AssertionError('Incorrect vector accepted')
 rankfile.write_text(saved)
 # Changing the reported median without changing timings must also fail.
 summary=case/folder_for(cell)/'summary.json';s=json.loads(summary.read_text());s['solve_median_s']=2.5;summary.write_text(json.dumps(s))
 try:validate_group(g)
 except AssertionError:pass
 else:raise AssertionError('Incorrect median accepted')
 for k in range(1,50):
  y=[x[0]+k*1e-6,x[1]-k*1e-6,x[2]]
  actual=math.fsum(abs(a-b) for a,b in zip(y,F(y)));bound=residual+(1+alpha)*math.fsum(abs(a-b) for a,b in zip(y,x));assert actual<=bound+1e-15
print('Independent edge reference, dangling-mass contraction bound, full-vector rejection and timing-median rejection checks passed')
