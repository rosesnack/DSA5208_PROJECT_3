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
from report_complete_results import CompleteResults

from reportlab.graphics import renderPDF
from reportlab.graphics.charts.axes import LogXValueAxis, LogYValueAxis
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Line, Rect, String, Group, Circle
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
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
HALO_PAIRS = list(csv.DictReader((DATA / 'halo_pairs.csv').open()))
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
BASELINE_GRAPHS = ('google', 'uniform', 'hub', 'strong_uniform', 'strong_hub', 'strong_controlled')
DISPLAY = {'google':'Google','uniform':'Original uniform','hub':'Original hub',
           'strong_uniform':'Large uniform','strong_hub':'Large hub',
           'strong_controlled':'Large controlled'}


def number(value):
    return float(value)


def fmt(value):
    return f'{float(value):.3g}'


def geomean(values):
    return math.exp(stats.mean(math.log(float(v)) for v in values))


def split_time(method, mode, threads):
    rows=[r for r in FIXED if r['context']=='cpu_node' and r['method']==method
          and int(r['host_nodes'])==8 and int(r['threads'])==int(threads)
          and int(r['processes'])*int(threads)==256 and r['communication']==mode]
    assert len(rows)==45
    return geomean(r['solve_median_s'] for r in rows)


def halo_times(context, family):
    rows=[r for r in HALO_PAIRS if r['context']==context and r['family']==family]
    return tuple(geomean(r[k] for r in rows) for k in ('allgatherv_s','halo_s'))


def ratio_time(ratio, seconds):
    return f'{float(ratio):.3g}× ({float(seconds):.3g} s)'


def short_ms(seconds):
    ms=float(seconds)*1000
    if ms>=10000:return f'{ms/1000:.0f}k'
    if ms>=1000:return f'{ms/1000:.1f}k'
    if ms>=10:return f'{ms:.0f}'
    return f'{ms:.1f}' if ms>=1 else f'{ms:.2f}'


def point_annotations(drawing, plot, labels, colors_for_series, font_size=5.6, best_labels=None):
    """Point-linked times; spread collocated labels vertically within each x column."""
    plot.draw()  # Configure axes before converting data coordinates.
    columns={}
    for j,points in enumerate(plot._positions):
        for k,(x,y) in enumerate(points):columns.setdefault(round(x,5),[]).append((y,j,labels[j][k]))
    for x,items in columns.items():
        items.sort()
        bottom=plot.y+4;top=plot.y+plot.height-6;gap=font_size+1.5
        positions=[]
        for y,j,label in items:positions.append(max(y+4,bottom if not positions else positions[-1]+gap))
        if positions[-1]>top:
            offset=positions[-1]-top;positions=[v-offset for v in positions]
        if positions[0]<bottom:
            positions=[bottom+i*gap for i in range(len(items))]
        for (y,j,label),label_y in zip(items,positions):
            width=stringWidth(label,'Helvetica',font_size)
            xx=x
            drawing.add(Line(x,y,xx,label_y,strokeColor=colors_for_series[j],strokeWidth=.3))
            drawing.add(Rect(xx-width/2-1,label_y-1,width+2,font_size+1.5,
                             fillColor=colors.Color(1,1,1,alpha=.9),strokeColor=None))
            drawing.add(String(xx,label_y,label,fontName='Helvetica-Bold' if best_labels and (j,label) in best_labels else 'Helvetica',fontSize=font_size,
                               textAnchor='middle',fillColor=colors_for_series[j]))


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
                log_y=True, x_format=None, y_format=None, height=255, shared_y=False, point_labels=None, highlight=None):
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
        if point_labels is not None:lp.yValueAxis.labels.dx=-12
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
        best_labels=set()
        if highlight:
            lp.draw()
            grouped={}
            for j,(_,pts,_,_) in enumerate(series[i]):
                for k,(x,y) in enumerate(pts):grouped.setdefault(x,[]).append((y,j,k))
            for values in grouped.values():
                best=(max if highlight=='max' else min)(v[0] for v in values)
                for y,j,k in values:
                    if y==best:
                        xx,yy=lp._positions[j][k]
                        drawing.add(Circle(xx,yy,3.4,fillColor=None,strokeColor=TEAL,strokeWidth=1.1))
                for j in range(0,len(series[i]),2):
                    pair=[v for v in values if v[1] in (j,j+1)]
                    if pair:
                        chosen=(max if highlight=='max' else min)(v[0] for v in pair)
                        for y,jj,kk in pair:
                            if y==chosen and point_labels is not None:best_labels.add((jj,point_labels[i][jj][kk]))
        if point_labels is not None:
            point_annotations(drawing,lp,point_labels[i],[v[2] for v in series[i]],6.5 if len(titles)==1 else 5.6,best_labels)
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
    all_rows=[row for panel in panels for policies_at_c in panel.values() for row in policies_at_c.values()]
    ymin=min(number(row['solve_min_s']) for row in all_rows)/1.18
    ymax=max(number(row['solve_max_s']) for row in all_rows)*1.22
    width=500/len(panels);bottom=54;plot_height=155
    for panel_index,(title,panel) in enumerate(zip(titles,panels)):
        left=panel_index*width+38;plot_width=width-54
        ticks=sorted(panel);xmin,xmax=math.log2(ticks[0]),math.log2(ticks[-1])
        def x(value):return left+(math.log2(value)-xmin)/(xmax-xmin)*plot_width
        def y(value):return bottom+math.log(value/ymin)/math.log(ymax/ymin)*plot_height
        candidates=[m*10**e for e in range(math.floor(math.log10(ymin)),math.ceil(math.log10(ymax))+1)
                    for m in (1,2,3,4,5,6,8) if ymin<=m*10**e<=ymax]
        tick_values=candidates[::max(1,math.ceil(len(candidates)/5))]
        for value in tick_values:
            yy=y(value)
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
                fastest=number(r['solve_median_s'])==min(number(v['solve_median_s']) for v in panel[c].values())
                if fastest:drawing.add(Circle(xx,median,3.8,fillColor=None,strokeColor=TEAL,strokeWidth=1.1))
                # Policy-specific vertical positions keep close automatic/forced values distinct.
                tx=x(c)+(policy_index-1)*21
                tx=max(left+10,min(tx,left+plot_width-10))
                ty=median+7+policy_index*8
                drawing.add(Line(xx,median,tx,ty,strokeColor=color,strokeWidth=.3))
                drawing.add(String(tx,ty,f"{number(r['solve_median_s']):.3g}",fontName='Helvetica-Bold' if fastest else 'Helvetica',fontSize=6,textAnchor='middle',fillColor=color))
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
    series=[];split_labels=[]
    for method,label,color in [('MPI+OpenMP','M+OMP',ORANGE),('MPI+Kokkos OpenMP','M+KK',TEAL)]:
        for mode in ('Allgatherv','Halo'):
            rows=[r for r in SPLITS if r['method']==method and r['communication']==mode]
            series.append((label+(' A' if mode=='Allgatherv' else ' H'),
                           [(int(r['threads']),number(r['geomean_speedup_vs_T1'])) for r in rows],color,mode=='Halo'))
            split_labels.append([('A' if mode=='Allgatherv' else 'H')+short_ms(split_time(method,mode,int(r['threads']))) for r in rows])
    result['04_fixed_256_splits']=line_panels(['Fixed 256 cores across all 45 graphs'],[series],
        'Threads per rank T (p=256/T)','Geometric-mean speedup vs T=1 (×)',[1,2,4,8,16,32],point_labels=[split_labels],highlight='max')
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
                if j==0:
                    h=halo_times(('cpu_node','gpu_node')[population],('google','uniform','hub','controlled')[category])[1]
                    d.add(String(x,y+8,'('+short_ms(h)+')',fontName='Helvetica',fontSize=5.5,textAnchor='middle',fillColor=INK))
        d.add(bar);d.add(String(j*250+125,224,title,fontName='Helvetica-Bold',fontSize=9,textAnchor='middle',fillColor=INK))
    legend(d,['CPU-node pairs','GPU-node pairs'],[BLUE,ORANGE],columns=2,y=14)
    result['05_halo_pairs']=d
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
                      'Iteration time (ms/iteration)',[4,16,64,256],height=212,shared_y=True,highlight='min')
    efficiency=[]
    for family,panel in zip(('uniform','hub','controlled'),panels):
        curves=[]
        for (label,points,color,dash) in panel:
            base=points[0][1]
            curves.append((label,[(c,base/value) for c,value in points],color,dash))
        efficiency.append(curves)
    retained=line_panels(['Uniform','Hub','Controlled'],efficiency,'Active CPU cores C (count)',
                         'Retained efficiency: C=4 reference (%)',[4,16,64,256],height=212,
                         shared_y=True,y_format=lambda v:f'{v:.1%}',highlight='max',
                         point_labels=[[[(('H' if dash else 'A')+short_ms(y/1000)) for c,y in points] for label,points,color,dash in panel] for panel in panels])
    combined=Drawing(500,438)
    group=Group(*times.contents);group.translate(0,224);combined.add(group)
    combined.add(Group(*retained.contents));result['07_core_weak']=combined

    phase_panels=[]
    labels=['CU1','CU2','KK1','KK2']
    for graph in BASELINE_GRAPHS[3:]:
        cases=[get(graph,method,'gpu_node',processes=p,threads=1,communication='Allgatherv')
               for method in ('MPI+CUDA','MPI+Kokkos CUDA') for p in (1,2)]
        phase_panels.append([(label,[(i+1,number(r[key])) for i,r in enumerate(cases)],color,False)
                             for label,key,color in [('Solve','solve_median_s',INK),
                                 ('Device compute','compute_median_s',BLUE),
                                 ('Host staging','transfer_median_s',ORANGE),
                                 ('MPI exchange','communication_median_s',TEAL)]])
    phase_drawing=line_panels([DISPLAY[g] for g in BASELINE_GRAPHS[3:]],phase_panels,
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
        'MPI processes p (count)','Payload (MB/rank/iteration)',[2,4,16,64,256],height=235,highlight='min',
        point_labels=[[[('H' if dash else 'A')+fmt(y) for x,y in points] for label,points,c,dash in panel] for panel in panels])
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
    styles.add(ParagraphStyle(name='ReferenceReport',parent=styles['CaptionReport'],fontSize=7.5,leading=9,spaceAfter=3))
    styles.add(ParagraphStyle(name='TableReport',fontName='Helvetica',fontSize=8,leading=10,textColor=INK))
    styles.add(ParagraphStyle(name='EquationReport',fontName='Times-Roman',fontSize=10,leading=15,alignment=TA_CENTER,spaceAfter=10,textColor=INK))
    styles.add(ParagraphStyle(name='TableCaptionReport',parent=styles['CaptionReport'],keepWithNext=True))
    story=[];md=[]
    complete=CompleteResults(FIXED,WEAK,CONTROLS,LAUNCHER_CONTROLS,GRAPHS,DATA,SUPPLEMENT)
    table_number=0
    equations=LatexEquations(REPORT/'equations', ROOT/'tmp/pdfs/latex_build')
    def para(text):
        text=notation(text)
        md.append(text+'\n');story.append(Paragraph(inline(text),styles['BodyReport']))
    def heading(text,level=1):
        md.append('#'*(level+1)+' '+text+'\n');story.append(Paragraph(html.escape(text),styles['SectionReport' if level==1 else 'SubReport' if level==2 else 'SubSubReport']))
    def table(headers,rows,widths=None,small=False,caption=None,emphasis=None,heatmap=None,extrema=None,paired=False):
        nonlocal table_number
        table_number+=1
        assert caption
        caption=f'Table {table_number}. '+notation(caption)
        emphasis=emphasis or {}
        emphasis=dict(emphasis)
        for column,direction in (extrema or {}).items():
            values=[float(str(row[column]).split()[0].replace('%','').replace('×','').replace(',','')) for row in rows]
            best=(max if direction=='max' else min)(values)
            for i,value in enumerate(values):
                if value==best:emphasis[i,column]='good'
        backgrounds={};foregrounds={};bold=set(emphasis)
        if paired:
            groups={}
            for i,row in enumerate(rows):
                vals=[float(str(row[j]).split('%')[0]) for j in (2,3)]
                for j,value in zip((2,3),vals):
                    if value==max(vals):bold.add((i,j))
                    groups.setdefault(str(row[0]),[]).append((value,i,j))
            for values in groups.values():
                best=max(v[0] for v in values)
                for v,i,j in values:
                    if v==best:backgrounds[i,j]=colors.HexColor('#dceee7');bold.add((i,j))
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
                    if value==best:
                        bold.add((i,j));backgrounds[i,j]=colors.HexColor('#dceee7');foregrounds[i,j]=INK
        for i,row in enumerate(rows):
            if str(row[0]).lower().startswith('total'):
                bold.update((i,j) for j in range(len(headers)))
        md.append(caption+'\n')
        md.append('| '+' | '.join(map(str,headers))+' |\n| '+' | '.join(['---']*len(headers))+' |')
        for i,row in enumerate(rows):
            md.append('| '+' | '.join(('**'+str(x)+'**') if (i,j) in bold and str(x) else str(x) for j,x in enumerate(row))+' |')
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
    para('We evaluate synchronous PageRank on 45 fixed directed graphs (3 original, 42 reproducible extensions) using Serial, OpenMP, MPI, MPI+OpenMP, CUDA, and Kokkos OpenMP/CUDA. The 19,530 fixed-input configurations test added parallelism and equal-core process/thread decompositions. A growing-input suite uses 27 scale-specific graph specifications (15 shared with the fixed set; 57 distinct input specifications overall), with 318 resource-scaled configurations and 54 fixed-resource size controls: it tests whether iteration time stays constant as work and resources grow together. Vanda measurements use one warm-up and the median of five timed solves, with independent numerical validation. Balanced inputs benefit from distributed execution; concentrated incoming edges limit effective parallelism. Halo reduces contribution traffic but not invariably runtime, and a second GPU need not accelerate the solve.')
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
    para("Uniform, Hub, and Controlled use scales s=1,2,4,8,16,32,64,128,256, with N=50,000s and E=800,000s: 27 input identifiers. Fifteen specifications are shared with the fixed set: the 12 degree-16 grid inputs at s=1/2/4/8, and the three large inputs at s=256. Thus 45+27 denotes experimental roles, covering 57 distinct input specifications rather than 72 different graphs.")
    para('Rank-normalized suites set s=p; core-normalized suites set s=C. CPU records comprise 150 rank-normalized and 84 core-normalized cases. GPU-node records use six inputs (3 families, s=1/2): 84 distributed resource-scaled cases and 54 standalone size controls. Total: 372 records, including 318 resource-scaled cases and 54 fixed-resource controls.')

    heading('2 Methodology')
    heading('2.1 Notation, implementations, and communication',2)
    table(['Symbol or term','Definition and unit'],[
        ['N; E','Numbers of vertices and directed edges (counts). Average out-degree is E/N.'],
        ['Node; n','A physical compute machine; n is the number of participating machines (nodes).'],
        ['MPI rank; p','An MPI rank identifies a participating process, not a PageRank score. p is the total process count; rank IDs are 0,...,p-1. Processes have separate local data.'],
        ['MPI+OpenMP; MPI+Kokkos OpenMP','MPI processes divide ownership; each process uses OpenMP or Kokkos OpenMP threads to update its owned rows.'],
        ['r; T','r is the number of MPI processes per node. T is the number of CPU threads per process (threads/process).'],
        ['C; G','C is active CPU parallelism (cores); G is the number of GPUs used by device computation (devices).'],
        ['t; I','t is solve time in seconds; I is the convergence iteration count. T denotes threads, never runtime.'],
        ['Affinity; NUMA','Affinity pins execution to assigned CPUs. NUMA (non-uniform memory access) means access cost can depend on the memory/socket placement.'],
        ['CSR; PPR','Compressed sparse row storage; personalized PageRank. We use the uniform-preference special case of PPR.'],
        ['OMP; KK; A; H','Figure abbreviations: OpenMP; Kokkos; Allgatherv; Halo. CUDA and Kokkos CUDA denote GPU computation.']], [100,400],caption='Symbols, terminology, and measurement units used in the experiment design.')
    equation('', r'$$p=nr,\qquad C=pT=nrT.$$')
    para('**How MPI+OpenMP and MPI+Kokkos OpenMP work.** MPI divides the graph among p separate processes. Within each process, T OpenMP or Kokkos OpenMP threads update its assigned rows. The two threaded MPI methods are separate implementations, not a combined program. For example, n=8,p=64,T=4 uses 256 active CPU cores; pure MPI instead uses p=256,T=1 at the same core budget. C=pT counts the execution budget, not measured CPU utilization; n counts participating machines, not exclusive use of every core on a machine.')
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
    para('**Timing protocol.** One warm-up, five timed solves, median recomputed from the original solve_s values. MPI time is the maximum across ranks. Timed: iterations, MPI, distributed per-iteration device staging. Untimed: input, distribution, backend construction, Halo setup, and standalone GPU setup/final rank copies. These are solver rather than end-to-end application times. Point labels round milliseconds for legibility (k=1,000 ms); statistics use the unrounded stored medians.')
    para('Standalone setup/final GPU copies lie outside solver timing; recurring distributed staging lies inside. Section 3.0 explains this algorithmic distinction.')
    para('**Backend boundaries.** OpenMP team creation is timed; Kokkos initialization is not. Distributed compute phases use fenced host clocks including dispatch/reduction costs; standalone native CUDA additionally records CUDA-event duration as ancillary metadata. Primary solve comparisons use host-clock time. Transfer phases cover explicit staging, not necessarily internal scalar-result copies. MPI+Kokkos OpenMP retains the shared distributed driver and its host-buffer copies. These comparisons therefore evaluate concrete implementations and scheduling policies.')
    para('Twelve identified MPI+Kokkos cases use lower-memory initialization but identical timed update/communication kernels; their graph construction and memory preparation remain untimed.')
    heading('2.3 Experimental configuration matrix',2)
    para('**Configuration = graph × implementation × valid layout × exchange**, not a timed repeat. All 45 graphs cross every listed row. Derived p=nr, C=pT, G=p=n are not extra dimensions; CPU layouts require rT<=32. Standalone methods have no MPI-exchange dimension.')
    para('**CPU nodes:** Q={1,2,4,8,16,32}; each MPI layout runs Allgatherv and Halo.')
    table(['Implementation','Nodes n','Ranks/node r','Threads/process T','Configs/graph'],[
        ['Serial','1','1','1','1'],
        ['OpenMP','1','1','1,2,4,8,16,32','6'],
        ['Kokkos OpenMP','1','1','1,2,4,8,16,32','6'],
        ['MPI','1,2,4,8','1,2,4,8,16,32','1','48'],
        ['MPI+OpenMP','1,2,4,8','1,2,4,8,16,32','1,2,4,8,16,32; rT<=32','168'],
        ['MPI+Kokkos OpenMP','1,2,4,8','1,2,4,8,16,32','1,2,4,8,16,32; rT<=32','168']], [118,65,105,147,65],small=True,caption='Complete CPU configuration matrix. Configs/graph counts layouts and applicable Allgatherv/Halo choices for one graph; all 45 graphs use every row. Derived p=nr and C=pT are not extra Cartesian dimensions.')
    para('MPI has 4×6=24 layouts/graph; each threaded MPI method has 4×21=84 valid (n,r,T) layouts/graph. Crossing 45 graphs and 2 exchanges gives 2,160 and 7,560 cases respectively; CPU-node total is 17,865. Standalone p=1 denotes one process without an MPI communicator.')
    para('**GPU nodes:** the first four rows compute on GPUs; the remaining rows are CPU controls on the same node class (G=0).')
    table(['Implementation','Nodes n','Processes p','CPU threads T','GPUs G','MPI exchange','Configs/graph'],[
        ['CUDA','1','1','1 host','1','Not applicable','1'],
        ['Kokkos CUDA','1','1','1 host','1','Not applicable','1'],
        ['MPI+CUDA','1,2','n','1 host','n','Allgatherv; Halo','4'],
        ['MPI+Kokkos CUDA','1,2','n','1 host','n','Allgatherv; Halo','4'],
        ['Serial CPU control','1','1','1','0','Not applicable','1'],
        ['OpenMP CPU control','1','1','1,2,4,8,16,32','0','Not applicable','6'],
        ['MPI CPU control','1,2','n','1','0','Allgatherv; Halo','4'],
        ['MPI+OpenMP CPU control','1,2','n','1,2,4,8','0','Allgatherv; Halo','16']], [118,44,50,65,42,124,57],small=True,caption='GPU-node fixed-input matrix: counts per graph, including device-computing methods and same-node-class CPU controls. G counts GPUs used for computation.')
    para('GPU-node total: 450 device cases + 1,215 CPU controls = 1,665; complete fixed-input total: **19,530**. Serial/ordinary OpenMP remain CPU methods; standalone rows have no exchange parameter.')
    para('All n/r/T layouts are displayed by thread/node groups in complete numerical heatmaps. Equal-core comparisons additionally hold C fixed and vary p=C/T; the C=256 aggregate is a summary across all 45 graphs, not a substitute for individual layouts.')
    heading('2.4 Scaling questions and statistical summaries',2)
    para('**Fixed graph, more workers:** hold N, E, structure, and stopping rule fixed; increase C. Ideal doubling of cores halves solve time. With t_ser and t(C) denoting matched Serial and parallel medians:')
    equation('', r'$$S(C)=\frac{t_{\mathrm{ser}}}{t(C)},\qquad \eta_{\mathrm{CPU}}(C)=\frac{S(C)}{C}.$$')
    para('Speedup is dimensionless; CPU efficiency S/C is a reference-normalized percentage, not CPU utilization (100% means linear speedup). Values above 100% can reflect cache, memory-placement or code-path differences relative to Serial; the fixed-cost assumptions of an ideal linear model need not hold. These curves locate communication, synchronization, or granularity limits. The separate C=256 test varies p/T to compare decompositions at equal resources.')
    para('**More work with more workers:** grow graph size with resources and ask whether iteration time remains constant. Rank-normalized inputs use N=50,000p,E=800,000p; core-normalized inputs use N=50,000C,E=800,000C, allowing equal nominal work/core across process/thread decompositions. Fixed counts per worker do not ensure constant communication or balanced incoming edges.')
    table(['Growing-input block','Graph scale','Resource layouts','Configurations'],[
        ['Rank-normalized CPU','s=p; 3 families','MPI and MPI+Kokkos T1: p=1,...,256 in powers of 2; MPI+OpenMP T4: p=1,...,64; Allgatherv and Halo','150'],
        ['Core-normalized CPU','s=C; 3 families','MPI+OpenMP and MPI+Kokkos OpenMP: T4, p=C/4; C=4,...,256 in powers of 2; Allgatherv and Halo','84'],
        ['GPU-node resource scaling','s=p=1,2; 3 families','n=p; MPI T1, MPI+OpenMP T1/2/4/8, MPI+CUDA and MPI+Kokkos CUDA T1; Allgatherv and Halo','84'],
        ['GPU-node input-size controls','s=1,2; 3 families','Standalone Serial, OpenMP, CUDA, and Kokkos CUDA retain one node while input size increases','54'],
        ['Total','','318 resource-scaled configurations + 54 fixed-resource controls','372']], [115,85,245,55],small=True,caption='Growing-input experiment groups. Counts refer to configurations, not five-run repetitions; fixed-resource controls are kept separate.')
    para('Convergence counts I can change with graph size. We therefore compare iteration time tau rather than confounding iteration cost with solve length; C0 is the smallest point in each resource series:')
    equation('', r'$$\tau(C)=\frac{t(C)}{I(C)},\qquad \eta_{\mathrm{grow,iter}}(C)=\frac{\tau(C_0)}{\tau(C)}.$$')
    para("Ideal retained efficiency is 100%; 25% means four times the reference iteration time. The common CPU plot uses C0=4 on identical family inputs: MPI p=C,T=1; MPI+OpenMP and MPI+Kokkos OpenMP p=C/4,T=4. All rank-normalized p0=1 series are printed in Section 3.6.3. CPU/GPU-node speedups use their own Serial reference; two-GPU scaling uses each method's one-GPU time.")
    para('**Two statistical levels:** median of five solves for a configuration; geometric mean of matched per-graph median ratios for cross-graph comparisons:')
    equation('', r'$$\widetilde{t}_{g,a}=\operatorname{median}(t_{g,a,1},\ldots,t_{g,a,5}),\qquad s_g=\frac{\widetilde{t}_{g,a}}{\widetilde{t}_{g,b}},\qquad \overline{s}_{\mathrm{geo}}=\left(\prod_{g=1}^{m}s_g\right)^{1/m}.$$')
    para("g indexes m graphs; s_g>1 favors b. Geometric means weight proportional changes equally: 2× and 0.5× combine to 1×. Speedup is computed from matched per-graph ratios, never pooled seconds or the five repeats. Parentheses on aggregate ratios show the geometric mean of durations for the identical matched population (t_geo); this is descriptive, not a single run or suite wall time. The ratio of the reference and tested t_geo values equals the reported geometric-mean speedup. Communication pairs additionally match backend, nodes, p, and T. The 45-row overview selects each method's best observed median across layouts; its budgets may differ.")
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
    para('Symmetric controls target each transition: automatic/Bruck/Ring at C32/64/128,T=4 on Hub and Controlled; automatic/basic_linear/pairwise at p64/128/256 on Uniform Halo. The Allgatherv comparison tests the two algorithms bordering this transition; the Alltoallv comparison covers its complete two-algorithm menu.')
    table(['Active cores C','Nodes','MPI p / Alltoallv','MPI+threads p / Alltoallv','MPI+threads Allgatherv'],[
        ['32','1','32 / basic_linear','8 / basic_linear','Bruck'],
        ['64','2','64 / pairwise','16 / basic_linear','Ring'],
        ['128','4','128 / basic_linear','32 / basic_linear','Ring'],
        ['256','8','256 / pairwise','64 / pairwise','Ring']], [85,40,130,135,110],caption='Installed tuned default-rule choices at the diagnostic resource points. Pure MPI uses T1 and MPI+OpenMP and MPI+Kokkos OpenMP T4; n is node count.')
    para('The MPI+OpenMP Allgatherv policy controls use T4. Forced IDs are Alltoallv 1=basic_linear,2=pairwise; Allgatherv 2=Bruck,3=Ring [9]. Only that operation changes. Policies share binary, graph, allocation, p/T, affinity, transport, and tuned/basic/libnbc/self availability. Component probes are untimed; policy plots show five-run medians and observed ranges.')
    para('**Equal cores need not mean equal collectives.** At C256, p256/T1 selects pairwise, p128/T2 basic_linear, p64/T4 pairwise, and p32/16/8 basic_linear. Changing p/T alters participation, local work sharing, and selection regime; forced-policy controls isolate one communication choice.')
    para('The tree is a general heuristic; controls test its suitability without replacing automatic mainline results by fastest policies. Separately, OpenMP schedule(dynamic,64) redistributes local vertex chunks; OMP_DYNAMIC=false fixes team size without disabling that scheduling.')
    heading('3 Results')
    para('**Reading the results:** every MPI curve includes Allgatherv/Halo and retains default MPI settings unless labeled forced. Algorithm-rule tables describe the installed tuned component. Section 3.5 pairs those same main-matrix records for exchange effects, then uses separate matched allocations for algorithm controls. Green/amber emphasis flags favorable values or costly mechanisms; captions specify the comparison.')
    heading('3.0 Timing scope and supporting setup costs',2)
    para('The performance question is the cost of repeated PageRank iterations on an already prepared graph. Solver timing includes local updates, synchronization and per-iteration data movement. One-time preparation is discussed separately so that graph loading and setup do not obscure the parallelization/scaling comparison. This common scope applies to Serial and parallel methods; it does not claim that complete application execution has no preparation cost.')
    table(['Stage','Recorded timing and boundary','Interpretation'],[
        ['Graph partition / distribution','No independent phase timer; before timed solves','Contiguous ownership, incoming-CSR construction and initial distribution are preparation, excluded from solver time.'],
        ['Halo dependency setup','communication_setup_s; before warm-up/timing','Measured once per prepared layout; builds remote-ID requests reused by all solves.'],
        ['Local thread scheduling','Embedded in solver/compute time; no scheduler-only timer','OpenMP dynamic chunks and Kokkos static ranges are part of the compared implementations.'],
        ['Device staging','Distributed transfer_median_s is inside solver','Explicit host/device buffer movement is measured; standalone setup/final copies remain outside solver.'],
        ['MPI exchange / waiting','communication_median_s is inside solver','Includes contribution packing/copies, collectives and reduction waits; not pure network transmission.']], [100,190,210],small=True,caption='Timing accounting. An uninstrumented stage is not a zero-cost stage. Independently rank-maximized phase medians are not additive critical-path components.')
    halo_setup=[r for r in FIXED if r['communication']=='Halo']
    table(['Implementation','Halo layouts','Median setup (s)','Setup range (s)'],[
        [m,str(len(rr)),fmt(stats.median(number(r['communication_setup_s']) for r in rr)),fmt(min(number(r['communication_setup_s']) for r in rr))+' - '+fmt(max(number(r['communication_setup_s']) for r in rr))]
        for m in ('MPI','MPI+OpenMP','MPI+Kokkos OpenMP','MPI+CUDA','MPI+Kokkos CUDA')
        for rr in [[r for r in halo_setup if r['method']==m]]], [155,80,115,150],small=True,caption='Supporting one-time Halo setup statistics over all fixed-input layouts on the relevant node classes. These pool different graph sizes/layouts for cost context, not a scaling or backend ranking.')
    table(['Implementation','n / p / T','Solve (s)','Compute (s)','Staging (s)','MPI/wait (s)'],[
        [m,f'{p} / {p} / 1',*[fmt(r[k]) for k in ('solve_median_s','compute_median_s','transfer_median_s','communication_median_s')]]
        for m in ('MPI+CUDA','MPI+Kokkos CUDA') for p in (1,2)
        for r in [get('strong_uniform',m,'gpu_node',processes=p,threads=1,communication='Allgatherv')]], [120,80,75,75,75,75],small=True,caption='Illustration of recorded solver phases: Large Uniform, Allgatherv, one GPU per process/node. Five-run medians in seconds. Supporting phase times use consistent implementation-specific boundaries; the complete solver-time matrix appears in Section 3.7.')
    para('**Transfer scope follows recurring algorithmic work.** A standalone GPU retains its graph and contribution vector on device during the iterations; setup and final-result copies prepare/return the solve. The MPI+GPU driver stages updated contribution buffers through host memory each iteration, including its p=1 execution path; at p>1 the exchange supplies remote values. This recurring implementation work is charged to solver time. Thus the boundary is consistently the iterative solver, while the distributed implementation performs additional timed data movement. Thread scheduling overhead is included in local computation/solver time; no independent scheduler timer is recorded, so it is not subtracted or reported as an isolated cost.')
    para('At one to two GPUs, Large Uniform approximately halves device compute time, while staging and MPI/wait remain material. These clocks explain why a compute-kernel gain need not produce the same solver gain. Scheduling changes how skewed rows reach workers; partitioning fixes destination ownership. Their effects are evaluated through measured solve time and structural load statistics rather than an invented isolated scheduling/partition duration.')
    para('All 19,530 fixed configurations, 372 growing-input entries and 59 diagnostic settings are printed in their corresponding Results subsections. Graph/thread/node groups are not replaced by a best-only summary. Bold and green indicate the explicitly named comparison metric; comparisons across different references do not imply identical absolute runtime.')
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
    baseline_headers=['Graph','Vertices N','Edges E','Degree E/N','Iterations I','Solve (s)','Iteration (ms)']
    def serial_row(label,row):
        return [label,f"{int(row['vertices']):,}",f"{int(row['edges']):,}",
                fmt(number(row['edges'])/int(row['vertices'])),row['iterations'],
                fmt(row['solve_median_s']),fmt(number(row['solve_median_s'])/int(row['iterations'])*1000)]
    density=[]
    for family in ('uniform','hub','controlled'):
        selected=sorted((r for r in GRAPHS if r['graph'].startswith('grid_'+family+'_n100000_')),key=lambda r:int(r['edges']))
        density.extend(serial_row(family.title(),r) for r in selected)
    table(baseline_headers,density,[95,80,85,55,55,60,70],small=True,
        caption='Serial density slice: N=100,000, varying E and mean out-degree. One CPU node/process/thread; five-run solve medians and solve/iteration. Column definitions match the baseline table.')
    para('**Sparsity has two distinct meanings here.** Mean degree is E/N; adjacency density is E/N² (self-links are allowed). The grid spans densities 0.001%-0.032%; the large inputs have density 0.000125%. At fixed N, higher degree raises edge work; at fixed degree, increasing N lowers density while increasing CSR work/storage linearly. Sparse adjacency does not guarantee selective communication: a partition can reference nearly every remote source, explaining Uniform’s small Halo savings at p=2.')
    para('**Denser need not mean a longer solve.** Controlled at N=100,000 needs 35/22/17 iterations for degree 4/8/16. Fewer iterations can offset more edge work, while the generator also changes exact destination concentration (Section 1.2). Per-iteration cost also depends on row structure and memory locality, so measured time need not be monotone in E.')
    table(baseline_headers,[serial_row(DISPLAY[g],get(g,'Serial')) for g in BASELINE_GRAPHS],
        [95,80,85,55,55,60,70],small=True,
        caption='Original and large Serial inputs, using the same columns, CPU-node context, one-thread layout, and five-run statistic as the density slice. The Google graph has a non-integer mean degree.')

    heading('3.2.2 PageRank concentration in the real Google graph',3)
    para(f"**Google scores are concentrated.** {GOOGLE['dangling_vertices']:,} vertices ({GOOGLE['dangling_vertices']/GOOGLE['vertices']:.1%}) are dangling, requiring mass redistribution; the top 1% hold {GOOGLE['top_1_percent_rank_mass']:.1%} of score mass. PageRank/in-degree Pearson correlation is {GOOGLE['pagerank_indegree_pearson']:.3f}: strongly associated, but degree is not the full weighting rule.")
    table(['Node ID','PageRank','In-degree','Out-degree'],[[r['node_id'],f"{r['rank']:.7f}",r['in_degree'],r['out_degree']] for r in GOOGLE['top10'][:5]], [120,140,120,120],caption='Five highest-scoring Google vertices. PageRank is a dimensionless probability score; in-degree and out-degree are edge counts.')
    para('The anonymized edge list does not identify websites or content quality; concentration and correlation describe graph structure, not causal importance.')

    heading('3.3 Fixed graphs with more CPU processes and nodes',2)
    heading('3.3.1 Increasing active cores through explicit process layouts',3)
    para('Every measured CPU layout is printed in Section 3.7, grouped by graph and T=1,2,4,8,16,32. Each thread group crosses n=1,2,4,8 with ranks/node r subject to rT<=32. Thus all process/thread/node combinations remain visible; no single thread choice substitutes for the matrix. Pure MPI has one computation thread per process (T=1); MPI+OpenMP and MPI+Kokkos OpenMP use the complete thread range.')
    para('Complete heatmaps report every solve median, grouped by node count and T; Serial-relative color shows proportional performance. Bold compares Allgatherv/Halo at identical layout; green marks the lowest time within a graph/node class. These are observed median winners, not significance tests.')
    uniform=get('strong_uniform','MPI',host_nodes=8,processes=256,threads=1,communication='Halo')
    para(f"**More cores help large Uniform, not small Google.** MPI Halo at C256 gives Uniform {number(uniform['speedup_vs_matched_serial']):.1f}× Serial speedup ({number(uniform['cpu_efficiency_vs_serial']):.1%} efficiency). Google instead goes from its best pure-MPI Halo point, n1/p32 = 0.149 s, to n8/p256 = 1.462 s: communication/synchronization outweigh local work. Equal-size Hub/Controlled also benefit less than Uniform.")
    para('The large Hub C4 Halo MPI+OpenMP point takes 5.06 s: 4.59× its Serial reference and 114.7% normalized efficiency. This is an observed superlinear reference ratio, not greater than 100% hardware utilization; cache/locality, execution-path and placement effects can contribute.')
    para('**Edge ownership, not vertex balance, controls the structural difference.** The next plot measures maximum/mean incoming-edge load under equal contiguous vertex partitions; 1 means perfect edge balance.')
    figure('13_rank_workload','Equal-size large inputs, contiguous equal-vertex ownership. Maximum/mean incoming edges versus process count (dimensionless); 1 denotes balance. These are partition statistics, not timing speedups.')
    equation('', r'$$B_E=\frac{\max_i E_i}{E/p},\qquad p_{\mathrm{edge}}=\frac{E}{\max_i E_i}=\frac{p}{B_E}.$$')
    table(['Large graph, p=256','Max/mean edge load','Busiest process edge share (%)','Equal-work process proxy'],[
        [DISPLAY[r['graph']],f"{number(r['max_mean_edges']):.3f}",f"{number(r['max_rank_edge_share']):.2%}",fmt(r['equivalent_balanced_ranks'])]
        for r in WORK if r['processes']=='256'],[125,115,140,120],
        caption='Work concentration at 256 processes. B_E is dimensionless. The equal-work process proxy assumes equal edge-scanning rates and describes load balance, not measured speedup. Amber marks concentrated work; all 256 processes were launched.', emphasis={(i,j):'warn' for i in (1,2) for j in (1,2,3)})
    para('**One process owns 29%-30% of Hub/Controlled edges at p256.** All processes run, but the slowest row scans govern iteration progress. The edge-only load equals about 3.4/3.3 balanced processes under equal scanning rates; Uniform stays balanced. The 75.0%/77.5% hot-edge fractions occupy the first 1% of IDs, fitting one partition for p<=100 and crossing boundaries above it. Halo preserves this ownership.')
    table(['Large graph; T=32','OpenMP time (s)','Kokkos OpenMP time (s)','Kokkos/OpenMP (×)','Largest static block edge share (%)'],[
        [DISPLAY[r['graph']],fmt(r['openmp_s']),fmt(r['kokkos_openmp_s']),ratio_time(r['kokkos_over_openmp'],r['kokkos_openmp_s']),f"{number(r['contiguous_32way_edge_share_proxy']):.1%}"] for r in POLICY],
        [105,85,105,90,115],caption='One-node scheduling comparison on the same large graphs. Each method uses one process and 32 CPU threads; times are five-run solve medians. Ratio parentheses give Kokkos seconds (>1× means slower). The static-block share is an analytical proxy; amber marks skewed ownership and the associated gap.', emphasis={(i,j):'warn' for i in (1,2) for j in (3,4)})
    para('**Static row ranges concentrate the same skew.** OpenMP distributes 64-vertex chunks dynamically; Kokkos RangePolicy defaults to static ranges [6]. A 32-way split puts 75.5%-78.0% of skewed edges in one block. Uniform times are similar, but Hub/Controlled differ by about 22×, implicating the implemented scheduling/ordering combination rather than intrinsic framework overhead.')

    heading('3.3.2 Fixed 256-core budget: changing the process/thread split',3)
    para("**Fixed n=8,C=256; vary p/T.** MPI+OpenMP and MPI+Kokkos OpenMP use six splits and two exchanges. Each graph's median is divided into its same-method/exchange p256/T1 median, then ratios are geometrically averaged over 45 graphs.")
    table(['Processes p','Threads/process T','MPI+OMP A (×)','MPI+OMP H (×)','MPI+KK A (×)','MPI+KK H (×)'],[
        [256//t,t,*[ratio_time(next(r for r in SPLITS if r['method']==method and r['communication']==mode and r['threads']==str(t))['geomean_speedup_vs_T1'],split_time(method,mode,t))
                   for method in ('MPI+OpenMP','MPI+Kokkos OpenMP') for mode in ('Allgatherv','Halo')]]
        for t in (1,2,4,8,16,32)], [70,90,85,85,85,85],
        caption='Equal-core process/thread comparison. Values are geometric means of 45 paired speedups, each based on five-run median times. All rows satisfy pT=256; A=Allgatherv, H=Halo. Cells are speedup (t_geo seconds) over the identical 45 graphs. The reference is the corresponding method\'s T=1 row; green marks column maxima.', extrema={2:'max',3:'max',4:'max',5:'max'})
    figure('04_fixed_256_splits','Fixed n8,C256; p=256/T. Geometric-mean speedup versus the same method/exchange at T1 (×), across 45 paired graph medians. Point labels are matched-population t_geo in ms (k=1,000 ms); green rings mark the largest relative gain at each T; these own-reference gains do not rank absolute durations across exchanges.')
    best={method:max((r for r in SPLITS if r['method']==method and r['communication']=='Halo'),key=lambda r:number(r['geomean_speedup_vs_T1']))
          for method in ('MPI+OpenMP','MPI+Kokkos OpenMP')}
    a=next(r for r in SPLITS if r['method']=='MPI+OpenMP' and r['communication']=='Allgatherv' and r['threads']=='32')
    k=next(r for r in SPLITS if r['method']=='MPI+Kokkos OpenMP' and r['communication']=='Allgatherv' and r['threads']=='32')
    para(f"**Fewer processes can use the same cores better.** At p8/T32, Allgatherv improves the T1 aggregate by {number(a['geomean_speedup_vs_T1']):.2f}× (MPI+OpenMP) and {number(k['geomean_speedup_vs_T1']):.2f}× (MPI+Kokkos). Best Halo splits use T{best['MPI+OpenMP']['threads']}/T{best['MPI+Kokkos OpenMP']['threads']}, gaining {number(best['MPI+OpenMP']['geomean_speedup_vs_T1']):.2f}×/{number(best['MPI+Kokkos OpenMP']['geomean_speedup_vs_T1']):.2f}×. Fewer ranks reduce collective participation; row sharing and memory locality can contribute to the observed gains; individual graph optima differ.")

    para('Section 3.7 prints every CPU layout in thread/node-grouped numerical heatmaps, rather than selecting a T=4 line. Each graph includes all T=1,2,4,8,16,32, every valid ranks/node choice and both exchanges. The standalone rows give all six thread choices as well.')
    heading('3.4 Standalone methods and one-to-two-GPU execution',2)
    heading('3.4.1 Standalone CPU/GPU baselines and MPI overhead',3)
    para('All standalone CPU thread counts and GPU results are printed for every graph in Section 3.7, alongside their matched Serial references and distributed counterparts. This complete matrix also exposes one-process MPI overhead without choosing a single thread count as the standalone result.')
    para('**MPI device overhead persists at one GPU.** Google CUDA/Kokkos CUDA take 0.115/0.094 s standalone versus 0.243/0.383 s under MPI Allgatherv p1. The distributed path stages contributions every iteration; input/backend setup is excluded.')
    heading('3.4.2 One versus two GPUs on fixed inputs',3)
    para('**Fixed graph; n=p=G changes 1→2**, one A40/process/node, automatic selection, both exchanges. CPU MPI and MPI+OpenMP T1 on the same node class are layout-matched controls. Each line uses its own one-node reference.')
    table(['Large graph','GPU method','Busiest p2 edge share (%)','Compute p1/p2 (×)','Solve p1/p2 (×)'],[
        [DISPLAY[r['graph']],r['method'],f"{number(r['p2_max_edge_share']):.1%}",ratio_time(r['compute_speedup'],r['p2_compute_s']),
         ratio_time(number(r['p1_solve_s'])/number(r['p2_solve_s']),r['p2_solve_s'])] for r in GPU_WORK],
        [105,135,100,80,80],caption='Allgatherv GPU comparisons, presented identically for all three large graphs and both backends. Each ratio divides the p1 median by the p2 median; values above 1× favor two GPUs. Parentheses give the corresponding p=2 compute/solve seconds. The edge share is a partition statistic.', emphasis={(i,3):'good' for i in (0,1)} | {(i,2):'warn' for i in (2,3,4,5)})
    para('**Uniform balances device work; skewed inputs do not.** Uniform obtains about 2× compute acceleration but MPI limits solve gains. Hub/Controlled leave 87%-89% of edges on one GPU: CUDA compute improves only about 1.1× while communication rises. Larger Kokkos gains are compatible with backend-specific kernel mapping, reduction, and locality costs; edge share is a mechanism, not a universal runtime bound.')

    para('The GPU-node subpanels in Section 3.7 print all 37 configurations per graph, including standalone methods, MPI+OpenMP CPU controls at T=1,2,4,8, all one/two-node choices and both exchanges. GPU kernel threads are independent of host T.')
    heading('3.5 Communication strategy and MPI implementation choice',2)
    para('**Two levels of control:** Section 3.5.1 changes the exact values exchanged (Allgatherv/Halo), reusing matched main-matrix cases; Section 3.5.2 holds the exchange fixed and changes the MPI collective algorithm in separate matched allocations.')
    heading('3.5.1 Allgatherv versus exact Halo exchange',3)
    para('Allgatherv assembles the complete contribution vector each iteration. Halo precomputes exact remote dependencies and exchanges only their current values through Alltoallv. Both retain the same PageRank equations, dangling-mass and convergence reductions. This comparison changes the exchange strategy; the next subsection changes its MPI implementation.')
    figure('05_halo_pairs','All 45 graphs, p>1: paired Allgatherv/Halo time ratio (geometric mean, ×; >1 favors Halo) and median logical payload reduction (%). Pairs match graph/method/n/p/T; explicit zero is measured. CPU/GPU-node layout populations differ, so bars are not hardware-only contrasts. Left-bar parentheses give Halo t_geo in ms (k=1,000 ms).')
    table(['Node class','Family','Matched pairs','Halo speedup (×)','Payload reduction (%)','Halo faster (%)'],[
        [r['context'].replace('_',' '),r['family'].title(),r['paired_configurations'],ratio_time(r['geomean_halo_speedup'],halo_times(r['context'],r['family'])[1]),
         f"{number(r['median_payload_reduction']):.1%}",f"{number(r['halo_faster_fraction']):.1%}"] for r in HALO],
        [90,80,70,85,95,80],caption='Populations and statistics behind the communication bars. Speedup is the geometric mean of paired five-run-median ratios. Payload reduction and the fraction of pairs favoring Halo are percentages; they are different statistics. Speedup parentheses show matched-population Halo t_geo in seconds.', emphasis={(0,3):'good',(5,4):'warn'})
    figure('15_payload_by_process','Pure MPI T1, n=max(1,p/32): family-median payload reduction (%) across fixed graphs at each p. Each A/H pair fixes graph/layout. Logical bytes exclude reductions/protocol overhead; this separates p effects from aggregate population differences.')
    para('**GPU Uniform savings are 0.0%, not missing.** Of 105 pairs, 91 save no contribution bytes: at p2 most partitions require all other-process sources. Large Uniform exchanges 102.4 MB globally per iteration under either strategy. This follows from graph dependencies, not GPU arithmetic.')
    para('**Payload savings do not determine runtime.** CPU Google gains 1.89× with 58.6% median payload reduction; synthetic families gain 1.19-1.23× in aggregate, while many cases favor Allgatherv. Packing, collective/reduction latency, imbalance, and device staging remain. Untimed Halo setup cannot cause timed-iteration slowdown.')
    table(['Graph; C=256','MPI p256/T1 (×)','MPI+OMP p64/T4 (×)','MPI+KK p64/T4 (×)'],[
        [DISPLAY[g],*[ratio_time(number(get(g,m,host_nodes=8,processes=256//t,threads=t,communication='Allgatherv')['solve_median_s'])/
                          number(get(g,m,host_nodes=8,processes=256//t,threads=t,communication='Halo')['solve_median_s']),
                          get(g,m,host_nodes=8,processes=256//t,threads=t,communication='Halo')['solve_median_s'])
                     for m,t in [('MPI',1),('MPI+OpenMP',4),('MPI+Kokkos OpenMP',4)]]] for g in BASELINE_GRAPHS],
        [125,120,125,130],caption='Paired Allgatherv/Halo time ratios on the same six inputs at eight nodes and 256 CPU cores. Each cell holds method, p, and T fixed; ratios above 1× favor Halo. Parentheses give Halo solve seconds; the method columns use different p but the same total C.', emphasis={(i,j):'good' if number(get(g,m,host_nodes=8,processes=256//t,threads=t,communication='Allgatherv')['solve_median_s'])>number(get(g,m,host_nodes=8,processes=256//t,threads=t,communication='Halo')['solve_median_s']) else 'warn' for i,g in enumerate(BASELINE_GRAPHS) for j,(m,t) in enumerate([('MPI',1),('MPI+OpenMP',4),('MPI+Kokkos OpenMP',4)],1)})

    heading('3.5.2 Default tuned selection versus fixed collective algorithms',3)
    para('**Automatic means rule-driven selection.** Main results keep dynamic_rules=false and algorithm IDs 0: MPI chooses from its compiled tree. Alltoallv uses communicator size p; Allgatherv also uses mean contribution bytes b=8N/p. Nodes n and threads T are not direct selector inputs: they affect p through p=nr and C=pT. This is not online network adaptation. Controls enable dynamic_rules=true and override only the named operation.')
    table(['Exchange / MPI operation','Available tuned IDs','Automatic inputs','Fixed controls here'],[
        ['Halo / Alltoallv','1 basic_linear; 2 pairwise','p only','Automatic; 1; 2'],
        ['Allgatherv / Allgatherv','1 GatherV+Bcast; 2 Bruck; 3 Ring; 4 neighbor exchange; 5 two_proc (p=2)','p and b=8N/p','Automatic; 2; 3']],
        [100,200,95,105],caption='Local guide to the policies compared below, for installed Open MPI 4.1.8. ID 0 preserves automatic selection; Allgatherv ID 1 is an implementation name, not the automatic mode. Full decision rules appear in Section 2.6.')

    para('Controls fix graph, layout, binary, affinity, and allocation within each policy comparison. Automatic uses dynamic_rules=0; forced runs use 1 plus one operation override (Section 2.6), not online learning.')
    policy_layouts=[]
    for graph in ('strong_uniform','strong_hub','strong_controlled'):
        for c in ((64,128,256) if graph=='strong_uniform' else (32,64,128)):
            t=1 if graph=='strong_uniform' else 4
            policy_layouts.append([DISPLAY[graph],c//32,c,c//t,t,
                'Halo' if t==1 else 'Allgatherv',
                ('pairwise' if c in (64,256) else 'basic_linear') if t==1 else ('Bruck' if c==32 else 'Ring'),
                'basic_linear; pairwise' if t==1 else 'Bruck; Ring',3])
    table(['Graph','Nodes n','Cores C','Processes p','Threads T','Exchange','Default-rule choice','Forced controls','Configs'],policy_layouts,
        [85,32,36,38,32,65,72,100,40],small=True,
        caption='Primary matched-policy matrix: nine Alltoallv configurations and eighteen Allgatherv configurations. Uniform uses pure MPI; Hub and Controlled use MPI+OpenMP. Each row tests the stated automatic choice plus both forced controls in one allocation, with C=pT=32n. Each configuration has one warm-up and five timed solves.')
    para('**59 unique settings:** 27 primary policies + 30 additional automatic contexts + 2 binding controls. Node-boundary context has 36 cases (2 graphs × 3 methods × 2 exchanges × 3 core counts); 6 overlap the primary matrix. Binding fixes n8,p256,T1,pairwise.')
    para('Both Alltoallv algorithms are tested. Allgatherv compares Bruck/Ring around p8→16; GatherV+Bcast and neighbor exchange are outside this targeted contrast, and two_proc applies only at p2 (complete menu: Section 2.6).')
    triples=[]
    for c in (64,128,256):
        selected={r['policy']:r for r in CONTROLS if r['graph']=='strong_uniform' and r['cores']==str(c)}
        assert set(selected)=={'default','a2av_linear','a2av_pairwise'}
        assert len({r['communication_bytes_per_iteration'] for r in selected.values()})==1
        triples.append((c,selected))
    figure('11_collective_policies','Large Uniform Halo; p=C=64/128/256. Automatic versus forced basic_linear/pairwise; five-run solve medians (s), whiskers=min..max (not confidence intervals). Policies share an allocation within p; allocations differ across p. Logarithmic process and time axes; labels give median seconds; green rings/bold labels mark the smallest median at each p. Markers are offset for visibility.')
    table(['Graph','n / p / T','Automatic (s)','basic_linear (s)','pairwise (s)','Auto/pairwise (×)','linear/pairwise (×)'],[
        ['Large Uniform',f'{c//32} / {c} / 1',*[fmt(r[k]['solve_median_s']) for k in ('default','a2av_linear','a2av_pairwise')],
         ratio_time(number(r['default']['solve_median_s'])/number(r['a2av_pairwise']['solve_median_s']),r['a2av_pairwise']['solve_median_s']),
         ratio_time(number(r['a2av_linear']['solve_median_s'])/number(r['a2av_pairwise']['solve_median_s']),r['a2av_pairwise']['solve_median_s'])]
        for c,r in triples], [90,65,60,60,60,82.5,82.5],small=True,
        caption='Uniform Halo / Alltoallv. Same graph, n/p/T and allocation within each row; five-run medians. Columns match the Allgatherv table: automatic time, two forced times, automatic/forced-2 gain and forced-1/forced-2 gain. Gain parentheses give forced-2 seconds. The p128 contrast is highlighted.',
        emphasis={(1,2):'warn',(1,3):'warn',(1,4):'good',(1,5):'good',(1,6):'good'})
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
    figure('12_allgatherv_policies','Hub/Controlled, MPI+OpenMP Allgatherv: automatic/Bruck/Ring at n1/2/4,C32/64/128,T4,p=C/4. Five-run solve medians (s), whiskers=min..max, common logarithmic time scale; labels give median seconds; green rings/bold labels mark the smallest observed median at each resource point. Policies share each resource-point allocation; markers offset for visibility.')
    table(['Graph','n / p / T','Automatic (s)','Bruck (s)','Ring (s)','Auto/Ring (×)','Bruck/Ring (×)'],[
        [DISPLAY[g],f'{c//32} / {c//4} / 4',*[fmt(r[k]['solve_median_s']) for k in ('default','agv_bruck','agv_ring')],
         ratio_time(number(r['default']['solve_median_s'])/number(r['agv_ring']['solve_median_s']),r['agv_ring']['solve_median_s']),
         ratio_time(number(r['agv_bruck']['solve_median_s'])/number(r['agv_ring']['solve_median_s']),r['agv_ring']['solve_median_s'])]
        for g,c,r in gather_controls], [90,65,60,60,60,82.5,82.5],small=True,
        caption='Hub/Controlled Allgatherv. Identical column roles and five-run statistic to the Alltoallv table; forced alternatives are now Bruck and Ring. C=pT=32/64/128, T=4. Gain parentheses give Ring seconds. Amber/green highlights the C64 Bruck/Ring contrast.',
        emphasis={(i,3):'warn' for i in (1,4)} | {(i,4):'good' for i in (1,4)})
    para('**At C64, Ring already matches automatic; Bruck is slower.** Hub: automatic/Ring/Bruck = 5.022/5.010/5.550 s; Controlled: 3.886/3.884/4.294 s. At C32 automatic matches Bruck. Unlike Uniform p128, switching back does not help this boundary.')
    context=[]
    for method,display in [('mpi','MPI'),('hybrid','MPI+OMP'),('mpi_kokkos','MPI+KK')]:
        for mode,label in [('allgather','Allgatherv'),('halo','Halo')]:
            ratios=[]
            for graph in ('strong_hub','strong_controlled'):
                a={int(r['cores']):r for r in CONTROLS if r['graph']==graph and r['implementation']==method
                   and r['communication']==mode and r['policy']=='default'}
                ratios.append(ratio_time(number(a[64]['solve_median_s'])/number(a[32]['solve_median_s']),a[64]['solve_median_s']))
            context.append([display,label,*ratios])
    table(['Method','Exchange','Hub: time64/time32 (×)','Controlled: time64/time32 (×)'],context,
        [100,100,150,150],caption='Default-policy node-boundary context from the same diagnostic matrix. Each ratio compares two nodes/64 cores with one node/32 cores. MPI uses T1 and MPI+OpenMP and MPI+Kokkos OpenMP T4; graph structure and policy are unchanged. Parentheses give the C64 solve seconds; values above 1 indicate slowdown, not speedup.')
    para('**The C32→64 context is nearly flat (0.93-1.04× time).** The hot block still belongs to one MPI+OpenMP process: Hub share 77.90→76.33%, Controlled 80.11→78.69%. Extra processes subdivide cold work while the second node adds progress/synchronization cost; the algorithm transition alone need not be harmful.')
    md.append('### 3.5.3 Complete diagnostic settings\n')
    complete.diagnostics(story,md)
    story.append(PageBreak())
    heading('3.6 Growing graph size together with resources',2)
    heading('3.6.1 Constant nominal work per CPU core',3)
    para('**Constant nominal work/core:** at C4/8/16/32/64/128/256, all methods use N=50,000C,E=800,000C. MPI p=C,T1; MPI+OpenMP and MPI+Kokkos OpenMP p=C/4,T4. The common C4 input/core reference permits matched efficiency comparisons; original rank-based p1 references remain in the data.')
    table(['Active cores C','Vertices N','Directed edges E','MPI p / T','MPI+OpenMP / MPI+Kokkos p / T'],[
        [c,f'{50000*c:,}',f'{800000*c:,}',f'{c} / 1',f'{c//4} / 4'] for c in (4,8,16,32,64,128,256)],
        [85,110,125,90,90],caption='Common growing-input CPU matrix. All three families and both Allgatherv/Halo settings use every row. Node count follows n=max(1,C/32); the per-core vertex and edge counts remain fixed.')
    figure('07_core_weak','N=50,000C,E=800,000C. Top: iteration time (ms); bottom: efficiency relative to own C4 iteration time (%). MPI T1, MPI+OpenMP and MPI+Kokkos OpenMP T4; A/H line styles and scales match across panels. Ideal growth gives flat time and 100% efficiency; points derive from five-run medians. Efficiency-panel labels give measured iteration ms, prefixed A/H (k=1,000 ms). Green rings mark lowest iteration time above and highest retained efficiency below; these are distinct criteria.')
    table(['Family','Method','Allgatherv efficiency (%)','Halo efficiency (%)'],[
        [f.title(),m,*[f"{number(next(r for r in GROWING if r['family']==f and r['method']==m and r['communication']==mode and r['active_cpu_threads']=='256')['matched_efficiency']):.2%} ({1000*number(next(r for r in GROWING if r['family']==f and r['method']==m and r['communication']==mode and r['active_cpu_threads']=='256')['seconds_per_iteration']):.3g} ms)"
                      for mode in ('Allgatherv','Halo')]]
        for f in ('uniform','hub','controlled') for m in ('MPI','MPI+OpenMP','MPI+Kokkos OpenMP')],
        [80,170,125,125],caption='Retained per-iteration efficiency at 256 CPU cores, using the common C=4 reference of the preceding figure. Each percentage divides its C4 iteration time by its C256 iteration time; no Serial baseline enters. Parentheses give the measured C256 iteration ms; bold compares Allgatherv/Halo within each row; green marks the best retained efficiency within each family, not the lowest absolute runtime.', paired=True)
    para('**Iteration time rises despite constant nominal work/core.** Uniform retains 1.9%-5.2% efficiency at C256; concentrated inputs retain less. Each method uses its own C4 time, so higher efficiency need not mean lower absolute time. With N proportional to p, Allgatherv traffic grows as p per process and p² globally; Hub/Controlled additionally retain edge imbalance.')
    figure('14_growing_communication','Growing Uniform, pure MPI T1: N=50,000p,E=800,000p. Left: logical payload (MB/rank/iteration); right: median MPI/wait divided by iterations (ms/iteration). Log-log axes; bytes exclude reductions/transport overhead. Green rings mark the lower payload/time at the same p; labels report MB/rank/iteration on the left and ms/iteration on the right.')
    para('**Reading the figure: rank means one MPI process; p is the number of ranks, not the number of threads.** Here pure MPI uses T=1, so p=128 also means 128 active CPU cores, configured across four nodes. Payload is the logical volume of contribution values delivered per iteration, averaged over ranks: MB/rank/iteration, with MB=10^6 bytes. It excludes reductions, protocol overhead and one-time request metadata; it is neither bandwidth nor elapsed time.')
    para('**The 128-rank Halo peak is communication-policy sensitive.** Halo MPI/wait is 17.28, 271.01 and 38.07 ms/iteration at p=64,128,256, while payload is nearly constant at 6.30,6.35,6.37 MB/rank/iteration. The installed Alltoallv rule switches pairwise -> basic_linear -> pairwise at these process counts. In the separate allocation-matched fixed Large Uniform control at p=128, automatic/basic_linear take 4.134/4.129 s, versus 0.886 s for pairwise (4.66x faster than automatic). This directly establishes sensitivity to the selected collective and supports the rule transition as an explanation for the growing-input peak. Request concurrency, MPI progress, buffering and shared-fabric conditions can also affect its amplitude; the fixed-input control uses N=12.8M, whereas the growing p128 point uses N=6.4M.')
    uniform_traffic=[r for r in TRAFFIC if r['family']=='uniform' and int(r['processes']) in (16,64,128,256)]
    table(['Processes p','Exchange','Payload (MB/rank/iteration)','MPI + waiting (ms/iteration)'],[
        [r['processes'],r['communication'],f"{number(r['counted_payload_bytes_per_rank'])/1e6:.2f}",f"{number(r['communication_ms_per_iteration']):.2f}"]
        for r in uniform_traffic],[75,100,160,165],caption='Matched contribution volume and communication duration for growing Uniform. Rows compare the two exchanges at the same graph and process count; per-iteration quantities, not total job traffic. Amber marks p256 costs despite bounded Halo bytes.', emphasis={(i,j):'warn' for i in (6,7) for j in (2,3)})
    para('**Nearly fixed Halo bytes still cost more at larger p.** Uniform payload stays near 6.4 MB/rank/iteration (Allgatherv reaches 102.0 MB at p256), yet Halo MPI/wait rises 17.28→38.07 ms from p64→256. Peer count, collective/reduction latency, packing, and contention matter beyond bytes; skewed inputs also wait for overloaded owners.')
    heading('3.6.2 Constant nominal work per GPU or MPI process',3)
    para("**GPU-node work/resource growth:** n=p=1→2, N=50,000p,E=800,000p, one GPU/process for device methods; CPU controls retain T1. Efficiency uses each method/exchange's p1 iteration time. This one-to-two-resource ratio has a different reference from CPU C4→256.")
    table(['Family','Method','Allgatherv efficiency (%)','Halo efficiency (%)'],[
        [family.title(),method.replace('Cuda','CUDA'),*[f"{number(next(r for r in WEAK if r['suite']=='gpu_node' and r['method']==method and r['family']==family and r['processes']=='2' and r['threads']=='1' and r['communication']==mode)['weak_efficiency_per_iteration']):.1%} ({1000*number(next(r for r in WEAK if r['suite']=='gpu_node' and r['method']==method and r['family']==family and r['processes']=='2' and r['threads']=='1' and r['communication']==mode)['seconds_per_iteration']):.3g} ms)"
                  for mode in ('Allgatherv','Halo')]]
        for family in ('uniform','hub','controlled') for method in ('MPI','MPI+OpenMP','MPI+CUDA','MPI+Kokkos Cuda')],
        [80,170,125,125],small=True,caption='GPU-node growth; same columns as the CPU table. n=p=1→2, T1; one GPU/device process. Cells give own-reference efficiency (p2 ms/iteration); CPU controls use no GPU. This p1 reference differs from CPU C4→C256. Bold marks the higher efficiency per row; green marks the highest efficiency per family.',paired=True)
    para('Standalone cases keep one node/device at both input sizes: 54 fixed-resource size controls, not resource-scaling efficiencies. They accompany the 318 scaled cases with their original layouts/reference definitions.')

    md.append('### 3.6.3 Complete growing-input matrices\n')
    complete.growing(story,md)
    complete.fixed_compact(story,md)
    story.append(PageBreak())
    cpu=OPTIMA['cpu_all'];device=OPTIMA['gpu_device_only'];controls=OPTIMA['gpu_with_cpu_controls']

    heading('4 Conclusions and insights')
    heading('4.1 What the experiments establish',2)
    para(f"**Workload structure determines the useful backend and parallel degree.** Standalone OpenMP/Kokkos OpenMP wins {cpu['method_counts'].get('OpenMP',0)+cpu['method_counts'].get('Kokkos OpenMP',0)}/45 CPU-node graphs; only {cpu['multirank_winners']} winning cases use multiple ranks. Standalone CUDA/Kokkos CUDA wins all device-only comparisons. Including GPU-node CPU controls gives OpenMP/CUDA/Kokkos CUDA {controls['method_counts'].get('OpenMP',0)}/{controls['method_counts'].get('CUDA',0)}/{controls['method_counts'].get('Kokkos CUDA',0)} wins. These are cross-budget optima; matched layouts separately show that larger balanced work benefits from extra participants, while small/skewed inputs favor fewer processes.")
    para('Edge ownership is the dominant structural constraint: equal vertex partitions leave 29%-30% of skewed edges on one process at p256. Local scheduling and p/T determine useful core participation; Halo does not rebalance ownership.')
    para('Communication volume alone predicts neither runtime nor multi-GPU benefit. Packing, collective schedules, synchronization, and staging remain; the matched p128 pairwise control improves Uniform by 4.66×, without establishing a universal best collective.')
    implications_start=len(story)
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
    heading('4.3 Study scope, timing definition and interpretation',2)
    para('The chosen scope is synchronous uniform-preference PageRank on the stated directed graphs, generator families and vertex orderings. Vanda comparisons use Platinum 8452Y and one/two A40 GPUs; the five C512 records form one small-graph example. Solver timing includes iteration work, MPI and staging, while excluding input, graph distribution and one-time setup. These choices define the question being measured.')
    para('Comparisons measure the implemented partitioning, scheduling and data-movement paths together, not intrinsic framework overhead. Five repeats describe within-allocation variability; cross-allocation placement, NUMA and shared-fabric conditions can also affect timings. Best-observed overview cells may use different resource budgets; fixed-layout and equal-core results provide the matched comparisons.')
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
    para('AI tools supported execution monitoring, result aggregation, and report refinement.')
    complete.finish()
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
    navigation_counter=[0]
    def navigation(flowable):
        if isinstance(flowable,Paragraph) and flowable.style.name in heading_styles:
            navigation_counter[0]+=1
            anchor='section_'+str(navigation_counter[0])
            doc.canv.bookmarkPage(anchor)
            doc.canv.addOutlineEntry(flowable.getPlainText(),anchor,level=0)
    doc.afterFlowable=navigation
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
