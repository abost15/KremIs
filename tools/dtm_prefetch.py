import json,numpy as np,subprocess,os,sys
from PIL import Image
def fetch(n):
    d=json.load(open(f'orig/{n}.json'));A=json.load(open(f'audit/{n}.json'))
    o=np.array(d['coordinates']['geo_origin_utm33']);th=np.radians(d['coordinates']['plusY_true_bearing_deg'])
    r=[x for x in A['objects'] if x['name']=='SURF_Rough'][0]
    lo=np.array(r['vmin'][:2]);hi=np.array(r['vmax'][:2])
    cs=np.array([[x,y] for x in (lo[0],hi[0]) for y in (lo[1],hi[1])])
    E=o[0]+cs[:,0]*np.cos(th)+cs[:,1]*np.sin(th);N=o[1]-cs[:,0]*np.sin(th)+cs[:,1]*np.cos(th)
    E0,N0,E1,N1=np.floor(E.min())-2,np.floor(N.min())-2,np.ceil(E.max())+2,np.ceil(N.max())+2
    res=0.5;tiles=[];W=int((E1-E0)/res);H=int((N1-N0)/res)
    Z=np.zeros((H,W),np.float32)
    step=1000  # px per tile
    for r0 in range(0,H,step):
        for c0 in range(0,W,step):
            w=min(step,W-c0);h=min(step,H-r0)
            e0=E0+c0*res;n1=N1-r0*res;e1=e0+w*res;n0=n1-h*res
            f=f'dtm/tile_{n}_{r0}_{c0}.tif'
            if not os.path.exists(f):
                subprocess.run(['curl','-s','-m','300','-o',f,f"https://wcs.geonorge.no/skwms1/wcs.hoyde-dtm-nhm-25833?service=WCS&version=1.0.0&request=GetCoverage&coverage=nhm_dtm_topo_25833&crs=EPSG:25833&bbox={e0},{n0},{e1},{n1}&width={w}&height={h}&format=GeoTIFF"])
            Z[r0:r0+h,c0:c0+w]=np.array(Image.open(f),np.float32)
    np.save(f'dtm/{n}.npy',Z);json.dump(dict(E0=E0,N1=N1,res=res,shape=Z.shape,o=o.tolist(),bearing=d['coordinates']['plusY_true_bearing_deg'],z0=d['model']['elevation_tee_masl']),open(f'dtm/{n}.json','w'))
    print(n,Z.shape,float(Z.min()),float(Z.max()))
for h in sys.argv[1:]: fetch(h)
