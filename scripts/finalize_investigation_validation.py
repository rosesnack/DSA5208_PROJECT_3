"""Mark a diagnostic group complete only after every independent case passes."""
import json
import os
from pathlib import Path
import re
import sys

root=Path(sys.argv[1]);reports=[]
for case in sorted(root.iterdir()):
    if not case.is_dir():continue
    match=re.fullmatch(r'(.+)_p(\d+)_t(\d+)_(allgather|halo)',case.name)
    if not match:continue
    method,p,t,mode=match.groups();p=int(p);t=int(t)
    prefix=method+('_halo' if mode=='halo' else '')
    folder=case/prefix
    if method=='mpi_kokkos':
        folder=folder/'OpenMP'
        if t>1:folder=folder/f'threads_{t}'
    report=json.loads((folder/'validation.json').read_text())
    assert report['failed']==0 and report['passed']==1
    check=report['checks'][0];assert check['processes']==p
    if method!='mpi':assert check['requested_threads']==t
    reports.append(str(folder/'validation.json'))
assert len(reports)==14
(root/'validation_index.json').write_text(json.dumps(reports,indent=2)+'\n')
(root/'validate_complete.txt').write_text(os.environ['PBS_JOBID']+'\n')
print('Independent validation complete for all 14 configurations.')
