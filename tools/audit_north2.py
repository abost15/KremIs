import json,glob,numpy as np,math
from shapely.geometry import Polygon,Point,LineString
from shapely.validation import make_valid
from shapely.ops import unary_union
F=json.load(open('web/osm_all.json'))
def poly(p):
    try:
        P=Polygon(p)
        if not P.is_valid: P=make_valid(P)
        if P.geom_type=='GeometryCollection': P=unary_union([g for g in P.geoms if g.geom_type in('Polygon','MultiPolygon')])
        return None if P.is_empty else P
    except Exception: return None
OSM={k:[(f['id'],np.array(f['utm'])) for f in F if f['golf']==k and len(f['utm'])>3] for k in('tee','green','bunker','fairway')}
rows=[]
for jf in sorted(glob.glob('orig/byneset_north_[0-9][0-9].json')):
    n=jf.split('/')[-1][:-5];d=json.load(open(jf));A=json.load(open(f'audit/{n}.json'))
    o=np.array(d['coordinates']['geo_origin_utm33']);th=math.radians(d['coordinates']['plusY_true_bearing_deg'])
    def M(u):
        v=np.array(u)-o;return np.stack([v[:,0]*math.cos(th)-v[:,1]*math.sin(th), v[:,0]*math.sin(th)+v[:,1]*math.cos(th)],1)
    hl=LineString(d['hole_line_blender'])
    own=hl.buffer(55)   # the hole's own play corridor
    out={'hole':n,'par':d['par']}
    for mk,ok in (('SURF_Green','green'),('SURF_Tee','tee'),('SURF_Fairway','fairway')):
        best=[]
        for isl in A['surf'].get(mk,[]):
            if not isl['loops']: continue
            mp=poly(np.array(isl['loops'][0]));c=Point(*isl['c'][:2])
            if mp is None or not own.intersects(mp): continue
            frac=mp.intersection(own).area/mp.area
            if frac<0.4: continue      # mostly outside this hole's corridor
            b=(0,None)
            for i,u in OSM[ok]:
                op=poly(M(u))
                if op is None or not op.intersects(mp): continue
                iou=op.intersection(mp).area/op.union(mp).area
                if iou>b[0]: b=(round(iou,2),i)
            best.append((round(isl['area']),b[0],b[1]))
        out[ok]=best
    # bunkers: model vs ALL osm bunkers
    bs=[]
    for isl in A['surf'].get('SURF_Sand',[]):
        c=np.array(isl['c'][:2])
        if own.distance(Point(*c))>15: continue
        ds=[(float(np.linalg.norm(M(u).mean(0)-c)),i) for i,u in OSM['bunker']]
        dmin,bid=min(ds) if ds else (None,None)
        bs.append((round(isl['area']),round(dmin,1),bid))
    out['bunker']=bs
    # osm features inside the corridor with no model counterpart
    miss={}
    for ok,mk in (('tee','SURF_Tee'),('bunker','SURF_Sand'),('fairway','SURF_Fairway'),('green','SURF_Green')):
        mc=[np.array(x['c'][:2]) for x in A['surf'].get(mk,[])]
        m=[]
        for i,u in OSM[ok]:
            mm=M(u);op=poly(mm)
            if op is None or not own.intersects(op) or op.intersection(own).area/op.area<0.4: continue
            if not mc or min(np.linalg.norm(np.array(mc)-mm.mean(0),axis=1))>6: m.append((i,[round(x,1) for x in mm.mean(0)],round(op.area)))
        if m: miss[ok]=m
    out['missing']=miss
    rows.append(out)
json.dump(rows,open('audit/north_own.json','w'),indent=1)
for r in rows:
    flag=lambda L:['%d m2 iou %.2f %s'%(a,i,s) for a,i,s in L]
    print('==',r['hole'],'par',r['par'])
    print('   green  ',flag(r['green']));print('   tee    ',flag(r['tee']));print('   fairway',flag(r['fairway']))
    print('   bunker ',['%d m2 d=%.1f'%(a,dd) for a,dd,_ in r['bunker']])
    if r['missing']: print('   MISSING IN MODEL:',r['missing'])
