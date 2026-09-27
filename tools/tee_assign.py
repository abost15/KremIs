import json,glob,numpy as np,math
from shapely.geometry import LineString,Point,Polygon
from shapely.validation import make_valid
F=json.load(open('web/osm_all.json'))
def poly(p):
    P=Polygon(p)
    if not P.is_valid: P=make_valid(P)
    return None if P.is_empty else P
TEE=[(f['id'],np.array(f['utm']),poly(np.array(f['utm']))) for f in F if f['golf']=='tee' and len(f['utm'])>3]
def mkU(o,th): return lambda x,y: np.array([o[0]+x*math.cos(th)+y*math.sin(th), o[1]-x*math.sin(th)+y*math.cos(th)])
H={}
for course in ('north','south'):
  for jf in sorted(glob.glob(f'orig/byneset_{course}_[0-9][0-9].json')):
    n=jf.split('/')[-1][:-5];d=json.load(open(jf))
    o=np.array(d['coordinates']['geo_origin_utm33']);th=math.radians(d['coordinates']['plusY_true_bearing_deg'])
    U=mkU(o,th)
    H[n]=dict(U=U,line=LineString([U(*p) for p in np.array(d['hole_line_blender'])]),cl=d['club_lengths_m_by_tee'],d=d,
              pin=U(*d['pin']['blender'][:2]))
def alen(hole,pt):
    L=H[hole]['line'];s=L.project(Point(*pt))
    return float(np.linalg.norm(pt-np.array(L.interpolate(s).coords[0]))+(L.length-s)), float(Point(*pt).distance(L))
# assign each OSM tee to the hole whose club length it best matches
assign={}
for tid,u,p in TEE:
    c=u.mean(0);best=[]
    for n in H:
        a,off=alen(n,c)
        if off>30: continue
        for j,q in enumerate(H[n]['cl']):
            best.append((abs(a-q),n,j,round(a),q,round(off)))
    best.sort()
    assign[tid]=best[:3]
print('=== OSM tee -> hole (best club-length fit, offset from line of play) ===')
for tid,b in sorted(assign.items(),key=lambda kv:(kv[1][0][1] if kv[1] else '')):
    if not b: print(f'{tid}: no hole fits');continue
    e=b[0];print(f"{tid}: {e[1][8:]} tee#{e[2]+1} len{e[3]}~{e[4]} off{e[5]}m  (d={e[0]:.0f})" + ('' if e[0]<12 else '   WEAK'))
print('\n=== what each hole JSON lists vs assignment ===')
for n in H:
    d=H[n]['d'];L=LineString(d['hole_line_blender'])
    mine=[tid for tid,b in assign.items() if b and b[0][1]==n and b[0][0]<12]
    listed=[]
    for t in d['tees']:
        c=np.array(t['center_blender'][:2]);cu=H[n]['U'](*c)
        hit=[tid for tid,u,p in TEE if p is not None and p.buffer(2.5).contains(Point(*cu))]
        listed.append(hit[0] if hit else 'noOSM@%s'%list(np.round(c,1)))
    wrong=[x for x in listed if x in assign and assign[x] and assign[x][0][1]!=n and assign[x][0][0]<12]
    missing=[x for x in mine if x not in listed]
    st=''
    if wrong: st+=' WRONG:'+','.join(f"{w}(={assign[w][0][1][8:]})" for w in wrong)
    if missing: st+=' MISSING:'+','.join(missing)
    print(f"{n[8:]:9s} club{len(H[n]['cl'])} listed{len(listed)} {listed}{st}")
