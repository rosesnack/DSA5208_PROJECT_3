"""Create a portable, same-allocation collective-policy experiment plan."""
import argparse
import json
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--graph',required=True)
p.add_argument('--manifest',required=True,type=Path)
p.add_argument('--processes',required=True,type=int)
p.add_argument('--nodes',required=True,type=int)
p.add_argument('--threads',type=int,default=1)
p.add_argument('--implementation',choices=('mpi','hybrid','mpi_kokkos'),default='mpi')
p.add_argument('--communication',choices=('halo','allgather'),required=True)
p.add_argument('--policies',nargs='+',required=True)
p.add_argument('--reference-root',type=Path,required=True)
p.add_argument('--results',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
allowed={'halo':{'default','a2av_linear','a2av_pairwise'},'allgather':{'default','agv_bruck','agv_ring'}}
assert set(a.policies)<=allowed[a.communication]
assert a.processes%a.nodes==0 and a.processes*a.threads==a.nodes*32
line=next(s for s in a.manifest.read_text().splitlines() if s.split()[0]==a.graph)
name,edges,nodes=line.split()
line=f'{name} {Path(edges).resolve()} {Path(nodes).resolve() if nodes!="-" else "-"}'
cells=[dict(id=f'{a.graph}_{a.implementation}_p{a.processes}_t{a.threads}_{a.communication}_{policy}',
            graph=a.graph,implementation=a.implementation,processes=a.processes,threads=a.threads,
            communication=a.communication,policy=policy) for policy in a.policies]
group=dict(id=a.output.stem,cores=a.processes*a.threads,nodes=a.nodes,cores_per_node=32,
           cells=cells,output=str(a.results.resolve()),serial_root=str(a.reference_root.resolve()),
           datasets={a.graph:line})
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps(group,indent=2)+'\n')
print(a.output)
