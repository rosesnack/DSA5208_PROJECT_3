import os,json,csv,subprocess,shlex,datetime
from pathlib import Path
base=Path('/scratch/hongxinran/DSA5208_PROJECT_3_assist_20261111');run='20261111_hongxinran_assist';root=base/'results/updated_vanda_scaling'/run;group={'graph': 'grid_uniform_n50000_d16', 'nodes': 8, 'cores_per_node': 64, 'cores': 512, 'extension': 'endpoint512_pair_20261117', 'raw_stage': 'cpu_core_groups_pair512_20261117', 'priority': 3, 'walltime': '00:30:00', 'prerequisite': '', 'required_job': '', 'dense_launch_pause_s': 65, 'cells': [{'implementation': 'hybrid', 'processes': 256, 'threads': 2, 'communication': 'allgather', 'canonical_summary': 'strong/grid_uniform_n50000_d16/nodes8_p512/hybrid/grid_uniform_n50000_d16/p256_t2/summary.json'}, {'implementation': 'hybrid', 'processes': 256, 'threads': 2, 'communication': 'halo', 'canonical_summary': 'strong/grid_uniform_n50000_d16/nodes8_p512/hybrid_halo/grid_uniform_n50000_d16/p256_t2/summary.json'}], 'dependency': '', 'scheduler_cpu_pool': 'cpu_all', 'walltime_basis': 'Two small 50k-vertex, 800k-edge Hybrid cases, same p256/T2 layout. Prior multi-case groups complete in minutes; 30 minutes includes launch/affinity and ample slack.'}
home=Path.home()/'dsa5208_endpoint512_20261117';home.mkdir(exist_ok=True);receipt=home/'submission_receipt.json';assert not receipt.exists(),'Existing receipt: do not submit twice'
output=subprocess.check_output(['hpc','project'],text=True);balance=float(next(x for x in output.splitlines() if x.strip().startswith('personal-hongxinran ')).split('|')[2]);assert balance>=320
ids=subprocess.check_output(['qselect','-u','hongxinran'],text=True).split();jobs={}
for i in range(0,len(ids),25):jobs.update(json.loads(subprocess.check_output(['qstat','-f','-F','json',*ids[i:i+25]],text=True))['Jobs'])
paid={k:v for k,v in jobs.items() if v.get('queue')=='batch_cpu'};assert all(v['job_state']=='H' and 'u' in v.get('Hold_Types','') for v in paid.values())
assert balance-256>=64
os.chdir(base)
registry=root/'core_group_jobs.tsv';rows=list(csv.DictReader(registry.open(),delimiter='\t'));known={c['canonical_summary'] for r in rows for c in json.loads(Path(r['plan']).read_text())['cells']}
assert not known.intersection(c['canonical_summary'] for c in group['cells'])
assert all(not (root/Path(c['canonical_summary']).parent/'complete.txt').exists() for c in group['cells'])
plan=root/'core_group_plans/grid_uniform_n50000_d16_n8_c64_pair512_20261117.json';plan.write_text(json.dumps(group,indent=2)+'\n')
check=home/'preflight.py';check.write_text("from pathlib import Path\nimport os\np=Path('/scratch/hongxinran/dsa5208_scaling/20261111_hongxinran_assist')/'endpoint512_write_probe.bin'\nwith p.open('wb') as f:\n f.write(bytes(64*1024*1024));f.flush();os.fsync(f.fileno())\np.unlink()\nprint('512 output preflight passed')\n")
pre=home/'preflight.pbs';pre.write_text('#!/usr/bin/env bash\n#PBS -j oe\nset -euo pipefail\npython3 '+str(check)+'\n')
proof=subprocess.check_output(['qsub','-q','auto_free','-l','select=1:ncpus=1:mem=2gb','-l','walltime=00:10:00','-o',str(home/'preflight.log'),str(pre)],cwd=base,text=True).strip();group['required_job']=group['dependency']=proof;plan.write_text(json.dumps(group,indent=2)+'\n')
env=os.environ.copy();env.update(RUN_ID=run,DATA_ROOT='/scratch/hongxinran/dsa5208_scaling/'+run,CORE_GROUP_PLAN=str(plan),OMPI_MCA_btl='self,vader,tcp',OMPI_MCA_pml='ob1',PAGERANK_HYBRID_MAX_TOTAL_THREADS='512');env.pop('UCX_NET_DEVICES',None)
p=subprocess.check_output(['qsub','-h','-N','dsa512-pair','-P','personal-hongxinran','-q','auto','-l','select=8:ncpus=64:mpiprocs=64:ompthreads=1:mem=64gb:node_pool=cpu_node:switch=cpu_all','-l','place=scatter','-l','walltime=00:30:00','-W','depend=afterok:'+proof,'-o',str(home/'performance.log'),'scripts/vanda_core_group_job.pbs'],cwd=base,env=env,text=True).strip()
row=dict(zip(rows[0].keys(),(group['graph'],8,64,512,p,'','00:30:00',2,str(plan),proof)));rows.append(row)
def save_registry():
 with registry.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys(),delimiter='\t');w.writeheader();w.writerows(rows)
save_registry()
v=subprocess.check_output(['qsub','-N','dsa512-pair-check','-q','auto_free','-W','depend=afterok:'+p,'-o',str(home/'validation.log'),'scripts/vanda_finalize_core_group_job.pbs'],cwd=base,env=env,text=True).strip();row['validation_job']=v;save_registry()
j=json.loads(subprocess.check_output(['qstat','-f','-F','json',p],text=True))['Jobs'][p];assert int(j['Resource_List']['ncpus'])==512 and int(j['Resource_List']['nodect'])==8
r={'time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'account':'hongxinran','project':'personal-hongxinran','verified_balance':balance,'new_maximum_cpuh':256,'uncommitted_after_reservation':balance-256,'minimum_margin':64,'user_held_legacy_jobs_left_deferred':sorted(paid),'group':group,'row':row,'preflight_job':proof,'workdir':str(base)};receipt.write_text(json.dumps(r,indent=2)+'\n')
subprocess.check_output(['qrls','-h','u',p],text=True)
print(json.dumps({'receipt':r,'plan':plan.read_text(),'registry':registry.read_text()}))
