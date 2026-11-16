"""Create the four-section report and vector figures from audited CSV tables.

Run analyze_report_results.py first. Uses ReportLab Graphics for scientific
line/bar plots and Platypus for the PDF. PNG previews use Poppler, when supplied
with --pdftoppm. No solver is run and no raw result is changed.
"""
import argparse
import csv
import html
import json
import math
from pathlib import Path
import statistics as stats
import subprocess

from reportlab.graphics import renderPDF
from reportlab.graphics.charts.axes import LogXValueAxis, LogYValueAxis
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Line, Rect, String, Group
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                               TableStyle, PageBreak, KeepTogether)

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/non512'
DATA = REPORT / 'data'
FIG = REPORT / 'figures'
PDF = ROOT / 'output/pdf/pagerank_non512_report.pdf'
BLUE = colors.HexColor('#16679b')
TEAL = colors.HexColor('#218671')
ORANGE = colors.HexColor('#d07a2b')
PURPLE = colors.HexColor('#865ba3')
GRAY = colors.HexColor('#6a7480')
INK = colors.HexColor('#172c3c')
FIXED = list(csv.DictReader((DATA / 'fixed_results_19530.csv').open()))
WEAK = list(csv.DictReader((DATA / 'weak_results_372.csv').open()))
GRAPHS = list(csv.DictReader((DATA / 'graphs_45.csv').open()))
MATRIX = list(csv.DictReader((DATA / 'runtime_matrix_45.csv').open()))
SUPPLEMENT = list(csv.DictReader((DATA / 'supplement_512.csv').open()))
HALO = list(csv.DictReader((DATA / 'halo_summary.csv').open()))
SPLITS = list(csv.DictReader((DATA / 'split_summary.csv').open()))
AUDIT = json.loads((DATA / 'audit.json').read_text())
GOOGLE = json.loads((DATA / 'google_insights.json').read_text())
REPRESENTATIVE = ('google', 'uniform', 'hub', 'strong_uniform', 'strong_hub', 'strong_controlled')
DISPLAY = {'google':'Google','uniform':'Original uniform','hub':'Original hub',
           'strong_uniform':'Large uniform','strong_hub':'Large hub',
           'strong_controlled':'Large controlled'}


def number(value):
    return float(value)


def fmt(value):
    return f'{float(value):.3g}'


def get(graph, method, context='cpu_node', **where):
    selected = [r for r in FIXED if r['graph']==graph and r['method']==method and r['context']==context
                and all(str(r[k])==str(v) for k,v in where.items())]
    assert len(selected)==1, (graph,method,context,where,len(selected))
    return selected[0]


def legend(drawing, labels, palette, dashed=None, columns=4, y=18):
    dashed = dashed or [False]*len(labels)
    width = drawing.width/columns
    for i,(text,color,dash) in enumerate(zip(labels,palette,dashed)):
        x = i%columns*width+7; yy=y-(i//columns)*12
        drawing.add(Line(x,yy+2,x+14,yy+2,strokeColor=color,strokeWidth=1.5,
                         strokeDashArray=[3,2] if dash else None))
        drawing.add(String(x+19,yy,text,fontName='Helvetica',fontSize=7,fillColor=INK))


def line_panels(titles, series, x_label, y_label, x_steps, log_x=True,
                log_y=True, x_format=None, y_format=None, height=255):
    drawing = Drawing(500,height)
    width=500/len(titles)
    for i,title in enumerate(titles):
        lp=LinePlot();lp.x=i*width+40;lp.y=57;lp.width=width-51;lp.height=height-100
        lp.data=[points for _,points,_,_ in series[i]]
        if log_x:lp.xValueAxis=LogXValueAxis()
        if log_y:lp.yValueAxis=LogYValueAxis()
        for axis in (lp.xValueAxis,lp.yValueAxis):
            axis.labels.fontName='Helvetica';axis.labels.fontSize=6.8
            axis.strokeColor=colors.HexColor('#9da8b0')
            axis.visibleGrid=True;axis.gridStrokeColor=colors.HexColor('#e1e6e9');axis.gridStrokeWidth=.35
        lp.xValueAxis.valueSteps=x_steps
        lp.xValueAxis.labelTextFormat=x_format or (lambda v:f'{v:g}')
        if y_format:lp.yValueAxis.labelTextFormat=y_format
        if not log_y:lp.yValueAxis.valueMin=0
        for j,(_,points,color,dash) in enumerate(series[i]):
            lp.lines[j].strokeColor=color;lp.lines[j].strokeWidth=1.25
            lp.lines[j].strokeDashArray=[3,2] if dash else None
            marker=makeMarker('FilledCircle');marker.size=3;marker.fillColor=color
            lp.lines[j].symbol=marker
        drawing.add(lp)
        drawing.add(String(i*width+width/2,height-15,title,fontName='Helvetica-Bold',fontSize=9,textAnchor='middle',fillColor=INK))
        drawing.add(String(i*width+40,height-30,y_label,fontName='Helvetica',fontSize=7,fillColor=GRAY))
        drawing.add(String(i*width+width/2,35,x_label,fontName='Helvetica',fontSize=7,textAnchor='middle',fillColor=GRAY))
    labels=[x[0] for x in series[0]]
    legend(drawing,labels,[x[2] for x in series[0]],[x[3] for x in series[0]],columns=min(4,len(labels)))
    return drawing


def abbreviated(graph):
    if graph in DISPLAY:return DISPLAY[graph].replace('Original ','o. ').replace('Large ','12.8M ')
    parts=graph.split('_')
    if graph.startswith('synthetic_'):return 's. '+parts[1]
    return f'{parts[1][0].upper()} {int(parts[2][1:])//1000}k/{parts[3][1:]}'


def figures():
    result={}
    serial=[]
    for family in ('uniform','hub','controlled'):
        curves=[]
        for degree,color in zip((4,8,16),(BLUE,ORANGE,TEAL)):
            rows=[r for r in FIXED if r['context']=='cpu_node' and r['method']=='Serial'
                  and r['graph'].startswith(f'grid_{family}_') and int(r['edges'])==degree*int(r['vertices'])]
            points=sorted((int(r['vertices']),number(r['solve_median_s'])) for r in rows)
            curves.append((f'd={degree}',points,color,False))
        serial.append(curves)
    result['01_serial_grid']=line_panels(['Uniform','Hub','Controlled'],serial,'Vertices','Solve time (s)',
                                        [50000,100000,200000,400000],x_format=lambda v:f'{v/1000:g}k')
    for name,graphs in [('02_strong_original',REPRESENTATIVE[:3]),('03_strong_large',REPRESENTATIVE[3:])]:
        panels=[]
        for graph in graphs:
            curves=[]
            for method,label,color,t in [('MPI','MPI',BLUE,1),('MPI+OpenMP','M+OMP',ORANGE,4),
                                         ('MPI+Kokkos OpenMP','M+KK',TEAL,4)]:
                for mode in ('Allgatherv','Halo'):
                    points=[]
                    for c in (4,8,16,32,64,128,256):
                        row=get(graph,method,host_nodes=max(1,c//32),processes=c//t,threads=t,communication=mode)
                        points.append((c,number(row['speedup_vs_matched_serial'])))
                    curves.append((label+(' A' if mode=='Allgatherv' else ' H'),points,color,mode=='Halo'))
            panels.append(curves)
        result[name]=line_panels([DISPLAY[g] for g in graphs],panels,'Active CPU cores','Speedup vs Serial',[4,16,64,256])
    series=[]
    for method,label,color in [('MPI+OpenMP','M+OMP',ORANGE),('MPI+Kokkos OpenMP','M+KK',TEAL)]:
        for mode in ('Allgatherv','Halo'):
            rows=[r for r in SPLITS if r['method']==method and r['communication']==mode]
            series.append((label+(' A' if mode=='Allgatherv' else ' H'),
                           [(int(r['threads']),number(r['geomean_speedup_vs_T1'])) for r in rows],color,mode=='Halo'))
    result['04_fixed_256_splits']=line_panels(['Fixed 256 cores across all 45 graphs'],[series],
        'Threads per rank T (p=256/T)','Geomean speedup relative to T=1',[1,2,4,8,16,32])
    d=Drawing(500,245)
    for j,(key,title) in enumerate([('geomean_halo_speedup','Matched Halo speedup'),
                                     ('median_payload_reduction','Median payload reduction')]):
        bar=VerticalBarChart();bar.x=j*250+35;bar.y=49;bar.width=205;bar.height=150
        bar.data=[[number(next(r for r in HALO if r['context']==ctx and r['family']==f)[key])
                   for f in ('google','uniform','hub','controlled')] for ctx in ('cpu_node','gpu_node')]
        bar.categoryAxis.categoryNames=['Google','Uniform','Hub','Ctrl']
        bar.categoryAxis.labels.fontSize=7;bar.valueAxis.labels.fontSize=7
        bar.valueAxis.valueMin=0;bar.bars[0].fillColor=BLUE;bar.bars[1].fillColor=ORANGE
        bar.bars.strokeWidth=0;bar.valueAxis.visibleGrid=True;bar.valueAxis.gridStrokeColor=colors.HexColor('#e1e6e9')
        if j:bar.valueAxis.labelTextFormat=lambda v:f'{v:.0%}'
        d.add(bar);d.add(String(j*250+125,224,title,fontName='Helvetica-Bold',fontSize=9,textAnchor='middle',fillColor=INK))
    legend(d,['CPU matrix','GPU-node matrix'],[BLUE,ORANGE],columns=2,y=14)
    result['05_halo_pairs']=d
    panels=[]
    for graph in REPRESENTATIVE[3:]:
        curves=[]
        for method,label,color in [('MPI','CPU MPI',GRAY),('MPI+OpenMP','CPU M+OMP',PURPLE),
                                   ('MPI+CUDA','M+CUDA',ORANGE),('MPI+Kokkos CUDA','M+KK Cuda',TEAL)]:
            for mode in ('Allgatherv','Halo'):
                one=get(graph,method,'gpu_node',processes=1,threads=1,communication=mode)
                two=get(graph,method,'gpu_node',processes=2,threads=1,communication=mode)
                curves.append((label+(' A' if mode=='Allgatherv' else ' H'),
                               [(1,1),(2,number(one['solve_median_s'])/number(two['solve_median_s']))],color,mode=='Halo'))
        panels.append(curves)
    result['06_gpu_node_scaling']=line_panels([DISPLAY[g] for g in REPRESENTATIVE[3:]],panels,
        'Node count','Speedup relative to own p=1',[1,2],False,False,height=265)
    panels=[]
    for family in ('uniform','hub','controlled'):
        curves=[]
        for method,label,color in [('MPI+OpenMP','M+OMP',ORANGE),('MPI+Kokkos OpenMP','M+KK',TEAL)]:
            for mode in ('Allgatherv','Halo'):
                rows=[r for r in WEAK if r['suite']=='core_cpu' and r['family']==family and r['method']==method and r['communication']==mode]
                curves.append((label+(' A' if mode=='Allgatherv' else ' H'),
                               sorted((int(r['active_cpu_threads']),number(r['weak_efficiency_per_iteration'])) for r in rows),color,mode=='Halo'))
        panels.append(curves)
    result['07_core_weak']=line_panels(['Uniform','Hub','Controlled'],panels,'Active CPU cores',
        'Per-iteration weak efficiency',[4,16,64,256],y_format=lambda v:f'{v:.1%}')
    lower=result['07_core_weak'];upper_panels=[]
    for family in ['uniform','hub','controlled']:
        series=[]
        for mode,c in [('Allgatherv',BLUE),('Halo',ORANGE)]:
            values=[r for r in WEAK if r['suite']=='rank_cpu_regular' and r['method']=='MPI' and r['family']==family and r['communication']==mode]
            series.append((mode,sorted((int(r['active_cpu_threads']),number(r['weak_efficiency_per_iteration'])) for r in values),c,mode=='Halo'))
        upper_panels.append(series)
    upper=line_panels(['Uniform','Hub','Controlled'],upper_panels,'Active CPU cores',
        'Per-iteration weak efficiency',[1,4,16,64,256],y_format=lambda v:f'{v:.1%}')
    combined=Drawing(500,550)
    g=Group(*upper.contents);g.translate(0,275);combined.add(g)
    combined.add(Group(*lower.contents))
    combined.add(String(250,540,'Pure MPI: rank-normalized weak scaling',fontName='Helvetica-Bold',fontSize=10,textAnchor='middle',fillColor=INK))
    combined.add(String(250,265,'Hybrid methods: core-normalized weak scaling',fontName='Helvetica-Bold',fontSize=10,textAnchor='middle',fillColor=INK))
    result['07_core_weak']=combined

    cases=[];names=[]
    for method,label in [('MPI+CUDA','CU'),('MPI+Kokkos CUDA','KK')]:
        for p in (1,2):
            for mode in ('Allgatherv','Halo'):
                cases.append(get('strong_controlled',method,'gpu_node',processes=p,communication=mode))
                names.append(f'{label}{p}'+('A' if mode=='Allgatherv' else 'H'))
    phase=[]
    for label,key,c in [('Solve','solve_median_s',INK),('Backend compute','compute_median_s',BLUE),
                        ('Host/device staging','transfer_median_s',ORANGE),('MPI communication','communication_median_s',TEAL)]:
        phase.append((label,[(i+1,number(r[key])) for i,r in enumerate(cases)],c,False))
    phase_drawing=line_panels(['Large controlled graph: solve and phase diagnostics'],[phase],
        'Implementation / rank count / communication','Time (s)',list(range(1,9)),False,True,
        x_format=lambda x:names[int(x)-1],y_format=lambda x:f'{x:g}')
    for item in phase_drawing.contents:
        if isinstance(item,LinePlot):
            item.yValueAxis.valueMin=.08;item.yValueAxis.valueMax=4
            item.yValueAxis.valueSteps=[.1,.2,.5,1,2,4]
            for j in range(4):item.lines[j].strokeColor=None
    result['08_gpu_phases']=phase_drawing
    d=Drawing(500,650);headers=['OMP','KK-OMP','MPI','M+OMP','M+KK','CUDA','KK-CU','M+CU','M+KKCU']
    methods=['OpenMP','Kokkos OpenMP','MPI','MPI+OpenMP','MPI+Kokkos OpenMP','CUDA','Kokkos CUDA','MPI+CUDA','MPI+Kokkos CUDA']
    cellw=44;cellh=12.1;x0=91;y0=591
    for j,label in enumerate(headers):d.add(String(x0+(j+.5)*cellw,611,label,fontName='Helvetica-Bold',fontSize=7,textAnchor='middle',fillColor=INK))
    d.add(String(210,635,'CPU node controls',fontName='Helvetica',fontSize=8,textAnchor='middle',fillColor=GRAY))
    d.add(String(400,635,'GPU node controls',fontName='Helvetica',fontSize=8,textAnchor='middle',fillColor=GRAY))
    for i,row in enumerate(MATRIX):
        y=y0-i*cellh;d.add(String(x0-6,y+3,abbreviated(row['graph']),fontName='Helvetica',fontSize=7,textAnchor='end',fillColor=INK))
        for j,method in enumerate(methods):
            context='cpu_node' if j<5 else 'gpu_node'
            baseline=get(row['graph'],'Serial',context)['solve_median_s']
            value=number(baseline)/number(row[method+'_best_s']);v=math.log2(value)
            if v>=0:
                t=min(v/6,1);c=colors.Color(1-t*.90,1-t*.55,1-t*.38)
            else:
                t=min(-v/4,1);c=colors.Color(1-t*.07,1-t*.50,1-t*.74)
            d.add(Rect(x0+j*cellw,y,cellw-1,cellh-1,fillColor=c,strokeColor=None))
    d.add(Line(x0+5*cellw-1,48,x0+5*cellw-1,606,strokeColor=GRAY,strokeWidth=.7))
    for j,(label,c) in enumerate([('<=1/16x',colors.Color(.93,.50,.26)),('1x',colors.white),('>=64x',colors.Color(.1,.45,.62))]):
        d.add(Rect(105+j*130,20,17,9,fillColor=c,strokeColor=GRAY,strokeWidth=.3));d.add(String(127+j*130,20,label,fontSize=7,fillColor=INK))
    result['09_runtime_matrix']=d
    return result


def write_figures(items, pdftoppm):
    FIG.mkdir(parents=True,exist_ok=True)
    for name,d in items.items():
        renderPDF.drawToFile(d,str(FIG/(name+'.pdf')))
        if pdftoppm:
            subprocess.run([pdftoppm,'-r','160','-png','-singlefile',str(FIG/(name+'.pdf')),str(FIG/name)],check=True,
                           stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)


def report(items):
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyReport',fontName='Times-Roman',fontSize=10.3,leading=13.5,spaceAfter=7,textColor=INK))
    styles.add(ParagraphStyle(name='SectionReport',fontName='Helvetica-Bold',fontSize=16,leading=20,spaceBefore=16,spaceAfter=10,textColor=INK,keepWithNext=True))
    styles.add(ParagraphStyle(name='SubReport',fontName='Helvetica-Bold',fontSize=11.5,leading=15,spaceBefore=11,spaceAfter=7,textColor=BLUE,keepWithNext=True))
    styles.add(ParagraphStyle(name='CaptionReport',fontName='Helvetica',fontSize=8,leading=10.5,spaceAfter=12,textColor=GRAY))
    styles.add(ParagraphStyle(name='ReferenceReport',parent=styles['CaptionReport'],spaceAfter=4))
    styles.add(ParagraphStyle(name='TableReport',fontName='Helvetica',fontSize=8,leading=10,textColor=INK))
    styles.add(ParagraphStyle(name='EquationReport',fontName='Times-Roman',fontSize=10,leading=15,alignment=TA_CENTER,spaceAfter=10,textColor=INK))
    story=[];md=[]
    def para(text):
        md.append(text+'\n');story.append(Paragraph(html.escape(text),styles['BodyReport']))
    def heading(text,level=1):
        md.append('#'*(level+1)+' '+text+'\n');story.append(Paragraph(html.escape(text),styles['SectionReport' if level==1 else 'SubReport']))
    def table(headers,rows,widths=None,small=False):
        md.append('| '+' | '.join(map(str,headers))+' |\n| '+' | '.join(['---']*len(headers))+' |')
        for row in rows:md.append('| '+' | '.join(map(str,row))+' |')
        md.append('')
        fs=7.0 if small else 8
        data=[[Paragraph(html.escape(str(x)),ParagraphStyle('cell',parent=styles['TableReport'],fontSize=fs,leading=fs+2)) for x in row]
              for row in [headers,*rows]]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eff4')),
            ('TEXTCOLOR',(0,0),(-1,0),INK),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LINEBELOW',(0,0),(-1,0),.65,BLUE),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f7f9')]),
            ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
            ('TOPPADDING',(0,0),(-1,-1),3 if not small else 2),('BOTTOMPADDING',(0,0),(-1,-1),3 if not small else 2)]))
        story.extend([KeepTogether([t,Spacer(1,8)])] if len(rows)<=12 else [t,Spacer(1,8)])
    def figure(name,caption):
        md.append(f'![{caption}](figures/{name}.png)\n')
        prefix=[]
        if story and isinstance(story[-1],Paragraph) and story[-1].style.name=='SubReport':
            prefix.append(story.pop())
        story.append(KeepTogether(prefix+[items[name],Paragraph(html.escape(caption),styles['CaptionReport'])]))
    def equation(pdf,markdown):
        story.append(Paragraph(pdf,styles['EquationReport']));md.append(markdown+'\n')

    title='Parallel PageRank on Vanda'
    md.extend(['# '+title,'','Parallel PageRank experiments - 17 November 2026',''])
    story.append(Paragraph(title,ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=25,leading=29,textColor=INK,spaceAfter=10)))
    story.append(Paragraph('DSA5208 Project 3 | 17 November 2026',styles['CaptionReport']))
    author_file=REPORT/'authors.json'
    if author_file.exists():
        authors=json.loads(author_file.read_text())
        for author in authors:para(author['name']+' - '+author['student_id'])
    para('We evaluate synchronous PageRank on 45 directed graphs using Serial, OpenMP, MPI, MPI+OpenMP, native CUDA and Kokkos with OpenMP and CUDA backends. The audited dataset contains 19,530 fixed-graph configurations and 372 separate non-512 weak-suite configurations or controls. All fixed-graph targets in this scope are complete and independently validated. Five available 512-core configurations are presented as a separate, explicitly incomplete supplement. Pending measurements are excluded.')
    heading('1 Introduction to the algorithm and data')
    heading('1.1 PageRank and its relation to PPR',2)
    para('PageRank assigns a probability score to each vertex of a directed graph. A random surfer follows an outgoing edge with probability alpha and otherwise jumps according to a preference vector. Personalized PageRank (PPR) uses a query-specific preference vector. Our implementation uses the uniform preference vector and uniform redistribution of dangling-vertex mass: it is standard PageRank, equivalently the uniform-preference special case of PPR. We do not implement source-specific personalized queries.')
    equation('r<sub>k+1</sub>(v) = (1 - alpha)/N + alpha D<sub>k</sub>/N + alpha sum<sub>u -&gt; v</sub> r<sub>k</sub>(u)/d<sub>out</sub>(u)',
             '$$r_v^{(k+1)}=(1-\\alpha)/N+\\alpha D_k/N+\\alpha\\sum_{u\\to v}r_u^{(k)}/d_{out}(u).$$')
    para('Here D_k is the total score of vertices with zero out-degree. Scores start at 1/N; alpha=0.85; iteration stops when the global L1 change is at most 10^-8, with a cap of 1,000 iterations. All kernels use double precision and synchronous old/new score buffers. The pull formulation traverses incoming-edge CSR rows, avoiding simultaneous writes to a destination. An iteration costs O(N+E) work and O(N+E) storage in serial.')
    para('This is not embarrassingly parallel: each iteration needs remote source contributions, a global dangling-mass reduction, and a global convergence reduction. Unequal incoming-edge counts make equal vertex counts an imperfect proxy for equal work.')
    heading('1.2 Three original graphs and 42 fixed extensions',2)
    table(['Source','Graphs','Vertices N','Directed edges E','Purpose'],[
        ['Original Google','1','875,713','5,105,039','Real web-link graph'],
        ['Original uniform and hub','2','100,000 each','1,000,000 each','Original synthetic controls'],
        ['Canonical extensions','3','100,000','1,000,000','One per generated family'],
        ['Size-density grid','36','50k / 100k / 200k / 400k','N x 4 / 8 / 16','3 families x 4 sizes x 3 densities'],
        ['Large extensions','3','12,800,000','204,800,000','One per generated family'],
        ['Total fixed graphs','45','','','3 original + 42 extensions']], [95,35,107,107,156])
    para('The generated families use seed 5208 and deterministic integer mixing. Uniform spreads destinations across all vertices with fixed source degree. Hub directs approximately 80% of each source\'s edges to the first 1% of vertices. Controlled combines the hub destination pattern with two source-degree classes: 80% lower-degree sources and 20% higher-degree sources. Integer rounding and unique arithmetic progressions determine exact counts. The original uniform/hub files are retained unchanged; they are not interchangeable with the new canonical graphs of the same size.')
    para('Vertex count and average out-degree are crossed systematically, not changed together in a single size parameter. The three large graphs have identical N and E but different structural concentration, making them useful for separating graph size from load imbalance. All 45 fixed graphs are reused unchanged across the full fixed-graph configuration matrix.')
    heading('1.3 Separate weak-scaling inputs',2)
    para('Weak scaling uses the same three generator families with 50,000 vertices and 800,000 edges per scaling unit. Rank-based series grow the graph with p; core-normalized series grow it with C=pT. Across the non-512 weak suites there are 27 distinct graph names. The GPU weak suite also runs standalone methods on both input sizes; these are fixed-resource size controls and are not labeled as resource-scaled weak-efficiency curves.')

    heading('2 Methodology')
    heading('2.1 Parallel implementations and design decisions',2)
    table(['Implementation','Compute and work distribution','MPI communication'],[
        ['Serial','One CPU thread; incoming CSR pull','None'],
        ['OpenMP','CPU threads; dynamic vertex schedule, chunk 64','None'],
        ['Kokkos OpenMP','CPU execution space; RangePolicy and parallel reductions','None'],
        ['CUDA / Kokkos CUDA','One GPU; incoming-row vertex kernels','None'],
        ['MPI','Contiguous destination partitions; one CPU thread/rank','Both modes'],
        ['MPI+OpenMP','Same MPI partitions; threaded pull within each rank','Both modes; MPI_THREAD_FUNNELED'],
        ['MPI+CUDA','One GPU/rank; host buffers between device and MPI','Both modes'],
        ['MPI+Kokkos','Shared distributed driver; OpenMP or CUDA execution space','Both modes']], [105,280,115])
    para('MPI partitions consecutive dense vertex IDs approximately equally. Each rank owns incoming rows and out-degrees for its vertices. Allgatherv replicates the complete vector of source contributions at every rank each iteration. Halo precomputes distinct remote source IDs, exchanges request metadata once, and then sends only requested values with Alltoallv. Both modes retain dangling-mass and convergence Allreduce calls. Halo is an exact dependency exchange, not approximate communication or dropped edges.')
    para('The counted per-iteration payload is the algorithm-level contribution-vector traffic, excluding collective implementation details, reduction traffic, and protocol overhead. Allgatherv counts 8N(p-1) aggregate bytes; Halo counts eight bytes per requested remote contribution. Metadata setup is recorded separately and lies outside solve time. Fewer counted bytes therefore need not imply lower measured latency.')
    para('The distributed device implementations stage contributions through host memory; they do not use CUDA-aware MPI or overlap communication with computation. The CUDA version uses 256-thread blocks and explicit kernels. Kokkos expresses comparable operations through Views, parallel_for/parallel_reduce and execution-space fences. Kokkos OpenMP and CUDA are two backends, not interchangeable hardware measurements.')
    heading('2.2 Hardware, software and timing protocol',2)
    para('All reported measurements are from NUS Vanda. CPU comparisons use Intel Xeon Platinum 8452Y hosts, GCC 13.3.0, Open MPI 4.1.8 and Release builds. GPU comparisons use NVIDIA A40 nodes with Platinum 8452Y CPUs; archived build metadata identifies CUDA toolkit 12.4.1. Driver-reported CUDA compatibility is not treated as the compiler toolkit version. Original laptop and mixed-hardware exploratory measurements are excluded.')
    para('Every configuration has one warm-up followed by five timed runs. All primary solve-time tables and figures report the median of those five timed runs. The exported statistic solve_median_s is recomputed here from the five original solve_s observations. MPI solve time is the maximum elapsed solver time across ranks. Graph input, partition distribution, backend construction and Halo setup are outside solve time; per-iteration MPI and host/device staging are inside the distributed solve. Standalone GPU setup and final rank copies are outside solve time. These are solver-time comparisons, not end-to-end application runtimes.')
    para('OpenMP creates its persistent thread team inside the timed solver, while Kokkos runtime initialization precedes solver timing. These boundaries follow the recorded solve_s metric and should be considered when interpreting very small graph runtimes.')
    para('Twelve low-core MPI+Kokkos configurations use the recorded compact_setup initialization: redundant root edge storage is released after distribution, and replaced Halo edge IDs are released before backend allocation. The measured update/communication loop is unchanged; these configurations are flagged in the exported table. No recompiled variant is substituted silently into an existing measurement.')
    heading('2.3 Fixed-graph configuration matrix',2)
    table(['Experiment','Node / rank / thread layout','45-graph targets'],[
        ['Serial CPU','n=1, p=1, T=1','45'],
        ['OpenMP; Kokkos OpenMP','n=1,p=1; T=1,2,4,8,16,32','270 each'],
        ['MPI CPU','n=1,2,4,8; r=1,2,4,8,16,32; p=nr,T=1; two modes','2,160'],
        ['MPI+OpenMP CPU','Same n,r; T=1,2,4,8,16,32 with rT<=32; two modes','7,560'],
        ['MPI+Kokkos OpenMP CPU','Same 84 layouts and two modes','7,560'],
        ['Standalone CUDA; Kokkos CUDA','n=1, one GPU','45 each'],
        ['MPI+CUDA; MPI+Kokkos CUDA','n=p=1,2; one rank/GPU/node; two modes','180 each'],
        ['GPU-node CPU controls','Serial45; OpenMP270; MPI180; hybrid720','1,215'],
        ['Complete main matrix','','19,530'],
        ['Partial CPU 512 supplement','n=8, 64 cores/node; available p/T and modes only','5 / 1,170']], [122,301,77])
    para('For CPU configurations the active core budget is C=pT=n(rT). The matrix contains 24 pure-MPI layouts and 84 layouts for each CPU hybrid method; every MPI layout is paired across communication modes. The main full-per-node strong-scaling line uses C=32/64/128/256 on n=1/2/4/8 nodes. Lower-core points use one node. At a fixed C, hybrid methods test every legal T from the six-value set with p=C/T; a larger allocation is not counted as higher parallelism unless pT increases. The full table also contains other node layouts at equal C.')
    para('On GPU nodes the CPU-only MPI and OpenMP variants are controls on the same node layout, not GPU implementations. Distributed GPU comparisons use p=1 or 2 with one GPU per rank. The GPU scope is one or two A40 devices. The 512-core fixed-graph supplement contains five validated configurations on one graph; its missing combinations are not used to construct a complete scaling curve. Weak-scaling comparisons here stop at 256 CPU cores.')
    heading('2.4 Strong scaling, weak scaling and aggregation',2)
    equation('S(C) = T<sub>serial</sub>/T(C), &nbsp;&nbsp; E(C) = S(C)/C',
             '$$S(C)=T_{serial}/T(C),\\qquad E(C)=S(C)/C.$$')
    para('Strong scaling holds the graph fixed and increases active resources. We also hold C=256 fixed and vary p/T to distinguish rank overhead from intra-rank threading. CPU speedup uses the matching CPU-node Serial reference; GPU-node acceleration uses its own Serial control. Two-GPU scaling uses each implementation\'s one-GPU solve time, not a different CPU baseline.')
    equation('E<sub>weak,iter</sub>(C) = [T(C<sub>0</sub>)/I(C<sub>0</sub>)] / [T(C)/I(C)]',
             '$$E_{weak,iter}(C)=\\frac{T(C_0)/I(C_0)}{T(C)/I(C)}.$$')
    para('Weak scaling grows work with resources. The core-normalized curves use T=4, p=C/4 and C=4..256, with the 4-core point as baseline. We show per-iteration efficiency because convergence counts can change with graph size; total-solve efficiency is also exported. The separate completed inventory contains 150 rank-based CPU cells, 84 core-normalized CPU cells and 138 GPU-node weak-suite cells/controls. These 372 entries are not part of the 19,530 denominator.')
    para('Communication ratios always pair the same graph, method, backend, nodes, ranks and threads. Ratios across graphs are aggregated geometrically; raw seconds from different graph sizes are never averaged into a speedup. The 45-row runtime matrix reports the best observed configuration within each method and explicitly allows different resources per cell; it is an achievable-runtime envelope, not a fixed-budget comparison.')
    heading('2.5 Correctness and reproducibility',2)
    para('The independent Python validators rebuild one PageRank update by streaming the original edge list, rather than sharing the C++ CSR traversal. Checks include vertex IDs/degrees, nonnegative finite ranks, total score within 10^-10 of one, residual within the stopping tolerance, full-vector L1 difference from Serial within 10^-8, history and repeated-run metadata. Allocation records and rank affinity maps verify the distributed layout. Raw rank vectors remain on Vanda; the repository holds summaries, timings, validation markers and provenance. The local analysis checks these saved proofs.')
    para('The source manifest, each summary path, independent completion marker, graph dimensions, node/rank/thread split, original job identifiers and timing-range diagnostics are retained in the report data. Report generation reads these records without executing performance measurements.')
    heading('2.6 AI usage',2)
    para('AI assistance was used for code adaptation within the existing project, experiment-matrix organization, job scripts, troubleshooting, result audits, visualization and this report draft. Runtime values come from compiled programs executed on Vanda. Report tables are derived from stored validated measurements; incomplete 512-core coverage is labeled separately and unvalidated work is excluded. The group remains responsible for reviewing the code, analysis, final wording and attribution before submission.')

    heading('3 Results')
    heading('3.1 Complete coverage and validation audit',2)
    table(['Audit item','Observed result'],[
        ['Fixed graphs / validated configurations','45 / 19,530 (100% of non-512 target)'],
        ['Timed solve observations','97,650; five per fixed configuration'],
        ['Separate non-512 weak suite','372 configurations or fixed-resource controls'],
        ['Maximum fixed-result residual L1',f"{AUDIT['max_residual_l1']:.3e}"],
        ['Maximum fixed-result rank-sum error',f"{AUDIT['max_rank_sum_error']:.3e}"],
        ['Summary median vs recomputed median','Exact match for all 19,530 configurations'],
        ['Convergence counts at fixed graph/context','Identical across methods/configurations in all 90 graph-context groups']], [238,262])
    para(f"The median relative five-run range (max-min)/median is {AUDIT['median_repeat_relative_range']:.1%}; its 95th percentile across configurations is {AUDIT['p95_repeat_relative_range']:.1%}. This is observed run-to-run dispersion, not a confidence interval. Five repeats inside one allocation do not establish independent-job uncertainty; small differences and best-of-matrix selections should be interpreted cautiously.")
    heading('3.2 Graph size and structural imbalance',2)
    figure('01_serial_grid','Figure 1. Serial solve time on all 36 grid graphs. Each family crosses vertex count with average out-degree d=4,8,16. Five-run medians; both axes are logarithmic.')
    density=[r for r in GRAPHS if r['graph'].startswith('grid_controlled_n100000_')]
    density.sort(key=lambda r:int(r['edges']))
    table(['Fixed N=100,000','Edges','Iterations','Serial s','Milliseconds / iteration'],[
        ['Controlled',r['edges'],r['iterations'],fmt(r['solve_median_s']),fmt(number(r['solve_median_s'])/int(r['iterations'])*1000)] for r in density], [110,100,80,100,110])
    para('Sparsity affects edge traversal and remote-source dependencies. At fixed vertex count, changing E/N changes the work per iteration, while E/(N*N) describes directed graph density. Total solve time also includes the number of convergence iterations, which changes with graph structure. Consequently, more edges need not produce a monotonic increase in total solve time; per-iteration time and iteration count must be inspected together. Hub concentration further changes load balance even at identical N and E.')
    rows=[]
    for g in REPRESENTATIVE:
        serial=get(g,'Serial');mpi=get(g,'MPI',host_nodes=8,processes=256,threads=1,communication='Allgatherv')
        rows.append([DISPLAY[g],f"{int(serial['vertices']):,}",str(serial['iterations']),fmt(serial['solve_median_s']),fmt(mpi['edge_imbalance'])])
    table(['Graph','Vertices','Iterations','Serial s','Max/min rank edges at p=256'],rows,[115,92,60,80,153])
    para('At identical 12.8M vertices and 204.8M edges, Uniform is almost edge-balanced across 256 ranks, while Hub and Controlled concentrate roughly 299x and 343x more incoming edges in the busiest rank than the least busy rank. This directly measures a limitation of contiguous equal-vertex partitioning. It provides a stronger explanation for structural scaling differences than graph size alone; it does not isolate every cache or runtime effect.')
    heading('3.3 CPU strong scaling',2)
    figure('02_strong_original','Figure 2. Strong scaling on the three original graphs. MPI uses T=1; the two hybrid curves use T=4. A=Allgatherv, H=Halo. Above 32 cores, nodes increase as C/32. Speedup uses each graph\'s CPU Serial reference.')
    figure('03_strong_large','Figure 3. The same predefined strong-scaling lines on the three large graphs. Logarithmic axes preserve slowdowns as well as speedups. The same graph and convergence criterion are used at every point.')
    para('More cores do not guarantee lower time. On Google, the best pure-MPI configuration is one node with p=32 and Halo: 0.149 s versus 1.896 s Serial (12.7x). At p=256 on eight nodes, pure MPI takes 0.799 s with Allgatherv and 1.462 s with Halo. The small original uniform and hub graphs show particularly poor 256-core efficiency: synchronization and contribution exchange outweigh the available per-rank work.')
    uniform=get('strong_uniform','MPI',host_nodes=8,processes=256,threads=1,communication='Halo')
    para(f"The large Uniform graph benefits from distributed resources: at 256 cores pure MPI with Halo reaches {number(uniform['speedup_vs_matched_serial']):.1f}x Serial speedup ({number(uniform['cpu_efficiency_vs_serial']):.1%} CPU efficiency). MPI+OpenMP with p=64,T=4 and Allgatherv reaches 28.3x (11.0% efficiency). The equal-size large Hub and Controlled graphs scale less well under pure MPI. Within-node dynamic OpenMP is competitive: the best hybrid results for these graphs use a single 32-thread rank, at 28.7x and 24.9x Serial speedup. These are different resource optima.")
    efficiency=[]
    for n in [1,2,4,8]:
        c=n*32; a=get('strong_uniform','MPI',host_nodes=n,processes=c,threads=1,communication='Halo')
        b=get('strong_uniform','MPI+OpenMP',host_nodes=n,processes=c//4,threads=4,communication='Allgatherv')
        efficiency.append([n,c,fmt(a['speedup_vs_matched_serial']),f"{number(a['cpu_efficiency_vs_serial']):.1%}",fmt(b['speedup_vs_matched_serial']),f"{number(b['cpu_efficiency_vs_serial']):.1%}"])
    table(['Nodes','CPU cores','MPI H speedup','MPI H efficiency','M+OMP A speedup','M+OMP A efficiency'],efficiency,[45,55,100,100,100,100])
    para('The preceding table holds the large Uniform graph fixed. MPI uses p=C,T=1; MPI+OpenMP uses p=C/4,T=4. Efficiency is speedup divided by active CPU cores. Non-monotonic points are retained. MPI phase timing includes synchronization and waiting, so a high communication fraction cannot alone identify network congestion.')
    diagnostic=[]
    for c in [64,128,256]:
        r=get('strong_uniform','MPI',host_nodes=c//32,processes=c,threads=1,communication='Halo')
        raw=json.loads((ROOT/r['source_summary']).read_text())
        diagnostic.append([c,fmt(r['solve_median_s']),fmt(r['communication_median_s']),f"{number(r['communication_fraction']):.1%}",fmt(raw['max_local_edges']/(int(raw['edges'])/c))])
    table(['Large Uniform cores','Solve s','Communication s','Median comm / solve','Max / mean edges'],diagnostic,[115,85,100,100,100])
    para('Solve and communication seconds are separate five-run medians; the percentage is the median of the five communication/solve ratios. The 128-core point is communication-dominated despite near-uniform edge work. The recorded communication scope includes packing, exchange, reductions and waiting; the solve and phase timers also take separate rank maxima. Thus the measurements locate a bottleneck in the communication/synchronization path without proving a single network cause. Collective message-size regimes, placement and contention are plausible mechanisms; distinguishing them requires controlled transport or collective-algorithm experiments.')
    rows=[]
    for g in REPRESENTATIVE:
        for mode in ('Allgatherv','Halo'):
            rows.append([DISPLAY[g],mode,*[fmt(get(g,m,host_nodes=8,processes=256//t,threads=t,communication=mode)['solve_median_s'])
                for m,t in [('MPI',1),('MPI+OpenMP',4),('MPI+Kokkos OpenMP',4)]]])
    table(['Graph','Communication','MPI p256 T1 (s)','M+OMP p64 T4 (s)','M+KK p64 T4 (s)'],rows,[112,88,100,100,100])
    heading('3.4 Equal-core rank and thread decomposition',2)
    figure('04_fixed_256_splits','Figure 4. All configurations use exactly 256 CPU threads on eight nodes. Paired speedup relative to the same method/graph/communication at p256,T1 is aggregated geometrically over 45 graphs. It is not speedup against Serial.')
    a=next(x for x in SPLITS if x['method']=='MPI+OpenMP' and x['communication']=='Allgatherv' and x['threads']=='32')
    k=next(x for x in SPLITS if x['method']=='MPI+Kokkos OpenMP' and x['communication']=='Allgatherv' and x['threads']=='32')
    best={m:max((x for x in SPLITS if x['method']==m and x['communication']=='Halo'),key=lambda x:number(x['geomean_speedup_vs_T1'])) for m in ['MPI+OpenMP','MPI+Kokkos OpenMP']}
    para(f"Changing p/T at fixed C has a large effect. With Allgatherv, T=32,p=8 improves geometric-mean time by {number(a['geomean_speedup_vs_T1']):.2f}x for MPI+OpenMP and {number(k['geomean_speedup_vs_T1']):.2f}x for MPI+Kokkos relative to T=1,p=256. The best aggregate Halo splits use T={best['MPI+OpenMP']['threads']} and T={best['MPI+Kokkos OpenMP']['threads']}, with improvements of {number(best['MPI+OpenMP']['geomean_speedup_vs_T1']):.2f}x and {number(best['MPI+Kokkos OpenMP']['geomean_speedup_vs_T1']):.2f}x. Reducing rank count changes both collective participation and local work; these measurements do not isolate one mechanism. The best split remains graph-dependent.")

    heading('3.5 Allgatherv versus exact Halo exchange',2)
    figure('05_halo_pairs','Figure 5. Within-layout paired ratios, excluding p=1. Left: geometric-mean Allgatherv/Halo solve-time ratio (>1 favors Halo). Right: median reduction in counted contribution payload. CPU and GPU-node aggregates have different method/configuration populations and are not direct hardware comparisons.')
    rows=[]
    for x in HALO:rows.append([x['context'].replace('_',' '),x['family'],x['paired_configurations'],fmt(x['geomean_halo_speedup']),f"{number(x['median_payload_reduction']):.1%}",f"{number(x['halo_faster_fraction']):.1%}"])
    table(['Context','Family','Pairs','Halo speedup','Payload reduction','Halo faster'],rows,[90,76,45,89,105,95])
    para('On CPU, Google has the strongest aggregate Halo gain: 1.89x geometric-mean speedup over 179 paired configurations and 58.6% median payload reduction. Uniform, Hub and Controlled show 1.19-1.23x aggregate gains, but many individual configurations still favor Allgatherv. On GPU nodes, the two-rank Halo ensembles have ratios below one. Small p, host staging, synchronization and exchange setup constrain gains; lower logical payload is insufficient to predict solver time.')
    heading('3.6 Standalone ablations and GPU-node comparisons',2)
    rows=[]
    for g in REPRESENTATIVE:
        rows.append([DISPLAY[g],fmt(get(g,'Serial')['solve_median_s']),fmt(get(g,'OpenMP',threads=32)['solve_median_s']),
                     fmt(get(g,'Kokkos OpenMP',threads=32)['solve_median_s']),fmt(get(g,'Serial','gpu_node')['solve_median_s']),
                     fmt(get(g,'CUDA','gpu_node')['solve_median_s']),fmt(get(g,'Kokkos CUDA','gpu_node')['solve_median_s'])])
    table(['Graph','CPU Serial s','OMP T32 s','KK OMP T32 s','GPU-node Serial s','CUDA 1GPU s','KK CUDA 1GPU s'],rows,[110,65,65,65,65,65,65])
    figure('06_gpu_node_scaling','Figure 6. One-to-two GPU-node strong scaling on the large graphs. Each curve is normalized by its own one-node value. The CPU-only controls use p=1/2,T=1 and no GPU kernels; the device methods use one A40 per rank. These are two measured points, not a 4/8-GPU extrapolation.')
    para('Standalone CUDA/Kokkos CUDA can outperform their distributed p=1 versions because the distributed driver stages source contributions through host memory on every iteration. Google takes 0.115 s with standalone CUDA and 0.094 s with standalone Kokkos CUDA, compared with about 0.243 s and 0.383 s for their MPI Allgatherv p=1 variants. The standalone timings exclude setup transfers, so these ratios describe solver execution rather than full startup cost.')
    para('Two GPUs do not consistently beat one. For large Uniform, MPI+CUDA Allgatherv improves from 0.788 s to 0.705 s (1.12x), whereas Halo becomes slower. Kokkos CUDA\'s distributed Allgatherv variant improves from 1.368 s to 1.126 s (1.22x). On large Hub and Controlled, distributed Kokkos improves from one to two GPUs but remains slower than native CUDA at the same layouts. Backend implementation and graph structure both matter; Kokkos portability does not imply identical performance.')
    figure('08_gpu_phases','Figure 7. Large Controlled phase diagnostics on a logarithmic time axis, in seconds. CU=native CUDA, KK=Kokkos CUDA; digit=rank/GPU count; A/H=communication. Markers are medians of the original solve_s, backend_compute_s, transfer_s or communication_s measurements. Phase medians are not additive components of one median run.')
    heading('3.7 Weak scaling',2)
    figure('07_core_weak','Figure 8. Top: pure MPI weak scaling, with N and E proportional to ranks and the one-rank point as baseline. Bottom: core-normalized hybrid weak scaling with T=4, p=C/4 and the four-core point as baseline. Both show baseline per-iteration time divided by measured per-iteration time; ideal efficiency is 100%. No 512-core endpoints are shown.')
    pure=[]
    for family in ['uniform','hub','controlled']:
        r=[x for x in WEAK if x['suite']=='rank_cpu_regular' and x['method']=='MPI' and x['family']==family and x['processes']=='256']
        pure.append([family,*[f"{number(next(x for x in r if x['communication']==mode)['weak_efficiency_per_iteration']):.2%}" for mode in ['Allgatherv','Halo']]])
    table(['Pure MPI family','C256 Allgatherv efficiency','C256 Halo efficiency'],pure,[160,170,170])
    para('Rank-normalized weak scaling keeps nominal local vertices and edges constant, but not the communication problem: the global contribution vector and collective participant count grow with resources. On the concentrated families, equal vertex partitions also produce severe incoming-edge imbalance. Communication timers include waiting for slow ranks and cannot be interpreted solely as network transmission time.')
    rows=[]
    for f in ('uniform','hub','controlled'):
        for m in ('MPI+OpenMP','MPI+Kokkos OpenMP'):
            a=[r for r in WEAK if r['suite']=='core_cpu' and r['family']==f and r['method']==m and int(r['active_cpu_threads'])==256]
            rows.append([f,m,*[f"{number(next(r for r in a if r['communication']==mode)['weak_efficiency_per_iteration']):.2%}" for mode in ('Allgatherv','Halo')]])
    table(['Family','Method','C256 Allgatherv efficiency','C256 Halo efficiency'],rows,[90,160,125,125])
    para('Weak scaling is poor despite constant nominal work per core. At C=256, the core-normalized uniform curves retain roughly 3.6-4.2% per-iteration efficiency; the skewed families are around 0.7-1.4%. Replicated vectors and global synchronization grow with resource count, while equal-vertex partitioning does not preserve equal incoming-edge work on the concentrated families. These measurements reject a claim of near-ideal weak scaling. They motivate a future edge-aware partitioner and communication/staging redesign; they do not establish which unimplemented change would be fastest.')
    story.append(PageBreak())
    heading('3.8 Full fixed-graph result matrix',2)
    para('The next table reports best observed solve medians within each method, over the complete non-512 sweep. Different cells can select different nodes, p/T and communication. The corresponding selected configurations are exported in runtime_matrix_45.csv; fixed-budget comparisons are given separately above. The associated heatmap uses matched Serial controls within each hardware context.')
    table(['Graph','Serial','OMP','KK-O','MPI','M-O','M-KO','CUDA','KK-C','M-C','M-KC','512*'],[
        [abbreviated(r['graph']),*[fmt(r[m+'_best_s']) for m in ('Serial','OpenMP','Kokkos OpenMP','MPI','MPI+OpenMP','MPI+Kokkos OpenMP','CUDA','Kokkos CUDA','MPI+CUDA','MPI+Kokkos CUDA')],fmt(r['512_partial_best_s']) if r['512_partial_best_s']!='-' else '-'] for r in MATRIX],
        [70]+[39]*10+[40],small=True)
    para('Values are five-run median solve times (s). KK=Kokkos; M=MPI; O=OpenMP; C=CUDA. U/H/C label graph families, followed by vertices and mean out-degree; o./s. denote original/canonical graphs. Cells can use different resource budgets. 512* is the best of five available cases on C 50k/4; a hyphen marks an unmeasured cell. This column is a partial supplement.')
    story.append(PageBreak())
    figure('09_runtime_matrix','Figure 9. Full 45-graph best-observed speedup matrix. CPU and GPU columns use their own matched Serial references. Color is log-scaled and clipped at 1/16x and 64x; exact timings and selected layouts are in the CSV. The resource budget can differ between cells.')

    story.append(PageBreak())
    heading('3.9 Partial 512-core supplement',2)
    para('The complete main matrix stops at 256 CPU cores. The supplement below contains five validated 512-core configurations out of 1,170 planned combinations, all on Controlled N=50,000 and E=200,000. Each uses eight nodes with 64 active cores per node. Missing methods, layouts and graphs are unmeasured, not zero-time results.')
    table(['Method','p / T','Communication','Solve s','Speedup','Efficiency'],[
        [x['method'],x['processes']+' / '+x['threads'],x['communication'],fmt(x['solve_median_s']),fmt(x['speedup']),f"{number(x['efficiency']):.3%}"] for x in SUPPLEMENT], [130,55,90,65,70,90])
    para('Every row reports the median of five timed runs after one warm-up and uses the matching CPU Serial baseline. All five cases are slower than Serial on this small graph, and Halo is particularly costly at p=512. This illustrates the cost of distributing a small workload; five cases on one graph do not support a general conclusion about 512-core scaling. This supplement is excluded from the main matrix best-time selection, geometric communication aggregates and weak-scaling curves.')

    heading('4 Conclusions and insights')
    heading('4.1 What the experiments establish',2)
    para('First, parallel degree is a choice, not a target to maximize unconditionally. Large balanced graphs exploit multiple nodes; small graphs and concentrated destination rows often favor fewer MPI ranks and more threads within a rank. At fixed 256 cores, rank/thread decomposition can change aggregate runtime by more than an order of magnitude.')
    para('Second, an exact Halo reduces contribution payload without guaranteeing faster execution. CPU and GPU-node observations differ, and even within the CPU matrix the large-graph best communication mode changes with structure and p/T. Communication must be evaluated with matched layouts and actual time, not bytes alone.')
    para('Third, Kokkos provides the same algorithm on CPU and GPU backends, while backend policy, staging and vertex work imbalance determine performance. The distributed device path has a substantial cost even at p=1. Multi-GPU performance cannot be inferred from a fast standalone kernel.')
    para('Fourth, equal-vertex partitioning is a clear structural limitation: extreme incoming-edge imbalance and weak-scaling degradation remain after all numerical checks pass. Edge-aware or reordered partitions, selective device/host staging, CUDA-aware MPI and overlap are reasonable future experiments. None is claimed as implemented or measured here.')
    heading('4.2 Conclusions about the real Google graph',2)
    para(f"The validated Google Serial vector has {GOOGLE['dangling_vertices']:,} dangling vertices ({GOOGLE['dangling_vertices']/GOOGLE['vertices']:.1%}), so dangling-mass redistribution is essential. The highest-scoring 1% of vertices carry {GOOGLE['top_1_percent_rank_mass']:.1%} of the total probability mass. Pearson correlation between PageRank and in-degree is {GOOGLE['pagerank_indegree_pearson']:.3f}: incoming links are strongly associated with rank, but raw in-degree is not the complete weighting rule.")
    table(['Node ID','PageRank','In-degree','Out-degree'],[[r['node_id'],f"{r['rank']:.7f}",r['in_degree'],r['out_degree']] for r in GOOGLE['top10'][:5]], [120,140,120,120])
    para('These anonymized vertex IDs cannot be mapped to named websites from this edge-list dataset alone. The observed rank concentration supports a structural statement about this graph; it does not identify trustworthy content or establish a causal relationship between links and importance.')
    heading('4.3 Limits, reproducibility and references',2)
    para('This report presents measured Vanda results with a complete main matrix and a partial 512-core supplement. There are five repeats per configuration within an allocation; placement and execution dates vary, and the best-observed matrix introduces selection effects. Shared-node allocations can span NUMA regions; NUMA locality is not fixed across every allocation. These are observed shared-cluster measurements. Full application startup, energy, communication overlap, source-specific PPR and 4/8-GPU scaling are outside scope. The partial 512-core table does not establish a complete high-core scaling curve.')
    para('Reproduction: analyze_report_results.py reads the validated inventory and all referenced summaries/timings; build_non512_report.py produces this PDF, the editable report text and nine vector figures. The data directory provides the full fixed and weak tables, paired communication ratios, equal-core decompositions, graph catalog and audit checks. The data-selection manifest maps every chosen measurement to its timing and validation evidence. Raw records are preserved; input and selection SHA-256 values are recorded in audit.json.')
    for reference in [
        '[1] Page, L., Brin, S., Motwani, R. and Winograd, T. The PageRank Citation Ranking: Bringing Order to the Web. Stanford, 1999. http://ilpubs.stanford.edu:8090/422/',
        '[2] Stanford SNAP. Google web graph dataset. https://snap.stanford.edu/data/web-Google.html',
        '[3] MPI Forum. MPI standard and collective communication. https://www.mpi-forum.org/docs/',
        '[4] Kokkos documentation. Execution spaces, Views and parallel dispatch. https://kokkos.org/kokkos-core-wiki/',
        '[5] Project source and Vanda result records, validated measurement collection of 17 November 2026. https://github.com/rosesnack/DSA5208_PROJECT_3']:
        story.append(Paragraph(html.escape(reference),styles['ReferenceReport']));md.append(reference+'\n')
    (REPORT/'report.md').write_text('\n'.join(md).rstrip()+'\n')
    PDF.parent.mkdir(parents=True,exist_ok=True)
    def page(canvas,doc):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(GRAY)
        canvas.drawString(47,25,'DSA5208 | Parallel PageRank | Vanda results')
        canvas.drawRightString(A4[0]-47,25,str(doc.page));canvas.restoreState()
    doc=SimpleDocTemplate(str(PDF),pagesize=A4,rightMargin=47,leftMargin=47,topMargin=42,bottomMargin=43,
                          title=title,author='DSA5208 project group',pageCompression=1)
    doc.build(story,onFirstPage=page,onLaterPages=page)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdftoppm',help='Poppler executable for PNG figure exports')
    args=parser.parse_args()
    assert AUDIT['fixed_configurations']==19530 and AUDIT['all_512_excluded']
    items=figures();write_figures(items,args.pdftoppm);report(items)
    print(PDF)
    print('Nine figures; 45-graph runtime matrix; four report sections; separate partial 512 supplement.')


if __name__=='__main__':
    main()
