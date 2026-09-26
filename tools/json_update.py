import json,numpy as np,math,os,struct,sys
from shapely.geometry import Polygon,Point
F={f['id']:f for f in json.load(open('web/osm_all.json'))}
def chaikin(p,it=3):
    p=np.asarray(p,float)
    for _ in range(it):
        q=np.roll(p,-1,0);p=np.stack([0.75*p+0.25*q,0.25*p+0.75*q],1).reshape(-1,2)
    return p
def resample(poly,step):
    p=np.vstack([poly,poly[:1]]);seg=np.linalg.norm(np.diff(p,axis=0),axis=1);cum=np.concatenate([[0],np.cumsum(seg)]);n=max(8,int(round(cum[-1]/step)))
    t=np.linspace(0,cum[-1],n,endpoint=False);return np.stack([np.interp(t,cum,p[:,0]),np.interp(t,cum,p[:,1])],1)
def tris(f):
    b=open(f,'rb').read();l=struct.unpack('<I',b[12:16])[0];j=json.loads(b[20:20+l]);a=j['accessors']
    return sum(a[q['indices']]['count']//3 for m in j['meshes'] for q in m['primitives'])
def update(n,orig_tris,new_tris):
    H=json.load(open(f'orig/{n}.json'));P=json.load(open(f'params/{n}.json'));M=json.load(open(f'new/{n}_meta.json'))
    Z=np.load(f'dtm/{n}.npy');ZJ=json.load(open(f'dtm/{n}.json'))
    o=np.array(H['coordinates']['geo_origin_utm33']);th=math.radians(H['coordinates']['plusY_true_bearing_deg']);z0=H['model']['elevation_tee_masl']
    def dtm(x,y):
        E=o[0]+x*math.cos(th)+y*math.sin(th);N=o[1]-x*math.sin(th)+y*math.cos(th)
        c=(E-ZJ['E0'])/ZJ['res']-0.5;r=(ZJ['N1']-N)/ZJ['res']-0.5;c0=int(c);r0=int(r);fc=c-c0;fr=r-r0
        return float(Z[r0,c0]*(1-fc)*(1-fr)+Z[r0,c0+1]*fc*(1-fr)+Z[r0+1,c0]*(1-fc)*fr+Z[r0+1,c0+1]*fc*fr)-z0
    polys=[]
    for tid in P.get('osm_tees',[]):
        u=np.array(F[tid]['utm']);v=u-o
        m=np.stack([v[:,0]*math.cos(th)-v[:,1]*math.sin(th),v[:,0]*math.sin(th)+v[:,1]*math.cos(th)],1)
        if np.allclose(m[0],m[-1]): m=m[:-1]
        polys.append((tid,resample(chaikin(resample(m,1.0),3),1.2)))
    pin=np.array(H['pin']['blender'][:2]);notes=[]
    if 'markers' in P and M.get('tees'):
        tees=[]
        for t in M['tees']:
            t2={k:v for k,v in t.items() if k!='colour'};t2['colour']=t['colour'];tees.append(t2)
    else:
        tees=[]
        for t in H['tees']:
            c=np.array(t['center_blender'][:2]);t2=dict(t)
            hit=[(tid,p) for tid,p in polys if Polygon(p).buffer(-0.5).contains(Point(*c)) or Polygon(p).contains(Point(*c))]
            near=[(tid,p) for tid,p in polys if Polygon(p).distance(Point(*c))<6]
            if not hit and near and any(Polygon(p).distance(Point(*c))>0 for _,p in near):
                tid,p=min(near,key=lambda q:Polygon(q[1]).distance(Point(*c)))
                inner=Polygon(p).buffer(-1.5);q=inner.exterior.interpolate(inner.exterior.project(Point(*c)))
                c=np.array([q.x,q.y]);hit=[(tid,p)];notes.append(f'tee centre moved onto OSM tee {tid}')
            if hit:
                tid,p=hit[0];z=dtm(*c)
                t2['center_blender']=[round(float(c[0]),2),round(float(c[1]),2),round(z,2)]
                t2['center_gltf']=[round(float(c[0]),3),round(z,3),round(-float(c[1]),3)]
                t2['to_pin_m']=round(float(np.linalg.norm(pin-c)),1)
                if 'outline_blender' in t2 or True: t2['outline_blender']=[[round(float(x),2),round(float(y),2)] for x,y in p]
                t2['osm_way']=tid
            tees.append(t2)
    H['tees']=tees
    g=M.get('green') or {}
    if g:
        pz=g['pin_z'];H['pin']['blender'][2]=round(pz,3);H['pin']['gltf'][1]=round(pz,3)
        H['model']['elevation_change_tee_to_pin_m']=round(pz,2)
        if 'green_slope_max_drop_m' in H['model']: H['model']['green_slope_max_drop_m']=g['green_drop']
    H['stats']['glb_MB']=round(os.path.getsize(f'out/{n}/{n}.glb')/1e6,2)
    H['stats']['glb_plain_MB']=round(os.path.getsize(f'out/{n}/{n}_plain.glb')/1e6,2)
    H['stats']['rendered_tris']+=new_tris-orig_tris;H['stats']['trees']=M['trees']
    parts=[]
    if P.get('osm_tees'): parts.append('tee pads replaced by the OpenStreetMap tee outlines ('+', '.join('way '+t for t in P['osm_tees'])+'), cut into the terrain on the Kartverket DTM')
    if P.get('green_dtm'): parts.append('green and fringe laid on the Kartverket 1 m DTM (they were a flat plane) with a 3 m blend')
    if P.get('drop_trees'): parts.append(f"{len(P['drop_trees'])} lidar trees removed that the aerial image shows as open grass, path or hay")
    if parts: H['update_note']='2026-09: '+'; '.join(parts)+'.'
    ea=b'\\u00' in open(f'orig/{n}.json','rb').read()
    open(f'out/{n}/{n}.json','w',newline='').write(json.dumps(H,indent=1,ensure_ascii=ea).replace('\n','\r\n'))
    return H,notes
if __name__=='__main__':
    n=sys.argv[1];H,notes=update(n,tris(f'orig_glb/{n}_plain.glb'),tris(f'out/{n}/{n}_plain.glb'))
    print(n,notes,[ (t['center_blender'],t['to_pin_m'],t.get('osm_way')) for t in H['tees']],'pin',H['pin']['blender'][2])
