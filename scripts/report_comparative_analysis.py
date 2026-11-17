"""Matched, descriptive comparisons of the existing audited PageRank measurements.

No benchmarks are submitted. A win refers to stored five-run medians, not a
significance test. Comparisons preserve graph, node class and the named controls.
"""
import csv
import json
import math
import statistics as stats
from collections import defaultdict
from pathlib import Path

METHODS=('MPI+OpenMP','MPI+Kokkos OpenMP')
MODES=('Allgatherv','Halo')
THREADS=(2,4,8,16,32)


def gm(values):
    return math.exp(stats.mean(math.log(v) for v in values))


def summarize(pairs):
    ratios=[b['time']/a['time'] for a,b in pairs]
    wins=[a['time']<b['time'] for a,b in pairs]
    payload_ok=[a['bytes']<=b['bytes'] for a,b in pairs]
    return dict(pairs=len(pairs),gain_geomean=gm(ratios),tested_time_geomean_s=gm([a['time'] for a,b in pairs]),
                reference_time_geomean_s=gm([b['time'] for a,b in pairs]),win_fraction=stats.mean(wins),
                gain_min=min(ratios),gain_max=max(ratios),
                time_win_no_payload_increase_fraction=stats.mean([w and ok for w,ok in zip(wins,payload_ok)]),
                payload_nonincrease_fraction=stats.mean(payload_ok),
                range_separated_win_fraction=stats.mean([a['max']<b['min'] for a,b in pairs]))


def simple(r):
    return dict(time=float(r['solve_median_s']),bytes=float(r['communication_bytes_per_iteration']),
                min=float(r['solve_min_s']),max=float(r['solve_max_s']))


def comparisons(fixed,weak):
    lookup={(r['graph'],r['context'],r['method'],int(r['host_nodes']),int(r['processes']),int(r['threads']),r['communication']):r for r in fixed}
    thread_groups=defaultdict(list);full_groups=defaultdict(list);common=[]
    for r in fixed:
        t=int(r['threads']);n=int(r['host_nodes']);p=int(r['processes']);c=p*t
        if r['context']!='cpu_node' or r['method'] not in METHODS or t==1:continue
        b=lookup[r['graph'],'cpu_node',r['method'],n,c,1,r['communication']]
        pair=(simple(r),simple(b));thread_groups[r['method'],r['communication'],t].append(pair)
        if c==32*n:
            full_groups[r['method'],r['communication'],t].append(pair)
            common.append(dict(graph=r['graph'],family=r['family'],method=r['method'],communication=r['communication'],nodes=n,cores=c,
                               processes=p,threads=t,gain=float(b['solve_median_s'])/float(r['solve_median_s']),
                               tested_time_s=float(r['solve_median_s']),reference_time_s=float(b['solve_median_s'])))
    assert len(common)==3600
    thread=[]
    for m in METHODS:
        for mode in MODES:
            for t in THREADS:
                thread.append(dict(method=m,communication=mode,threads=t,all_layouts=summarize(thread_groups[m,mode,t]),
                                   full_node_layouts=summarize(full_groups[m,mode,t])))
    # Same p/T at different node placements: payload is a function of ownership, not node mapping.
    placement_groups=defaultdict(list)
    for r in fixed:
        if r['context']=='cpu_node' and r['method'].startswith('MPI'):
            placement_groups[r['graph'],r['method'],r['communication'],r['processes'],r['threads']].append(r)
    placements=defaultdict(list)
    for key,rows in placement_groups.items():
        if len(rows)<2:continue
        rows.sort(key=lambda r:int(r['host_nodes']));a,b=rows[-1],rows[0]
        assert a['communication_bytes_per_iteration']==b['communication_bytes_per_iteration']
        placements[a['method'],a['communication']].append((simple(a),simple(b)))
    placement=[dict(method=m,communication=mode,**summarize(pairs)) for (m,mode),pairs in sorted(placements.items())]
    # Exact Halo versus complete-vector exchange on every p>1 layout, stratified by T/backend.
    halo_groups=defaultdict(list);halo=[]
    for r in fixed:
        if not r['method'].startswith('MPI') or r['communication']!='Halo' or int(r['processes'])==1:continue
        a=lookup[r['graph'],r['context'],r['method'],int(r['host_nodes']),int(r['processes']),int(r['threads']),'Allgatherv']
        pair=(simple(r),simple(a));assert pair[0]['bytes']<=pair[1]['bytes']
        halo_groups[r['context'],r['method'],int(r['threads'])].append(pair)
    for (context,m,t),pairs in sorted(halo_groups.items()):
        reductions=[1-a['bytes']/b['bytes'] for a,b in pairs]
        halo.append(dict(context=context,method=m,threads=t,payload_reduction_median=stats.median(reductions),**summarize(pairs)))
    gpu=[];graphs=sorted({r['graph'] for r in fixed})
    for m in ('MPI+CUDA','MPI+Kokkos CUDA'):
        for mode in MODES:
            pairs=[(simple(lookup[g,'gpu_node',m,2,2,1,mode]),simple(lookup[g,'gpu_node',m,1,1,1,mode])) for g in graphs]
            s=summarize(pairs);gpu.append(dict(method=m,communication=mode,gpu_seconds_ratio_geomean=2/s['gain_geomean'],**s))
    backend=[]
    for mode in MODES:
        for t in (1,*THREADS):
            pairs=[]
            for r in fixed:
                if r['context']=='cpu_node' and r['method']==METHODS[0] and r['communication']==mode and int(r['threads'])==t:
                    b=lookup[r['graph'],'cpu_node',METHODS[1],int(r['host_nodes']),int(r['processes']),t,mode]
                    assert r['communication_bytes_per_iteration']==b['communication_bytes_per_iteration']
                    pairs.append((simple(r),simple(b)))
            backend.append(dict(communication=mode,threads=t,**summarize(pairs)))
    standalone=[]
    for m,b in (('MPI+CUDA','CUDA'),('MPI+Kokkos CUDA','Kokkos CUDA')):
        for mode in MODES:
            pairs=[(simple(lookup[g,'gpu_node',b,1,1,1,'none']),simple(lookup[g,'gpu_node',m,1,1,1,mode])) for g in graphs]
            standalone.append(dict(method=m,standalone_method=b,communication=mode,**summarize(pairs)))
    # Kokkos T1 is also available at matched work/core, from the rank-normalized suite.
    extra=[]
    for f in ('uniform','hub','controlled'):
        for mode in MODES:
            rows=sorted([r for r in weak if r['suite']=='rank_cpu_regular' and r['method']==METHODS[1] and r['family']==f
                         and r['communication']==mode and int(r['active_cpu_threads'])>=4],key=lambda r:int(r['active_cpu_threads']))
            assert len(rows)==7
            base=float(rows[0]['seconds_per_iteration'])
            for r in rows:
                c=int(r['active_cpu_threads']);assert int(r['vertices'])==50000*c and int(r['edges'])==800000*c
                extra.append({**r,'matched_efficiency':base/float(r['seconds_per_iteration']),'reference_cores':4,'reference_summary':rows[0]['source_summary']})
    cores_per_node={c:sum(r['context']=='cpu_node' and int(r['active_cpu_threads'])//int(r['host_nodes'])==c for r in fixed)//45 for c in (1,2,4,8,16,32)}
    assert sum(cores_per_node.values())==397
    packing=[]
    for m,p,t in (('MPI',32,1),('MPI+OpenMP',8,4),('MPI+Kokkos OpenMP',8,4)):
        for mode in MODES:
            for n in (1,2,4,8):
                rr=[lookup[g,'cpu_node',m,n,p,t,mode] for g in graphs]
                packing.append(dict(method=m,communication=mode,nodes=n,processes=p,threads=t,cores_per_node=32//n,
                                    graphs=45,time_geomean_s=gm([float(r['solve_median_s']) for r in rr])))
    endpoint_fronts=[]
    for g in graphs:
        candidates=endpoint_candidates(fixed,g);assert len(candidates)==26
        assert len({r['iterations'] for r in candidates})==1
        frontier=pareto_rows(candidates)
        endpoint_fronts.append(dict(graph=g,options=26,frontier=[dict(method=r['method'],processes=int(r['processes']),threads=int(r['threads']),communication=r['communication'],
                                   time_s=float(r['solve_median_s']),iteration_ms=1000*float(r['seconds_per_iteration']),global_payload_mb=float(r['communication_bytes_per_iteration'])/1e6) for r in frontier]))
    return dict(thread_splits=thread,node_placement=placement,halo=halo,gpu_scaling=gpu,backend=backend,standalone_device=standalone,ordinary_cpu_configs_per_graph_by_node_cores=cores_per_node,packing_c32=packing,endpoint_frontiers=endpoint_fronts,
                comparisons_count_all_thread_layouts=sum(r['all_layouts']['pairs'] for r in thread),
                comparisons_count_common_thread_layouts=len(common),
                rules='Ratios compare stored five-run medians. Same graph and stated controls; descriptive, not significance tests.'),common,extra


def save_analysis(data,fixed,weak):
    result,common,extra=comparisons(fixed,weak)
    (data/'comparative_analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    with (data/'thread_split_matched_all_graphs.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(common[0]),lineterminator='\n');writer.writeheader();writer.writerows(common)
    return result,common,extra


def thread_figure(rows):
    """Five thread groups and a matched-layout matrix, 2 columns x 3 rows."""
    from reportlab.graphics.shapes import Drawing,String,Line,Rect,Circle
    from reportlab.lib import colors
    from reportlab.pdfbase.pdfmetrics import stringWidth
    d=Drawing(500,660);ink=colors.HexColor('#172c3c');green=colors.HexColor('#218671')
    specs=[('MPI+OpenMP','Allgatherv','#d07a2b',False),('MPI+OpenMP','Halo','#d07a2b',True),
           ('MPI+Kokkos OpenMP','Allgatherv','#218671',False),('MPI+Kokkos OpenMP','Halo','#218671',True)]
    aggregate={}
    for t in THREADS:
        for m,mode,color,dash in specs:
            for c in (32,64,128,256):
                rr=[r for r in rows if r['threads']==t and r['method']==m and r['communication']==mode and r['cores']==c]
                assert len(rr)==45
                aggregate[t,m,mode,c]=(gm([r['gain'] for r in rr]),gm([r['tested_time_s'] for r in rr]))
    all_y=[v[0] for v in aggregate.values()];ymin=min(.85,min(all_y)*.85);ymax=max(all_y)*1.25
    for panel,t in enumerate(THREADS):
        x0=(panel%2)*250;top=654-(panel//2)*218;left=x0+31;right=x0+237;bottom=top-161;upper=top-30
        def x(c):return left+math.log2(c/32)/3*(right-left)
        def y(v):return bottom+math.log(v/ymin)/math.log(ymax/ymin)*(upper-bottom)
        d.add(String(x0+125,top-8,f'T={t}: p=C/{t}',fontName='Helvetica-Bold',fontSize=9,textAnchor='middle',fillColor=ink))
        d.add(String(left,top-21,'Gain versus same C,n at T=1 (x)',fontName='Helvetica',fontSize=6.4,fillColor=ink))
        for value in (1,2,4,8,16):
            if not ymin<=value<=ymax:continue
            yy=y(value);d.add(Line(left,yy,right,yy,strokeColor=colors.HexColor('#dce2e7'),strokeWidth=.4))
            d.add(String(left-4,yy-2,str(value),fontName='Helvetica',fontSize=6.5,textAnchor='end',fillColor=ink))
        for c in (32,64,128,256):d.add(String(x(c),bottom-11,str(c),fontName='Helvetica',fontSize=6.5,textAnchor='middle',fillColor=ink))
        columns=defaultdict(list)
        for j,(m,mode,color,dash) in enumerate(specs):
            color=colors.HexColor(color);previous=None
            for c in (32,64,128,256):
                value,seconds=aggregate[t,m,mode,c];xx,yy=x(c),y(value)
                fastest=min(aggregate[t,mm,md,c][1] for mm,md,_,_ in specs)
                if seconds==fastest:d.add(Circle(xx,yy,3.5,fillColor=None,strokeColor=green,strokeWidth=1))
                if previous:d.add(Line(*previous,xx,yy,strokeColor=color,strokeWidth=1,strokeDashArray=[3,2] if dash else None))
                d.add(Circle(xx,yy,1.8,fillColor=color,strokeColor=None));previous=(xx,yy)
                label=('H' if dash else 'A')+f'{seconds*1000:.3g}'
                columns[c].append((yy,j,label,color,value))
        for c,values in columns.items():
            values.sort();ys=[]
            for yy,*_ in values:ys.append(max(yy+3,bottom+3 if not ys else ys[-1]+7))
            shift=max(0,ys[-1]-(upper-1));ys=[v-shift for v in ys]
            for (yy,j,label,color,value),ly in zip(values,ys):
                xx=x(c);w=stringWidth(label,'Helvetica',5.5);lx=max(left+w/2,min(xx,right-w/2))
                d.add(Line(xx,yy,lx,ly,strokeColor=color,strokeWidth=.25))
                d.add(Rect(lx-w/2-1,ly-1,w+2,7,fillColor=colors.white,strokeColor=None))
                d.add(String(lx,ly,label,fontName='Helvetica',fontSize=5.5,textAnchor='middle',fillColor=color))
        d.add(String(x0+125,bottom-23,'Active CPU cores C (log)',fontName='Helvetica',fontSize=6.5,textAnchor='middle',fillColor=ink))
        for j,(m,mode,col,dash) in enumerate(specs):
            xx=x0+5+(j%2)*122;yy=top-200-(j//2)*9
            d.add(Line(xx,yy+2,xx+12,yy+2,strokeColor=colors.HexColor(col),strokeWidth=1,strokeDashArray=[3,2] if dash else None))
            label=('MPI+OMP ' if m==METHODS[0] else 'MPI+KK OMP ')+('H' if dash else 'A')
            d.add(String(xx+16,yy,label,fontName='Helvetica',fontSize=6,fillColor=ink))
    left=256;top=211
    for dy,text,size in [(0,'Common matched matrix',9),(17,'All 45 graphs; Q={2,4,8,16,32};',7),(29,'two MPI+CPU methods; all five T choices.',7)]:
        d.add(String(left,top-dy,text,fontName='Helvetica-Bold' if dy==0 else 'Helvetica',fontSize=size,fillColor=ink))
    for j,label in enumerate(('n','C','p','r','T')):d.add(String(left+j*45,top-48,label,fontName='Helvetica-Bold',fontSize=7,fillColor=ink))
    for i,n in enumerate((1,2,4,8)):
        for j,label in enumerate((str(n),str(32*n),'C/T','32/T','Q')):
            d.add(String(left+j*45,top-63-i*16,label,fontName='Helvetica',fontSize=7,fillColor=ink))
    for i,text in enumerate(('3,600 paired ratios; 45 at every point.','Reference: same graph, method, mode, n,C;','p changes as T changes. Labels: time ms','(geometric mean of 45 solve medians).','All other valid layouts: next table + full atlas.')):
        d.add(String(left,top-137-i*11,text,fontName='Helvetica',fontSize=6.6,fillColor=ink))
    return d


def endpoint_candidates(fixed,graph):
    return [r for r in fixed if r['graph']==graph and r['context']=='cpu_node' and r['method'].startswith('MPI')
            and int(r['host_nodes'])==8 and int(r['active_cpu_threads'])==256]


def pareto_rows(rows):
    def dominates(a,b):
        x,y=float(a['solve_median_s']),float(a['communication_bytes_per_iteration'])
        u,v=float(b['solve_median_s']),float(b['communication_bytes_per_iteration'])
        return x<=u and y<=v and (x<u or y<v)
    return [r for r in rows if not any(dominates(other,r) for other in rows if other is not r)]


def growing_figure(rows,fixed):
    """Independent questions: measured growth timing versus all-T endpoint time/payload."""
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.charts.axes import LogXValueAxis,LogYValueAxis
    from reportlab.graphics.shapes import Drawing,String,Line,Circle
    from reportlab.graphics.widgets.markers import makeMarker
    from reportlab.lib import colors
    d=Drawing(500,665);ink=colors.HexColor('#172c3c');green=colors.HexColor('#218671')
    specs=[('MPI',1,'#16679b','MPI T=1'),('MPI+OpenMP',4,'#d07a2b','MPI+OpenMP T=4'),
           ('MPI+Kokkos OpenMP',1,'#865ba3','MPI+Kokkos OpenMP T=1'),('MPI+Kokkos OpenMP',4,'#218671','MPI+Kokkos OpenMP T=4')]
    shapes={1:('FilledCircle',0),2:('FilledSquare',0),4:('FilledDiamond',0),8:('FilledTriangle',0),16:('FilledTriangle',180),32:('StarFive',0)}
    method_colors={'MPI':'#16679b','MPI+OpenMP':'#d07a2b','MPI+Kokkos OpenMP':'#865ba3'}
    endpoints=[r for family in ('uniform','hub','controlled') for r in endpoint_candidates(fixed,'strong_'+family)]
    yvals=[1000*float(r['seconds_per_iteration']) for r in endpoints]
    ymin=min(yvals)*.75;ymax=max(yvals)*1.3
    for i,family in enumerate(('uniform','hub','controlled')):
        top=657-i*193
        lp=LinePlot();lp.x=38;lp.y=top-150;lp.width=198;lp.height=112
        lp.xValueAxis=LogXValueAxis();lp.yValueAxis=LogYValueAxis()
        lp.xValueAxis.valueSteps=[4,16,64,256];lp.xValueAxis.labelTextFormat=lambda v:f'{v:g}'
        lp.yValueAxis.valueMin=1;lp.yValueAxis.valueMax=1000;lp.yValueAxis.valueSteps=[1,10,100,1000]
        lp.yValueAxis.labelTextFormat=lambda v:f'{v:g}'
        for axis in (lp.xValueAxis,lp.yValueAxis):
            axis.labels.fontSize=6.8;axis.labels.fontName='Helvetica';axis.visibleGrid=True
            axis.gridStrokeColor=colors.HexColor('#e1e6e9');axis.gridStrokeWidth=.35;axis.strokeColor=colors.HexColor('#9da8b0')
        lp.data=[];styles=[]
        for m,t,col,label in specs:
            for mode in MODES:
                rr=sorted([r for r in rows if r['family']==family and r['method']==m and int(r['threads'])==t and r['communication']==mode],key=lambda r:int(r['active_cpu_threads']));assert len(rr)==7
                lp.data.append([(int(r['active_cpu_threads']),1000*float(r['seconds_per_iteration'])) for r in rr]);styles.append((col,mode))
        for k,(col,mode) in enumerate(styles):
            c=colors.HexColor(col);lp.lines[k].strokeColor=c;lp.lines[k].strokeWidth=1
            lp.lines[k].strokeDashArray=[3,2] if mode=='Halo' else None
            marker=makeMarker('FilledCircle');marker.size=2.6;marker.fillColor=c;lp.lines[k].symbol=marker
        d.add(lp);lp.draw()
        for k in range(7):
            best=min(series[k][1] for series in lp.data)
            for z,series in enumerate(lp.data):
                if series[k][1]==best:
                    xx,yy=lp._positions[z][k];d.add(Circle(xx,yy,3,fillColor=None,strokeColor=green,strokeWidth=.8))
        d.add(String(125,top-8,'Growth: '+family.title(),fontName='Helvetica-Bold',fontSize=9,textAnchor='middle',fillColor=ink))
        d.add(String(38,top-24,'Iteration time (ms/iteration)',fontName='Helvetica',fontSize=7,fillColor=ink))
        d.add(String(125,top-168,'Active CPU cores C (count, log)',fontName='Helvetica',fontSize=7,textAnchor='middle',fillColor=ink))
        # All 26 CPU options at the same input, n=8 and C=256; no growth inference from these points.
        left=289;right=488;bottom=top-150;upper=top-38
        def x(value):return left+math.log(value/200)/math.log(40000/200)*(right-left)
        def y(value):return bottom+math.log(value/ymin)/math.log(ymax/ymin)*(upper-bottom)
        for v in (300,1000,3000,10000,30000):
            xx=x(v);d.add(Line(xx,bottom,xx,upper,strokeColor=colors.HexColor('#e1e6e9'),strokeWidth=.35))
            d.add(String(xx,bottom-10,f'{v/1000:g}k' if v>=1000 else str(v),fontName='Helvetica',fontSize=6.5,textAnchor='middle',fillColor=ink))
        for v in (10,30,100,300,1000,3000):
            if not ymin<=v<=ymax:continue
            yy=y(v);d.add(Line(left,yy,right,yy,strokeColor=colors.HexColor('#e1e6e9'),strokeWidth=.35))
            d.add(String(left-4,yy-2,str(v),fontName='Helvetica',fontSize=6.5,textAnchor='end',fillColor=ink))
        rr=endpoint_candidates(fixed,'strong_'+family);front=pareto_rows(rr)
        ordered=sorted(front,key=lambda r:float(r['communication_bytes_per_iteration']))
        for a,b in zip(ordered,ordered[1:]):
            d.add(Line(x(float(a['communication_bytes_per_iteration'])/1e6),y(1000*float(a['seconds_per_iteration'])),x(float(b['communication_bytes_per_iteration'])/1e6),y(1000*float(b['seconds_per_iteration'])),strokeColor=green,strokeWidth=.9))
        for r in rr:
            xx=x(float(r['communication_bytes_per_iteration'])/1e6);yy=y(1000*float(r['seconds_per_iteration']))
            kind,angle=shapes[int(r['threads'])];m=makeMarker(kind);m.x=xx;m.y=yy;m.angle=angle;m.size=4
            m.strokeColor=colors.HexColor(method_colors[r['method']]);m.fillColor=m.strokeColor if r['communication']=='Allgatherv' else colors.white;m.strokeWidth=.7
            d.add(m)
            if r in front:d.add(Circle(xx,yy,4.2,fillColor=None,strokeColor=green,strokeWidth=.9))
        d.add(String(375,top-8,'Fixed C=256 endpoint: '+family.title(),fontName='Helvetica-Bold',fontSize=8.5,textAnchor='middle',fillColor=ink))
        d.add(String(289,top-24,'Iteration time (ms/iteration)',fontName='Helvetica',fontSize=7,fillColor=ink))
        d.add(String(375,top-168,'Global payload (MB/iteration, log)',fontName='Helvetica',fontSize=7,textAnchor='middle',fillColor=ink))
    for i,(m,t,col,label) in enumerate(specs):
        xx=5;yy=72-i*12;c=colors.HexColor(col)
        d.add(Line(xx,yy+2,xx+10,yy+2,strokeColor=c,strokeWidth=1.2))
        d.add(String(xx+12,yy,'A',fontName='Helvetica-Bold',fontSize=6.2,fillColor=ink))
        d.add(Line(xx+23,yy+2,xx+33,yy+2,strokeColor=c,strokeWidth=1.2,strokeDashArray=[3,2]))
        d.add(String(xx+35,yy,'H',fontName='Helvetica-Bold',fontSize=6.2,fillColor=ink))
        d.add(String(xx+47,yy,label,fontName='Helvetica',fontSize=6.5,fillColor=ink))
    d.add(String(5,11,'A=Allgatherv; H=Halo. 4 settings × 2 = 8 curves/family; green=fastest.',fontName='Helvetica',fontSize=5.4,fillColor=ink))
    for i,(m,label) in enumerate((('MPI','MPI'),('MPI+OpenMP','MPI+OpenMP'),('MPI+Kokkos OpenMP','MPI+Kokkos OpenMP'))):
        d.add(String(257,73-i*12,label,fontName='Helvetica',fontSize=6.7,fillColor=colors.HexColor(method_colors[m])))
    for i,t in enumerate((1,2,4,8,16,32)):
        xx=262+i*39;kind,angle=shapes[t];m=makeMarker(kind);m.x=xx;m.y=31;m.size=4.5;m.angle=angle;m.fillColor=ink;m.strokeColor=ink;d.add(m)
        d.add(String(xx+6,29,'T'+str(t),fontName='Helvetica',fontSize=6.4,fillColor=ink))
    d.add(String(257,11,'26 options/family (2+12+12); filled=A/open=H; green=Pareto.',fontName='Helvetica',fontSize=5.4,fillColor=ink))
    return d
