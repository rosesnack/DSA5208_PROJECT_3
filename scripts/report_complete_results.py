"""Complete in-report result atlas: every measured configuration is printed and indexed."""
import json
import math
from collections import defaultdict
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, PageBreak
from reportlab.graphics import renderPDF

INK=colors.HexColor('#172c3c'); BLUE=colors.HexColor('#16679b'); GREEN=colors.HexColor('#dceee7')
Q=(1,2,4,8,16,32)


def key(r):
    return tuple(str(r[x]) for x in ('graph','context','method','host_nodes','processes','threads','communication'))


def num(v):
    return f'{float(v):.3g}'


def txt(d,x,y,s,size=7,bold=False,color=INK,anchor='start'):
    d.add(String(x,y,str(s),fontName='Helvetica-Bold' if bold else 'Helvetica',fontSize=size,fillColor=color,textAnchor=anchor))


class Sheet(Flowable):
    def __init__(self,d,title):
        Flowable.__init__(self);self.d=d;self.width=485;self.height=d.height*.97;self.title=title
    def draw(self):
        name='complete_'+str(self.canv.getPageNumber())
        self.canv.bookmarkPage(name);self.canv.addOutlineEntry(self.title,name,level=0)
        self.canv.saveState();self.canv.scale(.97,.97)
        renderPDF.draw(self.d,self.canv,0,0)
        self.canv.restoreState()


class CompleteResults:
    def __init__(self,fixed,weak,controls,launcher,graphs,data,supplement):
        self.fixed=fixed;self.weak=weak;self.controls=controls;self.launcher=launcher;self.graphs=graphs;self.data=data
        self.lookup={key(r):r for r in fixed};self.seen=set();self.weak_seen=set();self.control_seen=set()
        self.chart_seen=set();self.sheets=0;self.supplement=supplement;self.supplement_seen=set()
    def row(self,g,context,m,n,p,t,mode):
        return self.lookup[(g,context,m,str(n),str(p),str(t),mode)]
    def add(self,story,md,d,title):
        story.append(PageBreak());story.append(Sheet(d,title));self.sheets+=1
        md.append('\n### '+title+'\n')
    def record(self,r,md):
        k=key(r);assert k not in self.seen,k;self.seen.add(k)
    def fixed_compact(self,story,md):
        """Two graph panels per portrait page; every median remains explicitly printed."""
        def ms(value):
            value=float(value)*1000
            return f'{value/1000:.3g}k' if value>=1000 else f'{value:.3g}'
        def paircell(d,x,y,w,rows,baseline,best):
            lo=min(float(r['solve_median_s']) for r in rows)
            for j,r in enumerate(rows):
                value=float(r['solve_median_s']);speed=baseline/value
                # Consistent Serial-relative color, deliberately light for dense numerical cells.
                t=min(abs(math.log2(speed))/6,1)
                color=colors.Color(1-.23*t,1-.08*t,1) if speed>=1 else colors.Color(1,1-.13*t,1-.23*t)
                if value==best:color=GREEN
                xx=x+j*w/len(rows);ww=w/len(rows)
                d.add(Rect(xx,y-1.4,ww-.4,7.6,fillColor=color,strokeColor=None))
                label=ms(value);fs=6.1
                while stringWidth(label,'Helvetica-Bold',fs)>ww-1.4:fs-=.1
                txt(d,xx+ww/2,y,label,fs,value==lo and len(rows)>1,anchor='middle')
                self.record(r,md)
                if r['method'].startswith('MPI'):self.chart_seen.add(key(r))
            if len(rows)==2:txt(d,x+w/2,y,'/',5.2,anchor='middle')
        ordered=sorted(self.graphs,key=lambda g:({'original':0,'canonical':1,'grid':2,'large':3}.get(g['origin'],4),{'google':0,'uniform':1,'hub':2,'controlled':3}.get(g['family'],4),int(g['vertices']),int(g['edges']),g['graph']))
        for start in range(0,len(ordered),2):
            d=Drawing(500,745)
            for slot,graph in enumerate(ordered[start:start+2]):
                g=graph['graph'];top=744-slot*374
                cpu=self.row(g,'cpu_node','Serial',1,1,1,'none');gpu=self.row(g,'gpu_node','Serial',1,1,1,'none')
                cpu_best=min(float(r['solve_median_s']) for r in self.fixed if r['graph']==g and r['context']=='cpu_node')
                gpu_best=min(float(r['solve_median_s']) for r in self.fixed if r['graph']==g and r['context']=='gpu_node')
                txt(d,0,top-9,('3.7 Complete fixed results | ' if start==0 and slot==0 else '')+g+' | all 434 configurations',9,True)
                txt(d,0,top-20,f"N={int(cpu['vertices']):,}; E={int(cpu['edges']):,}; I={cpu['iterations']}; Serial CPU/GPU-node={ms(cpu['solve_median_s'])}/{ms(gpu['solve_median_s'])} ms",7)
                self.record(cpu,md);self.record(gpu,md)
                txt(d,0,top-31,'Cells: A / H solve ms; k=1,000 ms. Bold: faster exchange. Green: fastest per graph/node class.',6.7)
                txt(d,0,top-43,'CPU standalone T',6.6,True)
                for j,t in enumerate(Q):txt(d,120+j*62,top-43,str(t),6.6,True,anchor='middle')
                for i,m in enumerate(('OpenMP','Kokkos OpenMP')):
                    yy=top-53-i*10;txt(d,0,yy,m,6.5)
                    for j,t in enumerate(Q):paircell(d,89+j*62,yy,61,[self.row(g,'cpu_node',m,1,1,t,'none')],float(cpu['solve_median_s']),cpu_best)
                txt(d,0,top-76,'MPI T=1; columns r',6.6,True)
                for j,r in enumerate(Q):txt(d,120+j*62,top-76,str(r),6.6,True,anchor='middle')
                for i,n in enumerate((1,2,4,8)):
                    yy=top-86-i*9;txt(d,0,yy,f'n={n}; p=n*r',6.5)
                    for j,r in enumerate(Q):paircell(d,89+j*62,yy,61,[self.row(g,'cpu_node','MPI',n,n*r,1,mode) for mode in ('Allgatherv','Halo')],float(cpu['solve_median_s']),cpu_best)
                txt(d,0,top-126,'r / T',6.5,True)
                for j,(m,n) in enumerate((m,n) for m in ('MPI+OpenMP','MPI+Kokkos OpenMP') for n in (1,2,4,8)):
                    txt(d,75+j*56,top-126,('MPI+OMP' if j<4 else 'MPI+KK')+f' n{n}',6.1,True,anchor='middle')
                for i,(r,t) in enumerate((r,t) for t in Q for r in Q if r*t<=32):
                    yy=top-136-i*7.7
                    if i in (6,11,15,18,20):d.add(Line(0,yy+6,500,yy+6,strokeColor=colors.HexColor('#ccd5dc'),strokeWidth=.35))
                    txt(d,0,yy,f'{r}/{t}',6.2,True)
                    for j,(m,n) in enumerate((m,n) for m in ('MPI+OpenMP','MPI+Kokkos OpenMP') for n in (1,2,4,8)):
                        paircell(d,47+j*56,yy,55,[self.row(g,'cpu_node',m,n,n*r,t,mode) for mode in ('Allgatherv','Halo')],float(cpu['solve_median_s']),cpu_best)
                txt(d,0,top-302,'GPU-node standalone',6.4,True)
                standalone=[('OMP'+str(t),'OpenMP',t) for t in Q]+[('CUDA','CUDA',1),('KK CUDA','Kokkos CUDA',1)]
                for j,(label,m,t) in enumerate(standalone):
                    x=90+j*51;txt(d,x+25,top-302,label,5.9,True,anchor='middle')
                    paircell(d,x,top-312,50,[self.row(g,'gpu_node',m,1,1,t,'none')],float(gpu['solve_median_s']),gpu_best)
                specs=[('MPI','MPI',1)]+[('MPI+OMP T'+str(t),'MPI+OpenMP',t) for t in (1,2,4,8)]+[('MPI+CU','MPI+CUDA',1),('MPI+KK CU','MPI+Kokkos CUDA',1)]
                txt(d,0,top-326,'GPU-node n=p',6.4,True)
                for j,(label,m,t) in enumerate(specs):txt(d,98+j*61,top-326,label,5.9,True,anchor='middle')
                for i,n in enumerate((1,2)):
                    yy=top-337-i*10;txt(d,0,yy,str(n),6.4,True)
                    for j,(label,m,t) in enumerate(specs):paircell(d,68+j*61,yy,60,[self.row(g,'gpu_node',m,n,n,t,mode) for mode in ('Allgatherv','Halo')],float(gpu['solve_median_s']),gpu_best)
                txt(d,0,top-360,'C=n*r*T; r*T<=32. KK=Kokkos (CPU: OpenMP). Blue: S>1; amber: S<1; saturation at 64x / 1/64x. GPU CPU controls use no GPU.',6.3)
                if slot==0:d.add(Line(0,top-369,500,top-369,strokeColor=BLUE,strokeWidth=.6))
            if start+1==len(ordered):
                txt(d,0,342,'3.7.1 Additional 512-core example | small Controlled graph',10,True)
                txt(d,0,326,'N=50,000; E=200,000; n=8, 64 active cores/node; p*T=512. Five-run solve medians.',7.5)
                txt(d,0,313,'These five cases are an additional small-input example, not a complete 512-core scaling curve.',7.3)
                for x,label in zip((0,150,195,235,303,370,434),('Implementation','p','T','Exchange','Solve ms','Speedup x','Efficiency %')):txt(d,x,290,label,7,True)
                for i,r in enumerate(self.supplement):
                    uid=tuple(r[k] for k in ('method','processes','threads','communication'))
                    assert uid not in self.supplement_seen;self.supplement_seen.add(uid)
                    yy=272-i*21
                    vals=[r['method'],r['processes'],r['threads'],r['communication'],ms(r['solve_median_s']),num(r['speedup']),num(float(r['efficiency'])*100)]
                    for x,label in zip((0,150,195,235,303,370,434),vals):txt(d,x,yy,label,7.5)
                txt(d,0,151,'Speedup uses the small graph CPU-node Serial, not the large graph above. Efficiency = speedup/512.',7.3)
                txt(d,0,137,'All five are slower than Serial: on this input, exchange and synchronization outweigh distributed work.',7.3)
                md.append('### 3.7.1 Additional 512-core example\n')
                md.append('| Method | p | T | Exchange | Median s | Speedup x | Efficiency |\n|---|---|---|---|---|---|---|')
                for r in self.supplement:md.append('| '+' | '.join(r[k] for k in ('method','processes','threads','communication','solve_median_s','speedup','efficiency'))+' |')
            title='3.7 Complete fixed-input heatmaps | '+', '.join(g['graph'] for g in ordered[start:start+2])
            self.add(story,md,d,title)
            md.append('| graph | node class | method | n | p | T | exchange | median s | speedup x | CPU efficiency |\n|---|---|---|---|---|---|---|---|---|---|')
            for graph in ordered[start:start+2]:
                for r in self.fixed:
                    if r['graph']==graph['graph']:md.append('| '+' | '.join(str(r[c]) for c in ('graph','context','method','host_nodes','processes','threads','communication','solve_median_s','speedup_vs_matched_serial','cpu_efficiency_vs_serial'))+' |')

    def growing(self,story,md):
        for family in ('uniform','hub','controlled'):
            d=Drawing(500,745);txt(d,0,731,'3.6.3 Complete growing-input results | '+family.title(),11,True)
            txt(d,0,715,'N=50,000*s; E=800,000*s. R: rank CPU s=p; C: core CPU s=p*T; G: GPU-node suite.',7)
            txt(d,0,704,'Cell: median solve ms / iteration ms / retained iteration efficiency %. - means not resource-scaled.',7)
            txt(d,0,693,'Bold: faster A/H at identical layout. Green: best retained efficiency at same family/suite/scale.',7)
            grouped=defaultdict(dict)
            for r in self.weak:
                if r['family']==family:
                    k=tuple(r[c] for c in ('suite','method','processes','threads','vertices','edges','iterations'))
                    grouped[k][r['communication']]=r
            cols=[0,22,123,148,184,210,306,402]
            for x,s in zip(cols,('Suite','Method','s','n/p/T','I','A: ms/ms/%','H: ms/ms/%','No MPI: ms/ms/%')):txt(d,x,678,s,6.1,True)
            for i,(k,modes) in enumerate(sorted(grouped.items(),key=lambda item:({'rank_cpu_regular':0,'core_cpu':1,'gpu_node':2}[item[0][0]],item[0][1],int(item[0][3]),int(item[0][4]),int(item[0][2])))):
                suite,m,p,t,N,E,I=k;y=665-i*8.65
                code={'rank_cpu_regular':'R','core_cpu':'C','gpu_node':'G'}[suite]
                n=(int(p) if suite=='gpu_node' and m.startswith('MPI') else 1 if suite=='gpu_node' else max(1,(int(p)*int(t)+31)//32))
                vals=[code,m.replace('Kokkos','KK').replace('Cuda','CUDA'),num(int(N)/50000),str(n)+'/'+p+'/'+t,I]
                for x,s in zip(cols,vals):txt(d,x,y,s,6)
                times=[float(r['seconds_per_iteration']) for r in modes.values()];best=min(times)
                for j,mode in enumerate(('Allgatherv','Halo','none')):
                    r=modes.get(mode)
                    if r is None:continue
                    uid=tuple(r[c] for c in ('suite','graph','method','processes','threads','communication'))
                    assert uid not in self.weak_seen;self.weak_seen.add(uid)
                    eff=r['weak_efficiency_per_iteration'] if r['resource_scaled']=='True' else '';eta=num(float(eff)*100) if eff else '-'
                    label=f"{num(float(r['solve_median_s'])*1000)}/{num(float(r['seconds_per_iteration'])*1000)}/{eta}"
                    peers=[z for z in self.weak if z['family']==family and z['suite']==suite and z['vertices']==N and z['resource_scaled']=='True']
                    if eff and peers and float(eff)==max(float(z['weak_efficiency_per_iteration']) for z in peers):
                        d.add(Rect(cols[5+j]-1,y-1,96,8.4,fillColor=GREEN,strokeColor=None))
                    txt(d,cols[5+j],y,label,5.9,float(r['seconds_per_iteration'])==best and mode!='none')
            txt(d,0,29,'n/p/T gives configured nodes/processes/threads: CPU n=max(1,ceil(p*T/32)); GPU distributed n=p.',6.8)
            txt(d,0,17,'Reference: R p1, C C4, G p1 at fixed method/T/exchange. G standalone n1 rows are size controls.',6.8)
            self.add(story,md,d,'3.6 Growing matrices | '+family)
            md.append('| suite | graph | method | p | T | exchange | N | E | I | median s | iteration s | efficiency |\n|---|---|---|---|---|---|---|---|---|---|---|---|')
            for r in self.weak:
                if r['family']==family:md.append('| '+' | '.join(r[c] for c in ('suite','graph','method','processes','threads','communication','vertices','edges','iterations','solve_median_s','seconds_per_iteration','weak_efficiency_per_iteration'))+' |')
    def diagnostics(self,story,md):
        d=Drawing(500,745);txt(d,0,731,'3.5.3 Complete allocation-matched diagnostic controls',11,True)
        txt(d,0,715,'All 57 collective settings + 2 launcher settings. Time ms: median [minimum, maximum] of five solves.',7)
        txt(d,0,703,'Bold: smallest median within same graph/implementation/layout/exchange/allocation. Green: same winner.',7)
        cols=[0,73,150,205,238,320,445]
        for x,s in zip(cols,('Graph','Implementation','n/p/T','Mode','Policy / launcher','Median [min,max] ms','MPI ms')):txt(d,x,684,s,6.2,True)
        allrows=self.controls+self.launcher
        for i,r in enumerate(allrows):
            y=670-i*10.6;uid=r['source_summary'];assert uid not in self.control_seen;self.control_seen.add(uid)
            peers=[z for z in allrows if all(z[k]==r[k] for k in ('graph','implementation','nodes','processes','threads','communication','performance_job'))]
            best=float(r['solve_median_s'])==min(float(z['solve_median_s']) for z in peers)
            if best:d.add(Rect(0,y-2,500,10.5,fillColor=GREEN,strokeColor=None))
            method={'hybrid':'MPI+OpenMP','mpi':'MPI','mpi_kokkos':'MPI+KK OMP'}[r['implementation']]
            vals=[r['graph'].replace('strong_',''),method,f"{r['nodes']}/{r['processes']}/{r['threads']}",'A' if r['communication']=='allgather' else 'H',r.get('launcher') or r['policy'],num(float(r['solve_median_s'])*1000)+' ['+num(float(r['solve_min_s'])*1000)+','+num(float(r['solve_max_s'])*1000)+']',num(float(r['communication_median_s'])*1000)]
            for x,s in zip(cols,vals):txt(d,x,y,s,6.1,best and x==320)
        txt(d,0,28,'Binding: native/explicit 2.975/3.111 s; ranges overlap. Independent policy allocation: p256 pairwise 3.563 s.',6.7)
        txt(d,0,16,'Placement, NUMA, fabric contention and peer progress can contribute; these controls remain separate from main curves.',6.7)
        self.add(story,md,d,'3.5.3 All diagnostic settings')
        md.append('| graph | method | n | p | T | exchange | policy | launcher | median s | min s | max s |\n|---|---|---|---|---|---|---|---|---|---|---|')
        for r in allrows:
            display={**r,'implementation':{'hybrid':'MPI+OpenMP','mpi':'MPI','mpi_kokkos':'MPI+Kokkos OpenMP'}[r['implementation']]}
            md.append('| '+' | '.join(display.get(c,'') for c in ('graph','implementation','nodes','processes','threads','communication','policy','launcher','solve_median_s','solve_min_s','solve_max_s'))+' |')
    def finish(self):
        expected={key(r) for r in self.fixed};assert self.seen==expected,(len(self.seen),len(expected))
        assert len(self.weak_seen)==len(self.weak)==372
        assert len(self.control_seen)==len(self.controls)+len(self.launcher)==59
        assert len(self.supplement_seen)==len(self.supplement)==5
        distributed={key(r) for r in self.fixed if r['method'].startswith('MPI')}
        assert distributed<=self.chart_seen,len(distributed-self.chart_seen)
        result={'fixed_configurations_visibly_printed':len(self.seen),'growing_configurations_visibly_printed':len(self.weak_seen),'diagnostic_configurations_visibly_printed':len(self.control_seen),'additional_512_configurations_visibly_printed':len(self.supplement_seen),'distributed_fixed_configurations_visualized':len(distributed),'complete_result_sheets':self.sheets,'missing_fixed_keys':[],'missing_growing_keys':[],'missing_control_keys':[]}
        (self.data/'report_full_coverage.json').write_text(json.dumps(result,indent=2)+'\n')
