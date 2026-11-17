"""Package the report and reproducible source without experimental log files."""
from pathlib import Path
import zipfile
import csv
import io

ROOT = Path(__file__).resolve().parents[1]


def main():
    files=[ROOT/name for name in ('report.pdf','README.md','CMakeLists.txt','requirements-report.txt',
                                  'third_party/kokkos_commit.txt','report_assets/authors.json')]
    files.extend(sorted((ROOT/'src').glob('*')))
    files.extend(sorted(p for p in (ROOT/'scripts').iterdir() if p.suffix in {'.py','.sh','.pbs','.cpp'}))
    output=ROOT/'submission.zip'
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in files:
            assert path.is_file()
            info=zipfile.ZipInfo(path.relative_to(ROOT).as_posix(),date_time=(2026,11,17,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            archive.writestr(info,path.read_bytes())
        for name in ('fixed_results_19530.csv','weak_results_372.csv','collective_controls.csv','launcher_controls.csv','supplement_512.csv'):
            rows=list(csv.DictReader((ROOT/'results/tables'/name).open()))
            fields=[k for k in rows[0] if not k.startswith(('source_','validation_')) and k not in ('account','performance_job')]
            stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore',lineterminator='\n')
            writer.writeheader();writer.writerows(rows)
            info=zipfile.ZipInfo('results/'+name,date_time=(2026,11,17,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,stream.getvalue())
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert not any(n.startswith(('tmp/','data/')) or n.endswith(('.log','.out','.err')) for n in archive.namelist())
        assert archive.read('report.pdf')==(ROOT/'report.pdf').read_bytes()
    print(output)


if __name__=='__main__':main()
