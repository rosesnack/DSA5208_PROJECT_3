import os,csv,json,subprocess,shutil,hashlib,datetime,shlex
from pathlib import Path
old=Path('/scratch/xtt_ella/DSA5208_PROJECT_3_20261107');home=Path.home()/'dsa5208_endpoint512_20261117';project=home/'project';data=home/'data';logs=home/'logs';root=project/'results/updated_vanda_scaling'/'20261106T185006Z'
proof=json.loads((home/'relocation_preparation.json').read_text())['preflight_job']
def query(ids):
 return json.loads(subprocess.check_output(['qstat','-x','-f','-F','json',*ids],text=True))['Jobs'] if ids else {}
def hours(j):
 h,m,s=map(int,j['Resource_List']['walltime'].split(':'));return int(j['Resource_List']['ncpus'])*(h+m/60+s/3600)
assert query([proof])[proof].get('Exit_status')==0
ids=subprocess.check_output(['qselect','-u','xtt_ella'],text=True).split();existing=query(ids)
old_perf=['1560661.stdct-mgmt-02','1560663.stdct-mgmt-02','1560665.stdct-mgmt-02'];old_val=['1560662.stdct-mgmt-02','1560664.stdct-mgmt-02','1560666.stdct-mgmt-02']
assert all(x not in existing or (existing[x]['job_state']=='H' and existing[x].get('resources_used') is None) for x in old_perf)
assert not any(j['job_state'] in ['Q','R','E'] and j['queue']=='batch_cpu' for j in existing.values())
other_pending=sum(hours(j) for k,j in existing.items() if k not in old_perf and j['queue']=='batch_cpu')
floor=4861.854-112;assert floor-other_pending-7*512>=256
allgroups=json.loads((old/'results/updated_vanda_scaling'/'20261106T185006Z'/'core_group_watch_plan_xtt_ella_20261113_refund.json').read_text())
graphs=['grid_controlled_n50000_d4','grid_uniform_n50000_d4','grid_hub_n50000_d4','grid_controlled_n50000_d8','grid_uniform_n50000_d8','grid_hub_n50000_d8','grid_controlled_n50000_d16']
groups=[next(g for g in allgroups if g['graph']==name and g.get('extension')=='additional_512_splits') for name in graphs]
assert len({c['canonical_summary'] for g in groups for c in g['cells']})==112
for g in groups:
 assert len(g['cells'])==16 and g['nodes']==8 and g['cores_per_node']==64
 assert all(c['processes']*c['threads']==512 and not (old/'results/updated_vanda_scaling'/'20261106T185006Z'/Path(c['canonical_summary']).parent/'complete.txt').exists() for c in g['cells'])
 rel=Path('results/serial_grid')/g['graph']/'serial'/g['graph'];ref=data/rel;ref.mkdir(parents=True,exist_ok=True)
 for name in ['summary.json','history.csv','timings.csv','ranks.csv']:
  source=Path('/scratch/xtt_ella/dsa5208_scaling')/'20261106T185006Z'/rel/name;target=ref/name
  if not target.exists():shutil.copy2(source,target)
  assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest()
perf=home/'performance.pbs';val=home/'validate.pbs'
common='#!/usr/bin/env bash\n#PBS -j oe\n#PBS -V\nset -euo pipefail\ncd '+shlex.quote(str(project))+'\nexport RUN_ID='+'20261106T185006Z'+'\nexport DATA_ROOT='+shlex.quote(str(data))+'\nexport PAGERANK_HYBRID_MAX_TOTAL_THREADS=512\nexport OMPI_MCA_btl=self,vader,tcp\nexport OMPI_MCA_pml=ob1\nunset UCX_NET_DEVICES\n'
perf.write_text(common+'module load openmpi/gcc/64/4.1.8 CMake/3.29.3-GCCcore-13.3.0\nexport LD_LIBRARY_PATH="/opt/pbs/lib:${LD_LIBRARY_PATH:-}"\npython3 scripts/run_vanda_core_group.py compute "${CORE_GROUP_PLAN:?}"\n')
val.write_text(common+'python3 scripts/run_vanda_core_group.py finalize "${CORE_GROUP_PLAN:?}"\n')
plans=root/'core_group_plans';plans.mkdir(exist_ok=True);registry=root/'core_group_jobs.tsv';receipt=home/'resubmission_receipt.json'
previous=json.loads(receipt.read_text()) if receipt.exists() else {'rows':[],'events':[]}
rows=previous['rows'];events=previous['events'];budget={'verified_balance':4861.854,'post_balance_max_paid_cpuh':112,'conservative_floor':floor,'other_pending_cpuh':other_pending,'new_pending_cpuh':7*512,'margin_cpuh':256,'uncommitted_after_margin':floor-other_pending-7*512-256}
fields=['graph','nodes','cores_per_node','cores','performance_job','validation_job','walltime','cells','plan','dependency']
def persist():
 with registry.open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=fields,delimiter='\t');writer.writeheader();writer.writerows(rows)
 receipt.write_text(json.dumps({'time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'budget':budget,'rows':rows,'events':events,'replaced_performance':old_perf,'replaced_validation':old_val,'data_root':str(data),'project':str(project),'free_preflight':proof},indent=2)+'\n')
for i,g in enumerate(groups):
 dependency=proof if i==0 else rows[0]['validation_job']
 g.update(walltime='01:00:00',dependency=dependency,required_job=dependency,scheduler_cpu_pool='cpu_all',walltime_basis='16 small-graph cases; one hour allows MPI launch/affinity probes and dense TCP cooldowns; 1 warmup +5 timed repeats.')
 path=plans/(g['graph']+'_n8_c64_additional_512_splits.json');path.write_text(json.dumps(g,indent=2)+'\n')
 env=os.environ.copy();env['CORE_GROUP_PLAN']=str(path)
 resources='select=8:ncpus=64:mpiprocs=64:ompthreads=1:mem=64gb:node_pool=cpu_node:switch=cpu_all'
 if i<len(rows):
  row=rows[i];assert row['graph']==g['graph'];p=row['performance_job']
 else:
  p=subprocess.check_output(['qsub','-h','-N','dsa512-'+str(i+1),'-P','personal-xtt_ella','-q','auto','-l',resources,'-l','place=scatter','-l','walltime=01:00:00','-W','depend=afterok:'+dependency,'-o',str(logs/(g['graph']+'_performance.log')),str(perf)],cwd=project,env=env,text=True).strip()
  row=dict(zip(fields,(g['graph'],8,64,512,p,'','01:00:00',16,str(path),dependency)));rows.append(row);persist()
  v=subprocess.check_output(['qsub','-N','dsa512-check','-q','auto_free','-l','select=1:ncpus=1:mem=20gb','-l','walltime=24:00:00','-W','depend=afterok:'+p,'-o',str(logs/(g['graph']+'_validation.log')),str(val)],cwd=project,env=env,text=True).strip();row['validation_job']=v;persist()
 actual=query([p])[p];r=actual['Resource_List'];assert actual['queue'] in ['auto','batch_cpu'] and int(r['ncpus'])==512 and int(r['nodect'])==8 and r['walltime']=='01:00:00'
 assert actual['Variable_List']['CORE_GROUP_PLAN']==str(path)
 if i==2:
  for job in old_val+old_perf:
   subprocess.run(['qdel',job],capture_output=True,text=True)
  live=set(subprocess.check_output(['qselect','-u','xtt_ella'],text=True).split());assert not live.intersection(old_perf+old_val)
  events.append({'action':'cancelled_replaced_never_started_jobs','jobs':old_val+old_perf});persist()
(root/'endpoint512_plan_20261117.json').write_text(json.dumps(groups,indent=2)+'\n')
for row in rows:
 subprocess.run(['qrls','-h','u',row['performance_job']],capture_output=True,text=True,check=True)
events.append({'action':'released_new_user_holds','jobs':[r['performance_job'] for r in rows]});persist()
state=query([r[k] for r in rows for k in ['performance_job','validation_job']]);compact={k:{f:v.get(f) for f in ['job_state','Hold_Types','queue','project','Resource_List','comment']} for k,v in state.items()}
(root/'queue_snapshot.json').write_text(json.dumps(compact,indent=2)+'\n')
files={'resubmission_receipt.json':receipt.read_text(),'queue_snapshot.json':json.dumps(compact,indent=2),'core_group_jobs.tsv':registry.read_text(),'endpoint512_plan_20261117.json':(root/'endpoint512_plan_20261117.json').read_text()}
for p in plans.glob('*.json'):files['plans/'+p.name]=p.read_text()
print(json.dumps({'receipt':json.loads(receipt.read_text()),'states':{k:v['job_state'] for k,v in compact.items()},'files':files}))
