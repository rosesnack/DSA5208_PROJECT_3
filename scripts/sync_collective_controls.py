"""Fetch this study's small artifacts and optionally rebuild the report as validation completes."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'results/updated_vanda_scaling/collective_controls_20261117'
REMOTE_CODE = r'''
import base64,json,zlib,datetime,subprocess
from pathlib import Path
home=Path.home()/'dsa5208_collective_controls_20261117'
receipt=json.loads((home/'submission_receipt.json').read_text())
files={}
for row in receipt['rows']:
 root=home/'results'/row['id']
 for p in root.rglob('*'):
  if p.is_file() and p.name!='ranks.csv' and 'serial' not in p.relative_to(root).parts and p.suffix in ('.json','.csv','.jsonl','.txt','.log'):
   files[str(Path('raw')/receipt['account']/row['id']/p.relative_to(root))]=p.read_text()
for p in (home/'reference_certificates').glob('*.json'):
 files['reference_certificates/'+receipt['account']+'/'+p.name]=p.read_text()
for name in ['watch_status.json','placement_events.jsonl','watch_process.json','watch_errors.log']:
 p=home/name
 if p.exists():files[receipt['account']+'_'+name]=p.read_text()
for row in receipt['rows']:
 for kind in ['performance','validation']:
  p=home/(row['id']+'_'+kind+'.log')
  if p.exists():files['logs/'+receipt['account']+'/'+p.name]=p.read_text()
ids=[r[k] for r in receipt['rows'] for k in ['performance_job','validation_job']]
for early in home.glob('early*validation_receipt.json'):
 ids.append(json.loads(early.read_text())['job'])
p=subprocess.run(['qstat','-x','-f','-F','json',*ids],text=True,capture_output=True,timeout=45)
jobs=json.loads(p.stdout).get('Jobs',{})
snapshot={'time':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'jobs':{k:{f:v.get(f) for f in ['job_state','Exit_status','queue','Resource_List','resources_used','exec_vnode','comment']} for k,v in jobs.items()}}
files['live_'+receipt['account']+'.json']=json.dumps(snapshot,indent=2)+'\n'
print(base64.b64encode(zlib.compress(json.dumps(files).encode())).decode())
'''


def sync_account(user):
    command = ['ssh', '-F', '/dev/null', '-o', 'ProxyCommand=none', '-o', 'ProxyJump=none',
               '-o', 'HostKeyAlias=vanda.nus.edu.sg', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
               '-i', str(Path.home() / '.ssh/id_rsa'), '-o', 'ConnectTimeout=12',
               '-o', 'ServerAliveInterval=20', '-o', 'ServerAliveCountMax=3',
               user + '@vanda.nus.edu.sg', 'python3 -']
    response = subprocess.run(command, input=REMOTE_CODE, text=True, capture_output=True, check=True, timeout=180)
    files = json.loads(zlib.decompress(base64.b64decode(response.stdout)))
    for name, text in files.items():
        p = DEST / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
    state = json.loads(files['live_' + user + '.json'])
    print(user, {k.split('.')[0]: (v['job_state'], v.get('Exit_status')) for k, v in state['jobs'].items()}, flush=True)


def cycle(rebuild, poppler):
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(sync_account, ('xtt_ella', 'hongxinran')))
    old = ROOT / 'reports/non512/data/collective_controls.csv'
    subprocess.run([sys.executable, 'scripts/analyze_collective_controls.py'], cwd=ROOT, check=True)
    extra=ROOT/'reports/non512/data/launcher_controls.csv'
    signature=hashlib.sha256(old.read_bytes()+extra.read_bytes()+(ROOT/'scripts/build_non512_report.py').read_bytes()).hexdigest()
    check_file=DEST/'auto_report_check.json'
    previous=json.loads(check_file.read_text()).get('source_signature') if check_file.exists() else None
    if rebuild and signature != previous:
        command = [sys.executable, 'scripts/build_non512_report.py']
        if poppler:
            command += ['--pdftoppm', poppler]
        subprocess.run(command, cwd=ROOT, check=True)
        from pypdf import PdfReader
        pdf = ROOT/'output/pdf/pagerank_non512_report.pdf'
        pages = PdfReader(pdf).pages
        texts = [p.extract_text() for p in pages]
        assert all('DSA5208 | Parallel PageRank | Vanda results' in t for t in texts)
        combined='\n'.join(texts)
        assert all(t in combined for t in ('1 Introduction to the algorithm and data','2 Methodology',
                                           '3 Results','4 Conclusions and insights'))
        review=ROOT/'tmp/pdfs/collective_auto_review'
        if poppler:
            review.mkdir(parents=True,exist_ok=True)
            subprocess.run([poppler,'-scale-to','900','-png',str(pdf),str(review/'page')],check=True)
        check_file.write_text(json.dumps({
            'pages':len(pages),'section_and_footer_checks_passed':True,
            'source_signature':signature,
            'validated_controls':sum(1 for line in old.read_text().splitlines()[1:] if line)+sum(1 for line in extra.read_text().splitlines()[1:] if line),
            'rendered_review_directory':str(review) if poppler else None},indent=2)+'\n')
    count=sum(1 for p in (DEST / 'raw').rglob('validation_complete.txt') if len(p.relative_to(DEST / 'raw').parts) == 4)
    target=sum(row['cells'] for user in ('xtt_ella','hongxinran') for row in json.loads((DEST/('submission_'+user+'.json')).read_text())['rows'])
    return count,target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild', action='store_true')
    parser.add_argument('--pdftoppm')
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--interval', type=int, default=120)
    parser.add_argument('--until', help='ISO timestamp with timezone')
    args = parser.parse_args()
    from datetime import datetime
    deadline = datetime.fromisoformat(args.until) if args.until else None
    while True:
        try:
            count,target = cycle(args.rebuild, args.pdftoppm)
            print('Validated controls:', count, '/',target, flush=True)
            if count == target:
                break
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            print('Sync deferred:', str(error), flush=True)
            if not args.watch:
                raise
        if not args.watch or (deadline and datetime.now(deadline.tzinfo) >= deadline):
            break
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
