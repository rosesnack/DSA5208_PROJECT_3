"""Create the four-section report and vector figures from audited CSV tables.

Run analyze_results.py and analyze_controls.py first. Uses ReportLab Graphics for scientific
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

from report_latex_equations import LatexEquations
from report_result_views import growing_cpu, payload_by_process, write_view

from reportlab.graphics import renderPDF
from reportlab.graphics.charts.axes import LogXValueAxis, LogYValueAxis
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Line, Rect, String, Group, Circle
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                               TableStyle, PageBreak, KeepTogether)

REPORT_DATE = datetime.now(ZoneInfo('Asia/Singapore')).strftime('%d %B %Y')
ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'report_assets'
DATA = ROOT / 'results/tables'
FIG = REPORT / 'figures'
PDF = ROOT / 'report.pdf'
PROJECT_URL = 'https://github.com/rosesnack/DSA5208_PROJECT_3'
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
GROWING = growing_cpu(WEAK)
PAYLOAD_BY_PROCESS = payload_by_process(FIXED)
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


def control_ranges(titles, panels, policies, x_label):
    drawing=Drawing(500,265)
    ymax=math.ceil(max(number(row['solve_max_s']) for panel in panels for policies_at_c in panel.values()
                       for row in policies_at_c.values())*1.12)
    width=500/len(panels);bottom=54;plot_height=155
    for panel_index,(title,panel) in enumerate(zip(titles,panels)):
        left=panel_index*width+38;plot_width=width-54
        ticks=sorted(panel);xmin,xmax=math.log2(ticks[0]),math.log2(ticks[-1])
        def x(value):return left+(math.log2(value)-xmin)/(xmax-xmin)*plot_width
        def y(value):return bottom+value/ymax*plot_height
        for i in range(5):
            value=ymax*i/4;yy=y(value)
            drawing.add(Line(left,yy,left+plot_width,yy,strokeColor=colors.HexColor('#e1e6e9'),strokeWidth=.4))
            drawing.add(String(left-5,yy-2,f'{value:g}',fontName='Helvetica',fontSize=7,textAnchor='end',fillColor=INK))
        drawing.add(Line(left,bottom,left,bottom+plot_height,strokeColor=GRAY,strokeWidth=.6))
        for c in ticks:drawing.add(String(x(c),bottom-13,str(c),fontName='Helvetica',fontSize=7,textAnchor='middle',fillColor=INK))
        for policy_index,(label,key,color) in enumerate(policies):
            previous=None
            for c in ticks:
                r=panel[c][key];xx=x(c)+(policy_index-1)*3
                low,median,high=[y(number(r[k])) for k in ('solve_min_s','solve_median_s','solve_max_s')]
                if previous:drawing.add(Line(*previous,xx,median,strokeColor=color,strokeWidth=1.1))
                drawing.add(Line(xx,low,xx,high,strokeColor=color,strokeWidth=.8))
                for yy in (low,high):drawing.add(Line(xx-2,yy,xx+2,yy,strokeColor=color,strokeWidth=.8))
                drawing.add(Circle(xx,median,2,fillColor=color,strokeColor=color))
                previous=(xx,median)
        drawing.add(String(panel_index*width+width/2,246,title,fontName='Helvetica-Bold',fontSize=9,textAnchor='middle',fillColor=INK))
        drawing.add(String(left,230,'Solve time (s)',fontName='Helvetica',fontSize=7,fillColor=GRAY))
        drawing.add(String(panel_index*width+width/2,25,x_label,fontName='Helvetica',fontSize=7,textAnchor='middle',fillColor=GRAY))
    legend(drawing,[p[0] for p in policies],[p[2] for p in policies],columns=3,y=9)
    return drawing


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
    result['01_serial_grid']=line_panels(['Uniform','Hub','Controlled'],serial,'Vertices N (count)','Solve time (s)',
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
        speed=line_panels([DISPLAY[g] for g in graphs],panels,'Active CPU cores C (count)',
                          'Speedup vs Serial (×)',[4,16,64,256],shared_y=True,height=250)
        efficiency=[[(label,[(c,y/c) for c,y in points],color,dash)
                     for label,points,color,dash in panel] for panel in panels]
        eff=line_panels([DISPLAY[g] for g in graphs],efficiency,'Active CPU cores C (count)',
                        'CPU efficiency (%)',[4,16,64,256],shared_y=True,height=250,
                        y_format=lambda v:f'{v:.1%}')
        combined=Drawing(500,530)
        group=Group(*speed.contents);group.translate(0,275);combined.add(group)
        combined.add(Group(*eff.contents));result[name]=combined
    series=[]
    for method,label,color in [('MPI+OpenMP','M+OMP',ORANGE),('MPI+Kokkos OpenMP','M+KK',TEAL)]:
        for mode in ('Allgatherv','Halo'):
            rows=[r for r in SPLITS if r['method']==method and r['communication']==mode]
            series.append((label+(' A' if mode=='Allgatherv' else ' H'),
                           [(int(r['threads']),number(r['geomean_speedup_vs_T1'])) for r in rows],color,mode=='Halo'))
    result['04_fixed_256_splits']=line_panels(['Fixed 256 cores across all 45 graphs'],[series],
        'Threads per rank T (p=256/T)','Geometric-mean speedup vs T=1 (×)',[1,2,4,8,16,32])
    d=Drawing(500,245)
    for j,(key,title) in enumerate([('geomean_halo_speedup','Halo speedup (×)'),
                                     ('median_payload_reduction','Median payload reduction (%)')]):
        bar=VerticalBarChart();bar.x=j*250+35;bar.y=49;bar.width=205;bar.height=150
        bar.data=[[number(next(r for r in HALO if r['context']==ctx and r['family']==f)[key])
                   for f in ('google','uniform','hub','controlled')] for ctx in ('cpu_node','gpu_node')]
        bar.categoryAxis.categoryNames=['Google','Uniform','Hub','Ctrl']
        bar.categoryAxis.labels.fontSize=7;bar.valueAxis.labels.fontSize=7
        bar.valueAxis.valueMin=0;bar.bars[0].fillColor=BLUE;bar.bars[1].fillColor=ORANGE
        bar.bars.strokeWidth=0;bar.valueAxis.visibleGrid=True;bar.valueAxis.gridStrokeColor=colors.HexColor('#e1e6e9')
        maximum=max(v for series in bar.data for v in series)
        bar.valueAxis.valueMax=1 if j else maximum*1.17
        if j:bar.valueAxis.labelTextFormat=lambda v:f'{v:.0%}'
        # Explicit values keep a measured zero visible instead of looking absent.
        for category in range(4):
            center=bar.x+(category+.5)*bar.width/4
            for population in range(2):
                value=bar.data[population][category]
                x=center+(-8 if population==0 else 8)
                y=bar.y+bar.height*value/bar.valueAxis.valueMax+4
                label=f'{value:.1%}' if j else f'{value:.2f}'
                d.add(String(x,y,label,fontName='Helvetica',fontSize=6,textAnchor='middle',fillColor=INK))
        d.add(bar);d.add(String(j*250+125,224,title,fontName='Helvetica-Bold',fontSize=9,textAnchor='middle',fillColor=INK))
    legend(d,['CPU-node pairs','GPU-node pairs'],[BLUE,ORANGE],columns=2,y=14)
    result['05_halo_pairs']=d
    panels=[]
    for graph in REPRESENTATIVE[3:]:
        curves=[]
        for method,label,color in [('MPI','CPU MPI',BLUE),('MPI+OpenMP','CPU M+OMP',ORANGE),
                                   ('MPI+CUDA','M+CUDA',PURPLE),('MPI+Kokkos CUDA','M+KK Cuda',TEAL)]:
            for mode in ('Allgatherv','Halo'):
                one=get(graph,method,'gpu_node',processes=1,threads=1,communication=mode)
                two=get(graph,method,'gpu_node',processes=2,threads=1,communication=mode)
                curves.append((label+(' A' if mode=='Allgatherv' else ' H'),
                               [(1,1),(2,number(one['solve_median_s'])/number(two['solve_median_s']))],color,mode=='Halo'))
        panels.append(curves)
    result['06_gpu_node_scaling']=line_panels([DISPLAY[g] for g in REPRESENTATIVE[3:]],panels,
        'Nodes n = GPUs G for device methods','Own one-node speedup (×)',[1,2],False,False,height=265,shared_y=True)
    panels=[]
    for family in ('uniform','hub','controlled'):
        curves=[]
        for method,label,color in [('MPI','MPI',BLUE),('MPI+OpenMP','M+OMP',ORANGE),
                                   ('MPI+Kokkos OpenMP','M+KK',TEAL)]:
            for mode in ('Allgatherv','Halo'):
                rows=sorted((r for r in GROWING if r['family']==family and r['method']==method
                             and r['communication']==mode),key=lambda r:int(r['active_cpu_threads']))
                curves.append((label+(' A' if mode=='Allgatherv' else ' H'),
                               [(int(r['active_cpu_threads']),1000*number(r['seconds_per_iteration'])) for r in rows],
                               color,mode=='Halo'))
        panels.append(curves)
    times=line_panels(['Uniform','Hub','Controlled'],panels,'Active CPU cores C (count)',
                      'Iteration time (ms/iteration)',[4,16,64,256],height=250,shared_y=True)
    efficiency=[]
    for family,panel in zip(('uniform','hub','controlled'),panels):
        curves=[]
        for (label,points,color,dash) in panel:
            base=points[0][1]
            curves.append((label,[(c,base/value) for c,value in points],color,dash))
        efficiency.append(curves)
    retained=line_panels(['Uniform','Hub','Controlled'],efficiency,'Active CPU cores C (count)',
                         'Retained efficiency: C=4 reference (%)',[4,16,64,256],height=250,
                         shared_y=True,y_format=lambda v:f'{v:.1%}')
    combined=Drawing(500,530)
    group=Group(*times.contents);group.translate(0,275);combined.add(group)
    combined.add(Group(*retained.contents));result['07_core_weak']=combined

    phase_panels=[]
    labels=['CU1','CU2','KK1','KK2']
    for graph in REPRESENTATIVE[3:]:
        cases=[get(graph,method,'gpu_node',processes=p,threads=1,communication='Allgatherv')
               for method in ('MPI+CUDA','MPI+Kokkos CUDA') for p in (1,2)]
        phase_panels.append([(label,[(i+1,number(r[key])) for i,r in enumerate(cases)],color,False)
                             for label,key,color in [('Solve','solve_median_s',INK),
                                 ('Device compute','compute_median_s',BLUE),
                                 ('Host staging','transfer_median_s',ORANGE),
                                 ('MPI exchange','communication_median_s',TEAL)]])
    phase_drawing=line_panels([DISPLAY[g] for g in REPRESENTATIVE[3:]],phase_panels,
        'Implementation / GPU count','Duration per solve (s)',[1,2,3,4],False,True,
        x_format=lambda x:labels[int(x)-1],shared_y=True,height=275)
    for item in phase_drawing.contents:
        if isinstance(item,LinePlot):
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
    result['13_rank_workload']=line_panels(['Fixed graphs: incoming-edge workload distribution'],[imbalance],
        'MPI processes p (count)','Max / mean incoming edges (dimensionless)',[1,4,16,64,256],height=250)
    panels=[]
    for key,scale in [('counted_payload_bytes_per_rank',1e-6),('communication_ms_per_iteration',1)]:
        curves=[]
        for mode,color in [('Allgatherv',BLUE),('Halo',ORANGE)]:
            rows=sorted((r for r in TRAFFIC if r['family']=='uniform' and r['communication']==mode and int(r['processes'])>1),key=lambda r:int(r['processes']))
            curves.append((mode,[(int(r['processes']),number(r[key])*scale) for r in rows],color,mode=='Halo'))
        panels.append(curves)
    drawing=line_panels(['Growing Uniform: contribution payload','Growing Uniform: MPI duration'],panels,
        'MPI processes p (count)','Payload (MB/rank/iteration)',[2,4,16,64,256],height=265)
    for obj in drawing.contents:
        if isinstance(obj,String) and obj.text=='Payload (MB/rank/iteration)' and obj.x>250:
            obj.text='Communication + waiting (ms/iteration)'
    result['14_growing_communication']=drawing
    payload_curves=[]
    for family,color in [('google',GRAY),('uniform',BLUE),('hub',ORANGE),('controlled',TEAL)]:
        points=[(p,stats.median(number(r['payload_reduction']) for r in PAYLOAD_BY_PROCESS
                                if r['family']==family and r['processes']==p))
                for p in (2,4,8,16,32,64,128,256)]
        payload_curves.append((family.title(),points,color,False))
    result['15_payload_by_process']=line_panels(['Contribution savings at matched process counts'],[payload_curves],
        'MPI processes p (count)','Median payload reduction (%)',[2,4,16,64,256],log_y=False,
        y_format=lambda v:f'{v:.0%}',height=260)
    for obj in result['15_payload_by_process'].contents:
        if isinstance(obj,LinePlot):obj.yValueAxis.valueMax=1
    uniform_panels=[]
    rows={int(r['cores']):{} for r in CONTROLS if r['graph']=='strong_uniform'}
    for r in CONTROLS:
        if r['graph']=='strong_uniform':rows[int(r['cores'])][r['policy']]=r
    if rows:
        result['11_collective_policies']=control_ranges(['Large Uniform: Alltoallv'],[rows],
            [('Automatic','default',BLUE),('basic_linear','a2av_linear',ORANGE),('pairwise','a2av_pairwise',TEAL)],
            'Processes p = CPU cores C (count)')
    gather=[]
    for graph in ('strong_hub','strong_controlled'):
        lookup={c:{} for c in (32,64,128)}
        for r in CONTROLS:
            if r['graph']==graph and r['implementation']=='hybrid' and r['communication']=='allgather':
                lookup[int(r['cores'])][r['policy']]=r
        gather.append(lookup)
    if CONTROLS:
        result['12_allgatherv_policies']=control_ranges(['Large Hub: Allgatherv','Large Controlled: Allgatherv'],gather,
            [('Automatic','default',BLUE),('Bruck','agv_bruck',ORANGE),('Ring','agv_ring',TEAL)],
            'CPU cores C (count); T=4, p=C/4')
    return result


def write_figures(items, pdftoppm):
    FIG.mkdir(parents=True,exist_ok=True)
    write_view(DATA/'growing_cpu_matched_reference.csv',GROWING)
    write_view(DATA/'payload_by_process.csv',PAYLOAD_BY_PROCESS)
    for name,d in items.items():
        renderPDF.drawToFile(d,str(FIG/(name+'.pdf')))
        if name.startswith(('11_','12_')):
            from reportlab.graphics import renderSVG
            renderSVG.drawToFile(d,str(FIG/(name+'.svg')))
        if pdftoppm:
            subprocess.run([pdftoppm,'-r','160','-png','-singlefile',str(FIG/(name+'.pdf')),str(FIG/name)],check=True,
                           stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)


def report(items):
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyReport',fontName='Times-Roman',fontSize=10.3,leading=13.5,spaceAfter=7,textColor=INK,allowWidows=0,allowOrphans=0))
    styles.add(ParagraphStyle(name='SectionReport',fontName='Helvetica-Bold',fontSize=16,leading=20,spaceBefore=16,spaceAfter=10,textColor=INK,keepWithNext=True))
    styles.add(ParagraphStyle(name='SubReport',fontName='Helvetica-Bold',fontSize=11.5,leading=15,spaceBefore=11,spaceAfter=7,textColor=BLUE,keepWithNext=True))
    styles.add(ParagraphStyle(name='SubSubReport',fontName='Helvetica-Bold',fontSize=10.5,leading=14,spaceBefore=10,spaceAfter=7,textColor=INK,keepWithNext=True))
    styles.add(ParagraphStyle(name='CaptionReport',fontName='Helvetica',fontSize=8,leading=10.5,spaceAfter=12,textColor=GRAY))
    styles.add(ParagraphStyle(name='ReferenceReport',parent=styles['CaptionReport'],spaceAfter=4))
    styles.add(ParagraphStyle(name='TableReport',fontName='Helvetica',fontSize=8,leading=10,textColor=INK))
    styles.add(ParagraphStyle(name='EquationReport',fontName='Times-Roman',fontSize=10,leading=15,alignment=TA_CENTER,spaceAfter=10,textColor=INK))
    styles.add(ParagraphStyle(name='TableCaptionReport',parent=styles['CaptionReport'],keepWithNext=True))
    story=[];md=[]
    table_number=0
    equations=LatexEquations(REPORT/'equations', ROOT/'tmp/pdfs/latex_build')
    def para(text):
        md.append(text+'\n');story.append(Paragraph(html.escape(text),styles['BodyReport']))
    def heading(text,level=1):
        md.append('#'*(level+1)+' '+text+'\n');story.append(Paragraph(html.escape(text),styles['SectionReport' if level==1 else 'SubReport' if level==2 else 'SubSubReport']))
    def table(headers,rows,widths=None,small=False,caption=None):
        nonlocal table_number
        table_number+=1
        assert caption
        caption=f'Table {table_number}. '+caption
        md.append(caption+'\n')
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
        prefix.append(Paragraph(html.escape(caption),styles['TableCaptionReport']))
        story.extend([KeepTogether(prefix+[t,Spacer(1,8)])] if len(rows)<=12 else prefix+[t,Spacer(1,8)])
    figure_number=0
    def figure(name,caption):
        nonlocal figure_number
        figure_number+=1
        caption=re.sub(r'^Figure [0-9]+[a-z]?\.\s*','',caption)
        caption=f'Figure {figure_number}. '+caption
        md.append(f'![{caption}](report_assets/figures/{name}.png)\n')
        prefix=[]
        if story and isinstance(story[-1],Paragraph) and story[-1].style.name=='SubReport':
            prefix.append(story.pop())
        story.append(KeepTogether(prefix+[items[name],Paragraph(html.escape(caption),styles['CaptionReport'])]))
    def equation(pdf,markdown):
        latex=markdown.strip().removeprefix('$$').removesuffix('$$')
        story.append(equations.display(latex));md.append(markdown+'\n')

    title='Parallel PageRank on Vanda'
    md.extend(['# '+title,'',f'Parallel PageRank experiments - {REPORT_DATE}',''])
    story.append(Paragraph(title,ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=25,leading=29,textColor=INK,spaceAfter=10)))
    story.append(Paragraph(f'DSA5208 Project 3 | {REPORT_DATE}',styles['CaptionReport']))
    author_file=REPORT/'authors.json'
    if author_file.exists():
        authors=json.loads(author_file.read_text())
        author_line='; '.join(author['name']+' ('+author['student_id']+')' for author in authors)
        md.append(author_line+'\n');story.append(Paragraph(html.escape(author_line),styles['CaptionReport']))
    md.append(f'Project repository: [{PROJECT_URL}]({PROJECT_URL})\n')
    story.append(Paragraph(f'Project repository: <link href="{PROJECT_URL}" color="#16679b">{PROJECT_URL}</link>',styles['CaptionReport']))
    heading('Abstract',2)
    para('We study synchronous PageRank using Serial, OpenMP, MPI, MPI+OpenMP, native CUDA, and Kokkos with OpenMP and CUDA backends. The fixed-input study comprises 45 directed graphs: three original graphs and 42 reproducible extensions spanning graph size, edge density, and destination concentration. Fixed-input resource experiments ask whether additional workers solve the same graph faster; fixed-core comparisons then separate the effect of MPI process/thread decomposition. These experiments contain 19,530 configurations. A separate growing-input suite uses 27 scale-specific synthetic inputs from three graph families, with 318 resource-scaled configurations and 54 fixed-resource input-size controls. It tests whether runtime per iteration remains stable as graph size and resources grow together. Measurements use one warm-up and the median of five timed solves on NUS Vanda, with independent numerical validation. Balanced graphs benefit from distributed execution, whereas concentrated incoming edges limit useful parallelism despite equal vertex ownership. Selective Halo exchange reduces contribution traffic without consistently reducing runtime, and adding a second GPU does not guarantee acceleration.')
    if CONTROLS:
        para(f"A further {len(CONTROLS)+len(LAUNCHER_CONTROLS)} matched diagnostic configurations examine MPI collective selection, node boundaries, and CPU binding. These controls distinguish communication-policy effects from the graph-partition and workload mechanisms underlying the scaling curves.")
    heading('1 Introduction to the algorithm and data')
    heading('1.1 PageRank and its relation to PPR',2)
    para('PageRank assigns a probability score to each vertex of a directed graph. A random surfer follows an outgoing edge with probability alpha and otherwise jumps according to a preference vector. Personalized PageRank (PPR) uses a query-specific preference vector. Our implementation uses the uniform preference vector and uniform redistribution of dangling-vertex mass: it is standard PageRank, equivalently the uniform-preference special case of PPR. Throughout this report, PageRank denotes this uniform-preference case.')
    equation('', r'$$r_v^{(k+1)}=\frac{1-\alpha}{N}+\frac{\alpha D^{(k)}}{N}+\alpha\sum_{u:(u,v)\in\mathcal{E}}\frac{r_u^{(k)}}{d_{\mathrm{out}}(u)}.$$')
    para('Here N is the number of vertices, the directed edge set is denoted by script E, r_v is the probability score of vertex v, and d_out(u) is the number of outgoing edges from u. A dangling vertex has no outgoing edges; D is the sum of scores at these vertices and is redistributed uniformly. All scores start at 1/N. We use alpha=0.85, double precision, and synchronous old/new score buffers. Iteration stops when the sum of absolute score changes is at most epsilon=10^-8, with a cap of 1,000 iterations:')
    equation('', r'$$D^{(k)}=\sum_{u:d_{\mathrm{out}}(u)=0}r_u^{(k)},\qquad \Delta^{(k)}=\left\|\mathbf{r}^{(k+1)}-\mathbf{r}^{(k)}\right\|_1\leq\varepsilon.$$')
    para('The pull formulation stores incoming edges in compressed sparse row (CSR) form: each destination vertex has a row listing its source vertices. Updating one destination requires scanning that row. Serial work and storage are O(N+E), where E is the number of directed edges.')
    para('PageRank workers cannot proceed independently. A vertex update may need a source score owned by another process, so scores must be exchanged every iteration. The processes must also combine dangling-vertex scores and the total score change to perform the same update and stopping test. Furthermore, a vertex with 10,000 incoming edges requires a much longer row scan than one with two. Assigning equal numbers of vertices can therefore give processes very different amounts of computation. These dependencies, collective operations, and unequal row lengths make parallelization nontrivial.')
    heading('1.2 Fixed-input graphs for resource comparisons',2)
    para('Fixed input means that a graph is unchanged when the hardware configuration changes. It does not mean only the three original files: all 45 graphs below are fixed inputs for the strong-scaling and fixed-core studies.')
    table(['Source','Graphs','Vertices N','Directed edges E','Purpose'],[
        ['Original Google','1','875,713','5,105,039','Real web-link graph'],
        ['Original uniform and hub','2','100,000 each','1,000,000 each','Original synthetic controls'],
        ['Canonical extensions','3','100,000','1,000,000','One per generated family'],
        ['Size-density grid','36','50k / 100k / 200k / 400k','N x 4 / 8 / 16','3 families x 4 sizes x 3 densities'],
        ['Large extensions','3','12,800,000','204,800,000','One per generated family'],
        ['Total fixed graphs','45','','','3 original + 42 extensions']], [95,35,107,107,156],caption='Fixed-input graph collection. N and E count vertices and directed edges; the grid crosses mean degree with vertex count.')
    para('The generated families use seed 5208 and deterministic integer mixing. Uniform spreads destinations across all vertices with fixed source degree. Hub directs approximately 80% of each source\'s edges to the first 1% of vertices. Controlled combines the hub destination pattern with two source-degree classes: 80% lower-degree sources and 20% higher-degree sources. Integer rounding and unique arithmetic progressions determine exact counts. The original uniform/hub files are retained unchanged; they are not interchangeable with the new canonical graphs of the same size.')
    para('For the three large graphs, E/N=16. The integer rule floor(4*d_out/5) sends exactly 75.0% of Hub edges and 77.5% of Controlled edges into the first 1% of destination IDs. These exact fractions, rather than an assumed 80%, are used in the workload model below. The concentration is deliberately aligned with contiguous vertex partitions; results therefore characterize this partitioner and vertex ordering as well as graph structure.')
    para('Integer rounding also qualifies the density-grid interpretation: Controlled sends 65.0% of its edges to the hot block at mean degree 4, and 77.5% at degrees 8 and 16. Changing density therefore changes this exact structural concentration as well as E. The grid is a reproducible generator-family study, not an intervention that isolates edge count from every other graph property.')
    para('Vertex count and average out-degree are crossed systematically, not changed together in a single size parameter. The three large graphs have identical N and E but different structural concentration, making them useful for separating graph size from load imbalance. All 45 fixed graphs are reused unchanged across the full fixed-graph configuration matrix.')
    heading('1.3 Graphs that grow with resource count',2)
    para('The growing-input experiments use Uniform, Hub, and Controlled graphs at nine scale factors s=1,2,4,8,16,32,64,128,256. Each input contains N=50,000s vertices and E=800,000s directed edges, giving 27 scale-specific graph identifiers. The largest scale has 12.8 million vertices and 204.8 million edges. The three large fixed-input graphs reuse these largest-scale inputs; the fixed-input and growing-input counts describe their experimental roles and should not simply be added.')
    para('In a rank-normalized experiment s equals the MPI process count p; in a core-normalized experiment s equals the active CPU core count C. The CPU suites contain 150 rank-normalized and 84 core-normalized configurations. On GPU nodes, six inputs (three families at s=1 and 2) provide 84 distributed resource-scaled configurations and 54 standalone fixed-resource controls. Thus 372 growing-input records comprise 318 resource-scaled configurations and 54 controls; the latter measure increasing input size without labeling them as resource-scaled efficiency measurements.')

    heading('2 Methodology')
    heading('2.1 Notation, implementations, and communication',2)
    table(['Symbol or term','Definition and unit'],[
        ['N; E','Numbers of vertices and directed edges (counts). Average out-degree is E/N.'],
        ['Node; n','A physical compute machine; n is the number of participating machines (nodes).'],
        ['MPI rank; p','An MPI rank identifies a participating process, not a PageRank score. p is the total process count; rank IDs are 0,...,p-1. Processes have separate local data.'],
        ['r; T','r is the number of MPI processes per node. T is the number of CPU threads per process (threads/process).'],
        ['C; G','C is active CPU parallelism (cores); G is the number of GPUs used by device computation (devices).'],
        ['t; I','t is solve time in seconds; I is the convergence iteration count. T denotes threads, never runtime.'],
        ['CSR; PPR','Compressed sparse row storage; personalized PageRank. We use the uniform-preference special case of PPR.'],
        ['OMP; KK; A; H','Figure abbreviations: OpenMP; Kokkos; Allgatherv; Halo. CUDA and Kokkos CUDA denote GPU computation.']], [100,400],caption='Symbols, terminology, and measurement units used in the experiment design.')
    equation('', r'$$p=nr,\qquad C=pT=nrT.$$')
    para('For example, four nodes with eight processes per node and four threads per process give p=32 and C=128 active CPU cores. The process count and thread count describe different levels of parallelism. On GPU nodes, distributed device methods use one process and one GPU per node, so G=p=n. Their GPU thread blocks are separate from the host CPU thread parameter T.')
    table(['Implementation','Compute and work distribution','MPI exchange'],[
        ['Serial','One CPU thread; incoming CSR pull','Not applicable'],
        ['OpenMP','CPU threads; dynamic row scheduling, chunks of 64 vertices','Not applicable'],
        ['Kokkos OpenMP','CPU threads; default static RangePolicy and reductions','Not applicable'],
        ['CUDA / Kokkos CUDA','One GPU; incoming-row vertex kernels','Not applicable'],
        ['MPI','Contiguous destination partitions; one CPU thread per process','Allgatherv; Halo'],
        ['MPI+OpenMP','Threaded pull within each MPI partition','Allgatherv; Halo'],
        ['MPI+CUDA','One GPU per MPI process; host buffers for MPI exchange','Allgatherv; Halo'],
        ['MPI+Kokkos','Distributed driver with OpenMP or CUDA execution space','Allgatherv; Halo']], [105,275,120],caption='Implemented compute methods, local work distribution, and applicable MPI exchange strategies.')
    para('The standalone methods execute in one process and make no MPI calls; their MPI exchange setting is therefore not applicable. OpenMP threads share memory, while CUDA threads exchange device data through the kernel and memory system. MPI+OpenMP requests MPI_THREAD_FUNNELED: only the main thread calls MPI.')
    para('MPI assigns approximately equal consecutive ranges of destination vertex IDs to processes. Each process updates its own destinations and stores their incoming-edge rows. The two communication strategies differ in which source contributions they make available for those updates:')
    table(['Strategy','Values exchanged each iteration','MPI operation'],[
        ['Allgatherv','Every process receives the contribution value for every vertex, assembling a complete vector. This is simple but also transfers values that a process may not need.','MPI_Allgatherv'],
        ['Halo','Each process receives only distinct remote-source values referenced by its incoming rows. Required source IDs are determined once; later iterations exchange their current values.','MPI_Alltoallv']], [75,320,105],caption='The two exact MPI contribution-exchange strategies and the data communicated in each iteration.')
    para('Both strategies calculate the same PageRank update and use MPI_Allreduce to combine dangling mass and convergence changes. Halo changes the communicated dependency set without dropping edges or approximating scores. Its request-list construction occurs before solve timing; packing and exchanging current values occur inside every timed iteration.')
    para('The counted per-iteration payload is the algorithm-level contribution-vector traffic, excluding collective implementation details, reduction traffic, and protocol overhead. Allgatherv counts 8N(p-1) aggregate bytes; Halo counts eight bytes per requested remote contribution. Payload sizes use decimal MB (one million bytes). Metadata setup is recorded separately and lies outside solve time. Fewer counted bytes therefore need not imply lower measured latency.')
    para('Local update work depends on both the number of owned vertices and their incoming edges. Global iteration progress waits for the slowest process and completion of collective operations. Equal vertex counts therefore do not imply equal computation time. The MPI timer includes packing/copies, collectives and waiting at reductions; it is not a network-only timer. Solve and phase timings take separate maxima across ranks, then separate medians across five runs. They cannot be subtracted or added to reconstruct one critical-path trace.')
    para('The distributed device implementations stage contributions through host memory; they do not use CUDA-aware MPI or overlap communication with computation. The CUDA version uses 256-thread blocks and explicit kernels. Kokkos expresses comparable operations through Views, parallel_for/parallel_reduce and execution-space fences. Kokkos OpenMP and CUDA are two backends, not interchangeable hardware measurements.')
    heading('2.2 Hardware, software and timing protocol',2)
    para('All reported measurements are from NUS Vanda. CPU comparisons use Intel Xeon Platinum 8452Y hosts, GCC 13.3.0, Open MPI 4.1.8 and Release builds. GPU comparisons use NVIDIA A40 nodes with Platinum 8452Y CPUs; archived build metadata identifies CUDA toolkit 12.4.1. Driver-reported CUDA compatibility is not treated as the compiler toolkit version. Original laptop and mixed-hardware exploratory measurements are excluded.')
    para('Every configuration has one warm-up followed by five timed runs. All primary solve-time tables and figures report the median of those five timed runs. The exported statistic solve_median_s is recomputed here from the five original solve_s observations. MPI solve time is the maximum elapsed solver time across ranks. Graph input, partition distribution, backend construction and Halo setup are outside solve time; per-iteration MPI and host/device staging are inside the distributed solve. Standalone GPU setup and final rank copies are outside solve time. These are solver-time comparisons, not end-to-end application runtimes.')
    para('OpenMP creates its persistent thread team inside the timed solver, while Kokkos runtime initialization precedes solver timing. Backend-compute phases use fenced host-clock intervals, including dispatch and reduction implementation costs; they are not CUDA-event measurements of pure kernel execution. Transfer phases measure explicit staging and need not capture every internal scalar-result copy. These boundaries should be considered when comparing backends or very small graph runtimes.')
    para('The twelve MPI+Kokkos configurations with a lower-memory initialization use the same timed update and communication kernels. Their initialization variant is identified in the accompanying data; graph construction and memory preparation remain outside solve time.')
    heading('2.3 Experimental configuration matrix',2)
    para('Every row below is applied to all 45 fixed-input graphs. One configuration is one graph, implementation, valid layout, and communication setting; its five timed repeats are not counted as five configurations. The design is a constrained Cartesian product: graph, implementation, valid resource layout, and communication strategy are crossed. Derived quantities are not additional independent dimensions: p=nr, C=pT, and for GPU computation G=p=n. CPU layouts satisfy rT<=32; combinations that exceed this per-node budget are excluded. Standalone methods have no MPI communication dimension.')
    para('CPU-node matrix. Q={1,2,4,8,16,32} is the tested set of per-node process and thread counts. Every listed MPI layout is measured separately with Allgatherv and Halo.')
    table(['Implementation','Nodes n','Ranks/node r','Processes p','Threads T','CPU cores C','MPI exchange','Configs'],[
        ['Serial','1','1','1','1','1','Not applicable','45'],
        ['OpenMP','1','1','1','Q','T','Not applicable','270'],
        ['Kokkos OpenMP','1','1','1','Q','T','Not applicable','270'],
        ['MPI','1,2,4,8','Q','nr','1','nr','Allgatherv; Halo','2,160'],
        ['MPI+OpenMP','1,2,4,8','Q','nr','Q; rT<=32','nrT','Allgatherv; Halo','7,560'],
        ['MPI+Kokkos OpenMP','1,2,4,8','Q','nr','Q; rT<=32','nrT','Allgatherv; Halo','7,560']], [100,43,52,56,60,50,86,53],small=True,caption='CPU-node fixed-input matrix. Every row is crossed with all 45 graphs; Q={1,2,4,8,16,32} and the constraint rT<=32 selects valid layouts.')
    para('For pure MPI, four node choices and six ranks-per-node choices give 24 layouts per graph. For each CPU hybrid method, 21 valid (r,T) pairs per node count give 84 layouts. Multiplying by 45 graphs and two communication settings yields 2,160 and 7,560 configurations, respectively. The CPU-node block contains 17,865 configurations. A standalone row uses p=1 to denote its one process, without creating an MPI communicator.')
    para('GPU-node matrix. The first four rows perform GPU computation; the last four execute on CPUs of the same GPU-node class as hardware-matched controls. G counts GPUs used for computation, so G=0 for those CPU controls.')
    table(['Implementation','Nodes n','Processes p','CPU threads T','GPUs G','MPI exchange','Configs'],[
        ['CUDA','1','1','1 host','1','Not applicable','45'],
        ['Kokkos CUDA','1','1','1 host','1','Not applicable','45'],
        ['MPI+CUDA','1,2','n','1 host','n','Allgatherv; Halo','180'],
        ['MPI+Kokkos CUDA','1,2','n','1 host','n','Allgatherv; Halo','180'],
        ['Serial CPU control','1','1','1','0','Not applicable','45'],
        ['OpenMP CPU control','1','1','1,2,4,8,16,32','0','Not applicable','270'],
        ['MPI CPU control','1,2','n','1','0','Allgatherv; Halo','180'],
        ['MPI+OpenMP CPU control','1,2','n','1,2,4,8','0','Allgatherv; Halo','720']], [118,44,50,65,42,124,57],small=True,caption='GPU-node fixed-input matrix, including device-computing methods and same-node-class CPU controls. G counts GPUs used for computation.')
    para('The GPU-node block contains 450 device-computing configurations and 1,215 CPU controls, giving 1,665 configurations. Together with the CPU-node block, the fixed-input matrix has 19,530 configurations. No communication setting is attached to a standalone method, and no GPU-computing version is implied for Serial or ordinary OpenMP.')
    para('The principal CPU scaling line increases C=32,64,128,256 on n=1,2,4,8 nodes, keeping 32 active CPU cores per node. Pure MPI uses p=C,T=1; the plotted hybrid line uses p=C/4,T=4. At fixed C, the matrix also contains every legal split with T in Q and p=C/T. Thus one can compare increasing total parallelism separately from changing the process/thread mix at the same total core budget.')
    heading('2.4 Scaling questions and statistical summaries',2)
    para('The fixed-input resource experiment asks: how much faster can the same graph be solved by adding workers? N, E, graph structure, and the convergence criterion are held fixed while C increases. The ideal is that doubling cores halves solve time. For each graph, let t_ser be its Serial solve median and t(C) the parallel solve median on C active cores. Speedup and CPU core efficiency are:')
    equation('', r'$$S(C)=\frac{t_{\mathrm{ser}}}{t(C)},\qquad \eta_{\mathrm{CPU}}(C)=\frac{S(C)}{C}.$$')
    para('Speedup is dimensionless; efficiency is reported as a percentage, with 100% representing ideal linear speedup relative to Serial. Fixed-input resource curves reveal where communication, synchronization, or insufficient local work outweighs the benefit of more workers. A different experiment holds C=256 fixed and varies p/T, asking which decomposition uses an equal core budget most effectively. This is a method comparison at fixed resources, not another increase in parallel degree.')
    para('The growing-input resource experiment asks: if graph size grows in proportion to resources, can each resource continue to handle the same nominal amount of work without increasing runtime? The graph must change in this experiment. Rank-normalized inputs use N=50,000p and E=800,000p; core-normalized inputs use N=50,000C and E=800,000C. The latter permits CPU hybrid methods with different process/thread decompositions to be compared at equal nominal work per core. Keeping vertex and edge counts per resource constant does not guarantee equal communication or balanced incoming-edge work; the growing-input experiment tests these additional costs.')
    table(['Growing-input block','Graph scale','Resource layouts','Configurations'],[
        ['Rank-normalized CPU','s=p; 3 families','MPI and MPI+Kokkos T1: p=1,...,256 in powers of 2; MPI+OpenMP T4: p=1,...,64; Allgatherv and Halo','150'],
        ['Core-normalized CPU','s=C; 3 families','MPI+OpenMP and MPI+Kokkos OpenMP: T4, p=C/4; C=4,...,256 in powers of 2; Allgatherv and Halo','84'],
        ['GPU-node resource scaling','s=p=1,2; 3 families','Distributed GPU methods and distributed CPU controls; n=p; Allgatherv and Halo','84'],
        ['GPU-node input-size controls','s=1,2; 3 families','Standalone Serial, OpenMP, CUDA, and Kokkos CUDA retain one node while input size increases','54'],
        ['Total','','318 resource-scaled configurations + 54 fixed-resource controls','372']], [115,85,245,55],small=True,caption='Growing-input experiment groups. Counts refer to configurations, not five-run repetitions; fixed-resource controls are kept separate.')
    para('Graphs can require different iteration counts as they grow. We therefore define retained per-iteration efficiency using time per iteration rather than conflating communication scaling with a change in convergence length. Let I(C) be the number of iterations and C0 the smallest resource point of the same series:')
    equation('', r'$$\tau(C)=\frac{t(C)}{I(C)},\qquad \eta_{\mathrm{grow,iter}}(C)=\frac{\tau(C_0)}{\tau(C)}.$$')
    para('Ideal proportional input/resource growth has constant time per iteration and 100% efficiency; a value of 25% means each iteration takes four times as long as at the reference point. The matched CPU figure uses C0=4 for all three methods on identical growing inputs. MPI follows p=C,T1; the hybrid methods use p=C/4,T4. The separate rank-normalized source series retains its p0=1 reference in the data. This normalization changes the plotted reference, not any timing observation. Total-solve efficiency is retained as a secondary metric. CPU speedup always uses the corresponding CPU-node Serial reference; GPU-node speedup uses its own Serial control. One-to-two-GPU scaling instead divides each implementation\'s one-GPU time by its two-GPU time.')
    para('Two statistical levels are used. First, every individual configuration reports the median of its five timed solves after one warm-up. Second, a cross-graph comparison first divides those medians to obtain a speedup for each graph, then takes the geometric mean of the speedups:')
    equation('', r'$$\widetilde{t}_{g,a}=\operatorname{median}(t_{g,a,1},\ldots,t_{g,a,5}),\qquad s_g=\frac{\widetilde{t}_{g,a}}{\widetilde{t}_{g,b}},\qquad \overline{s}_{\mathrm{geo}}=\left(\prod_{g=1}^{m}s_g\right)^{1/m}.$$')
    para('Here g indexes the m compared graphs, a and b are matched configurations, and s_g>1 favors b. The geometric mean is applied to dimensionless ratios, not to the five timings of a configuration and not to seconds pooled across graph sizes. A 2x improvement and a 2x slowdown combine to 1x, giving equal multiplicative weight to each compared graph. Communication comparisons additionally match method, backend, nodes, processes, and threads. The 45-row best-time matrix is an overview of each method\'s best observed median; it is kept separate from matched-layout scaling and equal-core comparisons.')
    para('The fixed-core aggregate uses 45 ratios, one per graph. Communication aggregates instead use matched graph/layout pairs, with pair counts reported explicitly. Payload reduction is the fraction of Allgatherv contribution bytes avoided by Halo; its aggregate is the median across those matched pairs.')
    heading('2.5 Correctness and reproducibility',2)
    para('The independent Python validators rebuild one PageRank update by streaming the original edge list, rather than sharing the C++ CSR traversal. Checks include vertex IDs/degrees, nonnegative finite ranks, total score within 10^-10 of one, residual within the stopping tolerance, full-vector L1 difference from Serial within 10^-8, history and repeated-run metadata. Allocation records and rank affinity maps verify the distributed layout. Raw rank vectors remain on Vanda; the repository holds summaries, timings, validation markers and provenance. The local analysis checks these saved proofs.')
    para('For the additional collective-policy controls, an independent raw-edge scan validates the Serial vector s once per graph. Every new vector x is compared in full, including IDs, degrees, probability mass and L1 error. The PageRank map is contractive in L1 with factor alpha=0.85. The new residual is therefore bounded by the reference residual plus 1.85 times the full-vector L1 difference. Requiring this bound to be at most 10^-8 independently certifies the new vector while reusing the reference scan. The distance to the unique stationary vector is at most the residual divided by 1-alpha. Timings, histories, actual threads and all five reported residuals are checked separately. These checks run on the free queue.')
    para('The accompanying data retain input identity, software version, hardware allocation, original timing observations, and independent validation records. These records support reconstruction of both the reported statistics and the configuration matched to each comparison.')
    heading('2.6 MPI collective selection and controlled policies',2)
    para('The main experiment preserves Open MPI\'s automatic collective selection rather than prescribing one communication algorithm for all resource counts. The tuned component chooses an implementation for each collective operation according to its installed rules. On Vanda, the recorded Open MPI 4.1.8 configuration uses coll_tuned_use_dynamic_rules=false and algorithm overrides set to 0 (ignore). Automatic selection therefore follows the compiled fixed decision tree. The word fixed describes the decision rules, not a single algorithm: the selected algorithm can change with process count, and for Allgatherv also with message size. This automatic rule-based behavior is distinct from online adaptation based on measured congestion.')
    para('We retain that automatic behavior for the main scaling study, then perform matched forced-policy controls around the 64-core and 128-process selection boundaries. These controls ask whether a rule transition contributes to the measured bend, while holding the graph, binary, resource count, and allocation fixed within each comparison. Enabling coll_tuned_use_dynamic_rules=1 is the mechanism used to force an algorithm in these diagnostic runs; it was not the mode of the main matrix.')
    table(['MPI operation','Algorithm ID','Implementation','Applicability'],[
        ['Alltoallv (Halo)','1','basic_linear','General process counts'],
        ['Alltoallv (Halo)','2','pairwise','General process counts'],
        ['Allgatherv','1','GatherV followed by Bcast; parameter name default','General process counts'],
        ['Allgatherv','2','Bruck','General process counts'],
        ['Allgatherv','3','Ring','General process counts'],
        ['Allgatherv','4','Neighbor exchange','Applicable at p=8,16,32'],
        ['Allgatherv','5','two_proc','Exactly two processes']], [110,65,210,115],caption='Collective algorithms exposed by the installed Open MPI 4.1.8 tuned component. Algorithm ID 0 retains automatic selection and is not another implementation.')
    para('Thus tuned exposes two actual Alltoallv algorithms and five actual Allgatherv algorithms in this version. ID 0 (ignore) retains automatic selection and is not another implementation. Allgatherv ID 1 is named default, but explicitly forcing it selects GatherV+Bcast; it does not mean restoring the automatic decision tree [9]. Other collectives, including Allreduce, have their own algorithm lists and retain their default settings here.')
    table(['Alltoallv communicator size p','Default tuned algorithm'],[
        ['p < 4','pairwise'],['4 <= p < 64','basic_linear'],
        ['64 <= p < 128','pairwise'],['128 <= p < 256','basic_linear'],
        ['256 <= p < 1024','pairwise'],['p >= 1024','basic_linear']], [235,265],caption='Compiled automatic Alltoallv selection rules in Open MPI 4.1.8. p is communicator process count, not CPU core count or payload size.')
    para('These are the fixed rules in Open MPI 4.1.8 [7] for communicators handled by tuned. A single-rank communicator can use the self component and has no remote Halo payload. For Alltoallv, this selector uses communicator size p, not message bytes, CPU cores or measured congestion. basic_linear starts nonblocking requests to the participating peers and waits for them; pairwise schedules rank-step exchanges [8]. Both implement the same blocking MPI_Alltoallv interface and transfer the same requested values. Their different request concurrency and message order can change latency and resource pressure. A blocking collective is not an MPI_Barrier.')
    para('Allgatherv has a separate selector using both p and average contribution bytes per rank, b=8N/p. On the large graphs N=12.8 million, the T=4 mainline changes from p=8, b=12.8 MB at 32 cores to p=16, b=6.4 MB at 64 cores. Its default Allgatherv algorithm changes from Bruck to Ring; at p=32 and 64 it remains Ring [7]. Thus a 64-core bend may involve a different collective transition from the 128-rank Halo peak.')
    para('The Allgatherv control deliberately compares the two implementations on either side of the observed rule transition: default selection, forced Bruck, and forced Ring, on both large concentrated graphs at C=32,64,128 with T=4. It is a symmetric transition test, not an exhaustive search for the fastest Allgatherv implementation. GatherV+Bcast and neighbor exchange are not part of that comparison; two_proc does not apply at its p=8,16,32. The Uniform Halo control instead compares default selection with both available Alltoallv algorithms at p=64,128,256.')
    table(['Active cores C','Nodes','MPI p / Alltoallv','Hybrid p / Alltoallv','Hybrid Allgatherv'],[
        ['32','1','32 / basic_linear','8 / basic_linear','Bruck'],
        ['64','2','64 / pairwise','16 / basic_linear','Ring'],
        ['128','4','128 / basic_linear','32 / basic_linear','Ring'],
        ['256','8','256 / pairwise','64 / pairwise','Ring']], [85,40,130,135,110],caption='Automatic collective choices on the principal resource line. Pure MPI uses T1 and CPU hybrids T4; n is node count.')
    para('Hybrid columns use T=4 and both CPU hybrid implementations. To isolate a collective policy, enable coll_tuned_use_dynamic_rules=1 and force only that operation: Alltoallv algorithm 1=basic_linear or 2=pairwise; Allgatherv algorithm 2=Bruck or 3=Ring [9]. Other collectives retain their fixed-rule choices. The dynamic switch enables forced/user-rule dispatch; it is not online timing-based learning. Paired policies use the same graph, binary, allocation, p/T, CPU affinity and transport, with identical tuned/basic/libnbc/self component availability. Component probes run outside the five timed solves. Five-run medians and ranges, rather than a selected fastest repeat, quantify policy sensitivity.')
    para('Equal CPU budgets do not imply equal MPI policies. At C=256, p256/T1 uses pairwise Alltoallv, p128/T2 uses basic_linear, and p64/T4 returns to pairwise. Reducing p further to 32/16/8 uses basic_linear. Rank/thread decomposition therefore changes collective participation, local work sharing and the runtime selection regime together. The matched fixed-policy controls distinguish the contribution of a specific communication choice.')
    para('The compiled tree is a general performance heuristic. The controlled comparisons assess how well its choices suit this graph and allocation, without replacing the main automatic-selection curves with selected fastest policies. OpenMP schedule(dynamic,64), which redistributes local vertex chunks among CPU threads, is independent of this MPI setting. OMP_DYNAMIC=false fixes the OpenMP team size and does not disable dynamic row scheduling.')
    heading('3 Results')
    para('The results follow the experimental questions in order: numerical agreement; serial input cost; more CPU resources for a fixed graph; single- and multi-GPU execution; communication policy; and proportional growth of inputs and resources. Unless explicitly labeled as a forced-policy control, every MPI result retains automatic tuned selection. Allgatherv and Halo are already present in the CPU and GPU comparisons; Section 3.5 re-expresses their matched results to isolate communication effects.')
    heading('3.1 Numerical agreement across implementations',2)
    table(['Numerical check','Acceptance criterion','Observed outcome'],[
        ['Full score vector versus Serial','L1 difference <= 10^-8','All independently validated configurations pass'],
        ['Final convergence residual','L1 residual <= 10^-8',f"Maximum {AUDIT['max_residual_l1']:.3e}"],
        ['Total probability mass','Absolute difference from 1 <= 10^-10',f"Maximum {AUDIT['max_rank_sum_error']:.3e}"],
        ['Iterations on a fixed graph and hardware class','Same stopping rule across implementations','Identical counts in all 90 graph/hardware groups']], [155,155,190],
        caption='Numerical consistency of the fixed-input results. L1 differences and probability-mass errors are dimensionless; 90 groups comprise 45 graphs on two node classes.')
    para('These checks establish that the implementations compute the same uniform-preference PageRank solution within the prescribed tolerance. The performance sections therefore compare the cost of an equivalent numerical task. Each configuration contributes the median of five timed solves after one warm-up; repeated timings do not increase the configuration count.')

    heading('3.2 Graph characteristics and serial reference costs',2)
    heading('3.2.1 Graph size, edge density, and iteration cost',3)
    para('The serial experiments establish the work scale before adding parallel resources. The same size-density grid is shown for Uniform, Hub, and Controlled, with vertex count on the horizontal axis and one line for each mean out-degree. Each point is one fixed graph; no process or thread count changes in this comparison.')
    figure('01_serial_grid','Serial solve time (s) for the 36 grid inputs: three families, four vertex counts, and mean out-degree d=4,8,16 edges/vertex. All runs use one CPU process and one thread. Points are five-run medians; both axes are logarithmic. Family panels use the same experimental design.')
    density=[]
    for family in ('uniform','hub','controlled'):
        selected=sorted((r for r in GRAPHS if r['graph'].startswith('grid_'+family+'_n100000_')),key=lambda r:int(r['edges']))
        for r in selected:
            density.append([family.title(),int(r['edges'])//100000,f"{int(r['edges']):,}",r['iterations'],
                            fmt(r['solve_median_s']),fmt(number(r['solve_median_s'])/int(r['iterations'])*1000)])
    table(['Family','Mean degree','Edges E','Iterations I','Solve time (s)','Time/iteration (ms)'],density,
          [85,60,85,70,95,105],caption='Density comparisons at N=100,000 vertices. Mean degree is E/N in edges/vertex; solve and per-iteration times separate convergence length from iteration cost.')
    para('More edges increase the work available to an iteration, but total solve time also depends on how many iterations the graph requires. Controlled at N=100,000 takes 35, 22, and 17 iterations as mean degree increases from 4 to 8 to 16. Its total time consequently need not increase monotonically. The density generator also changes the exact concentration of destination edges, as described in Section 1.2; the curves characterize the generated family rather than an isolated edge-count intervention.')
    table(['Graph','Vertices N','Directed edges E','Iterations I','Serial time (s)'],[
        [DISPLAY[g],f"{int(get(g,'Serial')['vertices']):,}",f"{int(get(g,'Serial')['edges']):,}",
         get(g,'Serial')['iterations'],fmt(get(g,'Serial')['solve_median_s'])] for g in REPRESENTATIVE],
        [120,110,115,70,85],caption='Serial baselines for the three original inputs and the three large inputs used in the resource curves. N and E are counts; all times are five-run medians on CPU nodes.')

    heading('3.2.2 PageRank concentration in the real Google graph',3)
    para(f"The validated Google Serial vector has {GOOGLE['dangling_vertices']:,} dangling vertices ({GOOGLE['dangling_vertices']/GOOGLE['vertices']:.1%}), so dangling-mass redistribution is essential. The highest-scoring 1% of vertices carry {GOOGLE['top_1_percent_rank_mass']:.1%} of the total probability mass. Pearson correlation between PageRank and in-degree is {GOOGLE['pagerank_indegree_pearson']:.3f}: incoming links are strongly associated with rank, but raw in-degree is not the complete weighting rule.")
    table(['Node ID','PageRank','In-degree','Out-degree'],[[r['node_id'],f"{r['rank']:.7f}",r['in_degree'],r['out_degree']] for r in GOOGLE['top10'][:5]], [120,140,120,120],caption='Five highest-scoring Google vertices. PageRank is a dimensionless probability score; in-degree and out-degree are edge counts.')
    para('These anonymized vertex IDs cannot be mapped to named websites from this edge-list dataset alone. The observed rank concentration supports a structural statement about this graph; it does not identify trustworthy content or establish a causal relationship between links and importance.')

    heading('3.3 Fixed graphs with more CPU processes and nodes',2)
    heading('3.3.1 Increasing active cores through explicit process layouts',3)
    para('The graph is held fixed while active CPU parallelism increases. C=4 is the first common point because the hybrid line uses four threads per process; lower-core measurements remain in the full matrix. Pure MPI starts p=C single-threaded processes. MPI+OpenMP and MPI+Kokkos OpenMP retain four CPU threads per process and start p=C/4 processes. Up to 32 cores the line uses one node; at 64, 128, and 256 cores it uses two, four, and eight nodes. Thus process count and, at the larger points, node count increase together.')
    table(['Active cores C','Nodes n','MPI processes p','MPI threads T','Hybrid processes p','Hybrid threads T'],[
        [c,max(1,c//32),c,1,c//4,4] for c in (4,8,16,32,64,128,256)],
        [65,55,90,80,105,105],caption='Layouts used in both fixed-graph CPU figures. Each row is measured with Allgatherv and Halo; C=pT for every method. Hybrid denotes MPI+OpenMP and MPI+Kokkos OpenMP.')
    para('The following two figures have identical organization: original inputs first, then the three large inputs; speedup above and CPU efficiency below. Across the CPU resource figures, colors identify the same methods, and solid/dashed lines identify Allgatherv/Halo. The matching CPU-node Serial median is the reference. The curves use default automatic collective selection; the fixed-algorithm tests are presented separately in Section 3.5.2.')
    figure('02_strong_original','Fixed original graphs with increasing CPU resources. Top: speedup relative to each graph\'s Serial baseline (×). Bottom: speedup divided by C, expressed as CPU efficiency (%). Layouts are listed in the preceding table. A=Allgatherv and H=Halo; MPI uses T=1 and both hybrid methods T=4. Points are derived from five-run solve medians; matching rows share axis scales.')
    figure('03_strong_large','The same CPU process/node experiment on the large Uniform, Hub, and Controlled graphs, each with N=12.8 million vertices and E=204.8 million directed edges. Top: Serial-relative speedup (×); bottom: CPU efficiency (%). Layout, method colors, communication line styles, and statistic match the original-graph figure.')
    uniform=get('strong_uniform','MPI',host_nodes=8,processes=256,threads=1,communication='Halo')
    para(f"The large balanced Uniform graph reaches {number(uniform['speedup_vs_matched_serial']):.1f}× Serial speedup with MPI Halo at 256 cores, corresponding to {number(uniform['cpu_efficiency_vs_serial']):.1%} CPU efficiency. Google behaves differently: its best pure-MPI point is one node with 32 processes and Halo, at 0.149 s, whereas eight nodes and 256 processes take 1.462 s. The added communication and synchronization are not offset by enough useful work on this smaller input. Hub and Controlled also obtain less benefit from more processes despite having the same size as large Uniform.")
    para('Incoming-edge work explains the structural distinction. Each process receives approximately the same number of destination vertices, but these vertices can own very different numbers of incoming edges. The next figure measures the resulting maximum-to-mean edge load as process count increases; one indicates perfect edge balance.')
    figure('13_rank_workload','Incoming-edge workload imbalance for the three equal-size large graphs. The horizontal axis is MPI process count p; the vertical axis is maximum/mean incoming-edge count (dimensionless). Equal consecutive vertex partitions are used for all families. These are partition statistics, not timing ratios.')
    equation('', r'$$B_E=\frac{\max_i E_i}{E/p},\qquad p_{\mathrm{edge}}=\frac{E}{\max_i E_i}=\frac{p}{B_E}.$$')
    table(['Large graph, p=256','Max/mean edge load','Busiest process edge share (%)','Equal-work process proxy'],[
        [DISPLAY[r['graph']],f"{number(r['max_mean_edges']):.3f}",f"{number(r['max_rank_edge_share']):.2%}",fmt(r['equivalent_balanced_ranks'])]
        for r in WORK if r['processes']=='256'],[125,115,140,120],
        caption='Work concentration at 256 processes. B_E is dimensionless. The equal-work process proxy assumes equal edge-scanning rates and describes load balance; it is not an observed speedup or the number of processes launched.')
    para('All 256 processes are launched, but one process owns about 29%-30% of all edges on Hub and Controlled. The iteration must wait for that process, even when the others finish early. The edge-only load corresponds to roughly 3.4 or 3.3 perfectly balanced processes under an equal-rate model. Uniform remains nearly balanced. The generator places 75.0% and 77.5% of edges into the first 1% of destination IDs; contiguous ownership preserves that concentration. The hot block stays inside one process while p<=100 and first crosses process boundaries at higher counts. Halo changes exchanged values while leaving this ownership unchanged.')
    table(['Large graph; T=32','OpenMP time (s)','Kokkos OpenMP time (s)','Kokkos/OpenMP (×)','Largest static block edge share (%)'],[
        [DISPLAY[r['graph']],fmt(r['openmp_s']),fmt(r['kokkos_openmp_s']),fmt(r['kokkos_over_openmp']),f"{number(r['contiguous_32way_edge_share_proxy']):.1%}"] for r in POLICY],
        [105,85,105,90,115],caption='One-node scheduling comparison on the same large graphs. Each method uses one process and 32 CPU threads; times are five-run solve medians. The static-block share is an analytical workload proxy.')
    para('The same issue can occur within one process. OpenMP dynamically distributes destination chunks of 64 vertices. The compiled Kokkos RangePolicy uses static ranges by default [6]. A contiguous 32-way split leaves about 75.5%-78.0% of the concentrated graphs\' edges in one block. The methods have similar Uniform times but differ by about 22× on Hub and Controlled. This associates the performance gap with their implemented scheduling policies and workload ordering, rather than assigning the entire gap to framework overhead.')

    heading('3.3.2 Fixed 256-core budget: changing the process/thread split',3)
    para('This experiment holds the total resource count fixed instead of increasing it. Every configuration uses eight nodes and 256 CPU cores; p decreases as T increases. Both CPU hybrid implementations use the same six splits and both communication strategies. Each plotted ratio compares a graph\'s five-run median with the same method and exchange at p=256,T=1, before aggregating over the 45 graphs.')
    table(['Processes p','Threads/process T','MPI+OMP A (×)','MPI+OMP H (×)','MPI+KK A (×)','MPI+KK H (×)'],[
        [256//t,t,*[f"{number(next(r for r in SPLITS if r['method']==method and r['communication']==mode and r['threads']==str(t))['geomean_speedup_vs_T1']):.2f}"
                   for method in ('MPI+OpenMP','MPI+Kokkos OpenMP') for mode in ('Allgatherv','Halo')]]
        for t in (1,2,4,8,16,32)], [70,90,85,85,85,85],
        caption='Equal-core process/thread comparison. Values are geometric means of 45 paired speedups, each based on five-run median times. All rows satisfy pT=256; A=Allgatherv, H=Halo. The reference is the corresponding method\'s T=1 row, not Serial.')
    figure('04_fixed_256_splits','Changing process/thread decomposition at a fixed eight-node, 256-core budget. Horizontal axis: threads per process T, with p=256/T. Vertical axis: geometric-mean speedup relative to the same method/exchange at T=1 (×), over 45 graphs. Method colors and Allgatherv/Halo line styles match the preceding figures.')
    best={method:max((r for r in SPLITS if r['method']==method and r['communication']=='Halo'),key=lambda r:number(r['geomean_speedup_vs_T1']))
          for method in ('MPI+OpenMP','MPI+Kokkos OpenMP')}
    a=next(r for r in SPLITS if r['method']=='MPI+OpenMP' and r['communication']=='Allgatherv' and r['threads']=='32')
    k=next(r for r in SPLITS if r['method']=='MPI+Kokkos OpenMP' and r['communication']=='Allgatherv' and r['threads']=='32')
    para(f"With Allgatherv, T=32,p=8 improves the aggregate time ratio by {number(a['geomean_speedup_vs_T1']):.2f}× for MPI+OpenMP and {number(k['geomean_speedup_vs_T1']):.2f}× for MPI+Kokkos relative to their T=1 configurations. The best aggregate Halo splits use T={best['MPI+OpenMP']['threads']} and T={best['MPI+Kokkos OpenMP']['threads']}, with {number(best['MPI+OpenMP']['geomean_speedup_vs_T1']):.2f}× and {number(best['MPI+Kokkos OpenMP']['geomean_speedup_vs_T1']):.2f}× improvements. Fewer processes reduce collective participation and allow more local sharing of hot rows. The optimum remains graph-dependent; these aggregate ratios do not imply that every graph favors the same split.")

    heading('3.4 Standalone methods and one-to-two-GPU execution',2)
    heading('3.4.1 Standalone CPU/GPU baselines and MPI overhead',3)
    table(['Graph','CPU Serial (s)','OpenMP T32 (s)','KK OpenMP T32 (s)','GPU-node Serial (s)','CUDA (s)','KK CUDA (s)'],[
        [DISPLAY[g],fmt(get(g,'Serial')['solve_median_s']),fmt(get(g,'OpenMP',threads=32)['solve_median_s']),
         fmt(get(g,'Kokkos OpenMP',threads=32)['solve_median_s']),fmt(get(g,'Serial','gpu_node')['solve_median_s']),
         fmt(get(g,'CUDA','gpu_node')['solve_median_s']),fmt(get(g,'Kokkos CUDA','gpu_node')['solve_median_s'])]
        for g in REPRESENTATIVE], [105,65,65,70,70,60,65],
        caption='Standalone baselines on the same six representative graphs. CPU methods use one node; device methods use one A40. All values are five-run solve medians in seconds. CPU-node and GPU-node Serial references are kept separate.')
    para('Standalone device methods and MPI device methods differ even at one GPU. The distributed driver stages source contributions through host memory every iteration. On Google, standalone CUDA and Kokkos CUDA take 0.115 and 0.094 s, compared with approximately 0.243 and 0.383 s for their MPI Allgatherv p=1 versions. The difference is part of the distributed solve path, not the one-time graph loading or backend initialization.')
    heading('3.4.2 One versus two GPUs on fixed inputs',3)
    para('The distributed device comparison keeps each graph fixed and changes n=p=G from one to two, with one MPI process and one A40 per node. Allgatherv and Halo are each measured under automatic tuned selection. CPU-only MPI and MPI+OpenMP T=1 on the same node class provide layout-matched controls. Each curve is normalized to its own one-node time.')
    figure('06_gpu_node_scaling','Fixed-graph one-to-two-node comparison on the three large inputs. Device methods use one GPU per MPI process and node; CPU controls use T=1 and no device computation. Vertical axis: each method/exchange\'s one-node time divided by its n-node time (×). One-node reference is 1×. Colors, communication line styles, and panel axes are consistent across graphs; all source times are five-run medians.')
    table(['Large graph','GPU method','Busiest p2 edge share (%)','Compute p1/p2 (×)','Solve p1/p2 (×)'],[
        [DISPLAY[r['graph']],r['method'],f"{number(r['p2_max_edge_share']):.1%}",fmt(r['compute_speedup']),
         fmt(number(r['p1_solve_s'])/number(r['p2_solve_s']))] for r in GPU_WORK],
        [105,135,100,80,80],caption='Allgatherv GPU comparisons, presented identically for all three large graphs and both backends. Each ratio divides the p1 median by the p2 median; values above 1× favor two GPUs. The edge share is a partition statistic.')
    figure('08_gpu_phases','Five-run phase medians per solve (s) for the same Allgatherv cases on all three large graphs. CU=CUDA, KK=Kokkos CUDA; suffix 1/2 is GPU and process count. Dots show total solve, device computation, host staging, and MPI exchange/waiting. Panels share a logarithmic time scale. Separately reduced and summarized phases are not additive pieces of one median execution.')
    para('Uniform divides incoming-edge work approximately in half: both backends obtain about 2× computation acceleration, but increased MPI cost limits end-to-end improvement. Hub and Controlled leave roughly 87%-89% of all edges on one GPU, so native CUDA computation improves only about 1.1× while communication rises. Kokkos improves more on those graphs, indicating additional effects from kernel mapping, vertex reductions, and memory locality. The edge-only workload proxy describes one mechanism, rather than a universal runtime bound.')

    heading('3.5 Communication strategy and MPI implementation choice',2)
    para('Communication appears in all preceding MPI results. This section separates two different questions. Section 3.5.1 compares which contribution values are exchanged: the complete Allgatherv vector or the exact Halo dependency set. Section 3.5.2 holds that strategy fixed and changes how Open MPI schedules the collective. The first comparison reuses main-matrix measurements; the second uses separately matched diagnostic allocations. No standalone method acquires an MPI exchange parameter.')
    heading('3.5.1 Allgatherv versus exact Halo exchange',3)
    figure('05_halo_pairs','Matched communication comparisons on all 45 fixed graphs. Left: geometric-mean Allgatherv/Halo solve-time ratio (×); above 1× favors Halo. Right: median reduction in logical contribution payload (%), with measured zero labeled explicitly. Each pair matches graph, method, nodes, processes, and threads; p=1 is excluded. CPU-node and GPU-node populations have different layout ranges, so their aggregate bars are not a hardware-only comparison.')
    table(['Node class','Family','Matched pairs','Halo speedup (×)','Payload reduction (%)','Halo faster (%)'],[
        [r['context'].replace('_',' '),r['family'].title(),r['paired_configurations'],fmt(r['geomean_halo_speedup']),
         f"{number(r['median_payload_reduction']):.1%}",f"{number(r['halo_faster_fraction']):.1%}"] for r in HALO],
        [90,80,70,85,95,80],caption='Populations and statistics behind the communication bars. Speedup is the geometric mean of paired five-run-median ratios. Payload reduction and the fraction of pairs favoring Halo are percentages; they are different statistics.')
    figure('15_payload_by_process','Payload reduction (%) versus process count on the same fixed graphs. Each point is the family median across graphs for pure MPI with T=1; layouts use n=max(1,p/32) nodes. Only p changes the dependency partition, and each communication comparison holds that layout fixed. This view separates process-count effects from the different populations in the aggregate bars; byte counts exclude reduction and protocol traffic.')
    para('GPU-node Uniform has a measured median reduction of 0.0%, not an absent GPU result. Of its 105 matched pairs, 91 have zero contribution-payload savings. At p=2, most Uniform partitions require all source contributions owned by the other process, making the Halo contribution payload equal to Allgatherv. For large Uniform the aggregate payload is 102.4 MB per iteration with either strategy. These dependency counts are properties of the graph and partition, not of GPU arithmetic.')
    para('On CPU nodes the Google aggregate favors Halo by about 1.89× with a 58.6% median payload reduction. The synthetic families have aggregate gains near 1.19-1.23×, but many individual configurations still favor Allgatherv. Saving bytes does not remove packing, collective latency, global reductions, or waiting for imbalanced work. On device paths it also does not remove host staging. One-time Halo setup is outside solve timing and therefore cannot explain a timed-iteration slowdown.')
    table(['Graph; C=256','MPI p256/T1 (×)','MPI+OMP p64/T4 (×)','MPI+KK p64/T4 (×)'],[
        [DISPLAY[g],*[fmt(number(get(g,m,host_nodes=8,processes=256//t,threads=t,communication='Allgatherv')['solve_median_s'])/
                          number(get(g,m,host_nodes=8,processes=256//t,threads=t,communication='Halo')['solve_median_s']))
                     for m,t in [('MPI',1),('MPI+OpenMP',4),('MPI+Kokkos OpenMP',4)]]] for g in REPRESENTATIVE],
        [125,120,125,130],caption='Paired Allgatherv/Halo time ratios on the same six inputs at eight nodes and 256 CPU cores. Each cell holds method, p, and T fixed; ratios above 1× favor Halo. The three columns need not use the same process count.')

    heading('3.5.2 Default tuned selection versus fixed collective algorithms',3)
    para('The preceding resource and exchange comparisons use Open MPI\'s default automatic selection. The diagnostic controls below isolate implementation choices within a fixed graph, process layout, binary, affinity map, and allocation. Default means the compiled selection tree with coll_tuned_use_dynamic_rules=0. Forced-policy runs set that parameter to 1 and override only the named collective; this is forced dispatch, not online performance learning.')
    policy_layouts=[]
    for graph in ('strong_uniform','strong_hub','strong_controlled'):
        for c in ((64,128,256) if graph=='strong_uniform' else (32,64,128)):
            t=1 if graph=='strong_uniform' else 4
            policy_layouts.append([DISPLAY[graph],c//32,c,c//t,t,
                'Halo' if t==1 else 'Allgatherv',
                'Automatic; basic_linear; pairwise' if t==1 else 'Automatic; Bruck; Ring',3])
    table(['Graph','Nodes n','Cores C','Processes p','Threads T','Exchange','MPI implementations','Configs'],policy_layouts,
        [95,35,45,45,40,90,100,50],small=True,
        caption='Primary matched-policy matrix: nine Alltoallv configurations and eighteen Allgatherv configurations. Uniform uses pure MPI; Hub and Controlled use MPI+OpenMP. Every row compares three policies within one allocation and satisfies C=pT=32n. Each configuration has one warm-up and five timed solves.')
    para('The 27 policy-comparison configurations are complemented by 30 automatic-selection context configurations and two binding configurations, giving 59 unique diagnostic settings. The full node-boundary context has 36 settings: both exchanges for MPI and the two CPU hybrid methods on both concentrated graphs at C=32,64,128. Six automatic Allgatherv settings are already in the primary matrix and are counted once. The binding comparison holds n=8,p=256,T=1 and pairwise fixed. These context and binding results follow the two policy comparisons below.')
    para('Alltoallv exposes two actual algorithms in this Open MPI version, and both are tested. The Allgatherv comparison targets Bruck and Ring because automatic selection crosses between them at p=8-to-16 for these large inputs; it is not an exhaustive search over its five available algorithms. GatherV+Bcast and neighbor exchange are outside that targeted contrast, and the two-process implementation does not apply at p=8,16,32. Section 2.6 lists the complete menus and the separate meaning of algorithm ID 0.')
    triples=[]
    for c in (64,128,256):
        selected={r['policy']:r for r in CONTROLS if r['graph']=='strong_uniform' and r['cores']==str(c)}
        assert set(selected)=={'default','a2av_linear','a2av_pairwise'}
        assert len({r['communication_bytes_per_iteration'] for r in selected.values()})==1
        triples.append((c,selected))
    figure('11_collective_policies','Large Uniform with Halo: automatic Alltoallv selection versus forced basic_linear and pairwise. Every point is a five-run solve median (s); error bars span the five observed times and are not confidence intervals. Each process count shares one allocation across policies, while different counts use different allocations. Markers are slightly offset horizontally for visibility; the process axis is logarithmic.')
    table(['Processes p = cores C','Automatic (s)','basic_linear (s)','pairwise (s)','Automatic/pairwise (×)'],[
        [c,*[fmt(r[k]['solve_median_s']) for k in ('default','a2av_linear','a2av_pairwise')],
         fmt(number(r['default']['solve_median_s'])/number(r['a2av_pairwise']['solve_median_s']))]
        for c,r in triples], [90,95,100,95,120],caption='Alltoallv comparison on the same graph and layout within each row. Each value is a five-run median; all policies produce independently validated PageRank vectors.')
    control128=dict(triples)[128]
    para(f"At p=128, automatic selection takes {number(control128['default']['solve_median_s']):.3f} s and forced basic_linear {number(control128['a2av_linear']['solve_median_s']):.3f} s. Pairwise takes {number(control128['a2av_pairwise']['solve_median_s']):.3f} s, a {number(control128['default']['solve_median_s'])/number(control128['a2av_pairwise']['solve_median_s']):.2f}× improvement over automatic selection. The default range is {number(control128['default']['solve_min_s']):.3f}-{number(control128['default']['solve_max_s']):.3f} s and the pairwise range {number(control128['a2av_pairwise']['solve_min_s']):.3f}-{number(control128['a2av_pairwise']['solve_max_s']):.3f} s. Communication/waiting falls from {number(control128['default']['communication_median_s']):.3f} to {number(control128['a2av_pairwise']['communication_median_s']):.3f} s while convergence remains 12 iterations. This directly demonstrates a policy effect in the MPI path.")
    para('The default Alltoallv rule changes pairwise-to-basic_linear-to-pairwise across p=64,128,256. The controller uses process count rather than graph payload or congestion; different request concurrency, buffering, and MPI progress can therefore produce different performance at the boundary. The same 128-process communication peak appears on the separate growing Uniform series. Its mean logical peer payload differs from the fixed-input case, supporting a scheduling explanation beyond one average-message-size threshold. TCP eager/rendezvous behavior and shared-resource contention may interact with that schedule.')
    gather_controls=[]
    for graph in ('strong_hub','strong_controlled'):
        for c in (32,64,128):
            selected={r['policy']:r for r in CONTROLS if r['graph']==graph and r['cores']==str(c)
                      and r['implementation']=='hybrid' and r['communication']=='allgather'}
            assert set(selected)=={'default','agv_bruck','agv_ring'}
            gather_controls.append((graph,c,selected))
    figure('12_allgatherv_policies','Large Hub and Controlled with MPI+OpenMP Allgatherv: automatic selection versus forced Bruck and Ring. Both panels use n=1/2/4, C=32/64/128, T=4, and p=C/4, with a common time scale. Points are five-run solve medians (s); error bars show observed minima and maxima. Policies share an allocation within a resource point; markers are slightly offset for visibility.')
    table(['Graph','C / p','Automatic (s)','Bruck (s)','Ring (s)','Bruck/Ring (×)'],[
        [DISPLAY[g],f'{c} / {c//4}',*[fmt(r[k]['solve_median_s']) for k in ('default','agv_bruck','agv_ring')],
         fmt(number(r['agv_bruck']['solve_median_s'])/number(r['agv_ring']['solve_median_s']))]
        for g,c,r in gather_controls], [110,60,85,80,80,85],caption='Allgatherv transition controls, presented symmetrically for both graphs and all three resource points. T=4 throughout; only the selected collective implementation changes within a row.')
    para('At 64 cores, Hub takes 5.022 s under automatic selection, 5.010 s with Ring, and 5.550 s with Bruck. Controlled takes 3.886, 3.884, and 4.294 s, respectively. The default therefore agrees with Ring, while restoring Bruck does not improve this point. Unlike the Uniform 128-process Alltoallv case, this transition is not evidence that the default chose the slower of the two tested algorithms. At C=32, the default agrees with Bruck; the two transitions are evaluated using their own operation-specific algorithm menus.')
    context=[]
    for method,display in [('mpi','MPI'),('hybrid','MPI+OMP'),('mpi_kokkos','MPI+KK')]:
        for mode,label in [('allgather','Allgatherv'),('halo','Halo')]:
            ratios=[]
            for graph in ('strong_hub','strong_controlled'):
                a={int(r['cores']):r for r in CONTROLS if r['graph']==graph and r['implementation']==method
                   and r['communication']==mode and r['policy']=='default'}
                ratios.append(number(a[64]['solve_median_s'])/number(a[32]['solve_median_s']))
            context.append([display,label,*[f'{v:.3f}' for v in ratios]])
    table(['Method','Exchange','Hub: time64/time32 (×)','Controlled: time64/time32 (×)'],context,
        [100,100,150,150],caption='Default-policy node-boundary context from the same diagnostic matrix. Each ratio compares two nodes/64 cores with one node/32 cores. MPI uses T1 and hybrids T4; graph structure and the policy setting are unchanged.')
    para('Across these twelve method/exchange/graph lines, time64/time32 lies near 0.93-1.04. The hot destination block still belongs to one hybrid process: its Hub edge share changes only from 77.90% to 76.33%, and Controlled from 80.11% to 78.69%. Extra processes mostly subdivide cold work, while crossing to two nodes adds inter-node progress and synchronization. This combination explains an approximately flat resource curve more naturally than an assumption that every algorithm transition must be harmful.')
    if LAUNCHER_CONTROLS:
        table(['Binding at p256, fixed pairwise','Solve median (s)','Five-run range (s)','MPI/wait median (s)'],[
            [('Native core binding' if r['launcher']=='ompi_core' else 'Explicit CPU mask'),fmt(r['solve_median_s']),
             f"{number(r['solve_min_s']):.3f}-{number(r['solve_max_s']):.3f}",fmt(r['communication_median_s'])]
            for r in LAUNCHER_CONTROLS], [175,95,125,105],caption='Launch-binding comparison within one eight-node, 256-core allocation. The graph and Alltoallv policy are fixed, and post-initialization affinity confirms one distinct CPU per process for both launchers.')
        para('The launchers produce medians of 2.975 and 3.111 s, with overlapping five-run ranges. Their modest difference does not account for the larger variation between allocations. In the policy-control allocation, p256 pairwise takes 3.563 s; in the binding allocation both launchers remain near 3 s. Host/NUMA placement, shared-fabric contention, and peer progress are plausible contributors. These matched controls quantify within-allocation changes and remain separate from the main resource curves; their values are not pooled or substituted into those curves.')

    heading('3.6 Growing graph size together with resources',2)
    heading('3.6.1 Constant nominal work per CPU core',3)
    para('This experiment changes the graph as CPU resources grow. At C=4,8,16,32,64,128,256, every method receives the same family input with N=50,000C vertices and E=800,000C edges. MPI uses p=C,T=1; the two hybrid methods use p=C/4,T=4. The principal comparison uses a common C=4 reference for all methods, so the graph sizes and efficiency definitions are directly comparable. This is a common reference definition applied to the saved per-iteration measurements. The separate rank-based p=1 reference series is retained in the accompanying data.')
    table(['Active cores C','Vertices N','Directed edges E','MPI p / T','Hybrid p / T'],[
        [c,f'{50000*c:,}',f'{800000*c:,}',f'{c} / 1',f'{c//4} / 4'] for c in (4,8,16,32,64,128,256)],
        [85,110,125,90,90],caption='Common growing-input CPU matrix. All three families and both Allgatherv/Halo settings use every row. Node count follows n=max(1,C/32); the per-core vertex and edge counts remain fixed.')
    figure('07_core_weak','Graph size grows with CPU resources at fixed nominal vertices and edges per core. Top: per-iteration solve time (ms/iteration). Bottom: retained efficiency (%) relative to each method/exchange at C=4 on the same family. MPI uses T1 and hybrids T4. Solid/dashed lines are Allgatherv/Halo; all panels use the same layouts and matching axis scales. Ideal proportional scaling retains a flat iteration time and 100% efficiency.')
    table(['Family','Method','C256 Allgatherv (%)','C256 Halo (%)'],[
        [f.title(),m,*[f"{number(next(r for r in GROWING if r['family']==f and r['method']==m and r['communication']==mode and r['active_cpu_threads']=='256')['matched_efficiency']):.2%}"
                      for mode in ('Allgatherv','Halo')]]
        for f in ('uniform','hub','controlled') for m in ('MPI','MPI+OpenMP','MPI+Kokkos OpenMP')],
        [80,170,125,125],caption='Retained per-iteration efficiency at 256 CPU cores, using the common C=4 reference of the preceding figure. Each percentage divides its C4 iteration time by its C256 iteration time; no Serial baseline enters this metric.')
    para('The common reference fixes the graph and core budget, but each method retains its own reference time. A higher retained percentage therefore need not mean a shorter absolute iteration; the two rows of the figure should be read together. Iteration cost increases even though nominal work per core is constant. On Uniform, retained efficiency at 256 cores is about 1.9%-5.2% depending on method and exchange; the concentrated families are lower. Allgatherv makes every process receive a contribution vector that grows with the global graph. With N proportional to p, its per-process contribution traffic is proportional to p and aggregate traffic to p squared. Equal vertex counts also fail to preserve equal incoming-edge work on Hub and Controlled.')
    figure('14_growing_communication','Pure-MPI growing Uniform inputs. Left: logical contribution payload (MB/rank/iteration); right: communication plus waiting (ms/iteration), each as a function of process count. N=50,000p and E=800,000p, T=1. Time points are the five-run median communication duration divided by iteration count. Both axes are logarithmic; byte counts exclude reductions and transport overhead.')
    uniform_traffic=[r for r in TRAFFIC if r['family']=='uniform' and int(r['processes']) in (16,64,256)]
    table(['Processes p','Exchange','Payload (MB/rank/iteration)','MPI + waiting (ms/iteration)'],[
        [r['processes'],r['communication'],f"{number(r['counted_payload_bytes_per_rank'])/1e6:.2f}",f"{number(r['communication_ms_per_iteration']):.2f}"]
        for r in uniform_traffic],[75,100,160,165],caption='Matched contribution volume and communication duration for growing Uniform. Rows compare the two exchanges at the same graph and process count; these are per-iteration quantities, not total job traffic.')
    para('Halo bounds Uniform payload near 6.4 MB per process per iteration, in contrast with Allgatherv\'s 102.0 MB at p=256. Nevertheless, Halo communication/waiting increases from 17.28 to 38.07 ms per iteration between p=64 and 256 while payload remains almost unchanged. More participating peers, collective/reduction latency, packing, and resource contention therefore matter in addition to contribution bytes. Concentrated inputs add waiting for heavily loaded processes to the same costs.')
    heading('3.6.2 Constant nominal work per GPU or MPI process',3)
    para('On GPU nodes, the growing-input comparison uses one and two nodes, with N=50,000p and E=800,000p. Device methods use one GPU per process; CPU controls use T=1 here to preserve the same host layout. Each method/exchange uses its own p=1 per-iteration time as reference. These percentages describe this one-to-two-resource experiment and are not compared numerically with the CPU C4-to-C256 percentages.')
    table(['GPU-node method','Uniform A (%)','Uniform H (%)','Hub A (%)','Hub H (%)','Controlled A (%)','Controlled H (%)'],[
        [method.replace('Cuda','CUDA'),*[f"{number(next(r for r in WEAK if r['suite']=='gpu_node' and r['method']==method and r['family']==family and r['processes']=='2' and r['threads']=='1' and r['communication']==mode)['weak_efficiency_per_iteration']):.1%}"
                  for family in ('uniform','hub','controlled') for mode in ('Allgatherv','Halo')]]
        for method in ('MPI','MPI+OpenMP','MPI+CUDA','MPI+Kokkos Cuda')],
        [140,60,60,60,60,60,60],small=True,caption='Per-iteration efficiency retained when both graph size and GPU-node process count double. A=Allgatherv, H=Halo; reference p1 and measured p2 each use five-run median time per iteration. CPU controls do not compute on GPUs.')
    para('The corresponding standalone runs on both graph sizes retain one node or device. They are fixed-resource input-size controls and are not assigned a resource-scaling efficiency. The complete growing-input inventory retains these 54 controls alongside the 318 resource-scaled configurations, with their layouts and original reference definitions.')

    story.append(PageBreak())
    heading('3.7 Complete fixed-input summary and additional high-core example',2)
    para('The following matrices summarize all 45 fixed graphs. Every cell is the best observed five-run median for that method over its legal configurations; selected layouts are retained in the accompanying data. The resource budget can differ between cells. These overview matrices complement, rather than replace, the fixed-layout and equal-core comparisons above.')
    table(['Graph','CPU Serial','OpenMP','KK OpenMP','MPI','MPI+OMP','MPI+KK'],[
        [abbreviated(r['graph']),*[fmt(r[m+'_best_s']) for m in ('Serial','OpenMP','Kokkos OpenMP','MPI','MPI+OpenMP','MPI+Kokkos OpenMP')]]
        for r in MATRIX],[140]+[60]*6,small=True,
        caption='CPU-node best observed solve medians (s), one row per fixed graph. KK=Kokkos; original/canonical are abbreviated o./s.; U/H/C identify generated families, followed by vertex count and mean out-degree.')
    story.append(PageBreak())
    table(['Graph','GPU-node Serial','CUDA','KK CUDA','MPI+CUDA','MPI+KK CUDA'],[
        [abbreviated(r['graph']),fmt(r['GPU-node Serial_s']),*[fmt(r[m+'_best_s']) for m in ('CUDA','Kokkos CUDA','MPI+CUDA','MPI+Kokkos CUDA')]]
        for r in MATRIX],[110]+[78]*5,small=True,
        caption='GPU-node best observed solve medians (s) for the same 45 graphs. The distributed device methods select over one/two GPUs and Allgatherv/Halo. The Serial column is measured on this node class.')
    story.append(PageBreak())
    figure('09_runtime_matrix','Best observed speedups (×) on all 45 graphs, each using its own node-class Serial reference. CPU and GPU-node blocks are separated. Color is logarithmic and clipped at 1/16× and 64×; the exact median seconds appear in the two tables. Different cells may use different resource budgets.')
    story.append(PageBreak())
    heading('3.7.1 Additional 512-core example',3)
    para('Five configurations on Controlled N=50,000 and E=200,000 use eight nodes with 64 active cores per node, giving 512 cores. This small-graph example is reported separately from the resource curves and aggregate method comparisons.')
    table(['Method','Processes p','Threads T','Exchange','Solve time (s)','Speedup (×)','CPU efficiency (%)'],[
        [r['method'],r['processes'],r['threads'],r['communication'],fmt(r['solve_median_s']),fmt(r['speedup']),f"{number(r['efficiency']):.3%}"]
        for r in SUPPLEMENT],[125,60,55,80,65,55,60],small=True,
        caption='Additional 512-core measurements. Every row satisfies pT=512 and uses one warm-up plus five timed solves; speedup uses this graph\'s CPU-node Serial median. The rows are not a complete 512-core scaling curve.')
    para('All five configurations are slower than Serial on this graph, and the p512 Halo configuration is particularly costly. Distributing a small amount of graph work across many participants amplifies synchronization and exchange overhead. The example therefore illustrates a workload-size constraint rather than a general high-core ranking.')
    cpu=OPTIMA['cpu_all'];device=OPTIMA['gpu_device_only'];controls=OPTIMA['gpu_with_cpu_controls']

    story.append(PageBreak())
    heading('4 Conclusions and insights')
    heading('4.1 What the experiments establish',2)
    para(f"Standalone OpenMP or Kokkos OpenMP gives the lowest observed CPU-node runtime on {cpu['method_counts'].get('OpenMP',0)+cpu['method_counts'].get('Kokkos OpenMP',0)}/45 graphs; only {cpu['multirank_winners']} winning configurations use multiple MPI ranks. Standalone CUDA or Kokkos CUDA wins all 45 device-only comparisons, but including GPU-node CPU controls changes the winners to OpenMP on {controls['method_counts'].get('OpenMP',0)} graphs, native CUDA on {controls['method_counts'].get('CUDA',0)}, and Kokkos CUDA on {controls['method_counts'].get('Kokkos CUDA',0)}. These best-observed comparisons screen implementations across budgets. The matched resource curves establish the separate scaling result: additional participants help large balanced inputs, while smaller or concentrated inputs often favor fewer processes and more threads per process.")
    para('The underlying constraint is the distribution of edge work, not graph size alone. Equal vertex ownership leaves roughly 29%-30% of the concentrated graphs’ edges on one process at p=256. Local scheduling and the process/thread split therefore determine how effectively the allocated cores can contribute. Exact Halo exchange changes communication dependencies but leaves this ownership imbalance intact.')
    para('Reduced contribution traffic is not equivalent to reduced solve time. Collective scheduling, packing, synchronization, and host/device staging also matter. Matched controls show that a fixed pairwise Alltoallv improves the p=128 Uniform solve by 4.66× relative to automatic selection; they do not establish a universally optimal collective. Similarly, faster device computation does not guarantee a benefit from a second GPU. The practical choices below follow from these workload-dependent effects.')
    heading('4.2 Design implications supported by the experiments',2)
    para('The results suggest different priorities for different workloads. More resources, fewer contribution bytes, and a portable execution interface address different costs; none alone determines runtime. The following decisions follow from the matched resource, exchange, and workload comparisons rather than from a universal ranking of programming models.')
    table(['Workload or decision','Evidence-based implication','Basis in the results'],[
        ['Small or moderate fixed graph','Evaluate a single-node backend before increasing MPI participation.','Standalone OpenMP/Kokkos OpenMP is fastest in 42 of 45 CPU-node best-observed comparisons.'],
        ['Large, balanced graph','Consider distributed execution and compare both exact exchanges at the target layout.','Large Uniform benefits from MPI resources; the selected 256-core Halo point reaches 28.6× Serial speedup.'],
        ['Concentrated incoming-edge work','Prioritize ownership balance and local scheduling; compare p/T at equal cores.','One process owns roughly 29%-30% of edges at p256. Changing the fixed-core split improves aggregate Halo ratios by over an order of magnitude.'],
        ['Collective-selection boundary','Retain the automatic baseline and test candidate implementations within matched allocations.','At p128 pairwise improves Uniform by 4.66×; at 64 cores Ring already matches or improves on Bruck for the tested concentrated graphs.'],
        ['Adding a second GPU','Measure end-to-end solve and staging/MPI costs alongside device computation.','Uniform obtains about 2× computation acceleration, while concentrated inputs leave most edge work on one GPU.'],
        ['Graph size grows with resources','Track iteration time and contribution volume separately from nominal vertices/edges per worker.','Allgatherv contribution traffic grows with the global vector; Halo bounds Uniform bytes but does not eliminate peer and synchronization costs.']],
        [105,200,195],caption='Practical implications of the measured cases. These are workload-dependent design choices, not claims that one backend or communication implementation is universally optimal.')
    para('The Google output provides a complementary data conclusion: score mass is concentrated and strongly associated with incoming links, while in-degree is not the full weighting rule. Numerical agreement across implementations preserves that graph-level conclusion; hardware and communication choices change the cost of obtaining it.')
    heading('4.3 Scope and reproducibility',2)
    para('The study combines fixed-input scaling, equal-core method comparisons, growing-input comparisons, and matched collective-policy controls. Each configuration uses five timed repeats within an allocation, with CPU models and process/core maps retained. Placement, NUMA regions, and execution dates vary across shared-cluster allocations. Solve time includes iterative computation, communication, and device staging; job startup and graph input are excluded. GPU comparisons use one or two A40 devices.')
    para('The repository [5] provides source code, reproducible input-generation parameters, original timing summaries, independent validation records, and measurement-selection rules. Report tables and figures can be regenerated from these records without repeating the performance experiments.')
    heading('4.4 References',2)
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
    heading('AI usage',2)
    para('AI assistance supported adaptation of the existing implementation, experiment design, job scripts, debugging, result verification, visualization, and report drafting. All performance values were measured by compiled programs on NUS Vanda. Numerical results were checked independently against Serial and residual criteria; tables and figures were generated from stored measurements. The authors are responsible for reviewing the code, experimental choices, interpretation, and final text.')
    (ROOT/'report.md').write_text('\n'.join(md).rstrip()+'\n')
    PDF.parent.mkdir(parents=True,exist_ok=True)
    def page(canvas,doc):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(GRAY)
        canvas.drawString(47,25,'DSA5208 | Parallel PageRank | Vanda results')
        canvas.drawRightString(A4[0]-47,25,str(doc.page));canvas.restoreState()
    doc=SimpleDocTemplate(str(PDF),pagesize=A4,rightMargin=47,leftMargin=47,topMargin=42,bottomMargin=43,
                          title=title,author='DSA5208 project group',pageCompression=1)
    # Keep a heading chain with its opening paragraph or table/figure block.
    # Explicit grouping also prevents ReportLab breaking before a nested KeepTogether.
    grouped=[];position=0
    heading_styles={'SectionReport','SubReport','SubSubReport'}
    while position<len(story):
        item=story[position]
        if isinstance(item,Paragraph) and item.style.name in heading_styles:
            block=[]
            while position<len(story) and isinstance(story[position],Paragraph) and story[position].style.name in heading_styles:
                block.append(story[position]);position+=1
            if position<len(story) and not isinstance(story[position],PageBreak):
                block.append(story[position]);position+=1
            grouped.append(KeepTogether(block))
        else:
            grouped.append(item);position+=1
    doc.build(grouped,onFirstPage=page,onLaterPages=page)
    equations.merge(PDF)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdftoppm',help='Poppler executable for PNG figure exports')
    args=parser.parse_args()
    assert AUDIT['fixed_configurations']==19530 and AUDIT['max_main_cpu_cores']==256
    items=figures();write_figures(items,args.pdftoppm);report(items)
    print(PDF)
    print('Structured results, matched layouts, explicit units, five-run policy ranges, and four report sections.')


if __name__=='__main__':
    main()
