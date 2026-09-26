"""Byneset South: bring a hole model in line with the real course.

  * tees:   replace the model tee pads that overlap OpenStreetMap tee polygons
            (golf=tee, mapped 2024) with the OSM outlines, cut into the
            terrain; heights from the Kartverket DTM
  * greens: where the green/fringe was built as a flat plane, lay it on the
            DTM (real break) with a 3 m blend into the surroundings
  * trees:  remove listed lidar trees that the aerial image shows as open
            grass, and divide their baked shade out of the vertex colours

Run with Blender 5.2:
    blender -b --python fix_south.py -- in.blend hole.json dtm.npy dtm.json osm_all.json params.json out.blend meta.json
"""
import bpy, bmesh, json, math, sys
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.geometry import delaunay_2d_cdt

SRC, HOLE, DTM, DTMJ, OSM, PARAMS, DST, META = sys.argv[-8:]
bpy.ops.wm.open_mainfile(filepath=SRC)
obj = bpy.data.objects
H = json.load(open(HOLE)); P = json.load(open(PARAMS))
Z = np.load(DTM); ZJ = json.load(open(DTMJ))
O = np.array(H['coordinates']['geo_origin_utm33']); TH = math.radians(H['coordinates']['plusY_true_bearing_deg'])
Z0 = H['model']['elevation_tee_masl']
PIN = np.array(H['pin']['blender'][:2])
log = []
def say(*a):
    s = ' '.join(str(x) for x in a); print(s); log.append(s)

# ------------------------------------------------------------------ frames / DTM
def to_utm(xy):
    xy = np.atleast_2d(xy)
    return np.stack([O[0] + xy[:, 0] * math.cos(TH) + xy[:, 1] * math.sin(TH),
                     O[1] - xy[:, 0] * math.sin(TH) + xy[:, 1] * math.cos(TH)], 1)
def to_model(utm):
    v = np.atleast_2d(utm) - O
    return np.stack([v[:, 0] * math.cos(TH) - v[:, 1] * math.sin(TH), v[:, 0] * math.sin(TH) + v[:, 1] * math.cos(TH)], 1)
def dtm(xy):
    """DTM height (model z) at model xy, bilinear on the 0.5 m grid."""
    u = to_utm(xy); r = ZJ['res']
    c = (u[:, 0] - ZJ['E0']) / r - 0.5; rr = (ZJ['N1'] - u[:, 1]) / r - 0.5
    c0 = np.clip(np.floor(c).astype(int), 0, Z.shape[1] - 2); r0 = np.clip(np.floor(rr).astype(int), 0, Z.shape[0] - 2)
    fc = np.clip(c - c0, 0, 1); fr = np.clip(rr - r0, 0, 1)
    z = (Z[r0, c0] * (1 - fc) * (1 - fr) + Z[r0, c0 + 1] * fc * (1 - fr) +
         Z[r0 + 1, c0] * (1 - fc) * fr + Z[r0 + 1, c0 + 1] * fc * fr)
    return z - Z0
def dtm_normal(xy, h=0.5):
    xy = np.atleast_2d(xy)
    gx = (dtm(xy + [h, 0]) - dtm(xy - [h, 0])) / (2 * h); gy = (dtm(xy + [0, h]) - dtm(xy - [0, h])) / (2 * h)
    n = np.c_[-gx, -gy, np.ones(len(xy))]; return n / np.linalg.norm(n, axis=1)[:, None]

# ------------------------------------------------------------------ 2D helpers
def chaikin(p, it=3):
    p = np.asarray(p, float)
    for _ in range(it):
        q = np.roll(p, -1, 0); p = np.stack([0.75 * p + 0.25 * q, 0.25 * p + 0.75 * q], 1).reshape(-1, 2)
    return p
def resample(poly, step):
    p = np.vstack([poly, poly[:1]]); seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)]); n = max(8, int(round(cum[-1] / step)))
    t = np.linspace(0, cum[-1], n, endpoint=False)
    return np.stack([np.interp(t, cum, p[:, 0]), np.interp(t, cum, p[:, 1])], 1)
def inside(poly, pts):
    pts = np.atleast_2d(pts); x, y = pts[:, 0], pts[:, 1]; res = np.zeros(len(pts), bool); j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]; xj, yj = poly[j]
        res ^= ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi); j = i
    return res
def seg_dist(poly, pts):
    pts = np.atleast_2d(pts); d = np.full(len(pts), np.inf)
    for p0, p1 in zip(poly, np.roll(poly, -1, 0)):
        v = p1 - p0; w = pts - p0; t = np.clip((w @ v) / (v @ v), 0, 1)
        d = np.minimum(d, np.linalg.norm(w - np.outer(t, v), axis=1))
    return d
def near_any(polys, xy, d):
    m = np.zeros(len(xy), bool)
    for p in polys: m |= inside(p, xy) | (seg_dist(p, xy) < d)
    return m
def grid_in(poly, step, margin, holes=()):
    lo, hi = poly.min(0), poly.max(0)
    gx, gy = np.meshgrid(np.arange(lo[0] + step / 2, hi[0], step), np.arange(lo[1] + step / 2, hi[1], step))
    g = np.stack([gx.ravel(), gy.ravel()], 1); g = g[inside(poly, g) & (seg_dist(poly, g) > margin)]
    for h in holes: g = g[~inside(h, g) & (seg_dist(h, g) > margin)]
    return g
def ccw(p):
    a = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]); return p if a > 0 else p[::-1]
def islands(bm):
    bm.faces.ensure_lookup_table(); seen = set(); out = []
    for f in bm.faces:
        if f.index in seen: continue
        st = [f]; isl = []; seen.add(f.index)
        while st:
            g = st.pop(); isl.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen: seen.add(h.index); st.append(h)
        out.append(isl)
    return out
def uv_fit(me):
    uv = me.uv_layers.active.data; L = []; U = []
    for p in me.polygons[:4000]:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co; L.append([v.x, v.y, 1]); U.append(uv[li].uv[:])
    return np.linalg.lstsq(np.array(L), np.array(U), rcond=None)[0]   # 3x2

# ------------------------------------------------------------------ trees / shade
DROP = P.get('drop_trees', [])
TREES = {o.name: (o.location.x, o.location.y) for o in obj if o.name.startswith('TREE_')}
def shade_curve():
    me = obj['SURF_Rough'].data
    c = np.array([d.color[:] for d in me.attributes['Col'].data]); lv = np.array([l.vertex_index for l in me.loops])
    co = np.array([v.co[:2] for v in me.vertices]); vc = np.zeros((len(co), 3)); n = np.zeros(len(co))
    np.add.at(vc, lv, c[:, :3]); np.add.at(n, lv, 1); ok = n > 0; lum = (vc[ok] / n[ok, None]).mean(1); xy = co[ok]
    T = np.array(list(TREES.values())) if TREES else np.zeros((0, 2))
    if len(T) == 0: return np.array([0.5, 15]), np.array([1.0, 1.0])
    dall = np.array([np.min(np.linalg.norm(T - p, axis=1)) for p in xy])
    ref = np.median(lum[dall > 15]); D = np.arange(0.5, 15, 1.0)
    S = np.array([np.median(lum[(dall >= d - .5) & (dall < d + .5)]) / ref if ((dall >= d - .5) & (dall < d + .5)).sum() > 5 else 1.0 for d in D])
    return D, np.minimum(np.maximum.accumulate(np.clip(S, 0.3, 1.0)), 1.0)
SH_D, SH_S = shade_curve()
def shade(xy, trees):
    xy = np.atleast_2d(xy)
    if len(trees) == 0: return np.ones(len(xy))
    d = np.linalg.norm(xy[:, None, :] - np.asarray(trees)[None], axis=2)
    return np.prod(np.interp(d, SH_D, SH_S, left=SH_S[0], right=1.0), axis=1)
KEPT = np.array([p for n, p in TREES.items() if n not in DROP]).reshape(-1, 2)
GONE = np.array([p for n, p in TREES.items() if n in DROP]).reshape(-1, 2)

# ------------------------------------------------------------------ OSM tees
OSMF = {f['id']: f for f in json.load(open(OSM))}
NEWTEES = []
for tid in P.get('osm_tees', []):
    m = to_model(np.array(OSMF[tid]['utm']))
    if np.allclose(m[0], m[-1]): m = m[:-1]
    t = ccw(resample(chaikin(resample(m, 1.0), 3), 1.2)); NEWTEES.append(t)
    say('osm tee', tid, 'area', round(0.5 * abs(np.sum(t[:, 0] * np.roll(t[:, 1], -1) - np.roll(t[:, 0], -1) * t[:, 1])), 1))

GROUND = [n for n in ('SURF_Rough', 'SURF_Semi', 'SURF_Hay', 'SURF_Fairway', 'SURF_Field') if n in obj]

def rebuild_ground(regions, holes_polys, freed, BUF=4.0):
    """Cut `holes_polys` (new tee outlines) into the joined ground surfaces
    and re-triangulate everything within BUF of `regions`; heights from DTM."""
    names = [n for n in GROUND]
    objs = [obj[n] for n in names]
    info = {}
    for o in objs:
        info[o.name] = dict(mesh=o.data.name, cols=list(o.users_collection), props=o['user_properties'].to_dict() if 'user_properties' in o else None,
                            uv=uv_fit(o.data), mat=o.data.materials[0])
    base = objs[0]
    with bpy.context.temp_override(active_object=base, selected_editable_objects=objs):
        bpy.ops.object.join()
    me = base.data
    matnames = [m.name for m in me.materials]
    src_of_mat = {i: [n for n in names if info[n]['mat'].name == mn][0] for i, mn in enumerate(matnames)}
    bm = bmesh.new(); bm.from_mesh(me)
    nv = len(bm.verts); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-3); say('ground joined', names, 'welded', nv - len(bm.verts))
    bm.to_mesh(me); bm.free(); me.update()
    corner_n = np.array([n.vector[:] for n in me.corner_normals])
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    uvl = bm.loops.layers.uv['UVMap']; coll = bm.loops.layers.color.get('Col') or bm.loops.layers.float_color.get('Col')
    newl = bm.faces.layers.int.new('is_new')
    vn_old = {}
    for li, l in enumerate(me.loops): vn_old.setdefault(l.vertex_index, []).append(corner_n[li])
    vn_old = {k: np.mean(v, 0) for k, v in vn_old.items()}
    vcol = {}
    for f in bm.faces:
        for l in f.loops: vcol.setdefault((f.material_index, l.vert.index), []).append(tuple(l[coll]))
    vcol = {k: np.mean(v, 0) for k, v in vcol.items()}
    vxy = np.array([v.co[:2] for v in bm.verts])
    region_v = near_any(regions, vxy, BUF)
    # boundary verts of the holes the removed tee pads leave behind are not
    # protected: those holes are rebuilt too
    bvx = np.array([v.index for v in bm.verts if v.is_boundary])
    freed_m = near_any(freed, vxy[bvx], 0.6) if len(bvx) else np.zeros(0, bool)
    pre_b = set(bvx[~freed_m].tolist())
    say('ground boundary verts freed (old tee holes)', int(freed_m.sum()))
    kill = [f for f in bm.faces if region_v[[v.index for v in f.verts]].any() and not any(v.index in pre_b for v in f.verts)]
    # material of killed faces, for the refill
    kc = np.array([f.calc_center_median()[:2] for f in kill]); km = np.array([f.material_index for f in kill])
    kkd = KDTree(len(kill))
    for i, c in enumerate(kc): kkd.insert((c[0], c[1], 0), i)
    kkd.balance()
    ckd = {}
    for mi in set(k[0] for k in vcol):
        ids = [k[1] for k in vcol if k[0] == mi]; t = KDTree(len(ids))
        for i in ids: t.insert((vxy[i][0], vxy[i][1], 0), i)
        t.balance(); ckd[mi] = t
    keep_bv = {bm.verts[i] for i in pre_b}
    pre_bedges = {e for e in bm.edges if e.is_boundary and e.verts[0].index in pre_b and e.verts[1].index in pre_b}
    old_key = {(round(x, 4), round(y, 4)): i for i, (x, y) in enumerate(vxy)}
    bmesh.ops.delete(bm, geom=kill, context='FACES'); bm.verts.ensure_lookup_table()
    bedges = [e for e in bm.edges if e.is_boundary and e not in pre_bedges]
    assert not any(v in keep_bv for e in bedges for v in e.verts)
    adj = {}
    for e in bedges:
        a, b = e.verts; adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    loops = []; used = set()
    for s in list(adj):
        if s in used: continue
        lp = [s]; used.add(s); prev = None; cur = s
        while True:
            nx = [n for n in adj[cur] if n is not prev and n not in used]
            if not nx: break
            prev, cur = cur, nx[0]; lp.append(cur); used.add(cur)
        loops.append(lp)
    say('ground faces removed', len(kill), 'hole loops', [len(l) for l in loops])
    made_all = 0
    for lp in loops:
        L = np.array([(v.co.x, v.co.y) for v in lp])
        hs = [h for h in holes_polys if inside(L, h[:1])[0]]
        g = grid_in(L, 2.0, 1.0, hs)
        pts = [tuple(p) for p in L]; faces_in = [list(range(len(L)))]; off = len(pts)
        for h in hs:
            pts += [tuple(p) for p in h]; faces_in.append(list(range(off, off + len(h)))); off += len(h)
        pts += [tuple(p) for p in g]
        ov, _, of, orig, _, _ = delaunay_2d_cdt([Vector(p) for p in pts], [], faces_in, 0, 1e-6, True)
        zz = dtm(np.array([(v.x, v.y) for v in ov]))
        bv = []
        for i, v in enumerate(ov):
            s = orig[i]
            bv.append(lp[s[0]] if s and s[0] < len(L) else bm.verts.new((v.x, v.y, zz[i])))
        for f in of:
            c = np.mean([(ov[i].x, ov[i].y) for i in f], 0)
            if not inside(L, c[None])[0] or any(inside(h, c[None])[0] for h in hs): continue
            vs = [bv[i] for i in f]
            if len(set(vs)) < 3: continue
            try: nf = bm.faces.new(vs)
            except ValueError: continue
            mi = int(km[kkd.find((c[0], c[1], 0))[1]]); nf.material_index = mi; nf.smooth = True; nf[newl] = 1
            U = info[src_of_mat[mi]]['uv']
            for l in nf.loops:
                l[uvl].uv = tuple(np.array([l.vert.co.x, l.vert.co.y, 1]) @ U)
                j = ckd[mi].find((l.vert.co.x, l.vert.co.y, 0))[1]; l[coll] = tuple(vcol[(mi, j)])
            made_all += 1
    say('ground faces added', made_all)
    bm.to_mesh(me); bm.free(); me.update()
    isnew = np.array([a.value for a in me.attributes['is_new'].data], bool)
    cn = np.array([n.vector[:] for n in me.corner_normals]); lv = np.array([l.vertex_index for l in me.loops])
    pol = np.empty(len(me.loops), int)
    for p in me.polygons: pol[p.loop_start:p.loop_start + p.loop_total] = p.index
    vco = np.array([v.co[:] for v in me.vertices])
    idx = np.nonzero(isnew[pol])[0]; dn = dtm_normal(vco[lv[idx], :2])
    for k, li in enumerate(idx):
        oi = old_key.get((round(vco[lv[li], 0], 4), round(vco[lv[li], 1], 4)))
        cn[li] = vn_old[oi] if oi is not None and oi in vn_old else dn[k]
    me.normals_split_custom_set([tuple(n) for n in cn]); me.attributes.remove(me.attributes['is_new'])
    # shade from dropped trees out of the colours
    fix_colours(me)
    # split back
    for mi, mn in enumerate(matnames):
        n = src_of_mat[mi]
        if n == base.name: continue
        m2 = me.copy(); m2.name = info[n]['mesh']
        b = bmesh.new(); b.from_mesh(m2)
        bmesh.ops.delete(b, geom=[f for f in b.faces if f.material_index != mi], context='FACES')
        for f in b.faces: f.material_index = 0
        b.to_mesh(m2); b.free(); m2.materials.clear(); m2.materials.append(info[n]['mat']); m2.update()
        o2 = bpy.data.objects.new(n, m2)
        for c in info[n]['cols']: c.objects.link(o2)
        if info[n]['props'] is not None: o2['user_properties'] = info[n]['props']
    bmi = [i for i, mn in enumerate(matnames) if src_of_mat[i] == base.name][0]
    b = bmesh.new(); b.from_mesh(me)
    bmesh.ops.delete(b, geom=[f for f in b.faces if f.material_index != bmi], context='FACES')
    for f in b.faces: f.material_index = 0
    b.to_mesh(me); b.free(); me.materials.clear(); me.materials.append(info[base.name]['mat']); me.update()
    base.name = names[0]

def fix_colours(me):
    if len(GONE) == 0: return
    ca = me.attributes['Col']; cc = np.array([d.color[:] for d in ca.data])
    lv = np.array([l.vertex_index for l in me.loops]); vco = np.array([v.co[:2] for v in me.vertices]); cxy = vco[lv]
    near = np.min(np.linalg.norm(cxy[:, None, :] - GONE[None], axis=2), 1) < 15
    if not near.any(): return
    f = shade(cxy[near], GONE); cc[near, :3] = np.clip(cc[near, :3] / f[:, None], 0, 1)
    dk = np.min(np.linalg.norm(cxy[:, None, :] - KEPT[None], axis=2), 1) if len(KEPT) else np.full(len(cxy), 1e9)
    for t in GONE:
        d = np.linalg.norm(cxy - t, axis=1); ring = (d > 8) & (d < 14) & (dk > 8)
        if ring.sum() < 10: continue
        med = np.median(cc[ring, :3], 0); m = (d < 8) & (cc[:, :3].mean(1) < med.mean())
        w = (1 - (d[m] / 8) ** 2)[:, None]; cc[m, :3] = cc[m, :3] * (1 - w) + med * w
    for d_, c in zip(ca.data, cc): d_.color = c

# marker heights above the ground they stand on, measured before any edit
_dg0 = bpy.context.evaluated_depsgraph_get()
_gb0 = [BVHTree.FromObject(obj[n], _dg0) for n in ('SURF_Tee', 'SURF_Rough') if n in obj]
MARK_LIFT = {}
for o in obj:
    if o.name.startswith('TEE_Marker_'):
        v = np.array([x.co[:] for x in o.data.vertices]); c = v.mean(0); hz = None
        for b in _gb0:
            h = b.ray_cast(Vector((c[0], c[1], 500)), Vector((0, 0, -1)))
            if h[0] is not None and (hz is None or h[0].z > hz): hz = h[0].z
        MARK_LIFT[o.name] = v[:, 2].min() - (hz if hz is not None else v[:, 2].min())

# ------------------------------------------------------------------ 1. tees
tee_changed = False
if NEWTEES:
    teeo = obj['SURF_Tee']; tme = teeo.data
    bm = bmesh.new(); bm.from_mesh(tme)
    colt = bm.loops.layers.color.get('Col') or bm.loops.layers.float_color.get('Col'); uvt = bm.loops.layers.uv['UVMap']
    tuv = uv_fit(tme)
    removed = []; removed_exact = []; old_cols = []
    for isl in islands(bm):
        xy = np.array([(v.co.x, v.co.y) for f in isl for v in f.verts])
        hit = any(inside(t, xy).any() or near_any([t], xy.mean(0)[None], 1.0)[0] for t in NEWTEES)
        extra = any(np.hypot(*(xy.mean(0) - np.array(c))) < 3 for c in P.get('remove_tees', []))
        if hit or extra:
            lo, hi = xy.min(0), xy.max(0); removed.append(np.array([[lo[0], lo[1]], [hi[0], lo[1]], [hi[0], hi[1]], [lo[0], hi[1]]]))
            removed_exact.append(xy)
            old_cols += [tuple(l[colt]) for f in isl for l in f.loops]
            bmesh.ops.delete(bm, geom=isl, context='FACES')
    if not old_cols: old_cols = [tuple(l[colt]) for f in bm.faces for l in f.loops]
    say('model tee pads removed', len(removed))
    base = np.mean(old_cols, 0)
    newt = bm.faces.layers.int.new('is_new')
    for T in NEWTEES:
        g = grid_in(T, 1.2, 0.6)
        pts = [tuple(p) for p in T] + [tuple(p) for p in g]
        ov, _, of, _, _, _ = delaunay_2d_cdt([Vector(p) for p in pts], [], [list(range(len(T)))], 0, 1e-6, True)
        zz = dtm(np.array([(v.x, v.y) for v in ov]))
        bv = [bm.verts.new((v.x, v.y, zz[i])) for i, v in enumerate(ov)]
        for f in of:
            c = np.mean([(ov[i].x, ov[i].y) for i in f], 0)
            if not inside(T, c[None])[0]: continue
            try: nf = bm.faces.new([bv[i] for i in f])
            except ValueError: continue
            nf.smooth = True; nf[newt] = 1
            for l in nf.loops:
                x, y = l.vert.co.x, l.vert.co.y
                l[uvt].uv = tuple(np.array([x, y, 1]) @ tuv)
                n = 0.5 * math.sin(0.61 * x + 0.23 * y) + 0.35 * math.sin(0.17 * x - 0.53 * y + 1.3) + 0.25 * math.sin(0.9 * y + 0.4 * x + 2.1)
                c4 = base.copy(); c4[:3] = np.clip(c4[:3] * (1 + 0.035 * n) * shade(np.array([x, y]), KEPT)[0], 0, 1); l[colt] = tuple(c4)
    bm.to_mesh(tme); bm.free(); tme.update()
    isnew = np.array([a.value for a in tme.attributes['is_new'].data], bool)
    cn = np.array([n.vector[:] for n in tme.corner_normals]); lv = np.array([l.vertex_index for l in tme.loops])
    pol = np.empty(len(tme.loops), int)
    for p in tme.polygons: pol[p.loop_start:p.loop_start + p.loop_total] = p.index
    vco = np.array([v.co[:] for v in tme.vertices]); idx = np.nonzero(isnew[pol])[0]
    cn[idx] = dtm_normal(vco[lv[idx], :2]); tme.normals_split_custom_set([tuple(n) for n in cn]); tme.attributes.remove(tme.attributes['is_new'])
    rebuild_ground(NEWTEES + removed, NEWTEES, removed)
    tee_changed = True
elif len(GONE):
    fix_colours(obj['SURF_Rough'].data)

# ------------------------------------------------------------------ 2. trees
for n in DROP:
    if n in obj: bpy.data.objects.remove(obj[n], do_unlink=True)
for o in list(obj):
    if o.name.startswith('TREE_') and any(inside(t, np.array([[o.location.x, o.location.y]]))[0] for t in NEWTEES):
        say('tree on new tee removed', o.name); bpy.data.objects.remove(o, do_unlink=True)
say('trees removed', len(DROP))
if 'GRASS_Tufts' in obj and NEWTEES:
    gt = obj['GRASS_Tufts']; hay = obj.get('SURF_Hay')
    hb = BVHTree.FromObject(hay, bpy.context.evaluated_depsgraph_get()) if hay else None
    bm = bmesh.new(); bm.from_mesh(gt.data); drop = []
    for isl in islands(bm):
        c = np.mean([(v.co.x, v.co.y) for f in isl for v in f.verts], 0)
        if any(inside(t, c[None])[0] or seg_dist(t, c[None])[0] < 5.0 for t in NEWTEES):
            if any(inside(t, c[None])[0] for t in NEWTEES) or hb is None or hb.ray_cast(Vector((c[0], c[1], 500)), Vector((0, 0, -1)))[0] is None:
                drop += isl
    bmesh.ops.delete(bm, geom=drop, context='FACES'); bm.to_mesh(gt.data); bm.free(); say('grass tuft faces removed', len(drop))

# ------------------------------------------------------------------ 3. greens on the DTM
green_info = {}
if P.get('green_dtm'):
    gp = []
    for n in ('SURF_Green', 'SURF_Fringe'):
        bm = bmesh.new(); bm.from_mesh(obj[n].data)
        for isl in islands(bm):
            xy = np.array([(v.co.x, v.co.y) for f in isl for v in f.verts])
            if np.min(np.linalg.norm(xy - PIN, axis=1)) < 20:
                be = {e for f in isl for e in f.edges if e.is_boundary}
                adj = {}
                for e in be:
                    a, b = e.verts; adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
                best = []
                used = set()
                for s in adj:
                    if s in used: continue
                    lp = [s]; used.add(s); cur = s; prev = None
                    while True:
                        nx = [q for q in adj[cur] if q is not prev and q not in used]
                        if not nx: break
                        prev, cur = cur, nx[0]; lp.append(cur); used.add(cur)
                    if len(lp) > len(best): best = lp
                gp.append(np.array([(v.co.x, v.co.y) for v in best]))
        bm.free()
    say('green/fringe outlines', len(gp))
    BLEND = 3.0
    terr = [n for n in ('SURF_Green', 'SURF_Fringe', 'SURF_Rough', 'SURF_Semi', 'SURF_Fairway', 'SURF_Hay', 'SURF_Sand', 'SURF_Field', 'SURF_Gravel', 'SURF_Road') if n in obj]
    # displacement for all non-sand vertices; sand follows its nearest non-sand vertex
    allv = {}
    for n in terr:
        allv[n] = np.array([v.co[:] for v in obj[n].data.vertices])
    def weight(xy):
        w = np.zeros(len(xy)); insd = np.zeros(len(xy), bool); d = np.full(len(xy), np.inf)
        lo = np.min([p.min(0) for p in gp], 0) - BLEND - 1; hi = np.max([p.max(0) for p in gp], 0) + BLEND + 1
        m = np.all((xy >= lo) & (xy <= hi), 1)
        for p in gp:
            insd[m] |= inside(p, xy[m]); d[m] = np.minimum(d[m], seg_dist(p, xy[m]))
        t = np.clip(1 - d / BLEND, 0, 1); w = np.where(insd, 1.0, t * t * (3 - 2 * t)); return w
    disp = {}
    nsxy = []; nsd = []
    for n in terr:
        if n == 'SURF_Sand': continue
        V = allv[n]; w = weight(V[:, :2]); d = np.zeros(len(V)); k = w > 0
        d[k] = w[k] * (dtm(V[k, :2]) - V[k, 2]); disp[n] = (w, d)
        nsxy.append(V[k, :2]); nsd.append(d[k])
    nsxy = np.vstack(nsxy) if nsxy else np.zeros((0, 2)); nsd = np.concatenate(nsd) if nsd else np.zeros(0)
    if 'SURF_Sand' in terr and len(nsxy):
        V = allv['SURF_Sand']; w = weight(V[:, :2]); d = np.zeros(len(V))
        kd = KDTree(len(nsxy))
        for i, p in enumerate(nsxy): kd.insert((p[0], p[1], 0), i)
        kd.balance()
        for i in np.nonzero(w > 0)[0]:
            _, j, dist = kd.find((V[i, 0], V[i, 1], 0))
            if dist < 3: d[i] = nsd[j]
        disp['SURF_Sand'] = (w, d)
    for n, (w, d) in disp.items():
        me = obj[n].data
        if not np.any(d != 0): continue
        cn = np.array([x.vector[:] for x in me.corner_normals]); lv = np.array([l.vertex_index for l in me.loops])
        co = allv[n].copy(); co[:, 2] += d
        me.vertices.foreach_set('co', co.ravel()); me.update()
        k = w[lv] > 0
        if n != 'SURF_Sand' and k.any():
            dn = dtm_normal(co[lv[k], :2]); ww = w[lv[k]][:, None]
            nn = cn[k] * (1 - ww) + dn * ww; cn[k] = nn / np.linalg.norm(nn, axis=1)[:, None]
            me.normals_split_custom_set([tuple(x) for x in cn])
        say('green dtm', n, 'verts moved', int((d != 0).sum()), 'max |dz| %.3f' % np.abs(d).max())
    gz = dtm(PIN[None])[0]
    dzp = gz - H['pin']['blender'][2]
    for o in obj:
        if o.name.startswith('PIN_'):
            o.data.transform(Matrix.Translation((0, 0, dzp))); o.data.update()
    green_info = dict(pin_z=round(float(gz), 3), pin_dz=round(float(dzp), 3))
    gv = np.array([v.co[:] for v in obj['SURF_Green'].data.vertices]); near = np.linalg.norm(gv[:, :2] - PIN, axis=1) < 25
    green_info['green_drop'] = round(float(np.ptp(gv[near, 2])), 2)
    say('pin moved dz %.3f' % dzp)

# ------------------------------------------------------------------ 4. markers, sign, camera (only when tees changed)
meta = dict(log=log, green=green_info)
dg = bpy.context.evaluated_depsgraph_get()
teeb = BVHTree.FromObject(obj['SURF_Tee'], dg)
def zat(x, y):
    h = teeb.ray_cast(Vector((x, y, 500)), Vector((0, 0, -1)))
    return h[0].z if h[0] is not None else float(dtm(np.array([[x, y]]))[0])
hl = np.array(H['hole_line_blender'])
def aim_point(c):
    if 'aim' in P: return np.array(P['aim'])
    if H['par'] == 3 or len(hl) < 2: return PIN
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(hl, axis=0), axis=1))])
    i = np.searchsorted(cum, 110); i = min(max(i, 1), len(hl) - 1); return hl[i]
tees_out = []
if tee_changed:
    pairs = {}
    for o in obj:
        if o.name.startswith('TEE_Marker_'):
            _, _, col, side = o.name.split('_'); pairs.setdefault(col, {})[side] = o
    ex = P.get('markers', {})
    for col, pr in pairs.items():
        vs = {s: np.array([v.co[:] for v in o.data.vertices]) for s, o in pr.items()}
        cen = np.mean([v[:, :2].mean(0) for v in vs.values()], 0)
        if col in ex: c = np.array(ex[col])
        else:
            c = cen.copy()
            on_pad = teeb.ray_cast(Vector((c[0], c[1], 500)), Vector((0, 0, -1)))[0] is not None
            in_new = [t for t in NEWTEES if inside(t, c[None])[0]]
            ok = on_pad and (not in_new or seg_dist(in_new[0], c[None])[0] > 0.8)
            if not ok:
                best = None
                for t in NEWTEES:
                    g = grid_in(t, 0.5, 1.8)
                    if len(g):
                        j = np.argmin(np.linalg.norm(g - cen, axis=1))
                        if best is None or np.linalg.norm(g[j] - cen) < np.linalg.norm(best - cen): best = g[j]
                if best is not None: c = best
        a = aim_point(c) - c; a /= np.linalg.norm(a); ang = math.atan2(-a[0], a[1]); left = np.array([-a[1], a[0]])
        half = np.linalg.norm(vs['L'][:, :2].mean(0) - vs['R'][:, :2].mean(0)) / 2 if 'L' in vs and 'R' in vs else 2.6
        for side, o in pr.items():
            v = vs[side]; mc = v.mean(0); zmin = v[:, 2].min()
            p = c + (1 if side == 'L' else -1) * left * half
            M = Matrix.Translation(Vector((p[0], p[1], zat(*p) + MARK_LIFT.get(o.name, 0.0)))) @ Matrix.Rotation(ang, 4, 'Z') @ Matrix.Translation(Vector((-mc[0], -mc[1], -zmin)))
            o.data.transform(M); o.data.update()
        tees_out.append((col, c))
        say('markers', col, np.round(cen, 1).tolist(), '->', np.round(c, 1).tolist())
    # sign: move off the tee if a new tee covers it
    sign = [o for o in obj if o.name.startswith('PROP_Sign')]
    if sign:
        allp = np.vstack([[v.co[:] for v in o.data.vertices] for o in sign]); b0 = np.array([allp[:, 0].mean(), allp[:, 1].mean(), allp[:, 2].min()])
        if any(inside(t, b0[None, :2])[0] or seg_dist(t, b0[None, :2])[0] < 1.0 for t in NEWTEES):
            t = min(NEWTEES, key=lambda t: seg_dist(t, b0[None, :2])[0])
            ring = resample(t, 0.5); cen = t.mean(0)
            j = np.argmin(np.linalg.norm(ring - b0[:2], axis=1)); out_dir = ring[j] - cen; out_dir /= np.linalg.norm(out_dir)
            sp = ring[j] + out_dir * 2.0
            for o in sign: o.data.transform(Matrix.Translation(Vector((sp[0] - b0[0], sp[1] - b0[1], float(dtm(sp[None])[0]) - b0[2])))); o.data.update()
            say('sign moved to', np.round(sp, 1).tolist())
    if 'CAM_Tee' in obj and tees_out:
        back = dict(tees_out).get(P.get('back_colour', 'yellow'), tees_out[0][1])
        a = aim_point(back) - back; a /= np.linalg.norm(a); cp = back - a * 8.0
        cam = obj['CAM_Tee']; cam.location = (cp[0], cp[1], float(dtm(cp[None])[0]) + 1.8)
        cam.rotation_euler = (math.radians(91.2), 0.0, math.atan2(-a[0], a[1]))
    order = P.get('tee_order', [c for c, _ in tees_out])
    for col in order:
        c = dict(tees_out)[col]; z = zat(*c)
        outl = [t for t in NEWTEES if inside(t, c[None])[0]]
        tees_out_j = {'colour': col, 'center_blender': [round(float(c[0]), 2), round(float(c[1]), 2), round(z, 2)],
                      'center_gltf': [round(float(c[0]), 3), round(z, 3), round(-float(c[1]), 3)],
                      'to_pin_m': round(float(np.linalg.norm(PIN - c)), 1)}
        if outl: tees_out_j['outline_blender'] = [[round(float(x), 2), round(float(y), 2)] for x, y in outl[0]]
        meta.setdefault('tees', []).append(tees_out_j)
meta['trees'] = sum(o.name.startswith('TREE_') for o in obj)
json.dump(meta, open(META, 'w'))
bpy.ops.wm.save_as_mainfile(filepath=DST, compress=True)
