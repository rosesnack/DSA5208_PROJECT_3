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
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
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

REPORT_DATE = datetime.now(ZoneInfo('Asia/Singapore')).strftime('%d %B %Y')
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
WORK = list(csv.DictReader((DATA/'rank_work_diagnostics.csv').open()))
POLICY = list(csv.DictReader((DATA/'thread_policy_diagnostics.csv').open()))
TRAFFIC = list(csv.DictReader((DATA/'weak_traffic_diagnostics.csv').open()))
SELECTOR = list(csv.DictReader((DATA/'mpi_selector_consistency.csv').open()))
GPU_WORK = list(csv.DictReader((DATA/'gpu_work_diagnostics.csv').open()))
OPTIMA = json.loads((DATA/'method_optima.json').read_text())
CONTROL_FILE = DATA/'collective_controls.csv'
CONTROLS = list(csv.DictReader(CONTROL_FILE.open())) if CONTROL_FILE.exists() else []
LAUNCHER_FILE = DATA/'launcher_controls.csv'
LAUNCHER_CONTROLS = list(csv.DictReader(LAUNCHER_FILE.open())) if LAUNCHER_FILE.exists() else []
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
                log_y=True, x_format=None, y_format=None, height=255, shared_y=False):
    drawing = Drawing(500,height)
    width=500/len(titles)
    if shared_y:
        values=[y for panel in series for _,points,_,_ in panel for x,y in points]
        y_bounds=(min(values)*.9,max(values)*1.1)
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
        if shared_y:lp.yValueAxis.valueMin,lp.yValueAxis.valueMax=y_bounds
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
        result[name]=line_panels([DISPLAY[g] for g in graphs],panels,'Active CPU cores','Speedup vs Serial',[4,16,64,256],shared_y=True)
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
    d.add(String(210,635,'CPU-node methods',fontName='Helvetica',fontSize=8,textAnchor='middle',fillColor=GRAY))
    d.add(String(400,635,'GPU-node methods',fontName='Helvetica',fontSize=8,textAnchor='middle',fillColor=GRAY))
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
    imbalance=[]
    for family,color in [('uniform',BLUE),('hub',ORANGE),('controlled',TEAL)]:
        rows=sorted((r for r in WORK if r['graph']=='strong_'+family),key=lambda r:int(r['processes']))
        imbalance.append((family.title(),[(int(r['processes']),number(r['max_mean_edges'])) for r in rows],color,False))
    top=line_panels(['Fixed 12.8M-vertex graphs: incoming-edge imbalance'],[imbalance],
        'MPI ranks p','Max / mean rank edges',[1,4,16,64,256],height=235,y_format=lambda x:f'{x:g}')
    panels=[]
    for key,scale in [('counted_payload_bytes_per_rank',1e-6),('communication_ms_per_iteration',1)]:
        curves=[]
        for mode,color in [('Allgatherv',BLUE),('Halo',ORANGE)]:
            rows=sorted((r for r in TRAFFIC if r['family']=='uniform' and r['communication']==mode
                         and (key!='counted_payload_bytes_per_rank' or int(r['processes'])>1)),key=lambda r:int(r['processes']))
            curves.append((mode,[(int(r['processes']),number(r[key])*scale) for r in rows],color,mode=='Halo'))
        panels.append(curves)
    bottom=line_panels(['Uniform weak scaling: payload','Uniform weak scaling: communication'],panels,
        'MPI ranks p','MB / rank (left); ms / iteration (right)',[1,4,16,64,256],height=245,y_format=lambda x:f'{x:g}')
    # Distinct y labels keep a byte count separate from a phase duration.
    for obj in bottom.contents:
        if isinstance(obj,String) and obj.text=='MB / rank (left); ms / iteration (right)':
            obj.text='Counted payload / rank (MB)' if obj.x<250 else 'Communication / iteration (ms)'
    mechanism=Drawing(500,500);group=Group();group.translate(0,265);group.add(top)
    mechanism.add(group);mechanism.add(bottom);result['10_scaling_mechanisms']=mechanism
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
    styles.add(ParagraphStyle(name='BodyReport',fontName='Times-Roman',fontSize=10.3,leading=13.5,spaceAfter=7,textColor=INK,allowWidows=0,allowOrphans=0))
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
        prefix=[]
        if len(rows)<=12 and story and isinstance(story[-1],Paragraph) and story[-1].style.name=='SubReport':
            prefix.append(story.pop())
        story.extend([KeepTogether(prefix+[t,Spacer(1,8)])] if len(rows)<=12 else [t,Spacer(1,8)])
    figure_number=0
    def figure(name,caption):
        nonlocal figure_number
        figure_number+=1
        caption=re.sub(r'^Figure [0-9]+[a-z]?\.',f'Figure {figure_number}.',caption)
        md.append(f'![{caption}](figures/{name}.png)\n')
        prefix=[]
        if story and isinstance(story[-1],Paragraph) and story[-1].style.name=='SubReport':
            prefix.append(story.pop())
        story.append(KeepTogether(prefix+[items[name],Paragraph(html.escape(caption),styles['CaptionReport'])]))
    def equation(pdf,markdown):
        story.append(Paragraph(pdf,styles['EquationReport']));md.append(markdown+'\n')

    title='Parallel PageRank on Vanda'
    md.extend(['# '+title,'',f'Parallel PageRank experiments - {REPORT_DATE}',''])
    story.append(Paragraph(title,ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=25,leading=29,textColor=INK,spaceAfter=10)))
    story.append(Paragraph(f'DSA5208 Project 3 | {REPORT_DATE}',styles['CaptionReport']))
    author_file=REPORT/'authors.json'
    if author_file.exists():
        authors=json.loads(author_file.read_text())
        author_line='; '.join(author['name']+' ('+author['student_id']+')' for author in authors)
        md.append(author_line+'\n');story.append(Paragraph(html.escape(author_line),styles['CaptionReport']))
    para('We evaluate synchronous PageRank on 45 directed graphs using Serial, OpenMP, MPI, MPI+OpenMP, native CUDA and Kokkos with OpenMP and CUDA backends. The audited dataset contains 19,530 fixed-graph configurations and 372 separate non-512 weak-suite configurations or controls. All fixed-graph targets in this scope are complete and independently validated. Five available 512-core configurations are presented as a separate, explicitly incomplete supplement.')
    if CONTROLS:
        control_topics="collective-policy, node-boundary and launch-binding" if LAUNCHER_CONTROLS else "collective-policy and node-boundary"
        para(f"An additional {len(CONTROLS)+len(LAUNCHER_CONTROLS)} independently certified matched controls examine {control_topics} effects. These controls are analyzed separately, with fixed rules and forced algorithms explicitly distinguished; they do not alter the main-matrix denominator.")
    heading('1 Introduction to the algorithm and data')
    heading('1.1 PageRank and its relation to PPR',2)
    para('PageRank assigns a probability score to each vertex of a directed graph. A random surfer follows an outgoing edge with probability alpha and otherwise jumps according to a preference vector. Personalized PageRank (PPR) uses a query-specific preference vector. Our implementation uses the uniform preference vector and uniform redistribution of dangling-vertex mass: it is standard PageRank, equivalently the uniform-preference special case of PPR. We do not implement source-specific personalized queries.')
    equation('r<sub>k+1</sub>(v) = (1 - alpha)/N + alpha D<sub>k</sub>/N + alpha sum<sub>u -&gt; v</sub> r<sub>k</sub>(u)/d<sub>out</sub>(u)',
             '$$r_v^{(k+1)}=(1-\\alpha)/N+\\alpha D_k/N+\\alpha\\sum_{u\\to v}r_u^{(k)}/d_{out}(u).$$')
    para('Here D_k is the total score of vertices with zero out-degree. Scores start at 1/N; alpha=0.85; iteration stops when the global L1 change is at most 10^-8, with a cap of 1,000 iterations. All kernels use double precision and synchronous old/new score buffers. The pull formulation traverses incoming-edge compressed sparse row (CSR) storage, avoiding simultaneous writes to a destination. An iteration costs O(N+E) work and O(N+E) storage in serial.')
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
    para('For the three large graphs, E/N=16. The integer rule floor(4*d_out/5) sends exactly 75.0% of Hub edges and 77.5% of Controlled edges into the first 1% of destination IDs. These exact fractions, rather than an assumed 80%, are used in the workload model below. The concentration is deliberately aligned with contiguous vertex partitions; results therefore characterize this partitioner and vertex ordering as well as graph structure.')
    para('Integer rounding also qualifies the density-grid interpretation: Controlled sends 65.0% of its edges to the hot block at mean degree 4, and 77.5% at degrees 8 and 16. Changing density therefore changes this exact structural concentration as well as E. The grid is a reproducible generator-family study, not an intervention that isolates edge count from every other graph property.')
    para('Vertex count and average out-degree are crossed systematically, not changed together in a single size parameter. The three large graphs have identical N and E but different structural concentration, making them useful for separating graph size from load imbalance. All 45 fixed graphs are reused unchanged across the full fixed-graph configuration matrix.')
    heading('1.3 Separate weak-scaling inputs',2)
    para('Weak scaling uses the same three generator families with 50,000 vertices and 800,000 edges per scaling unit. Rank-based series grow the graph with p; core-normalized series grow it with C=pT. Across the non-512 weak suites there are 27 distinct graph names. The GPU weak suite also runs standalone methods on both input sizes; these are fixed-resource size controls and are not labeled as resource-scaled weak-efficiency curves.')

    heading('2 Methodology')
    heading('2.1 Parallel implementations and design decisions',2)
    table(['Implementation','Compute and work distribution','MPI communication'],[
        ['Serial','One CPU thread; incoming CSR pull','None'],
        ['OpenMP','CPU threads; dynamic vertex schedule, chunk 64','None'],
        ['Kokkos OpenMP','CPU execution space; default static RangePolicy and reductions','None'],
        ['CUDA / Kokkos CUDA','One GPU; incoming-row vertex kernels','None'],
        ['MPI','Contiguous destination partitions; one CPU thread/rank','Both modes'],
        ['MPI+OpenMP','Same MPI partitions; threaded pull within each rank','Both modes; MPI_THREAD_FUNNELED'],
        ['MPI+CUDA','One GPU/rank; host buffers between device and MPI','Both modes'],
        ['MPI+Kokkos','Shared distributed driver; OpenMP or CUDA execution space','Both modes']], [105,280,115])
    para('MPI partitions consecutive dense vertex IDs approximately equally. Each rank owns incoming rows and out-degrees for its vertices. Allgatherv replicates the complete vector of source contributions at every rank each iteration. Halo precomputes distinct remote source IDs, exchanges request metadata once, and then sends only requested values with Alltoallv. Both modes retain dangling-mass and convergence Allreduce calls. Halo is an exact dependency exchange, not approximate communication or dropped edges.')
    para('The counted per-iteration payload is the algorithm-level contribution-vector traffic, excluding collective implementation details, reduction traffic, and protocol overhead. Allgatherv counts 8N(p-1) aggregate bytes; Halo counts eight bytes per requested remote contribution. Metadata setup is recorded separately and lies outside solve time. Fewer counted bytes therefore need not imply lower measured latency.')
    para('Two costs must be distinguished: local work is approximately a*N_i+b*E_i, while global progress waits for the slowest rank and collective completion. Incoming-edge imbalance changes E_i even when every N_i is equal. The MPI timer includes packing/copies, collectives and waiting at reductions; it is not a network-only timer. Solve and phase timings take separate maxima across ranks, then separate medians across five runs. They cannot be subtracted or added to reconstruct one critical-path trace.')
    para('The distributed device implementations stage contributions through host memory; they do not use CUDA-aware MPI or overlap communication with computation. The CUDA version uses 256-thread blocks and explicit kernels. Kokkos expresses comparable operations through Views, parallel_for/parallel_reduce and execution-space fences. Kokkos OpenMP and CUDA are two backends, not interchangeable hardware measurements.')
    heading('2.2 Hardware, software and timing protocol',2)
    para('All reported measurements are from NUS Vanda. CPU comparisons use Intel Xeon Platinum 8452Y hosts, GCC 13.3.0, Open MPI 4.1.8 and Release builds. GPU comparisons use NVIDIA A40 nodes with Platinum 8452Y CPUs; archived build metadata identifies CUDA toolkit 12.4.1. Driver-reported CUDA compatibility is not treated as the compiler toolkit version. Original laptop and mixed-hardware exploratory measurements are excluded.')
    para('Every configuration has one warm-up followed by five timed runs. All primary solve-time tables and figures report the median of those five timed runs. The exported statistic solve_median_s is recomputed here from the five original solve_s observations. MPI solve time is the maximum elapsed solver time across ranks. Graph input, partition distribution, backend construction and Halo setup are outside solve time; per-iteration MPI and host/device staging are inside the distributed solve. Standalone GPU setup and final rank copies are outside solve time. These are solver-time comparisons, not end-to-end application runtimes.')
    para('OpenMP creates its persistent thread team inside the timed solver, while Kokkos runtime initialization precedes solver timing. Backend-compute phases use fenced host-clock intervals, including dispatch and reduction implementation costs; they are not CUDA-event measurements of pure kernel execution. Transfer phases measure explicit staging and need not capture every internal scalar-result copy. These boundaries should be considered when comparing backends or very small graph runtimes.')
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
    para('For CPU configurations the active core budget is C=pT=n(rT). The matrix contains 24 pure-MPI layouts and 84 layouts for each CPU hybrid method; every MPI layout is paired across communication modes. The main 32-core-per-node strong-scaling line uses C=32/64/128/256 on n=1/2/4/8 nodes. Lower-core points use one node. At a fixed C, hybrid methods test every legal T from the six-value set with p=C/T; a larger allocation is not counted as higher parallelism unless pT increases. The full table also contains other node layouts at equal C.')
    para('On GPU nodes the CPU-only MPI and OpenMP variants are controls on the same node layout, not GPU implementations. Distributed GPU comparisons use p=1 or 2 with one GPU per rank. The GPU scope is one or two A40 devices. The 512-core fixed-graph supplement contains five validated configurations on one graph; its missing combinations are not used to construct a complete scaling curve. Weak-scaling comparisons here stop at 256 CPU cores.')
    heading('2.4 Strong scaling, weak scaling and aggregation',2)
    equation('S(C) = T<sub>serial</sub>/T(C), &nbsp;&nbsp; E(C) = S(C)/C',
             '$$S(C)=T_{serial}/T(C),\\qquad E(C)=S(C)/C.$$')
    para('Strong scaling holds the graph fixed and increases active resources. We also hold C=256 fixed and vary p/T to distinguish rank overhead from intra-rank threading. CPU speedup uses the matching CPU-node Serial reference; GPU-node acceleration uses its own Serial control. Two-GPU scaling uses each implementation\'s one-GPU solve time, not a different CPU baseline.')
    equation('E<sub>weak,iter</sub>(C) = [T(C<sub>0</sub>)/I(C<sub>0</sub>)] / [T(C)/I(C)]',
             '$$E_{weak,iter}(C)=\\frac{T(C_0)/I(C_0)}{T(C)/I(C)}.$$')
    para('Weak scaling grows work with resources. The core-normalized curves use T=4, p=C/4 and C=4..256, with the 4-core point as baseline. We show per-iteration efficiency because convergence counts can change with graph size; total-solve efficiency is also exported. The separate completed inventory contains 150 rank-based CPU cells, 84 core-normalized CPU cells and 138 GPU-node weak-suite cells/controls. These 372 entries are not part of the 19,530 denominator.')
    para('Communication ratios always pair the same graph, method, backend, nodes, ranks and threads. The geometric mean treats reciprocal proportional changes symmetrically: a 2x improvement and a 2x slowdown average to 1x. It also gives each graph equal multiplicative weight. Raw seconds from different graph sizes are never averaged into a speedup. The 45-row runtime matrix selects the best observed configuration within each method and permits different resource budgets. It is a runtime envelope; strong-scaling lines and equal-core comparisons carry the scaling argument.')
    heading('2.5 Correctness and reproducibility',2)
    para('The independent Python validators rebuild one PageRank update by streaming the original edge list, rather than sharing the C++ CSR traversal. Checks include vertex IDs/degrees, nonnegative finite ranks, total score within 10^-10 of one, residual within the stopping tolerance, full-vector L1 difference from Serial within 10^-8, history and repeated-run metadata. Allocation records and rank affinity maps verify the distributed layout. Raw rank vectors remain on Vanda; the repository holds summaries, timings, validation markers and provenance. The local analysis checks these saved proofs.')
    para('For the additional collective-policy controls, an independent raw-edge scan validates the Serial vector s once per graph. Every new vector x is compared in full, including IDs, degrees, probability mass and L1 error. Because the PageRank map F is alpha-contractive in L1, residual(x) is bounded by residual(s)+(1+alpha)*L1(x-s). Requiring this bound to be at most 10^-8 independently certifies the new vector while reusing the reference scan. The same contraction bounds L1 distance to the unique stationary vector by residual/(1-alpha). Timings, histories, actual threads and all five reported residuals are checked separately. These checks run on the free queue.')
    para('The source manifest, each summary path, independent completion marker, graph dimensions, node/rank/thread split, original job identifiers and timing-range diagnostics are retained in the report data. Report generation reads these records without executing performance measurements.')
    heading('2.6 MPI collective selection and controlled policies',2)
    para('Open MPI separates a collective operation from its implementation. Our Halo calls MPI_Alltoallv; tuned is the component that selects its message schedule. The main benchmark scripts leave tuned at its default settings. Compute-node installation probes on both accounts report coll_tuned_use_dynamic_rules=false, with Alltoallv and Allgatherv algorithm overrides set to ignore. This is distinct from OpenMP schedule(dynamic,64), which assigns local vertex work to CPU threads. OMP_DYNAMIC=false fixes the team size; it does not disable dynamic chunk scheduling.')
    table(['Alltoallv communicator size p','Default tuned algorithm'],[
        ['p < 4','pairwise'],['4 <= p < 64','basic_linear'],
        ['64 <= p < 128','pairwise'],['128 <= p < 256','basic_linear'],
        ['256 <= p < 1024','pairwise'],['p >= 1024','basic_linear']], [235,265])
    para('These are the fixed rules in Open MPI 4.1.8 [7] for communicators handled by tuned. A single-rank communicator can use the self component and has no remote Halo payload. For Alltoallv, this selector uses communicator size p, not message bytes, CPU cores or measured congestion. basic_linear starts nonblocking requests to the participating peers and waits for them; pairwise schedules rank-step exchanges [8]. Both implement the same blocking MPI_Alltoallv interface and transfer the same requested values. Their different request concurrency and message order can change latency and resource pressure. A blocking collective is not an MPI_Barrier.')
    para('Allgatherv has a separate selector using both p and average contribution bytes per rank, b=8N/p. On the large graphs N=12.8 million, the T=4 mainline changes from p=8, b=12.8 MB at 32 cores to p=16, b=6.4 MB at 64 cores. Its default Allgatherv algorithm changes from Bruck to Ring; at p=32 and 64 it remains Ring [7]. Thus a 64-core bend may involve a different collective transition from the 128-rank Halo peak.')
    table(['Active cores C','Nodes','MPI p / Alltoallv','Hybrid p / Alltoallv','Hybrid Allgatherv'],[
        ['32','1','32 / basic_linear','8 / basic_linear','Bruck'],
        ['64','2','64 / pairwise','16 / basic_linear','Ring'],
        ['128','4','128 / basic_linear','32 / basic_linear','Ring'],
        ['256','8','256 / pairwise','64 / pairwise','Ring']], [85,40,130,135,110])
    para('Hybrid columns use T=4 and both CPU hybrid implementations. To isolate a collective policy, enable coll_tuned_use_dynamic_rules=1 and force only that operation: Alltoallv algorithm 1=basic_linear or 2=pairwise; Allgatherv algorithm 2=Bruck or 3=Ring [9]. Other collectives retain their fixed-rule choices. The dynamic switch enables forced/user-rule dispatch; it is not online timing-based learning. Paired policies use the same graph, binary, allocation, p/T, CPU affinity and transport, with identical tuned/basic/libnbc/self component availability. Component probes run outside the five timed solves. Five-run medians and ranges, rather than a selected fastest repeat, quantify policy sensitivity.')
    para('Equal CPU budgets do not imply equal MPI policies. At C=256, p256/T1 uses pairwise Alltoallv, p128/T2 uses basic_linear, and p64/T4 returns to pairwise. Reducing p further to 32/16/8 uses basic_linear. Rank/thread decomposition therefore changes collective participation, local work sharing and the runtime selection regime together. The matched fixed-policy controls distinguish the contribution of a specific communication choice.')
    para('The default tree is a compiled heuristic: it does not benchmark this graph or profile the current Vanda allocation. A rule can therefore be correct and reproducible while selecting a slower implementation for a particular rank count and message pattern.')
    heading('2.7 AI usage',2)
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
    para(f"The median relative five-run range (max-min)/median is {AUDIT['median_repeat_relative_range']:.1%}; its 95th percentile across configurations is {AUDIT['p95_repeat_relative_range']:.1%}. These ranges describe within-allocation variability. Matched policy contrasts hold placement fixed, and timing differences are read relative to the observed five-run spread. The best-observed matrix also retains the selected resource configuration for each cell.")
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
    equation('B<sub>E</sub> = max<sub>i</sub>(E<sub>i</sub>)/(E/p), &nbsp;&nbsp; p<sub>edge</sub> = E/max<sub>i</sub>(E<sub>i</sub>) = p/B<sub>E</sub>',
             '$$B_E=\\frac{\\max_i E_i}{E/p},\\qquad p_{edge}=\\frac{E}{\\max_i E_i}=\\frac{p}{B_E}.$$')
    table(['Large graph, p=256','Max / mean edges','Busiest rank edge share','Equivalent balanced ranks'],[
        [DISPLAY[r['graph']],f"{number(r['max_mean_edges']):.3f}",f"{number(r['max_rank_edge_share']):.2%}",fmt(r['equivalent_balanced_ranks'])]
        for r in WORK if r['processes']=='256'],[135,110,125,130])
    para('The edge-work equivalent is an equal-rate model, not a measured speedup ceiling across different cache layouts or backends. At p=256, Hub and Controlled provide only about 3.4 and 3.3 balanced-rank equivalents for edge traversal. A single rank owns roughly 29%-30% of all edges; hundreds of lightly loaded ranks cannot shorten that rank\'s row scans. Halo changes which values move, while destination ownership stays fixed, so it cannot remove this imbalance.')
    para('The generator explains the shape quantitatively. A partition of width 1/p contains all hot destination IDs while p<=100; beyond that, several ranks share the hot block. If q is its edge fraction and h=0.01 its vertex fraction, the maximum edge share is approximately q+(1-q)*(1/p-h)/(1-h) for 1/p>=h, and q/(p*h) otherwise. The model predicts B_E near 75 and 77.5 at p=256, matching the observed 75.002 and 77.508. This links the slowdown to a concrete graph-ordering/partition interaction.')
    table(['Large graph; T=32','OpenMP s','Kokkos OpenMP s','Kokkos / OpenMP','32-block max edge share'],[
        [DISPLAY[r['graph']],fmt(r['openmp_s']),fmt(r['kokkos_openmp_s']),fmt(r['kokkos_over_openmp']),f"{number(r['contiguous_32way_edge_share_proxy']):.1%}"] for r in POLICY],
        [120,75,100,100,105])
    para('Scheduling also matters within a node. OpenMP uses schedule(dynamic,64) for destination updates. The compiled Kokkos 4.5.01 sources default RangePolicy to Schedule<Static>; its OpenMP reduction assigns a vertex interval to each worker and enables stealing only for Dynamic [6]. Each vertex still scans its incoming row sequentially. A 32-block equal-vertex partition places 75.5%-78.0% of the skewed graphs\' edges in one block, while Uniform is balanced. This is a work-distribution proxy for static thread ranges. Kokkos and OpenMP take similar time on Uniform but differ by about 22x on the skewed graphs. Static row assignment may concentrate the expensive rows on a small subset of workers; dynamic chunks can redistribute those rows. Reduction and memory-locality costs can also contribute to the observed difference.')
    para('This comparison evaluates the implemented scheduling policies together with their runtimes. It cannot be read as a controlled measurement of intrinsic Kokkos framework overhead.')
    heading('3.3 CPU strong scaling',2)
    figure('02_strong_original','Figure 2. Strong scaling on the three original graphs. MPI uses T=1; the two hybrid curves use T=4. A=Allgatherv, H=Halo. Above 32 cores, nodes increase as C/32. Speedup uses each graph\'s CPU Serial reference; panels share the same logarithmic speedup range.')
    figure('03_strong_large','Figure 3. The same predefined strong-scaling lines on the three large graphs, with a common logarithmic speedup range across panels. The same graph and convergence criterion are used at every point; values below one represent slowdowns.')
    para('More cores do not guarantee lower time. On Google, the best pure-MPI configuration is one node with p=32 and Halo: 0.149 s versus 1.896 s Serial (12.7x). At p=256 on eight nodes, pure MPI takes 0.799 s with Allgatherv and 1.462 s with Halo. The small original uniform and hub graphs show particularly poor 256-core efficiency: synchronization and contribution exchange outweigh the available per-rank work.')
    uniform=get('strong_uniform','MPI',host_nodes=8,processes=256,threads=1,communication='Halo')
    para(f"The large Uniform graph benefits from distributed resources: at 256 cores pure MPI with Halo reaches {number(uniform['speedup_vs_matched_serial']):.1f}x Serial speedup ({number(uniform['cpu_efficiency_vs_serial']):.1%} CPU efficiency). MPI+OpenMP with p=64,T=4 and Allgatherv reaches 28.3x (11.0% efficiency). The equal-size large Hub and Controlled graphs scale less well under pure MPI. Within-node dynamic OpenMP is competitive: the best hybrid results for these graphs use a single 32-thread rank, at 28.7x and 24.9x Serial speedup. These are different resource optima.")
    efficiency=[]
    for n in [1,2,4,8]:
        c=n*32; a=get('strong_uniform','MPI',host_nodes=n,processes=c,threads=1,communication='Halo')
        b=get('strong_uniform','MPI+OpenMP',host_nodes=n,processes=c//4,threads=4,communication='Allgatherv')
        efficiency.append([n,c,fmt(a['speedup_vs_matched_serial']),f"{number(a['cpu_efficiency_vs_serial']):.1%}",fmt(b['speedup_vs_matched_serial']),f"{number(b['cpu_efficiency_vs_serial']):.1%}"])
    table(['Nodes','CPU cores','MPI H speedup','MPI H efficiency','M+OMP A speedup','M+OMP A efficiency'],efficiency,[45,55,100,100,100,100])
    para('The preceding table holds the large Uniform graph fixed. MPI uses p=C,T=1; MPI+OpenMP uses p=C/4,T=4. Efficiency is speedup divided by active CPU cores. MPI phase timing includes synchronization and rank waiting as well as contribution exchange.')
    diagnostic=[]
    for c in [64,128,256]:
        r=get('strong_uniform','MPI',host_nodes=c//32,processes=c,threads=1,communication='Halo')
        raw=json.loads((ROOT/r['source_summary']).read_text())
        diagnostic.append([c,f"{number(r['solve_median_s']):.3f}",f"{number(r['communication_median_s']):.3f}",f"{number(r['communication_fraction']):.1%}",f"{number(r['communication_bytes_per_iteration'])/c/1e6:.2f}",f"{raw['max_local_edges']/(int(raw['edges'])/c):.4f}"])
    table(['Large Uniform cores','Solve s','Communication s','Median comm / solve','Payload MB / rank','Max / mean edges'],diagnostic,[90,65,90,90,85,80])
    para('Solve and communication seconds are separate five-run medians; the percentage is the median of the five communication/solve ratios. The 128-core point is communication-dominated despite near-uniform edge work. The recorded communication scope includes packing, exchange, reductions and waiting; the solve and phase timers also take separate rank maxima. The peak is therefore located in the communication/synchronization path. Collective request concurrency, placement and contention are plausible mechanisms.')
    p128=get('strong_uniform','MPI',host_nodes=4,processes=128,threads=1,communication='Halo')
    para(f"At 128 cores all five solve times lie between {number(p128['solve_min_s']):.3f} and {number(p128['solve_max_s']):.3f} s. The graph, 12-iteration convergence count and full rank vector agree with Serial, and the affinity map contains 128 distinct CPU assignments over four hosts. Its payload per rank is smaller than at 64 cores, and B_E remains near one. Extra edge work, extra iterations and a single slow repeat do not explain the peak. The communication/runtime path is the natural explanation: Alltoallv scheduling can alter peer concurrency, while NUMA (non-uniform memory access) placement and contention can alter packing, memory access and rank arrival times.")
    table(['MPI ranks','Strong comm ms / iter','Weak comm ms / iter','Weak payload MB / rank','Default tuned rule'],[
        [r['processes'],f"{number(r['strong_communication_ms_per_iteration']):.2f}",f"{number(r['weak_communication_ms_per_iteration']):.2f}",f"{number(r['weak_payload_MB_per_rank']):.2f}",r['default_tuned_source_candidate']] for r in SELECTOR],
        [60,105,105,105,125])
    para('A version-specific mechanism makes this more precise. The upstream Open MPI 4.1.8 fixed tuned selector uses pairwise Alltoallv for 64<=p<128, basic_linear for 128<=p<256, and pairwise for 256<=p<1024 [7]. Pairwise schedules rank-step exchanges; basic_linear starts peer requests together and waits for completion [8]. These are different progress/concurrency regimes even at similar byte counts. The Uniform weak series, with half the strong graph size at p=128, also shows a large 128-rank communication peak while its payload stays close to 6.35 MB/rank. The two series therefore support a collective-selection hypothesis more specifically than a byte-volume explanation.')
    para('The alignment between a rank-count selection boundary and two communication peaks makes Alltoallv scheduling a plausible contributor. A basic_linear exchange can create more concurrent peer requests than a pairwise schedule, changing progress and buffering pressure. Node placement and contention may amplify that effect. This interpretation concerns the communication implementation; the converged PageRank values and logical Halo dependencies are unchanged.')
    para('Transport protocols are a separate layer. The installation reports a TCP eager limit of 65,536 bytes. At p=128 the average counted Halo payload per remote peer is about 100 kB on the large fixed graph and 50 kB in the Uniform weak suite; at p=256 both are about 25 kB. These are mean logical contribution sizes, not wire traces. The two input sizes therefore encounter the 128-rank peak at different average message sizes, which is more consistent with a rank-dependent scheduling effect than with one average-byte threshold alone. Eager/rendezvous behavior and buffering may still interact with the chosen schedule.')

    triples=[]
    for c in (64,128,256):
        found={r['policy']:r for r in CONTROLS if r['graph']=='strong_uniform' and r['cores']==str(c)}
        if all(k in found for k in ('default','a2av_linear','a2av_pairwise')):
            assert len({r['communication_bytes_per_iteration'] for r in found.values()})==1
            triples.append((c,found))
    if triples:
        heading('Within-allocation Alltoallv policy comparison',2)
        para('The following controls keep the large Uniform graph, binary, transport, p=C, T=1 and CPU mapping fixed within each allocation. Only the tuned Alltoallv policy changes. Each value is a median of five timed solves after one warm-up; full-vector agreement is certified against an independently raw-edge-validated Serial reference using the residual bound in Section 2.5. These policy controls are separate from the 19,530-configuration main matrix.')
        table(['C / p','Default s','Fixed linear s','Fixed pairwise s','Default / pairwise'],[
            [c,fmt(r['default']['solve_median_s']),fmt(r['a2av_linear']['solve_median_s']),fmt(r['a2av_pairwise']['solve_median_s']),
             f"{number(r['default']['solve_median_s'])/number(r['a2av_pairwise']['solve_median_s']):.2f}x"] for c,r in triples], [60,100,110,115,115])
        for c,r in triples:
            a,b=r['default'],r['a2av_pairwise']
            if c==128:
                separated=number(a['solve_min_s'])>number(b['solve_max_s'])
                para(f"At p=128, fixed pairwise changes the solve median from {number(a['solve_median_s']):.3f} to {number(b['solve_median_s']):.3f} s ({number(a['solve_median_s'])/number(b['solve_median_s']):.2f}x). Fixed basic_linear takes {number(r['a2av_linear']['solve_median_s']):.3f} s. The default five-run range is {number(a['solve_min_s']):.3f}-{number(a['solve_max_s']):.3f} s; pairwise is {number(b['solve_min_s']):.3f}-{number(b['solve_max_s']):.3f} s. "+('The ranges do not overlap. ' if separated else '')+'This same-allocation contrast directly demonstrates sensitivity to the Alltoallv policy. The magnitudes characterize the tested allocation and message pattern, rather than a universal preference for one algorithm.')
                para(f"The communication/waiting median changes from {number(a['communication_median_s']):.3f} to {number(b['communication_median_s']):.3f} s, locating the improvement in the MPI path. The graph still converges in {a['iterations']} iterations. This changes the communication schedule, not the PageRank result, global-vector traffic law or equal-vertex partitioning costs.")
        if len(triples)==3:
            by_core=dict(triples)
            first,last=by_core[64],by_core[256]
            para(f"Holding basic_linear fixed changes solve time from {number(first['a2av_linear']['solve_median_s']):.3f} s at p=64 to {number(last['a2av_linear']['solve_median_s']):.3f} s at p=256, while counted Halo payload per rank falls from {number(first['a2av_linear']['communication_bytes_per_iteration'])/64/1e6:.2f} to {number(last['a2av_linear']['communication_bytes_per_iteration'])/256/1e6:.2f} MB. Fixed pairwise takes {number(first['a2av_pairwise']['solve_median_s']):.3f} and {number(last['a2av_pairwise']['solve_median_s']):.3f} s at the same endpoints. The default curve combines different communication regimes as p changes. Alltoallv fixed rules do not inspect transport or payload size; request concurrency and MPI progress on the measured TCP/Vader path are plausible reasons for these policy differences.")
            middle=by_core[128]['a2av_pairwise'];end=last['a2av_pairwise']
            if number(end['solve_median_s'])>number(middle['solve_median_s']):
                para(f"In the controlled eight-node allocation, even pairwise takes {number(end['solve_median_s']):.3f} s at p=256 versus {number(middle['solve_median_s']):.3f} s at p=128. The associated communication/waiting medians are {number(end['communication_median_s']):.3f} and {number(middle['communication_median_s']):.3f} s. Policy selection improves execution within an allocation, while additional peer participation, host/NUMA placement and shared-fabric contention can still dominate across allocations. This is a measured allocation-specific result, not a universal scaling curve for a fixed algorithm.")
        if len(triples)>=2:
            from reportlab.graphics import renderSVG
            policy_series=[[(name,[(c,number(r[key]['solve_median_s'])) for c,r in triples],color,False)
                            for name,key,color in [('Default tuned rules','default',BLUE),('Forced basic_linear','a2av_linear',ORANGE),('Forced pairwise','a2av_pairwise',TEAL)]]]
            drawing=line_panels(['Large Uniform: Alltoallv policy'],policy_series,'MPI ranks = active CPU cores','Solve seconds',[c for c,r in triples],height=240)
            renderSVG.drawToFile(drawing,str(FIG/'11_collective_policies.svg'))
            figure_number+=1
            caption=f'Figure {figure_number}. Matched Alltoallv policies on large Uniform. Five-run solve medians; each rank-count group shares an allocation and mapping.'
            story.append(KeepTogether([drawing,Paragraph(html.escape(caption),styles['CaptionReport'])]));md.append(f'![{caption}](figures/11_collective_policies.svg)\n')
    if len(LAUNCHER_CONTROLS)==2:
        heading('Launch-binding control at 256 ranks',2)
        para('Both runs use the same eight-node allocation, 32 active cores per node, p=256,T=1, the large Uniform graph and forced pairwise Alltoallv. The launch strategy is the only configured change: native Open MPI core binding versus explicit per-rank CPU masks after an unbound launch. Pre-init and post-MPI_Init affinity records verify 256 distinct one-core assignments in both cases. Each row passes the full-vector residual certificate.')
        table(['Launch binding','Solve median s','Five-run minimum s','Five-run maximum s','Comm / waiting s'],[
            ['MPI native core' if r['launcher']=='ompi_core' else 'Explicit CPU mask',*[f"{number(r[k]):.3f}" for k in ('solve_median_s','solve_min_s','solve_max_s','communication_median_s')]] for r in LAUNCHER_CONTROLS],[130,90,95,95,90])
        pair={r['launcher']:r for r in LAUNCHER_CONTROLS};a=pair['ompi_core'];b=pair['pin_wrapper'];ratio=number(b['solve_median_s'])/number(a['solve_median_s'])
        para(f"Explicit-mask/native-core solve ratio is {ratio:.2f}. Both strategies retain the requested active parallelism after MPI initialization. "+('The timing difference indicates that runtime-aware binding and rank/core ordering can affect the MPI path even with the same active-core count.' if max(ratio,1/ratio)>1.2 else 'The similar timings favor an allocation/communication-environment explanation for larger differences between separate 256-rank observations, rather than a loss of assigned cores under the explicit-mask launcher.')+' Host selection, NUMA distribution and shared-network progress remain possible mechanisms for cross-allocation variation.')
    para('The 32-to-64-core bend has three interacting mechanisms. First, all mainline methods cross from one physical node to two. Second, the T=4 hybrids change Allgatherv from Bruck at p=8 to Ring at p=16, while their Halo Alltoallv stays basic_linear; pure MPI instead changes Alltoallv from basic_linear at p=32 to pairwise at p=64. Third, concentrating 75%-77.5% of edges in the first 1% of destination IDs means doubling ranks barely relieves the busiest rank. For Hub, its edge share falls only from 77.90% to 76.33% at p=8-to-16; Controlled falls from 80.11% to 78.69%. Most extra ranks receive cold rows. Inter-node exchange and synchronization can therefore increase while the heavy rank gets almost the same edge work.')
    para('The partition boundary explains this quantitatively. The hot destination block has 128,000 vertices; an equal-vertex partition keeps the entire block in one MPI rank while p<=100. It first spans two ranks at p=128 and three at p=256. The T=4 mainline reaches only p=64 at C=256, so the dominant hot block stays within one four-thread rank throughout that line. More active cores mainly subdivide cold rows. The balanced Uniform graph is therefore used for the Alltoallv policy contrast, while Hub/Controlled diagnose this separate work-distribution mechanism.')
    para('The same equal-range work model explains why Kokkos OpenMP can track pure MPI on these graphs. Static destination ranges give one/one/two/three workers access to the hot block at C=32/64/128/256, respectively. Dynamic OpenMP can share the hot rows among the four workers of the loaded rank even before an MPI partition boundary crosses that block. This is a scheduling-and-ordering mechanism, rather than an intrinsic cost assigned to the Kokkos API.')
    worker_model=[]
    for graph in ('strong_hub','strong_controlled'):
        for c in (32,64,128,256):
            static=next(r for r in WORK if r['graph']==graph and r['processes']==str(c))
            rank=next(r for r in WORK if r['graph']==graph and r['processes']==str(c//4))
            omp=get(graph,'MPI+OpenMP',host_nodes=c//32,processes=c//4,threads=4,communication='Allgatherv')
            kk=get(graph,'MPI+Kokkos OpenMP',host_nodes=c//32,processes=c//4,threads=4,communication='Allgatherv')
            proxy=4*number(static['max_rank_edge_share'])/number(rank['max_rank_edge_share'])
            worker_model.append([DISPLAY[graph],c,f"{proxy:.2f}",f"{number(kk['solve_median_s'])/number(omp['solve_median_s']):.2f}"])
    table(['Graph','C','Static / dynamic worker-edge proxy','Observed KK / OMP solve'],worker_model,[120,40,180,160])
    para('The proxy is 4*w(C)/w(C/4), where w(q) is the busiest equal-vertex block share with q blocks. It assumes equal edge-processing rates and ideal four-thread dynamic sharing within the loaded rank. Main-matrix matched-layout medians use T=4 and Allgatherv. The shrinking measured gap broadly follows the work model; static chunk rounding, vertex/reduction work and memory locality can also affect the ratio. This supports a scheduling explanation without assigning every timing difference to framework overhead.')
    para('This mechanism also explains why the two communication modes may bend together: rank imbalance delays global reductions in both, and the first inter-node boundary affects both. An Alltoallv algorithm transition alone would not explain an Allgatherv slowdown or a T=4 Halo bend at C=64. CPU cache/NUMA locality, collective scheduling and shared-resource contention may further change the size of the bend.')
    gather_controls=[]
    for graph in ('strong_hub','strong_controlled'):
        for c in (32,64,128):
            found={r['policy']:r for r in CONTROLS if r['graph']==graph and r['cores']==str(c) and r['implementation']=='hybrid' and r['communication']=='allgather'}
            if all(k in found for k in ('default','agv_bruck','agv_ring')):
                gather_controls.append((graph,c,found))
    if gather_controls:
        heading('Matched Allgatherv policies across the node boundary',2)
        para('MPI+OpenMP uses T=4 and all C active cores, on one/two/four nodes at C=32/64/128. Each row compares three policies within the same allocation; the graphs and convergence settings are fixed. Ratios compare forced Ring with forced Bruck and expose policy sensitivity separately from the default rule change.')
        table(['Graph','C / p','Default s','Bruck s','Ring s','Bruck / Ring'],[
            [DISPLAY[g],str(c)+' / '+str(c//4),fmt(r['default']['solve_median_s']),fmt(r['agv_bruck']['solve_median_s']),fmt(r['agv_ring']['solve_median_s']),
             f"{number(r['agv_bruck']['solve_median_s'])/number(r['agv_ring']['solve_median_s']):.2f}x"] for g,c,r in gather_controls],[115,65,80,80,80,80])
        if len(gather_controls)==6:
            for graph in ('strong_hub','strong_controlled'):
                measured={c:r for g,c,r in gather_controls if g==graph}
                ratios={key:number(measured[64][key]['solve_median_s'])/number(measured[32][key]['solve_median_s']) for key in ('default','agv_bruck','agv_ring')}
                separated=all(number(measured[64][key]['solve_min_s'])>number(measured[32][key]['solve_max_s']) for key in ('agv_bruck','agv_ring'))
                para(f"For {DISPLAY[graph]}, the C64/C32 time ratios are {ratios['default']:.2f} under default selection, {ratios['agv_bruck']:.2f} with Bruck fixed, and {ratios['agv_ring']:.2f} with Ring fixed. "+
                     ('The five-run ranges increase with both algorithms held fixed, so the collective rule switch does not by itself explain the node-boundary bend. The nearly unchanged hot-rank edge work and added inter-node synchronization are consistent mechanisms.' if separated else
                      'The modest changes should be read alongside the five-run ranges. The hot rank receives almost the same edge work despite twice the active cores, so an almost flat curve is consistent with the partition model. Inter-node exchange, locality and shared-resource effects may offset the remaining work reduction.'))
                r=measured[64]
                if number(r['agv_bruck']['solve_median_s'])>=number(r['agv_ring']['solve_median_s']):
                    para(f"At C=64, default selection takes {number(r['default']['solve_median_s']):.3f} s and fixed Ring {number(r['agv_ring']['solve_median_s']):.3f} s; fixed Bruck takes {number(r['agv_bruck']['solve_median_s']):.3f} s. Reverting to the p=8 Bruck policy does not improve this point. The 64-core behavior therefore differs from the Uniform p128 Alltoallv case: a default algorithm change is not automatically an inferior choice.")
            from reportlab.graphics import renderSVG
            series=[]
            for graph in ('strong_hub','strong_controlled'):
                series.append([(name,[(c,number(r[key]['solve_median_s'])) for g,c,r in gather_controls if g==graph],color,False)
                    for name,key,color in [('Default','default',BLUE),('Forced Bruck','agv_bruck',ORANGE),('Forced Ring','agv_ring',TEAL)]])
            drawing=line_panels(['Large Hub','Large Controlled'],series,'Active CPU cores; T=4','Solve seconds',[32,64,128],height=240,shared_y=True)
            renderSVG.drawToFile(drawing,str(FIG/'12_allgatherv_policies.svg'))
            figure_number+=1
            caption=f'Figure {figure_number}. MPI+OpenMP Allgatherv policy controls. C=32/64/128 uses one/two/four nodes with T=4 and p=C/4; panels share the same solve-time range.'
            story.append(KeepTogether([drawing,Paragraph(html.escape(caption),styles['CaptionReport'])]));md.append(f'![{caption}](figures/12_allgatherv_policies.svg)\n')
    node_controls=[]
    for graph in ('strong_hub','strong_controlled'):
        for method,label in [('mpi','MPI'),('hybrid','MPI+OMP'),('mpi_kokkos','MPI+KK OpenMP')]:
            for mode,short in [('allgather','A'),('halo','H')]:
                selected={int(r['cores']):r for r in CONTROLS if r['graph']==graph and r['implementation']==method and r['communication']==mode and r['policy']=='default'}
                if all(c in selected for c in (32,64,128)):
                    node_controls.append([DISPLAY[graph],label+' '+short,*[fmt(selected[c]['solve_median_s']) for c in (32,64,128)],
                        f"{number(selected[64]['solve_median_s'])/number(selected[32]['solve_median_s']):.2f}"])
    if node_controls:
        heading('Matched default-policy node-count controls',2)
        para('The node-boundary panel covers both exchange modes and all three CPU MPI implementations on the two concentrated large graphs. MPI uses p=C,T=1; hybrid methods use p=C/4,T=4. All nodes contribute 32 active cores, with n=1/2/4 at C=32/64/128. Each displayed line has all three independently certified points. C64/C32 above one is a slowdown despite twice the active resources; this is distinct from the same-allocation forced-policy contrasts above.')
        table(['Graph','Method / mode','C32 s','C64 s','C128 s','C64 / C32'],node_controls,[100,120,70,70,70,70])
        if len(node_controls)==12:
            ratios=[float(row[-1]) for row in node_controls]
            para(f"Across these twelve matched method/mode lines, C64/C32 solve ratios range from {min(ratios):.2f} to {max(ratios):.2f}. The node-boundary controls therefore show approximately flat scaling rather than a consistent large 64-core penalty. The limited reduction in hot-rank work explains why doubling active resources need not improve time; inter-node progress, memory locality and shared-resource effects can determine the smaller differences.")
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
    para('The split has a workload effect as well as a message effect. With ideal sharing of each rank\'s edge work over T threads, the edge-only equivalent core count is T*E/max(E_i)=C/B_E(p). For large Hub at C=256 this proxy rises from 3.4 with p256,T1 to about 41 with p8,T32: dynamic threads can share the hot rows owned by one rank. Static contiguous thread subdivision can preserve the original edge skew even as ranks decrease. This explains why fewer ranks plus more threads is a substantive design choice. C verifies assigned parallelism; it does not imply C equally productive workers, and the proxy does not predict a measured runtime by itself.')

    heading('3.5 Allgatherv versus exact Halo exchange',2)
    figure('05_halo_pairs','Figure 5. Within-layout paired ratios, excluding p=1. Left: geometric-mean Allgatherv/Halo solve-time ratio (>1 favors Halo). Right: median reduction in counted contribution payload. CPU and GPU-node aggregates have different method/configuration populations and are not direct hardware comparisons.')
    rows=[]
    for x in HALO:rows.append([x['context'].replace('_',' '),x['family'],x['paired_configurations'],fmt(x['geomean_halo_speedup']),f"{number(x['median_payload_reduction']):.1%}",f"{number(x['halo_faster_fraction']):.1%}"])
    table(['Context','Family','Pairs','Halo speedup','Payload reduction','Halo faster'],rows,[90,76,45,89,105,95])
    para('On CPU, Google has the strongest aggregate Halo gain: 1.89x geometric-mean speedup over 179 paired configurations and 58.6% median payload reduction. Uniform, Hub and Controlled show 1.19-1.23x aggregate gains, but many individual configurations still favor Allgatherv. On GPU nodes, the two-rank Halo ensembles have ratios below one. Small p, host staging, packing and synchronization constrain gains; one-time Halo setup is excluded from solve time. Thus its setup cost cannot explain a measured solve-time slowdown.')
    para('Halo exploits repeated use of the same remote source by local destination rows: each distinct remote contribution is sent once. It does not communicate a fixed spatial boundary on these non-geometric graphs. Uniform edges spread dependencies widely; skewed destination rows can reuse more source IDs and reduce payload substantially, yet also concentrate computation. Payload savings and workload balance are different properties. The paired ratios hold graph and p/T fixed, but separate allocations can still differ in placement and contention; the comparison does not isolate a pure network-bandwidth effect.')
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
    table(['Large graph','Backend','p2 max edge share','Compute speedup 1 to 2','Solve p1 s','Solve p2 s'],[
        [DISPLAY[r['graph']].replace('Large ',''),'CUDA' if r['method']=='MPI+CUDA' else 'Kokkos CUDA',f"{number(r['p2_max_edge_share']):.1%}",fmt(r['compute_speedup']),fmt(r['p1_solve_s']),fmt(r['p2_solve_s'])] for r in GPU_WORK],
        [90,90,90,100,65,65])
    cu=next(r for r in GPU_WORK if r['graph']=='strong_controlled' and r['method']=='MPI+CUDA')
    kk=next(r for r in GPU_WORK if r['graph']=='strong_controlled' and r['method']=='MPI+Kokkos CUDA')
    para(f"The two-rank partition leaves {number(cu['p2_max_edge_share']):.1%} of Controlled edges on one GPU. Under equal edge-processing rates, the edge-only speedup proxy is just {number(cu['equal_edge_rate_speedup_proxy']):.2f}x; native CUDA's measured compute speedup is {number(cu['compute_speedup']):.2f}x. Its compute median falls from {fmt(cu['p1_compute_s'])} to {fmt(cu['p2_compute_s'])} s, while Allgatherv communication rises from {fmt(cu['p1_communication_s'])} to {fmt(cu['p2_communication_s'])} s and solve time increases. Uniform instead divides edges nearly in half and both backends achieve about 2x compute acceleration. The structure of the partition therefore explains a concrete part of native CUDA's scaling limit.")
    para(f"Kokkos CUDA on Controlled reduces compute from {fmt(kk['p1_compute_s'])} to {fmt(kk['p2_compute_s'])} s and staging from {fmt(kk['p1_transfer_s'])} to {fmt(kk['p2_transfer_s'])} s; its solve improves despite rising communication. Its {number(kk['compute_speedup']):.2f}x compute change exceeds the equal-edge-rate proxy. That proxy is not a universal runtime bound: vertex reductions, kernel mapping and memory locality also change with partition size. The records cannot separate those contributions. Both device implementations traverse each incoming row within one GPU work item; a team/warp-per-row variant would test the remaining long-row bottleneck, but is not measured here.")
    heading('3.7 Weak scaling',2)
    figure('07_core_weak','Figure 8. Top: pure MPI weak scaling, with N and E proportional to ranks and the one-rank point as baseline. Bottom: core-normalized hybrid weak scaling with T=4, p=C/4 and the four-core point as baseline. Both show baseline per-iteration time divided by measured per-iteration time; ideal efficiency is 100%. No 512-core endpoints are shown.')
    pure=[]
    for family in ['uniform','hub','controlled']:
        r=[x for x in WEAK if x['suite']=='rank_cpu_regular' and x['method']=='MPI' and x['family']==family and x['processes']=='256']
        pure.append([family,*[f"{number(next(x for x in r if x['communication']==mode)['weak_efficiency_per_iteration']):.2%}" for mode in ['Allgatherv','Halo']],
            *[f"{number(next(x for x in TRAFFIC if x['family']==family and x['processes']=='256' and x['communication']==mode)['weak_efficiency_vs_p32_per_iteration']):.2%}" for mode in ['Allgatherv','Halo']]])
    table(['MPI at p=256','Allgatherv: p1 ref','Halo: p1 ref','Allgatherv: p32 ref','Halo: p32 ref'],pure,[100]*5)
    para('The primary weak-efficiency reference is p=1, where contribution exchange has no remote payload. The p=32 columns are a baseline-sensitivity analysis of the same saved series, with inter-rank communication already present. They quantify further degradation from 32 to 256 ranks without replacing the primary definition. Baseline choice changes the percentage; neither comparison supports near-ideal scaling.')
    para('Rank-normalized weak scaling keeps nominal local vertices and edges constant, but not the communication problem: the global contribution vector and collective participant count grow with resources. On the concentrated families, equal vertex partitions also produce severe incoming-edge imbalance. Communication timers include waiting for slow ranks and cannot be interpreted solely as network transmission time.')
    rows=[]
    for f in ('uniform','hub','controlled'):
        for m in ('MPI+OpenMP','MPI+Kokkos OpenMP'):
            a=[r for r in WEAK if r['suite']=='core_cpu' and r['family']==f and r['method']==m and int(r['active_cpu_threads'])==256]
            rows.append([f,m,*[f"{number(next(r for r in a if r['communication']==mode)['weak_efficiency_per_iteration']):.2%}" for mode in ('Allgatherv','Halo')]])
    table(['Family','Method','C256 Allgatherv efficiency','C256 Halo efficiency'],rows,[90,160,125,125])
    para('Weak scaling is poor despite constant nominal work per core. At C=256, the core-normalized uniform curves retain roughly 3.6-4.2% per-iteration efficiency; the skewed families are around 0.7-1.4%. Replicated vectors and global synchronization grow with resource count, while equal-vertex partitioning does not preserve equal incoming-edge work on the concentrated families. These measurements reject a claim of near-ideal weak scaling. They motivate a future edge-aware partitioner and communication/staging redesign; they do not establish which unimplemented change would be fastest.')
    para('The weak-scaling problem is structural for Allgatherv. With N=n0*p and E=e0*p, nominal local graph work is fixed, but each rank receives 8*n0*(p-1) contribution bytes and stores an O(p*n0) source vector. Aggregate counted traffic is O(p^2); dividing time by the iteration count cannot remove this communication growth. At p=256 the Uniform contribution vector costs 102.0 MB per rank per iteration, despite only 50,000 owned vertices.')
    para('Halo improves the byte scaling: a rank needs no more distinct remote sources than its incoming edges, so for balanced Uniform its counted payload is bounded by roughly 8*800,000=6.4 MB per rank. Observed Halo payload grows only from 6.30 to 6.37 MB between p=64 and 256, yet communication/waiting rises from 17.28 to 38.07 ms per iteration. Growing peer participation, collective/reduction latency, packing and resource contention remain plausible; a byte-only model is insufficient. On Hub and Controlled, nominal work per rank also hides a 75x-78x busiest-rank excess at p=256, so their near-zero efficiency has an additional load-balance mechanism. A high MPI timer on these graphs includes fast ranks waiting for the loaded ranks.')
    figure('10_scaling_mechanisms','Figure 9. Mechanism diagnostics derived from saved measurements. Top: large-graph maximum/mean incoming edges per rank. Bottom left: Uniform weak-suite counted contribution payload per rank, excluding p=1 where it is zero. Bottom right: five-run median communication/waiting time per iteration. All axes are logarithmic. Byte counts exclude reductions and transport overhead; they are not measured link throughput.')
    uniform_traffic=[r for r in TRAFFIC if r['family']=='uniform' and int(r['processes']) in [16,64,256]]
    table(['Uniform ranks','Communication','Payload MB / rank','Comm + waiting ms / iter'],[
        [r['processes'],r['communication'],f"{number(r['counted_payload_bytes_per_rank'])/1e6:.2f}",f"{number(r['communication_ms_per_iteration']):.2f}"] for r in uniform_traffic],
        [85,125,135,155])
    story.append(PageBreak())
    heading('3.8 Full fixed-graph result matrix',2)
    para('The two tables contain all 45 graphs and each method\'s best observed five-run solve median (s). Cells may select different node counts, p/T and communication. Selected configurations are in runtime_matrix_45.csv; these envelopes complement the matched-layout and equal-core comparisons above. CPU-S and GPU-S are different matched Serial controls.')
    table(['Graph','CPU-S','OMP','KK-O','MPI','M-O','M-KO','512*'],[
        [abbreviated(r['graph']),*[fmt(r[m+'_best_s']) for m in ('Serial','OpenMP','Kokkos OpenMP','MPI','MPI+OpenMP','MPI+Kokkos OpenMP')],fmt(r['512_partial_best_s']) if r['512_partial_best_s']!='-' else '-'] for r in MATRIX],
        [94]+[58]*7,small=True)
    para('CPU-node methods. KK=Kokkos; M=MPI; O=OpenMP. U/H/C identify graph families, then vertices and mean out-degree; o./s. mean original/canonical. 512* is the best of five available cases on C 50k/4, not a complete comparison. A hyphen marks unmeasured cells.')
    story.append(PageBreak())
    table(['Graph','GPU-S','CUDA','KK-CUDA','MPI+CUDA','MPI+KK CUDA'],[
        [abbreviated(r['graph']),fmt(r['GPU-node Serial_s']),*[fmt(r[m+'_best_s']) for m in ('CUDA','Kokkos CUDA','MPI+CUDA','MPI+Kokkos CUDA')]] for r in MATRIX],
        [110]+[78]*5,small=True)
    para('GPU-node device methods and their own Serial control. Five-run median solve times (s); the distributed variants select over one/two GPUs and both communication modes. CPU controls on GPU nodes remain in the full record export and the optimum-count analysis below.')
    story.append(PageBreak())
    figure('09_runtime_matrix','Figure 10. Full 45-graph best-observed speedup matrix. CPU-node and GPU-node methods use their own matched Serial references. Color is log-scaled and clipped at 1/16x and 64x; exact timings and selected layouts are in the CSV. The resource budget can differ between cells.')
    cpu=OPTIMA['cpu_all'];device=OPTIMA['gpu_device_only'];controls=OPTIMA['gpu_with_cpu_controls']

    story.append(PageBreak())
    heading('3.9 Partial 512-core supplement',2)
    para('The complete main matrix stops at 256 CPU cores. The supplement below contains five validated 512-core configurations out of 1,170 planned combinations, all on Controlled N=50,000 and E=200,000. Each uses eight nodes with 64 active cores per node. Missing methods, layouts and graphs are unmeasured, not zero-time results.')
    table(['Method','p / T','Communication','Solve s','Speedup','Efficiency'],[
        [x['method'],x['processes']+' / '+x['threads'],x['communication'],fmt(x['solve_median_s']),fmt(x['speedup']),f"{number(x['efficiency']):.3%}"] for x in SUPPLEMENT], [130,55,90,65,70,90])
    para('Every row reports the median of five timed runs after one warm-up and uses the matching CPU Serial baseline. All five cases are slower than Serial on this small graph, and Halo is particularly costly at p=512. This illustrates the cost of distributing a small workload; five cases on one graph do not support a general conclusion about 512-core scaling. This supplement is excluded from the main matrix best-time selection, geometric communication aggregates and weak-scaling curves.')

    heading('4 Conclusions and insights')
    heading('4.1 What the experiments establish',2)
    para(f"On CPU nodes, standalone OpenMP or Kokkos OpenMP is fastest on {cpu['method_counts'].get('OpenMP',0)+cpu['method_counts'].get('Kokkos OpenMP',0)}/45 graphs; only {cpu['multirank_winners']} winning configurations use multiple MPI ranks. Among the four actual GPU implementations, standalone CUDA/Kokkos CUDA wins all 45 graphs. With the GPU-node CPU controls included, however, OpenMP wins {controls['method_counts'].get('OpenMP',0)}/45 graphs, native CUDA {controls['method_counts'].get('CUDA',0)}, and Kokkos CUDA {controls['method_counts'].get('Kokkos CUDA',0)}. These are observed optima over different budgets, not hardware cost rankings. The result supports graph-dependent selection and does not justify a general claim that GPU-node workloads always favor GPU computation.")
    para('First, parallel degree is a choice, not a target to maximize unconditionally. Large balanced graphs exploit multiple nodes; small graphs and concentrated destination rows often favor fewer MPI ranks and more threads within a rank. At fixed 256 cores, rank/thread decomposition can change aggregate runtime by more than an order of magnitude.')
    para('Second, an exact Halo reduces contribution payload without guaranteeing faster execution. CPU and GPU-node observations differ, and even within the CPU matrix the large-graph best communication mode changes with structure and p/T. Communication must be evaluated with matched layouts and actual time, not bytes alone.')
    para('Third, Kokkos provides the same algorithm on CPU and GPU backends, while backend policy, staging and vertex work imbalance determine performance. The distributed device path has a substantial cost even at p=1. Multi-GPU performance cannot be inferred from a fast standalone kernel.')
    para('Fourth, equal-vertex partitioning is a clear structural limitation: extreme incoming-edge imbalance and weak-scaling degradation remain after all numerical checks pass. Edge-aware or reordered partitions, selective device/host staging, CUDA-aware MPI and overlap are reasonable future experiments. None is claimed as implemented or measured here.')
    control128=next((r for c,r in triples if c==128),None)
    if control128:
        para(f"The matched p=128 control also establishes that the communication policy is consequential: fixed pairwise takes {number(control128['a2av_pairwise']['solve_median_s']):.3f} s versus {number(control128['default']['solve_median_s']):.3f} s under default rules, a {number(control128['default']['solve_median_s'])/number(control128['a2av_pairwise']['solve_median_s']):.2f}x improvement with the graph, active cores, mapping and binary unchanged. Collective implementation is therefore an experimental parameter, rather than a universally optimal runtime detail.")
    heading('4.2 Mechanisms behind the scaling patterns',2)
    peak_evidence='Both fixed-graph and weak-scaling series peak at p128. The fixed tuned rule changes pairwise-to-basic_linear-to-pairwise across p64/128/256.'
    peak_mechanism='A change in request concurrency and MPI progress is a plausible contributor, potentially interacting with placement and contention.'
    if control128:
        peak_evidence=f"Same-allocation p128 controls: default {number(control128['default']['solve_median_s']):.3f} s, fixed linear {number(control128['a2av_linear']['solve_median_s']):.3f} s, fixed pairwise {number(control128['a2av_pairwise']['solve_median_s']):.3f} s. All three pass independent vector/residual certificates."
        peak_mechanism='The fixed-algorithm comparison demonstrates a large policy effect. Request concurrency, buffering and MPI progress are possible implementation mechanisms; the graph and parallel degree are held fixed.'
    boundary_evidence='The mainline crosses from one node to two; hybrid p=8-to-16 changes Allgatherv from Bruck to Ring. The busiest hybrid rank still owns 76%-79% of the edges.'
    boundary_mechanism='More nodes introduce inter-node traffic while the hot rank receives little work relief. Collective scheduling and NUMA/locality may affect the crossover.'
    if len(gather_controls)==6:
        boundary_evidence='Matched C64 Allgatherv controls favor Ring over Bruck. The hot rank still owns 76%-79% of the edges; doubling ranks barely changes its work.'
        boundary_mechanism='Reverting the default algorithm does not improve this point. Limited useful-work relief, inter-node progress and locality explain an almost flat or non-monotonic resource curve.'
    table(['Observation','Quantitative evidence','Mechanism and interpretation'],[
        ['Skewed graphs scale poorly','At p=256, one rank owns 29%-30% of all edges; default static worker ranges also align with the hot destination block.','Equal-vertex ownership concentrates edge work. Static local scheduling may concentrate it again within a rank; dynamic chunks redistribute destination rows.'],
        ['32-to-64-core bend',boundary_evidence,boundary_mechanism],
        ['Uniform Halo peak at p=128',peak_evidence,peak_mechanism],
        ['Poor weak efficiency','Allgatherv per-rank vector traffic grows with p. Halo caps Uniform contribution bytes near 6.4 MB/rank, while the number of peers and global reductions still grows.','Constant nominal local work does not keep communication constant. Skewed inputs add slow-rank waiting to the collective cost.'],
        ['Two GPUs do not always improve solve time','Native CUDA at p2 leaves 87%-89% of all edges on one rank; measured compute relief is about 1.1x.','The hot GPU remains the critical worker; added host staging and MPI exchange can exceed the saved compute time. Backend mapping and locality also affect Kokkos.']],
        [100,200,200])
    para('The measured edge distribution, source-level scheduling and counted traffic establish concrete mechanisms. Matched policy controls quantify the effect of a collective setting where available. NUMA/cache locality, protocol buffering and shared-resource contention can interact with the message schedule to produce further non-monotonic behavior. Their practical importance depends on graph structure and rank/thread decomposition.')
    para('Optimization priority follows the evidence. For Hub/Controlled, first redistribute incoming-edge work and test dynamic or team-based row scheduling; reducing bytes alone leaves the straggler in place. For balanced Uniform, first separate collective latency, packing and staging, then test overlap or transport settings. An edge-balanced partition must also be checked for increased remote-source dependencies: balancing computation can worsen communication. Finally, an MPI speedup on one large graph should not replace a simple one-node method on the many smaller graphs where it loses.')
    heading('4.3 Conclusions about the real Google graph',2)
    para(f"The validated Google Serial vector has {GOOGLE['dangling_vertices']:,} dangling vertices ({GOOGLE['dangling_vertices']/GOOGLE['vertices']:.1%}), so dangling-mass redistribution is essential. The highest-scoring 1% of vertices carry {GOOGLE['top_1_percent_rank_mass']:.1%} of the total probability mass. Pearson correlation between PageRank and in-degree is {GOOGLE['pagerank_indegree_pearson']:.3f}: incoming links are strongly associated with rank, but raw in-degree is not the complete weighting rule.")
    table(['Node ID','PageRank','In-degree','Out-degree'],[[r['node_id'],f"{r['rank']:.7f}",r['in_degree'],r['out_degree']] for r in GOOGLE['top10'][:5]], [120,140,120,120])
    para('These anonymized vertex IDs cannot be mapped to named websites from this edge-list dataset alone. The observed rank concentration supports a structural statement about this graph; it does not identify trustworthy content or establish a causal relationship between links and importance.')
    heading('4.4 Scope and reproducibility',2)
    para('This report presents a complete Vanda main matrix, matched collective-policy controls and a separate partial 512-core supplement. Each configuration uses five timed repeats within an allocation, with CPU models and rank/core maps retained. Placement, NUMA regions and execution dates vary across shared-cluster allocations. The reported solve metric covers iterative computation, communication and device staging; job startup and graph I/O are tracked separately for resource budgeting. GPU comparisons cover one and two A40 devices. The 512-core table describes its five specified configurations on one graph.')
    para('Reproduction: analyze_report_results.py reads the validated inventory and referenced summaries/timings; analyze_collective_controls.py exports the separately certified policy controls; build_non512_report.py produces this PDF, editable report text, ten baseline vector figures and the paired-control SVG plots. The exported fixed, weak and partial-512 tables map measurements to source summaries and validation markers. Additional diagnostic tables retain rank-edge shares, static-block proxies, weak payload/phase medians, GPU work changes and the three explicitly defined optimum populations. The selection file records 27 selected sources. Raw records are preserved; audit.json records manifest and selection SHA-256 values. No new performance run is required to reproduce these derivations.')
    heading('4.5 References',2)
    for reference in [
        '[1] Page, L., Brin, S., Motwani, R. and Winograd, T. The PageRank Citation Ranking: Bringing Order to the Web. Stanford, 1999. http://ilpubs.stanford.edu:8090/422/',
        '[2] Stanford SNAP. Google web graph dataset. https://snap.stanford.edu/data/web-Google.html',
        '[3] MPI Forum. MPI standard and collective communication. https://www.mpi-forum.org/docs/',
        '[4] Kokkos documentation. RangePolicy and execution policies. https://kokkos.org/kokkos-core-wiki/API/core/policies/RangePolicy.html',
        f'[5] Project source and Vanda result records, report data snapshot compiled {REPORT_DATE}. https://github.com/rosesnack/DSA5208_PROJECT_3',
        '[6] Kokkos 4.5.01 source, commit 175257a51ff29a0059ec48bcd233ee096b2c0438: traits/Kokkos_ScheduleTrait.hpp and OpenMP/Kokkos_OpenMP_Parallel_Reduce.hpp. https://github.com/kokkos/kokkos/tree/4.5.01/core/src',
        '[7] Open MPI v4.1.8. Fixed Alltoallv and Allgatherv algorithm selection, coll_tuned_decision_fixed.c. https://github.com/open-mpi/ompi/blob/v4.1.8/ompi/mca/coll/tuned/coll_tuned_decision_fixed.c',
        '[8] Open MPI v4.1.8. Pairwise and basic-linear implementations, coll_base_alltoallv.c. https://github.com/open-mpi/ompi/blob/v4.1.8/ompi/mca/coll/base/coll_base_alltoallv.c',
        '[9] Open MPI v4.1.8. Forced collective algorithm parameters, coll_tuned_alltoallv_decision.c and coll_tuned_allgatherv_decision.c. https://github.com/open-mpi/ompi/tree/v4.1.8/ompi/mca/coll/tuned']:
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
    print('Ten baseline vector figures; validated collective controls add paired tables and SVG plots; four report sections and a separate partial 512 supplement.')


if __name__=='__main__':
    main()
