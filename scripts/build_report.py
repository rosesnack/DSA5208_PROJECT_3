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
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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


def speedup_color(speedup):
    """Common diverging scale: orange <1x, white 1x, blue >1x."""
    v=math.log2(speedup)
    if v>=0:
        t=min(v/6,1)
        return colors.Color(1-.90*t,1-.55*t,1-.38*t)
    t=min(-v/4,1)
    return colors.Color(1-.07*t,1-.50*t,1-.74*t)


def notation(text):
    return re.sub(r'\b([npTCG])([1-9][0-9]*)(?![0-9=])',r'\1=\2',str(text))


def inline(text):
    """Render explicit Markdown emphasis without admitting arbitrary markup."""
    return re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',html.escape(str(text)))


def runtime_legend():
    d=Drawing(500,32)
    d.add(String(0,21,'Cell number: solve median (s)   |   Color: Serial / cell time (×)',
                 fontName='Helvetica',fontSize=8,fillColor=INK))
    for i,v in enumerate((1/16,1/4,1,4,16,64)):
        x=8+i*65
        d.add(Rect(x,1,25,11,fillColor=speedup_color(v),strokeColor=GRAY,strokeWidth=.3))
        d.add(String(x+29,3,('<=1/16' if v==1/16 else '>=64' if v==64 else f'{v:g}')+'×',
                     fontName='Helvetica',fontSize=7,fillColor=INK))
    return d


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
                          'Speedup vs Serial (×)',[4,16,64,256],shared_y=True,height=212)
        efficiency=[[(label,[(c,y/c) for c,y in points],color,dash)
                     for label,points,color,dash in panel] for panel in panels]
        eff=line_panels([DISPLAY[g] for g in graphs],efficiency,'Active CPU cores C (count)',
                        'CPU efficiency (%)',[4,16,64,256],shared_y=True,height=212,
                        y_format=lambda v:f'{v:.1%}')
        combined=Drawing(500,438)
        group=Group(*speed.contents);group.translate(0,224);combined.add(group)
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
                      'Iteration time (ms/iteration)',[4,16,64,256],height=212,shared_y=True)
    efficiency=[]
    for family,panel in zip(('uniform','hub','controlled'),panels):
        curves=[]
        for (label,points,color,dash) in panel:
            base=points[0][1]
            curves.append((label,[(c,base/value) for c,value in points],color,dash))
        efficiency.append(curves)
    retained=line_panels(['Uniform','Hub','Controlled'],efficiency,'Active CPU cores C (count)',
                         'Retained efficiency: C=4 reference (%)',[4,16,64,256],height=212,
                         shared_y=True,y_format=lambda v:f'{v:.1%}')
    combined=Drawing(500,438)
    group=Group(*times.contents);group.translate(0,224);combined.add(group)
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
    styles.add(ParagraphStyle(name='BodyReport',fontName='Times-Roman',fontSize=10.3,leading=12.8,spaceAfter=5.5,textColor=INK,allowWidows=0,allowOrphans=0))
    styles.add(ParagraphStyle(name='SectionReport',fontName='Helvetica-Bold',fontSize=15,leading=18.5,spaceBefore=13,spaceAfter=8,textColor=INK,keepWithNext=True))
    styles.add(ParagraphStyle(name='SubReport',fontName='Helvetica-Bold',fontSize=11.5,leading=15,spaceBefore=9,spaceAfter=6,textColor=BLUE,keepWithNext=True))
    styles.add(ParagraphStyle(name='SubSubReport',fontName='Helvetica-Bold',fontSize=10.5,leading=14,spaceBefore=10,spaceAfter=7,textColor=INK,keepWithNext=True))
    styles.add(ParagraphStyle(name='CaptionReport',fontName='Helvetica',fontSize=8,leading=10,spaceAfter=8,textColor=GRAY))
    styles.add(ParagraphStyle(name='ReferenceReport',parent=styles['CaptionReport'],spaceAfter=4))
    styles.add(ParagraphStyle(name='TableReport',fontName='Helvetica',fontSize=8,leading=10,textColor=INK))
    styles.add(ParagraphStyle(name='EquationReport',fontName='Times-Roman',fontSize=10,leading=15,alignment=TA_CENTER,spaceAfter=10,textColor=INK))
    styles.add(ParagraphStyle(name='TableCaptionReport',parent=styles['CaptionReport'],keepWithNext=True))
    story=[];md=[]
    table_number=0
    equations=LatexEquations(REPORT/'equations', ROOT/'tmp/pdfs/latex_build')
    def para(text):
        text=notation(text)
        md.append(text+'\n');story.append(Paragraph(inline(text),styles['BodyReport']))
    def heading(text,level=1):
        md.append('#'*(level+1)+' '+text+'\n');story.append(Paragraph(html.escape(text),styles['SectionReport' if level==1 else 'SubReport' if level==2 else 'SubSubReport']))
    def table(headers,rows,widths=None,small=False,caption=None,emphasis=None,heatmap=None,extrema=None):
        nonlocal table_number
        table_number+=1
        assert caption
        caption=f'Table {table_number}. '+notation(caption)
        emphasis=emphasis or {}
        emphasis=dict(emphasis)
        for column,direction in (extrema or {}).items():
            values=[float(str(row[column]).replace('%','').replace(',','')) for row in rows]
            best=(max if direction=='max' else min)(values)
            for i,value in enumerate(values):
                if value==best:emphasis[i,column]='good'
        backgrounds={};foregrounds={};bold=set(emphasis)
        for cell,kind in emphasis.items():
            if kind=='good':backgrounds[cell]=colors.HexColor('#dceee7')
            elif kind=='warn':backgrounds[cell]=colors.HexColor('#fae5cc')
        if heatmap:
            for i,(values,baseline) in enumerate(zip(heatmap['values'],heatmap['baselines'])):
                best=min(values)
                for j,value in enumerate(values,1):
                    if j==1:
                        backgrounds[i,j]=colors.HexColor('#e8edf1')
                    else:
                        c=speedup_color(baseline/value);backgrounds[i,j]=c
                        if .2126*c.red+.7152*c.green+.0722*c.blue<.57:
                            foregrounds[i,j]=colors.white
                    if value==best:bold.add((i,j))
        for i,row in enumerate(rows):
            if str(row[0]).lower().startswith('total'):
                bold.update((i,j) for j in range(len(headers)))
        md.append(caption+'\n')
        md.append('| '+' | '.join(map(str,headers))+' |\n| '+' | '.join(['---']*len(headers))+' |')
        for i,row in enumerate(rows):
            md.append('| '+' | '.join(('**'+str(x)+'**') if (i,j) in bold else str(x) for j,x in enumerate(row))+' |')
        md.append('')
        fs=7.8 if heatmap else 7.0 if small else 8
        data=[]
        for i,row in enumerate([headers,*rows]):
            rendered=[]
            for j,x in enumerate(row):
                heavy=i==0 or (i-1,j) in bold
                style=ParagraphStyle('cell',parent=styles['TableReport'],fontSize=fs,
                    leading=9 if heatmap else fs+2,fontName='Helvetica-Bold' if heavy else 'Helvetica',
                    textColor=foregrounds.get((i-1,j),INK),alignment=TA_CENTER if heatmap and j else TA_LEFT)
                rendered.append(Paragraph(inline(x),style))
            data.append(rendered)
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        commands=[('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eff4')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.65,BLUE),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f7f9')]),
            ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
            ('TOPPADDING',(0,0),(-1,-1),1.6 if heatmap else 2 if small else 2.5),
            ('BOTTOMPADDING',(0,0),(-1,-1),1.6 if heatmap else 2 if small else 2.5)]
        for (i,j),c in backgrounds.items():commands.append(('BACKGROUND',(j,i+1),(j,i+1),c))
        if heatmap:
            for i,j in bold:commands.append(('BOX',(j,i+1),(j,i+1),.8,INK))
            for i in (3,6,42):commands.append(('LINEABOVE',(0,i+1),(-1,i+1),.55,GRAY))
        t.setStyle(TableStyle(commands))
        prefix=[]
        if len(rows)<=12 and story and isinstance(story[-1],Paragraph) and story[-1].style.name=='SubReport':
            prefix.append(story.pop())
        prefix.append(Paragraph(inline(caption),styles['TableCaptionReport']))
        story.extend([KeepTogether(prefix+[t,Spacer(1,6)])] if len(rows)<=12 else prefix+[t,Spacer(1,6)])
    figure_number=0
    def figure(name,caption):
        nonlocal figure_number
        figure_number+=1
        caption=re.sub(r'^Figure [0-9]+[a-z]?\.\s*','',caption)
        caption=f'Figure {figure_number}. '+notation(caption)
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
    para('We evaluate synchronous PageRank on 45 fixed directed graphs (3 original, 42 reproducible extensions) using Serial, OpenMP, MPI, MPI+OpenMP, CUDA, and Kokkos OpenMP/CUDA. The 19,530 fixed-input configurations test added parallelism and equal-core process/thread decompositions. A separate suite contains 27 scale-specific inputs, 318 resource-scaled configurations, and 54 fixed-resource size controls: it tests whether iteration time stays constant as work and resources grow together. Vanda measurements use one warm-up and the median of five timed solves, with independent numerical validation. Balanced inputs benefit from distributed execution; concentrated incoming edges limit effective parallelism. Halo reduces contribution traffic but not invariably runtime, and a second GPU need not accelerate the solve.')
    if CONTROLS:
        para(f"A further {len(CONTROLS)+len(LAUNCHER_CONTROLS)} allocation-matched diagnostic settings separate collective policies, node boundaries, and binding effects from graph/partition behavior.")
    heading('1 Introduction to the algorithm and data')
    heading('1.1 PageRank and its relation to PPR',2)
    para('PageRank is the stationary probability of a random surfer: with probability alpha it follows an outgoing edge; otherwise it jumps according to a preference vector. We use uniform preference and uniform dangling-mass redistribution: standard PageRank, the uniform-preference special case of personalized PageRank (PPR).')
    equation('', r'$$r_v^{(k+1)}=\frac{1-\alpha}{N}+\frac{\alpha D^{(k)}}{N}+\alpha\sum_{u:(u,v)\in\mathcal{E}}\frac{r_u^{(k)}}{d_{\mathrm{out}}(u)}.$$')
    para('N is vertex count, script E the directed edge set, r_v the score, and d_out(u) the outgoing degree. D sums scores of dangling vertices (out-degree zero) for uniform redistribution. Scores start at 1/N. We use alpha=0.85, double precision, synchronous old/new buffers, and stop at L1 score change epsilon=10^-8 or 1,000 iterations:')
    equation('', r'$$D^{(k)}=\sum_{u:d_{\mathrm{out}}(u)=0}r_u^{(k)},\qquad \Delta^{(k)}=\left\|\mathbf{r}^{(k+1)}-\mathbf{r}^{(k)}\right\|_1\leq\varepsilon.$$')
    para('Incoming CSR (compressed sparse row) stores one source list per destination. Each update scans that row; work per iteration and storage are O(N+E).')
    para('Parallelism requires per-iteration remote source scores and global reductions for dangling mass and convergence. Equal vertex ownership does not balance row scans: a destination with 10,000 incoming edges costs more than one with two. Communication, synchronization, and unequal row lengths make this a nontrivial parallel workload.')
    heading('1.2 Fixed-input graphs for resource comparisons',2)
    para('All 45 inputs stay unchanged across resource and fixed-core comparisons, including the 42 extensions; fixed input does not refer only to the original three files.')
    table(['Source','Graphs','Vertices N','Directed edges E','Purpose'],[
        ['Original Google','1','875,713','5,105,039','Real web-link graph'],
        ['Original uniform and hub','2','100,000 each','1,000,000 each','Original synthetic controls'],
        ['Canonical extensions','3','100,000','1,000,000','One per generated family'],
        ['Size-density grid','36','50k / 100k / 200k / 400k','N x 4 / 8 / 16','3 families x 4 sizes x 3 densities'],
        ['Large extensions','3','12,800,000','204,800,000','One per generated family'],
        ['Total fixed graphs','45','','','3 original + 42 extensions']], [95,35,107,107,156],caption='Fixed-input graph collection. N and E count vertices and directed edges; the grid crosses mean degree with vertex count.')
    para("Extensions use seed 5208, deterministic integer mixing, and unique arithmetic progressions. Uniform has fixed source degree and destinations spread across all vertices. Hub targets approximately 80% of each source's edges at the first 1% of vertices. Controlled adds two source-degree classes: 80% lower-degree and 20% higher-degree sources. Original Uniform/Hub files are preserved and differ from same-size canonical extensions.")
    para('At E/N=16, floor(4*d_out/5) sends exactly 75.0% of Hub edges and 77.5% of Controlled edges to the first 1% of destination IDs. These fractions drive the workload model. The hot block aligns with contiguous partitions, so the experiment evaluates structure together with vertex ordering and ownership.')
    para("Controlled's hot-block fraction is 65.0% at mean degree 4 and 77.5% at degrees 8 and 16. Density changes both E and exact concentration; the grid characterizes a reproducible generator family rather than an isolated edge-count intervention.")
    para('The grid crosses vertex count and mean out-degree independently. The large graphs hold N and E equal across families to isolate structural differences. Every fixed-input configuration uses the same 45 graphs.')
    heading('1.3 Graphs that grow with resource count',2)
    para("Uniform, Hub, and Controlled use scales s=1,2,4,8,16,32,64,128,256, with N=50,000s and E=800,000s: 27 input identifiers. The largest scale (12.8M vertices, 204.8M edges) is also each family's large fixed input; these role-based input counts overlap.")
    para('Rank-normalized suites set s=p; core-normalized suites set s=C. CPU records comprise 150 rank-normalized and 84 core-normalized cases. GPU-node records use six inputs (3 families, s=1/2): 84 distributed resource-scaled cases and 54 standalone size controls. Total: 372 records, including 318 resource-scaled cases and 54 fixed-resource controls.')

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
    para('Example: n=4,r=8,T=4 gives p=32 processes and C=128 active CPU cores. Distributed device methods use one process and GPU per node, G=p=n. GPU kernel threads are separate from host CPU threads T.')
    table(['Implementation','Compute and work distribution','MPI exchange'],[
        ['Serial','One CPU thread; incoming CSR pull','Not applicable'],
        ['OpenMP','CPU threads; dynamic row scheduling, chunks of 64 vertices','Not applicable'],
        ['Kokkos OpenMP','CPU threads; default static RangePolicy and reductions','Not applicable'],
        ['CUDA / Kokkos CUDA','One GPU; incoming-row vertex kernels','Not applicable'],
        ['MPI','Contiguous destination partitions; one CPU thread per process','Allgatherv; Halo'],
        ['MPI+OpenMP','Threaded pull within each MPI partition','Allgatherv; Halo'],
        ['MPI+CUDA','One GPU per MPI process; host buffers for MPI exchange','Allgatherv; Halo'],
        ['MPI+Kokkos','Distributed driver with OpenMP or CUDA execution space','Allgatherv; Halo']], [105,275,120],caption='Implemented compute methods, local work distribution, and applicable MPI exchange strategies.')
    para('Standalone methods make no MPI calls: OpenMP threads share host memory; CUDA threads cooperate through device kernels/memory. MPI+OpenMP uses MPI_THREAD_FUNNELED (only the main thread calls MPI).')
    para("MPI partitions consecutive destination IDs approximately equally. Each process stores and updates its destinations' incoming rows; the exchanges differ in the source contributions supplied to those rows:")
    table(['Strategy','Values exchanged each iteration','MPI operation'],[
        ['Allgatherv','Every process receives the contribution value for every vertex, assembling a complete vector. This is simple but also transfers values that a process may not need.','MPI_Allgatherv'],
        ['Halo','Each process receives only distinct remote-source values referenced by its incoming rows. Required source IDs are determined once; later iterations exchange their current values.','MPI_Alltoallv']], [75,320,105],caption='The two exact MPI contribution-exchange strategies and the data communicated in each iteration.')
    para('Both exchanges are exact and retain dangling-mass/convergence Allreduce calls. Halo builds request lists before timing; packing and current-value exchange occur inside each timed iteration.')
    para('Logical contribution payload excludes reductions, protocol overhead, and collective-internal traffic. Allgatherv counts 8N(p-1) aggregate bytes; Halo counts 8 bytes per requested remote contribution. MB denotes 10^6 bytes. Metadata setup is separate and untimed; smaller payload need not imply lower latency.')
    para('Iteration progress waits for the slowest owner and the collectives. MPI phase time includes packing/copies, collective calls, and reduction waits, not only network transfer. Solve and phase times each take the maximum across ranks, then the median across runs; separately reduced phases are not additive components of one critical-path execution.')
    para('Distributed device methods stage contributions through host memory, without CUDA-aware MPI or computation/communication overlap. CUDA uses 256-thread blocks; Kokkos uses Views, parallel_for/parallel_reduce, and execution-space fences. Its OpenMP and CUDA backends execute on different hardware.')
    heading('2.2 Hardware, software and timing protocol',2)
    para('All timings are from Vanda: Intel Xeon Platinum 8452Y, GCC 13.3.0, Open MPI 4.1.8, Release builds; GPU nodes add NVIDIA A40 and CUDA toolkit 12.4.1. Toolkit identity comes from build metadata, not driver compatibility. Laptop/mixed-hardware exploratory data are excluded.')
    para('**Timing protocol.** One warm-up, five timed solves, median recomputed from the original solve_s values. MPI time is the maximum across ranks. Timed: iterations, MPI, device staging. Untimed: input, distribution, backend construction, Halo setup, and standalone GPU setup/final rank copies. These are solver rather than end-to-end application times.')
    para('**Backend boundaries.** OpenMP team creation is timed; Kokkos initialization is not. Compute phases use fenced host clocks, including dispatch/reduction costs, rather than pure-kernel CUDA events. Transfer phases cover explicit staging, not necessarily internal scalar-result copies. These differences matter particularly for small inputs.')
    para('Twelve identified MPI+Kokkos cases use lower-memory initialization but identical timed update/communication kernels; their graph construction and memory preparation remain untimed.')
    heading('2.3 Experimental configuration matrix',2)
    para('**Configuration = graph × implementation × valid layout × exchange**, not a timed repeat. All 45 graphs cross every listed row. Derived p=nr, C=pT, G=p=n are not extra dimensions; CPU layouts require rT<=32. Standalone methods have no MPI-exchange dimension.')
    para('**CPU nodes:** Q={1,2,4,8,16,32}; each MPI layout runs Allgatherv and Halo.')
    table(['Implementation','Nodes n','Ranks/node r','Processes p','Threads T','CPU cores C','MPI exchange','Configs'],[
        ['Serial','1','1','1','1','1','Not applicable','45'],
        ['OpenMP','1','1','1','Q','T','Not applicable','270'],
        ['Kokkos OpenMP','1','1','1','Q','T','Not applicable','270'],
        ['MPI','1,2,4,8','Q','nr','1','nr','Allgatherv; Halo','2,160'],
        ['MPI+OpenMP','1,2,4,8','Q','nr','Q; rT<=32','nrT','Allgatherv; Halo','7,560'],
        ['MPI+Kokkos OpenMP','1,2,4,8','Q','nr','Q; rT<=32','nrT','Allgatherv; Halo','7,560']], [100,43,52,56,60,50,86,53],small=True,caption='CPU-node fixed-input matrix. Every row is crossed with all 45 graphs; Q={1,2,4,8,16,32} and the constraint rT<=32 selects valid layouts.')
    para('MPI has 4×6=24 layouts/graph; each CPU hybrid has 4×21=84 valid (n,r,T) layouts/graph. Crossing 45 graphs and 2 exchanges gives 2,160 and 7,560 cases respectively; CPU-node total is 17,865. Standalone p=1 denotes one process without an MPI communicator.')
    para('**GPU nodes:** the first four rows compute on GPUs; the remaining rows are CPU controls on the same node class (G=0).')
    table(['Implementation','Nodes n','Processes p','CPU threads T','GPUs G','MPI exchange','Configs'],[
        ['CUDA','1','1','1 host','1','Not applicable','45'],
        ['Kokkos CUDA','1','1','1 host','1','Not applicable','45'],
        ['MPI+CUDA','1,2','n','1 host','n','Allgatherv; Halo','180'],
        ['MPI+Kokkos CUDA','1,2','n','1 host','n','Allgatherv; Halo','180'],
        ['Serial CPU control','1','1','1','0','Not applicable','45'],
        ['OpenMP CPU control','1','1','1,2,4,8,16,32','0','Not applicable','270'],
        ['MPI CPU control','1,2','n','1','0','Allgatherv; Halo','180'],
        ['MPI+OpenMP CPU control','1,2','n','1,2,4,8','0','Allgatherv; Halo','720']], [118,44,50,65,42,124,57],small=True,caption='GPU-node fixed-input matrix, including device-computing methods and same-node-class CPU controls. G counts GPUs used for computation.')
    para('GPU-node total: 450 device cases + 1,215 CPU controls = 1,665; complete fixed-input total: **19,530**. Serial/ordinary OpenMP remain CPU methods; standalone rows have no exchange parameter.')
    para('Principal line: n=1/2/4/8, C=32/64/128/256, 32 active cores/node; MPI p=C,T=1, hybrids p=C/4,T=4. Equal-core tests instead vary T in Q and p=C/T within the same C.')
    heading('2.4 Scaling questions and statistical summaries',2)
    para('**Fixed graph, more workers:** hold N, E, structure, and stopping rule fixed; increase C. Ideal doubling of cores halves solve time. With t_ser and t(C) denoting matched Serial and parallel medians:')
    equation('', r'$$S(C)=\frac{t_{\mathrm{ser}}}{t(C)},\qquad \eta_{\mathrm{CPU}}(C)=\frac{S(C)}{C}.$$')
    para('Speedup is dimensionless; CPU efficiency is a percentage (100% means ideal linear speedup). These curves locate communication, synchronization, or granularity limits. The separate C=256 test varies p/T to compare decompositions at equal resources.')
    para('**More work with more workers:** grow graph size with resources and ask whether iteration time remains constant. Rank-normalized inputs use N=50,000p,E=800,000p; core-normalized inputs use N=50,000C,E=800,000C, allowing equal nominal work/core across hybrid decompositions. Fixed counts per worker do not ensure constant communication or balanced incoming edges.')
    table(['Growing-input block','Graph scale','Resource layouts','Configurations'],[
        ['Rank-normalized CPU','s=p; 3 families','MPI and MPI+Kokkos T1: p=1,...,256 in powers of 2; MPI+OpenMP T4: p=1,...,64; Allgatherv and Halo','150'],
        ['Core-normalized CPU','s=C; 3 families','MPI+OpenMP and MPI+Kokkos OpenMP: T4, p=C/4; C=4,...,256 in powers of 2; Allgatherv and Halo','84'],
        ['GPU-node resource scaling','s=p=1,2; 3 families','Distributed GPU methods and distributed CPU controls; n=p; Allgatherv and Halo','84'],
        ['GPU-node input-size controls','s=1,2; 3 families','Standalone Serial, OpenMP, CUDA, and Kokkos CUDA retain one node while input size increases','54'],
        ['Total','','318 resource-scaled configurations + 54 fixed-resource controls','372']], [115,85,245,55],small=True,caption='Growing-input experiment groups. Counts refer to configurations, not five-run repetitions; fixed-resource controls are kept separate.')
    para('Convergence counts I can change with graph size. We therefore compare iteration time tau rather than confounding iteration cost with solve length; C0 is the smallest point in each resource series:')
    equation('', r'$$\tau(C)=\frac{t(C)}{I(C)},\qquad \eta_{\mathrm{grow,iter}}(C)=\frac{\tau(C_0)}{\tau(C)}.$$')
    para("Ideal retained efficiency is 100%; 25% means four times the reference iteration time. The common CPU plot uses C0=4 on identical family inputs: MPI p=C,T=1; hybrids p=C/4,T=4. Rank-normalized p0=1 series and total-solve efficiency remain in the data. CPU/GPU-node speedups use their own Serial reference; two-GPU scaling uses each method's one-GPU time.")
    para('**Two statistical levels:** median of five solves for a configuration; geometric mean of matched per-graph median ratios for cross-graph comparisons:')
    equation('', r'$$\widetilde{t}_{g,a}=\operatorname{median}(t_{g,a,1},\ldots,t_{g,a,5}),\qquad s_g=\frac{\widetilde{t}_{g,a}}{\widetilde{t}_{g,b}},\qquad \overline{s}_{\mathrm{geo}}=\left(\prod_{g=1}^{m}s_g\right)^{1/m}.$$')
    para("g indexes m graphs; s_g>1 favors b. Geometric means weight proportional changes equally: 2× and 0.5× combine to 1×. They apply to ratios, never pooled times or the five repeats. Communication pairs additionally match backend, nodes, p, and T. The 45-row overview selects each method's best observed median across layouts; its budgets may differ.")
    para('Fixed-core aggregates use 45 graph ratios. Communication aggregates use explicitly counted matched graph/layout pairs. Payload reduction is the fraction of Allgatherv bytes avoided by Halo, summarized by the pairwise median.')
    heading('2.5 Correctness and reproducibility',2)
    para('Independent Python checks stream raw edges to rebuild one update, without reusing the C++ CSR traversal. They check IDs/degrees, finite nonnegative scores, mass error <=10^-10, residual/full-vector L1 error versus Serial <=10^-8, histories, and repeat metadata. Allocation/affinity logs verify layouts. Archived timings and validation proofs support local reanalysis; full vectors remain on Vanda, with the Google vector also archived.')
    para('Controls reuse an independently edge-validated Serial vector s and compare every new vector x in full (IDs, degrees, mass, L1 error). PageRank is L1-contractive with alpha=0.85: residual(x) <= residual(s)+1.85||x-s||_1. Requiring this bound <=10^-8 certifies x; its stationary-vector error is at most residual/(1-alpha). Free-queue checks also verify timing/history, actual threads, and all five residuals.')
    para("Input identities, software/hardware metadata, original timings, and independent proofs retain each statistic's provenance and matched configuration.")
    heading('2.6 MPI collective selection and controlled policies',2)
    para("**Main matrix: automatic tuned selection.** Vanda Open MPI 4.1.8 records coll_tuned_use_dynamic_rules=false and overrides 0 (ignore): the compiled fixed decision tree selects each operation's implementation. The rules are fixed; the chosen algorithm may vary with p and, for Allgatherv, message size. This is rule-based selection, not online congestion learning.")
    para('**Controls: forced policies at selection boundaries.** Around 64 cores and 128 processes, hold graph, binary, layout, and allocation fixed and change only the named collective. coll_tuned_use_dynamic_rules=1 enables forced dispatch in these controls, not in the main matrix.')
    table(['MPI operation','Algorithm ID','Implementation','Applicability'],[
        ['Alltoallv (Halo)','1','basic_linear','General process counts'],
        ['Alltoallv (Halo)','2','pairwise','General process counts'],
        ['Allgatherv','1','GatherV followed by Bcast; parameter name default','General process counts'],
        ['Allgatherv','2','Bruck','General process counts'],
        ['Allgatherv','3','Ring','General process counts'],
        ['Allgatherv','4','Neighbor exchange','Applicable at p=8,16,32'],
        ['Allgatherv','5','two_proc','Exactly two processes']], [110,65,210,115],caption='Collective algorithms exposed by the installed Open MPI 4.1.8 tuned component. Algorithm ID 0 retains automatic selection and is not another implementation.')
    para('ID 0 preserves automatic selection; it is not an algorithm. Allgatherv ID 1, named default, explicitly selects GatherV+Bcast rather than restoring automatic rules [9]. Allreduce and other collectives retain their own default choices.')
    table(['Alltoallv communicator size p','Default tuned algorithm'],[
        ['p < 4','pairwise'],['4 <= p < 64','basic_linear'],
        ['64 <= p < 128','pairwise'],['128 <= p < 256','basic_linear'],
        ['256 <= p < 1024','pairwise'],['p >= 1024','basic_linear']], [235,265],caption='Compiled automatic Alltoallv selection rules in Open MPI 4.1.8. p is communicator process count, not CPU core count or payload size.')
    para('These Open MPI 4.1.8 rules apply when tuned handles Alltoallv [7]; p=1 can use self and has no remote Halo payload. Selection depends on p, not bytes, cores, or congestion. basic_linear posts nonblocking requests to peers then waits; pairwise performs rank-step exchanges [8]. Both provide blocking Alltoallv (not Barrier) with the same values but different concurrency/order.')
    para("**Allgatherv uses p and mean contribution bytes b=8N/p.** For N=12.8M,T=4, C32→64 gives p8→16 and b12.8→6.4 MB, switching Bruck→Ring; p32/64 remain Ring [7]. This boundary differs from Halo's p128 Alltoallv transition.")
    para('Symmetric controls compare automatic/Bruck/Ring at C32/64/128,T=4 on Hub and Controlled, and automatic/basic_linear/pairwise at p64/128/256 on Uniform Halo. Allgatherv targets the transition, not its full menu: GatherV+Bcast/neighbor exchange are untested here; two_proc is inapplicable at p8/16/32.')
    table(['Active cores C','Nodes','MPI p / Alltoallv','Hybrid p / Alltoallv','Hybrid Allgatherv'],[
        ['32','1','32 / basic_linear','8 / basic_linear','Bruck'],
        ['64','2','64 / pairwise','16 / basic_linear','Ring'],
        ['128','4','128 / basic_linear','32 / basic_linear','Ring'],
        ['256','8','256 / pairwise','64 / pairwise','Ring']], [85,40,130,135,110],caption='Automatic collective choices on the principal resource line. Pure MPI uses T1 and CPU hybrids T4; n is node count.')
    para('Both hybrids use T4. Forced IDs are Alltoallv 1=basic_linear,2=pairwise; Allgatherv 2=Bruck,3=Ring [9]. Only that operation changes. Policies share binary, graph, allocation, p/T, affinity, transport, and tuned/basic/libnbc/self availability. Component probes are untimed; policy plots show five-run medians and observed ranges.')
    para('**Equal cores need not mean equal collectives.** At C256, p256/T1 selects pairwise, p128/T2 basic_linear, p64/T4 pairwise, and p32/16/8 basic_linear. Changing p/T alters participation, local work sharing, and selection regime; forced-policy controls isolate one communication choice.')
    para('The tree is a general heuristic; controls test its suitability without replacing automatic mainline results by fastest policies. Separately, OpenMP schedule(dynamic,64) redistributes local vertex chunks; OMP_DYNAMIC=false fixes team size without disabling that scheduling.')
    heading('3 Results')
    para('**Reading the results:** every MPI curve includes Allgatherv/Halo and automatic tuned selection unless labeled forced. Section 3.5 pairs those same main-matrix records for exchange effects, then uses separate matched allocations for algorithm controls. Green/amber emphasis flags favorable values or costly mechanisms; captions specify the comparison.')
    heading('3.1 Numerical agreement across implementations',2)
    table(['Numerical check','Acceptance criterion','Observed outcome'],[
        ['Full score vector versus Serial','L1 difference <= 10^-8','All independently validated configurations pass'],
        ['Final convergence residual','L1 residual <= 10^-8',f"Maximum {AUDIT['max_residual_l1']:.3e}"],
        ['Total probability mass','Absolute difference from 1 <= 10^-10',f"Maximum {AUDIT['max_rank_sum_error']:.3e}"],
        ['Iterations on a fixed graph and hardware class','Same stopping rule across implementations','Identical counts in all 90 graph/hardware groups']], [155,155,190],
        caption='Numerical consistency of the fixed-input results. L1 differences and probability-mass errors are dimensionless; 90 groups comprise 45 graphs on two node classes.', emphasis={(i,2):'good' for i in range(4)})
    para('**All implementations agree within tolerance.** Each performance case therefore solves an equivalent numerical task; its five repeats contribute one median and one configuration.')

    heading('3.2 Graph characteristics and serial reference costs',2)
    heading('3.2.1 Graph size, edge density, and iteration cost',3)
    para('The 36-input grid varies N and mean degree within each family, with one process/thread throughout. Solve time combines per-iteration cost and convergence length.')
    figure('01_serial_grid','Serial grid (36 inputs): 3 families × N=50k/100k/200k/400k × d=4/8/16 edges/vertex. One CPU process/thread; five-run median solve time (s); log-log axes.')
    density=[]
    for family in ('uniform','hub','controlled'):
        selected=sorted((r for r in GRAPHS if r['graph'].startswith('grid_'+family+'_n100000_')),key=lambda r:int(r['edges']))
        for r in selected:
            density.append([family.title(),int(r['edges'])//100000,f"{int(r['edges']):,}",r['iterations'],
                            fmt(r['solve_median_s']),fmt(number(r['solve_median_s'])/int(r['iterations'])*1000)])
    table(['Family','Mean degree','Edges E','Iterations I','Solve time (s)','Time/iteration (ms)'],density,
          [85,60,85,70,95,105],caption='Density comparisons at N=100,000 vertices. Mean degree is E/N in edges/vertex; solve and per-iteration times separate convergence length from iteration cost.')
    para('**Denser does not necessarily mean a longer solve.** Controlled at N=100,000 needs 35/22/17 iterations for d=4/8/16; fewer iterations can offset more edges. Its density changes exact destination concentration too (Section 1.2).')
    table(['Graph','Vertices N','Directed edges E','Iterations I','Serial time (s)'],[
        [DISPLAY[g],f"{int(get(g,'Serial')['vertices']):,}",f"{int(get(g,'Serial')['edges']):,}",
         get(g,'Serial')['iterations'],fmt(get(g,'Serial')['solve_median_s'])] for g in REPRESENTATIVE],
        [120,110,115,70,85],caption='Serial baselines for the three original inputs and the three large inputs used in the resource curves. N and E are counts; all times are five-run medians on CPU nodes.')

    heading('3.2.2 PageRank concentration in the real Google graph',3)
    para(f"**Google scores are concentrated.** {GOOGLE['dangling_vertices']:,} vertices ({GOOGLE['dangling_vertices']/GOOGLE['vertices']:.1%}) are dangling, requiring mass redistribution; the top 1% hold {GOOGLE['top_1_percent_rank_mass']:.1%} of score mass. PageRank/in-degree Pearson correlation is {GOOGLE['pagerank_indegree_pearson']:.3f}: strongly associated, but degree is not the full weighting rule.")
    table(['Node ID','PageRank','In-degree','Out-degree'],[[r['node_id'],f"{r['rank']:.7f}",r['in_degree'],r['out_degree']] for r in GOOGLE['top10'][:5]], [120,140,120,120],caption='Five highest-scoring Google vertices. PageRank is a dimensionless probability score; in-degree and out-degree are edge counts.')
    para('The anonymized edge list does not identify websites or content quality; concentration and correlation describe graph structure, not causal importance.')

    heading('3.3 Fixed graphs with more CPU processes and nodes',2)
    heading('3.3.1 Increasing active cores through explicit process layouts',3)
    para('**Fixed input; increasing p and n.** MPI uses p=C,T1; both hybrids p=C/4,T4. C=4 is their first common point (lower-core cases remain in the matrix). Up to C32 uses one node; C64/128/256 use 2/4/8, so process and node counts grow together.')
    table(['Active cores C','Nodes n','MPI processes p','MPI threads T','Hybrid processes p','Hybrid threads T'],[
        [c,max(1,c//32),c,1,c//4,4] for c in (4,8,16,32,64,128,256)],
        [65,55,90,80,105,105],caption='Layouts used in both fixed-graph CPU figures. Each row is measured with Allgatherv and Halo; C=pT for every method. Hybrid denotes MPI+OpenMP and MPI+Kokkos OpenMP.')
    para('Original and large graphs use parallel displays: speedup above, CPU efficiency below; identical method colors and Allgatherv/Halo line styles. Each uses its CPU Serial reference and automatic selection; forced tests appear in Section 3.5.2.')
    figure('02_strong_original','Fixed original inputs; C=4..256 with the preceding layouts. Top: speedup versus matched CPU Serial (×); bottom: S/C (%). MPI T1, hybrids T4; A/H=Allgatherv/Halo. Five-run medians, common scales across families.')
    figure('03_strong_large','The same CPU layouts on equal-size large inputs (N=12.8M,E=204.8M). Top: Serial-relative speedup (×); bottom: S/C (%). Method colors, A/H line styles, common scales, and medians match the original-input figure.')
    uniform=get('strong_uniform','MPI',host_nodes=8,processes=256,threads=1,communication='Halo')
    para(f"**More cores help large Uniform, not small Google.** MPI Halo at C256 gives Uniform {number(uniform['speedup_vs_matched_serial']):.1f}× Serial speedup ({number(uniform['cpu_efficiency_vs_serial']):.1%} efficiency). Google instead goes from its best pure-MPI Halo point, n1/p32 = 0.149 s, to n8/p256 = 1.462 s: communication/synchronization outweigh local work. Equal-size Hub/Controlled also benefit less than Uniform.")
    para('**Edge ownership, not vertex balance, controls the structural difference.** The next plot measures maximum/mean incoming-edge load under equal contiguous vertex partitions; 1 means perfect edge balance.')
    figure('13_rank_workload','Equal-size large inputs, contiguous equal-vertex ownership. Maximum/mean incoming edges versus process count (dimensionless); 1 denotes balance. These are partition statistics, not timing speedups.')
    equation('', r'$$B_E=\frac{\max_i E_i}{E/p},\qquad p_{\mathrm{edge}}=\frac{E}{\max_i E_i}=\frac{p}{B_E}.$$')
    table(['Large graph, p=256','Max/mean edge load','Busiest process edge share (%)','Equal-work process proxy'],[
        [DISPLAY[r['graph']],f"{number(r['max_mean_edges']):.3f}",f"{number(r['max_rank_edge_share']):.2%}",fmt(r['equivalent_balanced_ranks'])]
        for r in WORK if r['processes']=='256'],[125,115,140,120],
        caption='Work concentration at 256 processes. B_E is dimensionless. The equal-work process proxy assumes equal edge-scanning rates and describes load balance, not measured speedup. Amber marks concentrated work; all 256 processes were launched.', emphasis={(i,j):'warn' for i in (1,2) for j in (1,2,3)})
    para('**One process owns 29%-30% of Hub/Controlled edges at p256.** All processes run, but the slowest row scans govern iteration progress. The edge-only load equals about 3.4/3.3 balanced processes under equal scanning rates; Uniform stays balanced. The 75.0%/77.5% hot-edge fractions occupy the first 1% of IDs, fitting one partition for p<=100 and crossing boundaries above it. Halo preserves this ownership.')
    table(['Large graph; T=32','OpenMP time (s)','Kokkos OpenMP time (s)','Kokkos/OpenMP (×)','Largest static block edge share (%)'],[
        [DISPLAY[r['graph']],fmt(r['openmp_s']),fmt(r['kokkos_openmp_s']),fmt(r['kokkos_over_openmp']),f"{number(r['contiguous_32way_edge_share_proxy']):.1%}"] for r in POLICY],
        [105,85,105,90,115],caption='One-node scheduling comparison on the same large graphs. Each method uses one process and 32 CPU threads; times are five-run solve medians. The static-block share is an analytical proxy; amber marks skewed edge ownership and its associated time gap.', emphasis={(i,j):'warn' for i in (1,2) for j in (3,4)})
    para('**Local scheduling magnifies the same skew.** OpenMP distributes 64-vertex chunks dynamically; Kokkos RangePolicy defaults to static ranges [6]. A 32-way split puts 75.5%-78.0% of skewed edges in one block. Uniform times are similar, but Hub/Controlled differ by about 22×, implicating the implemented scheduling/ordering combination rather than intrinsic framework overhead.')

    heading('3.3.2 Fixed 256-core budget: changing the process/thread split',3)
    para("**Fixed n=8,C=256; vary p/T.** Both hybrids use six splits and two exchanges. Each graph's median is divided into its same-method/exchange p256/T1 median, then ratios are geometrically averaged over 45 graphs.")
    table(['Processes p','Threads/process T','MPI+OMP A (×)','MPI+OMP H (×)','MPI+KK A (×)','MPI+KK H (×)'],[
        [256//t,t,*[f"{number(next(r for r in SPLITS if r['method']==method and r['communication']==mode and r['threads']==str(t))['geomean_speedup_vs_T1']):.2f}"
                   for method in ('MPI+OpenMP','MPI+Kokkos OpenMP') for mode in ('Allgatherv','Halo')]]
        for t in (1,2,4,8,16,32)], [70,90,85,85,85,85],
        caption='Equal-core process/thread comparison. Values are geometric means of 45 paired speedups, each based on five-run median times. All rows satisfy pT=256; A=Allgatherv, H=Halo. The reference is the corresponding method\'s T=1 row, not Serial; green marks each column maximum.', extrema={2:'max',3:'max',4:'max',5:'max'})
    figure('04_fixed_256_splits','Fixed n8,C256; p=256/T. Geometric-mean speedup versus the same method/exchange at T1 (×), across 45 paired graph medians. Colors and A/H line styles match preceding plots.')
    best={method:max((r for r in SPLITS if r['method']==method and r['communication']=='Halo'),key=lambda r:number(r['geomean_speedup_vs_T1']))
          for method in ('MPI+OpenMP','MPI+Kokkos OpenMP')}
    a=next(r for r in SPLITS if r['method']=='MPI+OpenMP' and r['communication']=='Allgatherv' and r['threads']=='32')
    k=next(r for r in SPLITS if r['method']=='MPI+Kokkos OpenMP' and r['communication']=='Allgatherv' and r['threads']=='32')
    para(f"**Fewer processes can use the same cores better.** At p8/T32, Allgatherv improves the T1 aggregate by {number(a['geomean_speedup_vs_T1']):.2f}× (MPI+OpenMP) and {number(k['geomean_speedup_vs_T1']):.2f}× (MPI+Kokkos). Best Halo splits use T{best['MPI+OpenMP']['threads']}/T{best['MPI+Kokkos OpenMP']['threads']}, gaining {number(best['MPI+OpenMP']['geomean_speedup_vs_T1']):.2f}×/{number(best['MPI+Kokkos OpenMP']['geomean_speedup_vs_T1']):.2f}×. Reduced collective participation and shared hot rows explain the direction; individual graph optima differ.")

    heading('3.4 Standalone methods and one-to-two-GPU execution',2)
    heading('3.4.1 Standalone CPU/GPU baselines and MPI overhead',3)
    table(['Graph','CPU Serial (s)','OpenMP T32 (s)','KK OpenMP T32 (s)','GPU-node Serial (s)','CUDA (s)','KK CUDA (s)'],[
        [DISPLAY[g],fmt(get(g,'Serial')['solve_median_s']),fmt(get(g,'OpenMP',threads=32)['solve_median_s']),
         fmt(get(g,'Kokkos OpenMP',threads=32)['solve_median_s']),fmt(get(g,'Serial','gpu_node')['solve_median_s']),
         fmt(get(g,'CUDA','gpu_node')['solve_median_s']),fmt(get(g,'Kokkos CUDA','gpu_node')['solve_median_s'])]
        for g in REPRESENTATIVE], [105,65,65,70,70,60,65],
        caption='Standalone baselines on the same six representative graphs. CPU methods use one node; device methods use one A40. All values are five-run solve medians in seconds. CPU-node and GPU-node Serial references are kept separate.')
    para('**MPI device overhead persists at one GPU.** Google CUDA/Kokkos CUDA take 0.115/0.094 s standalone versus 0.243/0.383 s under MPI Allgatherv p1. The distributed path stages contributions every iteration; input/backend setup is excluded.')
    heading('3.4.2 One versus two GPUs on fixed inputs',3)
    para('**Fixed graph; n=p=G changes 1→2**, one A40/process/node, automatic selection, both exchanges. CPU MPI and MPI+OpenMP T1 on the same node class are layout-matched controls. Each line uses its own one-node reference.')
    figure('06_gpu_node_scaling','Fixed large graphs; n1→2. Device methods: one A40/rank/node; CPU controls: T1, no GPU computation. Own one-node median / n-node median (×), with 1× reference; common scales and A/H line styles.')
    table(['Large graph','GPU method','Busiest p2 edge share (%)','Compute p1/p2 (×)','Solve p1/p2 (×)'],[
        [DISPLAY[r['graph']],r['method'],f"{number(r['p2_max_edge_share']):.1%}",fmt(r['compute_speedup']),
         fmt(number(r['p1_solve_s'])/number(r['p2_solve_s']))] for r in GPU_WORK],
        [105,135,100,80,80],caption='Allgatherv GPU comparisons, presented identically for all three large graphs and both backends. Each ratio divides the p1 median by the p2 median; values above 1× favor two GPUs. The edge share is a partition statistic.', emphasis={(i,3):'good' for i in (0,1)} | {(i,2):'warn' for i in (2,3,4,5)})
    figure('08_gpu_phases','Allgatherv phases on the same large graphs. CU/KK=CUDA/Kokkos CUDA; suffix 1/2=GPUs/processes. Dots: five-run solve, device, host-staging, and MPI/wait medians (s), common log scale. Separately rank-reduced phase medians are not additive.')
    para('**Uniform balances device work; skewed inputs do not.** Uniform obtains about 2× compute acceleration but MPI limits solve gains. Hub/Controlled leave 87%-89% of edges on one GPU: CUDA compute improves only about 1.1× while communication rises. Larger Kokkos gains also involve kernel mapping, reductions, and locality; edge share is a mechanism, not a universal runtime bound.')

    heading('3.5 Communication strategy and MPI implementation choice',2)
    para('**Two levels of control:** Section 3.5.1 changes the exact values exchanged (Allgatherv/Halo), reusing matched main-matrix cases; Section 3.5.2 holds the exchange fixed and changes the MPI collective algorithm in separate matched allocations.')
    heading('3.5.1 Allgatherv versus exact Halo exchange',3)
    figure('05_halo_pairs','All 45 graphs, p>1: paired Allgatherv/Halo time ratio (geometric mean, ×; >1 favors Halo) and median logical payload reduction (%). Pairs match graph/method/n/p/T; explicit zero is measured. CPU/GPU-node layout populations differ, so bars are not hardware-only contrasts.')
    table(['Node class','Family','Matched pairs','Halo speedup (×)','Payload reduction (%)','Halo faster (%)'],[
        [r['context'].replace('_',' '),r['family'].title(),r['paired_configurations'],fmt(r['geomean_halo_speedup']),
         f"{number(r['median_payload_reduction']):.1%}",f"{number(r['halo_faster_fraction']):.1%}"] for r in HALO],
        [90,80,70,85,95,80],caption='Populations and statistics behind the communication bars. Speedup is the geometric mean of paired five-run-median ratios. Payload reduction and the fraction of pairs favoring Halo are percentages; they are different statistics.', emphasis={(0,3):'good',(5,4):'warn'})
    figure('15_payload_by_process','Pure MPI T1, n=max(1,p/32): family-median payload reduction (%) across fixed graphs at each p. Each A/H pair fixes graph/layout. Logical bytes exclude reductions/protocol overhead; this separates p effects from aggregate population differences.')
    para('**GPU Uniform savings are 0.0%, not missing.** Of 105 pairs, 91 save no contribution bytes: at p2 most partitions require all other-process sources. Large Uniform exchanges 102.4 MB globally per iteration under either strategy. This follows from graph dependencies, not GPU arithmetic.')
    para('**Payload savings do not determine runtime.** CPU Google gains 1.89× with 58.6% median payload reduction; synthetic families gain 1.19-1.23× in aggregate, while many cases favor Allgatherv. Packing, collective/reduction latency, imbalance, and device staging remain. Untimed Halo setup cannot cause timed-iteration slowdown.')
    table(['Graph; C=256','MPI p256/T1 (×)','MPI+OMP p64/T4 (×)','MPI+KK p64/T4 (×)'],[
        [DISPLAY[g],*[fmt(number(get(g,m,host_nodes=8,processes=256//t,threads=t,communication='Allgatherv')['solve_median_s'])/
                          number(get(g,m,host_nodes=8,processes=256//t,threads=t,communication='Halo')['solve_median_s']))
                     for m,t in [('MPI',1),('MPI+OpenMP',4),('MPI+Kokkos OpenMP',4)]]] for g in REPRESENTATIVE],
        [125,120,125,130],caption='Paired Allgatherv/Halo time ratios on the same six inputs at eight nodes and 256 CPU cores. Each cell holds method, p, and T fixed; ratios above 1× favor Halo. The three columns need not use the same process count.', emphasis={(i,j):'good' if number(get(g,m,host_nodes=8,processes=256//t,threads=t,communication='Allgatherv')['solve_median_s'])>number(get(g,m,host_nodes=8,processes=256//t,threads=t,communication='Halo')['solve_median_s']) else 'warn' for i,g in enumerate(REPRESENTATIVE) for j,(m,t) in enumerate([('MPI',1),('MPI+OpenMP',4),('MPI+Kokkos OpenMP',4)],1)})

    heading('3.5.2 Default tuned selection versus fixed collective algorithms',3)
    para('Controls fix graph, layout, binary, affinity, and allocation within each policy comparison. Automatic uses dynamic_rules=0; forced runs use 1 plus one operation override (Section 2.6), not online learning.')
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
    para('**59 unique settings:** 27 primary policies + 30 additional automatic contexts + 2 binding controls. Node-boundary context has 36 cases (2 graphs × 3 methods × 2 exchanges × 3 core counts); 6 overlap the primary matrix. Binding fixes n8,p256,T1,pairwise.')
    para('Both Alltoallv algorithms are tested. Allgatherv compares Bruck/Ring around p8→16; GatherV+Bcast and neighbor exchange are outside this targeted contrast, and two_proc applies only at p2 (complete menu: Section 2.6).')
    triples=[]
    for c in (64,128,256):
        selected={r['policy']:r for r in CONTROLS if r['graph']=='strong_uniform' and r['cores']==str(c)}
        assert set(selected)=={'default','a2av_linear','a2av_pairwise'}
        assert len({r['communication_bytes_per_iteration'] for r in selected.values()})==1
        triples.append((c,selected))
    figure('11_collective_policies','Large Uniform Halo; p=C=64/128/256. Automatic versus forced basic_linear/pairwise; five-run solve medians (s), whiskers=min..max (not confidence intervals). Policies share an allocation within p; allocations differ across p. Logarithmic p axis; markers offset for visibility.')
    table(['Processes p = cores C','Automatic (s)','basic_linear (s)','pairwise (s)','Automatic/pairwise (×)'],[
        [c,*[fmt(r[k]['solve_median_s']) for k in ('default','a2av_linear','a2av_pairwise')],
         fmt(number(r['default']['solve_median_s'])/number(r['a2av_pairwise']['solve_median_s']))]
        for c,r in triples], [90,95,100,95,120],caption='Alltoallv comparison on the same graph and layout within each row. Each value is a five-run median; all policies pass independent validation. The p128 row highlights automatic/basic_linear cost (amber) and pairwise gain (green).', emphasis={(1,1):'warn',(1,2):'warn',(1,3):'good',(1,4):'good'})
    control128=dict(triples)[128]
    para(f"**At p128, pairwise improves automatic selection by {number(control128['default']['solve_median_s'])/number(control128['a2av_pairwise']['solve_median_s']):.2f}×.** Automatic/basic_linear/pairwise take {number(control128['default']['solve_median_s']):.3f}/{number(control128['a2av_linear']['solve_median_s']):.3f}/{number(control128['a2av_pairwise']['solve_median_s']):.3f} s. Automatic range: {number(control128['default']['solve_min_s']):.3f}-{number(control128['default']['solve_max_s']):.3f} s; pairwise: {number(control128['a2av_pairwise']['solve_min_s']):.3f}-{number(control128['a2av_pairwise']['solve_max_s']):.3f} s. MPI/wait falls {number(control128['default']['communication_median_s']):.3f}→{number(control128['a2av_pairwise']['communication_median_s']):.3f} s at the same 12 iterations, directly identifying a policy effect.")
    para('**The p128 peak aligns with pairwise→basic_linear→pairwise at p64/128/256.** The selector sees p, not payload/congestion. Different concurrency, buffering, and progress can change boundary costs. Growing Uniform also peaks at p128 despite different mean peer payload, supporting a schedule effect beyond one message-size threshold; TCP eager/rendezvous and shared contention may interact.')
    gather_controls=[]
    for graph in ('strong_hub','strong_controlled'):
        for c in (32,64,128):
            selected={r['policy']:r for r in CONTROLS if r['graph']==graph and r['cores']==str(c)
                      and r['implementation']=='hybrid' and r['communication']=='allgather'}
            assert set(selected)=={'default','agv_bruck','agv_ring'}
            gather_controls.append((graph,c,selected))
    figure('12_allgatherv_policies','Hub/Controlled, MPI+OpenMP Allgatherv: automatic/Bruck/Ring at n1/2/4,C32/64/128,T4,p=C/4. Five-run solve medians (s), whiskers=min..max, common scale. Policies share each resource-point allocation; markers offset for visibility.')
    table(['Graph','C / p','Automatic (s)','Bruck (s)','Ring (s)','Bruck/Ring (×)'],[
        [DISPLAY[g],f'{c} / {c//4}',*[fmt(r[k]['solve_median_s']) for k in ('default','agv_bruck','agv_ring')],
         fmt(number(r['agv_bruck']['solve_median_s'])/number(r['agv_ring']['solve_median_s']))]
        for g,c,r in gather_controls], [110,60,85,80,80,85],caption='Allgatherv transition controls, presented symmetrically for both graphs and all three resource points. T=4 throughout; only the collective implementation changes within a row. At C64, amber/green contrast Bruck with Ring.', emphasis={(i,3):'warn' for i in (1,4)} | {(i,4):'good' for i in (1,4)})
    para('**At C64, Ring already matches automatic; Bruck is slower.** Hub: automatic/Ring/Bruck = 5.022/5.010/5.550 s; Controlled: 3.886/3.884/4.294 s. At C32 automatic matches Bruck. Unlike Uniform p128, switching back does not help this boundary.')
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
    para('**The C32→64 context is nearly flat (0.93-1.04× time).** The hot block still belongs to one hybrid process: Hub share 77.90→76.33%, Controlled 80.11→78.69%. Extra processes subdivide cold work while the second node adds progress/synchronization cost; the algorithm transition alone need not be harmful.')
    if LAUNCHER_CONTROLS:
        table(['Binding at p256, fixed pairwise','Solve median (s)','Five-run range (s)','MPI/wait median (s)'],[
            [('Native core binding' if r['launcher']=='ompi_core' else 'Explicit CPU mask'),fmt(r['solve_median_s']),
             f"{number(r['solve_min_s']):.3f}-{number(r['solve_max_s']):.3f}",fmt(r['communication_median_s'])]
            for r in LAUNCHER_CONTROLS], [175,95,125,105],caption='Launch-binding comparison within one eight-node, 256-core allocation. The graph and Alltoallv policy are fixed, and post-initialization affinity confirms one distinct CPU per process for both launchers.')
        para('**Binding does not explain the larger between-allocation variation.** Native/explicit binding medians are 2.975/3.111 s with overlapping ranges; a separate policy allocation gives p256 pairwise 3.563 s. Host/NUMA placement, shared-fabric contention, and peer progress are plausible contributors. These allocation-matched controls remain separate from main curves.')

    heading('3.6 Growing graph size together with resources',2)
    heading('3.6.1 Constant nominal work per CPU core',3)
    para('**Constant nominal work/core:** at C4/8/16/32/64/128/256, all methods use N=50,000C,E=800,000C. MPI p=C,T1; hybrids p=C/4,T4. The common C4 input/core reference permits matched efficiency comparisons; original rank-based p1 references remain in the data.')
    table(['Active cores C','Vertices N','Directed edges E','MPI p / T','Hybrid p / T'],[
        [c,f'{50000*c:,}',f'{800000*c:,}',f'{c} / 1',f'{c//4} / 4'] for c in (4,8,16,32,64,128,256)],
        [85,110,125,90,90],caption='Common growing-input CPU matrix. All three families and both Allgatherv/Halo settings use every row. Node count follows n=max(1,C/32); the per-core vertex and edge counts remain fixed.')
    figure('07_core_weak','N=50,000C,E=800,000C. Top: iteration time (ms); bottom: efficiency relative to own C4 iteration time (%). MPI T1, hybrids T4; A/H line styles and scales match across panels. Ideal growth gives flat time and 100% efficiency; points derive from five-run medians.')
    table(['Family','Method','C256 Allgatherv (%)','C256 Halo (%)'],[
        [f.title(),m,*[f"{number(next(r for r in GROWING if r['family']==f and r['method']==m and r['communication']==mode and r['active_cpu_threads']=='256')['matched_efficiency']):.2%}"
                      for mode in ('Allgatherv','Halo')]]
        for f in ('uniform','hub','controlled') for m in ('MPI','MPI+OpenMP','MPI+Kokkos OpenMP')],
        [80,170,125,125],caption='Retained per-iteration efficiency at 256 CPU cores, using the common C=4 reference of the preceding figure. Each percentage divides its C4 iteration time by its C256 iteration time; no Serial baseline enters. Green marks each column maximum, not equal absolute runtime.', extrema={2:'max',3:'max'})
    para('**Iteration time rises despite constant nominal work/core.** Uniform retains 1.9%-5.2% efficiency at C256; concentrated inputs retain less. Each method uses its own C4 time, so higher efficiency need not mean lower absolute time. With N proportional to p, Allgatherv traffic grows as p per process and p² globally; Hub/Controlled additionally retain edge imbalance.')
    figure('14_growing_communication','Growing Uniform, pure MPI T1: N=50,000p,E=800,000p. Left: logical payload (MB/rank/iteration); right: median MPI/wait divided by iterations (ms/iteration). Log-log axes; bytes exclude reductions/transport overhead.')
    uniform_traffic=[r for r in TRAFFIC if r['family']=='uniform' and int(r['processes']) in (16,64,256)]
    table(['Processes p','Exchange','Payload (MB/rank/iteration)','MPI + waiting (ms/iteration)'],[
        [r['processes'],r['communication'],f"{number(r['counted_payload_bytes_per_rank'])/1e6:.2f}",f"{number(r['communication_ms_per_iteration']):.2f}"]
        for r in uniform_traffic],[75,100,160,165],caption='Matched contribution volume and communication duration for growing Uniform. Rows compare the two exchanges at the same graph and process count; per-iteration quantities, not total job traffic. Amber marks p256 costs despite bounded Halo bytes.', emphasis={(i,j):'warn' for i in (4,5) for j in (2,3)})
    para('**Nearly fixed Halo bytes still cost more at larger p.** Uniform payload stays near 6.4 MB/rank/iteration (Allgatherv reaches 102.0 MB at p256), yet Halo MPI/wait rises 17.28→38.07 ms from p64→256. Peer count, collective/reduction latency, packing, and contention matter beyond bytes; skewed inputs also wait for overloaded owners.')
    heading('3.6.2 Constant nominal work per GPU or MPI process',3)
    para("**GPU-node work/resource growth:** n=p=1→2, N=50,000p,E=800,000p, one GPU/process for device methods; CPU controls retain T1. Efficiency uses each method/exchange's p1 iteration time. This one-to-two-resource ratio has a different reference from CPU C4→256.")
    table(['GPU-node method','Uniform A (%)','Uniform H (%)','Hub A (%)','Hub H (%)','Controlled A (%)','Controlled H (%)'],[
        [method.replace('Cuda','CUDA'),*[f"{number(next(r for r in WEAK if r['suite']=='gpu_node' and r['method']==method and r['family']==family and r['processes']=='2' and r['threads']=='1' and r['communication']==mode)['weak_efficiency_per_iteration']):.1%}"
                  for family in ('uniform','hub','controlled') for mode in ('Allgatherv','Halo')]]
        for method in ('MPI','MPI+OpenMP','MPI+CUDA','MPI+Kokkos Cuda')],
        [140,60,60,60,60,60,60],small=True,caption='Per-iteration efficiency retained when both graph size and GPU-node process count double. A=Allgatherv, H=Halo; reference p1 and measured p2 each use five-run median time per iteration. CPU controls do not compute on GPUs.')
    para('Standalone cases keep one node/device at both input sizes: 54 fixed-resource size controls, not resource-scaling efficiencies. They accompany the 318 scaled cases with their original layouts/reference definitions.')

    story.append(PageBreak())
    heading('3.7 Complete fixed-input summary and additional high-core example',2)
    para('**Overview: values = best observed solve medians (s); color = speedup versus the same node-class Serial.** Budgets may differ across cells; selected layouts remain in the CSV. Bold outlines mark the fastest method in each row. CPU and GPU tables use separate Serial references and the same color scale.')
    story.append(runtime_legend())
    cpu_methods=('Serial','OpenMP','Kokkos OpenMP','MPI','MPI+OpenMP','MPI+Kokkos OpenMP')
    cpu_values=[[number(r[m+'_best_s']) for m in cpu_methods] for r in MATRIX]
    table(['Graph','Serial','OpenMP','KK OMP','MPI','MPI+OMP','MPI+KK'],[
        [abbreviated(r['graph']),*[fmt(v) for v in values]] for r,values in zip(MATRIX,cpu_values)],
        [95]+[67.5]*6,heatmap={'values':cpu_values,'baselines':[v[0] for v in cpu_values]},
        caption='CPU-node runtime heatmap: all 45 fixed graphs, seconds in cells; color encodes matched Serial speedup. Bold/outlined cells are row minima (including Serial). KK=Kokkos; o./s.=original/canonical; U/H/C grid labels give vertices and mean degree. Each cell selects its own best legal layout.')
    story.append(PageBreak())
    story.append(runtime_legend())
    gpu_values=[[number(r['GPU-node Serial_s']),*[number(r[m+'_best_s']) for m in ('CUDA','Kokkos CUDA','MPI+CUDA','MPI+Kokkos CUDA')]] for r in MATRIX]
    table(['Graph','Serial on GPU node','CUDA','KK CUDA','MPI+CUDA','MPI+KK CUDA'],[
        [abbreviated(r['graph']),*[fmt(v) for v in values]] for r,values in zip(MATRIX,gpu_values)],
        [95]+[81]*5,heatmap={'values':gpu_values,'baselines':[v[0] for v in gpu_values]},
        caption='GPU-node runtime heatmap: the same 45 graphs and color scale, seconds in cells. Reference is this node class’s CPU Serial, not the CPU-node table. Bold/outlined cells are row minima; distributed methods select over one/two GPUs and Allgatherv/Halo. CPU controls remain in the full results CSV.')
    example_start=len(story)
    heading('3.7.1 Additional 512-core example',3)
    para('Controlled N=50,000,E=200,000 has five additional measurements on 8 nodes × 64 active cores/node (C=512). They are a small-graph example, separate from the main resource curves and aggregate rankings.')
    table(['Method','Processes p','Threads T','Exchange','Solve time (s)','Speedup (×)','CPU efficiency (%)'],[
        [r['method'],r['processes'],r['threads'],r['communication'],fmt(r['solve_median_s']),fmt(r['speedup']),f"{number(r['efficiency']):.3%}"]
        for r in SUPPLEMENT],[125,60,55,80,65,55,60],small=True,
        caption='Additional 512-core measurements. Every row satisfies pT=512 and uses one warm-up plus five timed solves; speedup uses this graph\'s CPU-node Serial median. The rows are not a complete 512-core scaling curve. Amber speedups are below 1×.', emphasis={(i,5):'warn' for i in range(5)})
    para('**All five are slower than Serial**, especially p512 Halo. On this small input, exchange/synchronization overhead outweighs the work distributed; this is a workload-size effect, not a general high-core ranking.')
    story[example_start:]=[KeepTogether(story[example_start:])]
    cpu=OPTIMA['cpu_all'];device=OPTIMA['gpu_device_only'];controls=OPTIMA['gpu_with_cpu_controls']

    heading('4 Conclusions and insights')
    heading('4.1 What the experiments establish',2)
    para(f"**Workload structure determines the useful backend and parallel degree.** Standalone OpenMP/Kokkos OpenMP wins {cpu['method_counts'].get('OpenMP',0)+cpu['method_counts'].get('Kokkos OpenMP',0)}/45 CPU-node graphs; only {cpu['multirank_winners']} winning cases use multiple ranks. Standalone CUDA/Kokkos CUDA wins all device-only comparisons. Including GPU-node CPU controls gives OpenMP/CUDA/Kokkos CUDA {controls['method_counts'].get('OpenMP',0)}/{controls['method_counts'].get('CUDA',0)}/{controls['method_counts'].get('Kokkos CUDA',0)} wins. These are cross-budget optima; matched layouts separately show that larger balanced work benefits from extra participants, while small/skewed inputs favor fewer processes.")
    para('Edge ownership is the dominant structural constraint: equal vertex partitions leave 29%-30% of skewed edges on one process at p256. Local scheduling and p/T determine useful core participation; Halo does not rebalance ownership.')
    para('Communication volume alone predicts neither runtime nor multi-GPU benefit. Packing, collective schedules, synchronization, and staging remain; the matched p128 pairwise control improves Uniform by 4.66×, without establishing a universal best collective.')
    heading('4.2 Design implications supported by the experiments',2)
    para('Choose optimizations by the measured bottleneck:')
    table(['Workload or decision','Evidence-based implication','Basis in the results'],[
        ['Small or moderate fixed graph','Evaluate a single-node backend before increasing MPI participation.','Standalone OpenMP/Kokkos OpenMP is fastest in 42 of 45 CPU-node best-observed comparisons.'],
        ['Large, balanced graph','Consider distributed execution and compare both exact exchanges at the target layout.','Large Uniform benefits from MPI resources; the selected 256-core Halo point reaches 28.6× Serial speedup.'],
        ['Concentrated incoming-edge work','Prioritize ownership balance and local scheduling; compare p/T at equal cores.','One process owns roughly 29%-30% of edges at p256. Changing the fixed-core split improves aggregate Halo ratios by over an order of magnitude.'],
        ['Collective-selection boundary','Retain the automatic baseline and test candidate implementations within matched allocations.','At p128 pairwise improves Uniform by 4.66×; at 64 cores Ring already matches or improves on Bruck for the tested concentrated graphs.'],
        ['Adding a second GPU','Measure end-to-end solve and staging/MPI costs alongside device computation.','Uniform obtains about 2× computation acceleration, while concentrated inputs leave most edge work on one GPU.'],
        ['Graph size grows with resources','Track iteration time and contribution volume separately from nominal vertices/edges per worker.','Allgatherv contribution traffic grows with the global vector; Halo bounds Uniform bytes but does not eliminate peer and synchronization costs.']],
        [105,200,195],caption='Practical implications of the measured cases. These are workload-dependent design choices, not claims that one backend or communication implementation is universally optimal.')
    para("Google's scores are concentrated and strongly associated with incoming links, though degree alone is not the weighting rule. Numerical agreement preserves this data conclusion across backends.")
    heading('4.3 Scope and reproducibility',2)
    para('The study covers fixed-input resource curves, equal-core splits, proportional work/resource growth, and allocation-matched controls, with five timed repeats and saved CPU/affinity evidence. Shared-cluster placement, NUMA, and dates vary. Solve timing includes iterations/MPI/staging, not input/startup; GPU comparisons use one/two A40s.')
    para('Repository [5] contains source, input generators, original timings, independent proofs, and selection records; its tables/figures regenerate without new performance runs.')
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
    para('AI assisted implementation adaptation, experiment/job design, debugging, verification, visualization, and drafting. Compiled programs measured all performance values on Vanda; independent Serial/residual checks validated scores. Stored records generate tables/figures. The authors are responsible for reviewing the code, design, interpretation, and text.')
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
    print('Dense four-section report: unchanged measurements, targeted emphasis, and numerical runtime heatmaps.')


if __name__=='__main__':
    main()
