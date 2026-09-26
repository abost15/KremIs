"""Byneset South hole 9: replace the misplaced tee boxes with the L-shaped tee
complex from the club's hole diagram (outline traced on the aerial image),
remove lidar trees the aerial image and diagram show as open grass, and move
the tee markers, hole sign and tee camera.  Run with Blender 5.2:
    blender -b --python fix_tee.py -- in.blend out.blend out_meta.json
"""
import bpy, bmesh, json, math, sys
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

SRC, DST, META = sys.argv[-3:]
bpy.ops.wm.open_mainfile(filepath=SRC)
dg = bpy.context.evaluated_depsgraph_get()
obj = bpy.data.objects

# lidar trees where the aerial image and the club diagram show open grass
DROP = ['TREE_Birch_088', 'TREE_Birch_089', 'TREE_Spruce_091', 'TREE_Birch_092', 'TREE_Birch_093',
        'TREE_Birch_094', 'TREE_Spruce_095', 'TREE_Birch_096', 'TREE_Birch_097', 'TREE_Birch_098',
        'TREE_Birch_099', 'TREE_Birch_100', 'TREE_Spruce_101', 'TREE_Birch_102']
TREES = {o.name: (o.location.x, o.location.y) for o in obj if o.name.startswith('TREE_')}
KEPT = np.array([p for n, p in TREES.items() if n not in DROP])
GONE = np.array([p for n, p in TREES.items() if n in DROP])

# ---------------------------------------------------------------- geometry helpers
def chaikin(pts, it=3):
    p = np.asarray(pts, float)
    for _ in range(it):
        q = np.roll(p, -1, 0)
        p = np.stack([0.75 * p + 0.25 * q, 0.25 * p + 0.75 * q], 1).reshape(-1, 2)
    return p

def resample(poly, step):
    p = np.vstack([poly, poly[:1]])
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    n = max(8, int(round(cum[-1] / step)))
    t = np.linspace(0, cum[-1], n, endpoint=False)
    return np.stack([np.interp(t, cum, p[:, 0]), np.interp(t, cum, p[:, 1])], 1)

def inside(poly, pts):
    pts = np.atleast_2d(pts); x, y = pts[:, 0], pts[:, 1]
    res = np.zeros(len(pts), bool)
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]; xj, yj = poly[j]
        c = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi)
        res ^= c; j = i
    return res

def seg_dist(poly, pts):
    pts = np.atleast_2d(pts); d = np.full(len(pts), np.inf)
    a = poly; b = np.roll(poly, -1, 0)
    for p0, p1 in zip(a, b):
        v = p1 - p0; w = pts - p0
        t = np.clip((w @ v) / (v @ v), 0, 1)
        d = np.minimum(d, np.linalg.norm(w - np.outer(t, v), axis=1))
    return d

def grid_in(poly, step, margin, holes=()):
    lo, hi = poly.min(0), poly.max(0)
    gx, gy = np.meshgrid(np.arange(lo[0] + step / 2, hi[0], step), np.arange(lo[1] + step / 2, hi[1], step))
    g = np.stack([gx.ravel(), gy.ravel()], 1)
    g = g[inside(poly, g) & (seg_dist(poly, g) > margin)]
    for h in holes:
        g = g[~inside(h, g) & (seg_dist(h, g) > margin)]
    return g

# ---------------------------------------------------------------- tee complex outline
# Traced on the aerial image registered to the model (bunker fit, ~1.5 m) and
# checked against the club diagram: an arm pointing up the hole with a foot
# running west along the tree line.
CTRL = [(-6, 17), (-4.5, 20), (-1, 21.5), (3, 21), (6, 19), (7.5, 15), (7.5, 5), (7.3, -6),
        (6.5, -13), (4.5, -16.5), (0, -17.5), (-10, -18), (-20, -18.5), (-27, -17.5),
        (-30.5, -15), (-31, -11), (-29, -8), (-24, -6.8), (-14, -6.3), (-8.5, -5),
        (-6.5, -2.5), (-6.5, 5), (-6.5, 12)]
# The arm of the tee does not point at the green but along the line of play
# into the middle of the fairway: 13 deg left of the tee->pin line (marked by
# the user on the club diagram).  Bend the arm about the corner by the yellow
# tee, blending from 0 deg along the foot to the full angle up the arm, so the
# foot stays along the tree line and the complex gets a slight curve.
AIM_DEG = 13.0
PIVOT = np.array([0.5, -10.0])
def bend(p):
    p = np.asarray(p, float)
    w = np.clip((p[1] + 8.0) / 13.0, 0, 1); w = w * w * (3 - 2 * w)
    a = math.radians(AIM_DEG) * w; c, s_ = math.cos(a), math.sin(a)
    d = p - PIVOT
    return PIVOT + np.array([c * d[0] - s_ * d[1], s_ * d[0] + c * d[1]])
CTRL = [bend(p) for p in CTRL]
TEE = resample(chaikin(CTRL, 3), 1.2)
area = 0.5 * np.sum(TEE[:, 0] * np.roll(TEE[:, 1], -1) - np.roll(TEE[:, 0], -1) * TEE[:, 1])
if area < 0:
    TEE = TEE[::-1]
print('tee complex area m2', round(abs(area), 1))

YELLOW = np.array([1.8, -9.5])   # back tee  (club 265 m)
RED = bend([-1.0, 5.5])          # front tee (club 250 m), 15 m up the bent arm

# ---------------------------------------------------------------- terrain samples
rough = obj['SURF_Rough']; teeo = obj['SURF_Tee']

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

bt = bmesh.new(); bt.from_mesh(teeo.data)
old_tee_polys = []   # (xy outline of island bbox) for islands of this hole
old_tee_islands = []
for isl in islands(bt):
    vs = {v for f in isl for v in f.verts}
    xy = np.array([(v.co.x, v.co.y) for v in vs])
    c = xy.mean(0)
    if np.hypot(*(c - [-2.3, 7.15])) < 3 or np.hypot(*(c - [30.71, -25.3])) < 3:
        old_tee_islands.append(isl)
        lo, hi = xy.min(0), xy.max(0)
        old_tee_polys.append(np.array([[lo[0], lo[1]], [hi[0], lo[1]], [hi[0], hi[1]], [lo[0], hi[1]]]))
assert len(old_tee_islands) == 2, len(old_tee_islands)

# natural-ground samples: rough verts not on the old tee banks + old tee platforms
rv = np.array([v.co[:] for v in rough.data.vertices])
tv = np.array([v.co[:] for v in teeo.data.vertices])
def near_any(polys, xy, d):
    m = np.zeros(len(xy), bool)
    for p in polys:
        m |= inside(p, xy) | (seg_dist(p, xy) < d)
    return m
loc = (np.abs(rv[:, 0] - 0) < 90) & (np.abs(rv[:, 1] + 5) < 70)
rs = rv[loc]
rs = rs[~near_any(old_tee_polys, rs[:, :2], 3.2)]
ts = tv[near_any(old_tee_polys, tv[:, :2], 0.1)]
SAMP = np.vstack([rs, ts])

def ground(xy, sigma=5.0):
    xy = np.atleast_2d(xy); out = np.empty(len(xy)); grad = np.empty((len(xy), 2))
    for i, p in enumerate(xy):
        d2 = ((SAMP[:, :2] - p) ** 2).sum(1)
        w = np.exp(-d2 / (2 * sigma ** 2)); k = w > 1e-4
        A = np.c_[SAMP[k, 0] - p[0], SAMP[k, 1] - p[1], np.ones(k.sum())]
        W = w[k]
        coef = np.linalg.lstsq(A * W[:, None] ** 0.5, SAMP[k, 2] * W ** 0.5, rcond=None)[0]
        out[i] = coef[2]; grad[i] = coef[:2]
    return out, grad

def nrm(g):
    n = np.c_[-g[:, 0], -g[:, 1], np.ones(len(g))]
    return n / np.linalg.norm(n, axis=1)[:, None]

# ---------------------------------------------------------------- sanity: other surfaces inside new tee?
for o in obj:
    if o.type == 'MESH' and o.name.startswith('SURF_') and o.name not in ('SURF_Rough', 'SURF_Tee', 'SURF_Far'):
        v = np.array([x.co[:2] for x in o.data.vertices])
        hit = inside(TEE, v) | (seg_dist(TEE, v) < 4.5)
        if hit.any():
            print('WARNING surface near new tee:', o.name, hit.sum())

# ---------------------------------------------------------------- rebuild rough around tees
me = rough.data
col_name = 'Col'
bm = bmesh.new(); bm.from_mesh(me)
bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
uvl = bm.loops.layers.uv['UVMap']
coll = bm.loops.layers.color.get(col_name) or bm.loops.layers.float_color.get(col_name)
newl = bm.faces.layers.int.new('is_new')

# per-vertex colour and custom normal of the original rough (for filling)
corner_n = np.array([n.vector[:] for n in me.corner_normals])
vn_old = {}
for li, l in enumerate(me.loops):
    vn_old.setdefault(l.vertex_index, []).append(corner_n[li])
vcol = {}
for f in bm.faces:
    for l in f.loops:
        vcol.setdefault(l.vert.index, []).append(tuple(l[coll]))
vcol = {k: np.mean(v, 0) for k, v in vcol.items()}
# The rough vertex colours carry baked shade under trees (darker close to a
# trunk).  Estimate the falloff so shade from removed trees can be divided out
# and shade from kept trees applied to the new tee.
_ids = np.array(list(vcol)); _xy = np.array([me.vertices[i].co[:2] for i in _ids])
_lum = np.array([vcol[i][:3].mean() for i in _ids])
_dall = np.min(np.linalg.norm(_xy[:, None, :] - np.array(list(TREES.values()))[None], axis=2), 1)
_ref = np.median(_lum[_dall > 15])
SH_D = np.arange(0.5, 15, 1.0)
SH_S = np.array([np.median(_lum[(_dall >= d - 0.5) & (_dall < d + 0.5)]) / _ref if ((_dall >= d - 0.5) & (_dall < d + 0.5)).sum() > 5 else 1.0 for d in SH_D])
SH_S = np.minimum(np.maximum.accumulate(np.clip(SH_S, 0.3, 1.0)), 1.0)
print('shade curve', dict(zip(SH_D.round(1).tolist(), SH_S.round(2).tolist())))
def shade(xy, trees):
    xy = np.atleast_2d(xy)
    if len(trees) == 0: return np.ones(len(xy))
    d = np.linalg.norm(xy[:, None, :] - trees[None], axis=2)
    return np.prod(np.interp(d, SH_D, SH_S, left=SH_S[0], right=1.0), axis=1)
vn_old = {k: np.mean(v, 0) for k, v in vn_old.items()}
vxy = np.array([v.co[:2] for v in bm.verts])

BUF = 4.0
regions = [TEE, old_tee_polys[0], old_tee_polys[1]]
region_verts = near_any(regions, vxy, BUF)
old_hole = near_any(old_tee_polys, vxy, 0.3)
pre_boundary = {v.index for v in bm.verts if v.is_boundary}
keep_boundary = {i for i in pre_boundary if not old_hole[i]}   # boundaries of other features
kill = []
for f in bm.faces:
    idx = [v.index for v in f.verts]
    c = np.mean(vxy[idx], 0)
    if (region_verts[idx].any() or near_any(regions, c[None], BUF)[0]) and not any(i in keep_boundary for i in idx):
        kill.append(f)
print('rough faces removed', len(kill))
old_vcount = len(bm.verts)
key = lambda co: (round(co.x, 4), round(co.y, 4))
bnd_normal = {}
keep_bv = {bm.verts[i] for i in keep_boundary}   # BMVert refs survive the delete, indices do not
pre_bedges = {e for e in bm.edges if e.is_boundary}
bmesh.ops.delete(bm, geom=kill, context='FACES')
bm.verts.ensure_lookup_table()

bedges = [e for e in bm.edges if e.is_boundary and e not in pre_bedges]
assert not any(v in keep_bv for e in bedges for v in e.verts)
# chain into loops
adj = {}
for e in bedges:
    a, b = e.verts
    adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
loops = []; used = set()
for start in list(adj):
    if start in used: continue
    lp = [start]; used.add(start); prev = None; cur = start
    while True:
        nxt = [n for n in adj[cur] if n is not prev and n not in used]
        if not nxt:
            break
        prev, cur = cur, nxt[0]; lp.append(cur); used.add(cur)
    loops.append(lp)
print('hole loops', [len(l) for l in loops])

def add_faces(bmx, tri_idx, bverts, uvscale, colfn, layer_uv, layer_col, mat=0):
    made = []
    for t in tri_idx:
        vs = [bverts[i] for i in t]
        if len(set(vs)) < 3: continue
        try:
            f = bmx.faces.new(vs)
        except ValueError:
            continue
        f.smooth = True; f.material_index = mat
        for l in f.loops:
            l[layer_uv].uv = (l.vert.co.x * uvscale, l.vert.co.y * uvscale)
            l[layer_col] = colfn(l.vert)
        made.append(f)
    return made

old_xy = vxy  # for colour lookup
old_idx_by_key = {}
for i, (x, y) in enumerate(old_xy):
    old_idx_by_key[(round(x, 4), round(y, 4))] = i
from mathutils.kdtree import KDTree
kd = KDTree(len(old_xy))
for i, (x, y) in enumerate(old_xy):
    if i in vcol: kd.insert((x, y, 0), i)
kd.balance()
def rough_col(v):
    _, i, _ = kd.find((v.co.x, v.co.y, 0))
    return tuple(vcol[i])

new_rough_verts = set()
TEE_R = resample(TEE, 1.2)
for lp in loops:
    L = np.array([(v.co.x, v.co.y) for v in lp])
    has_tee = inside(L, TEE_R[:1])[0]
    holes = [TEE_R] if has_tee else []
    g = grid_in(L, 2.0, 1.0, holes)
    pts = [tuple(p) for p in L]
    faces_in = [list(range(len(L)))]
    off = len(pts)
    if has_tee:
        pts += [tuple(p) for p in TEE_R]; faces_in.append(list(range(off, off + len(TEE_R)))); off += len(TEE_R)
    pts += [tuple(p) for p in g]
    out_v, out_e, out_f, orig_v, _, _ = delaunay_2d_cdt([Vector(p) for p in pts], [], faces_in, 0, 1e-6, True)
    # map output verts -> bmesh verts
    zmap, gmap = ground(np.array([(v.x, v.y) for v in out_v]))
    bverts = []
    for i, v in enumerate(out_v):
        src = orig_v[i]
        if src and src[0] < len(L):
            bverts.append(lp[src[0]])
        else:
            nv = bm.verts.new((v.x, v.y, zmap[i])); new_rough_verts.add(nv); bverts.append(nv)
    tris = []
    for f in out_f:
        c = np.mean([(out_v[i].x, out_v[i].y) for i in f], 0)
        if inside(L, c[None])[0] and not (has_tee and inside(TEE_R, c[None])[0]):
            tris.append(f)
    made = add_faces(bm, tris, bverts, 0.25, rough_col, uvl, coll)
    for f in made: f[newl] = 1
    print('loop', len(L), 'tee' if has_tee else 'fill', 'faces', len(made))

# normals for the rebuilt part
bm.verts.index_update(); bm.faces.index_update()
bm.to_mesh(me); bm.free()
me.update()
isnew = np.array([a.value for a in me.attributes['is_new'].data], bool)
cn = np.array([n.vector[:] for n in me.corner_normals])
poly_of_loop = np.empty(len(me.loops), int)
for p in me.polygons:
    poly_of_loop[p.loop_start:p.loop_start + p.loop_total] = p.index
lv = np.array([l.vertex_index for l in me.loops])
vco = np.array([v.co[:] for v in me.vertices])
# vertices touched by new faces
touched = np.unique(lv[isnew[poly_of_loop]])
g_z, g_grad = ground(vco[touched, :2])
tn = dict(zip(touched.tolist(), nrm(g_grad)))
out = cn.copy()
for li in range(len(lv)):
    vi = lv[li]
    if isnew[poly_of_loop[li]]:
        # vertex that also belongs to old faces keeps its old normal for a seamless join
        k = (round(vco[vi, 0], 4), round(vco[vi, 1], 4))
        oi = old_idx_by_key.get(k)
        if oi is not None and oi in vn_old:
            out[li] = vn_old[oi]
        else:
            out[li] = tn[vi]
me.normals_split_custom_set([tuple(n) for n in out])
me.attributes.remove(me.attributes['is_new'])
ca = me.attributes['Col']
cc = np.array([d.color[:] for d in ca.data])
fix = shade(vco[lv, :2], GONE)
cc[:, :3] = np.clip(cc[:, :3] / fix[:, None], 0, 1)
# residual per-tree darkening: pull darker corners near each removed tree
# toward the colour of the surrounding ring (away from kept trees)
cxy = vco[lv, :2]
dk = np.min(np.linalg.norm(cxy[:, None, :] - KEPT[None], axis=2), 1)
for t in GONE:
    d = np.linalg.norm(cxy - t, axis=1)
    ring = (d > 8) & (d < 14) & (dk > 8)
    if ring.sum() < 10:
        continue
    med = np.median(cc[ring, :3], 0)
    m = (d < 8) & (cc[:, :3].mean(1) < med.mean())
    w = (1 - (d[m] / 8) ** 2)[:, None]
    cc[m, :3] = cc[m, :3] * (1 - w) + med * w
for d, c in zip(ca.data, cc): d.color = c
print('rough corners un-shaded', int((fix < 0.99).sum()))

# ---------------------------------------------------------------- tee surface
tme = teeo.data
tcorner = np.array([n.vector[:] for n in tme.corner_normals])
bm = bmesh.new(); bm.from_mesh(tme)
uvt = bm.loops.layers.uv['UVMap']
colt = bm.loops.layers.color.get(col_name) or bm.loops.layers.float_color.get(col_name)
newt = bm.faces.layers.int.new('is_new')
tcols = np.array([tuple(l[colt]) for f in bm.faces for l in f.loops])
bm.faces.ensure_lookup_table()
kill = set()
bmi = islands(bm)
for isl in bmi:
    xy = np.array([(v.co.x, v.co.y) for f in isl for v in f.verts]); c = xy.mean(0)
    if np.hypot(*(c - [-2.3, 7.15])) < 3 or np.hypot(*(c - [30.71, -25.3])) < 3:
        kill.update(isl)
# colours of the old hole-9 tee platforms, reused (tiled) on the new one
old_cols = [tuple(l[colt]) for f in kill for l in f.loops]
bmesh.ops.delete(bm, geom=list(kill), context='FACES')
g = grid_in(TEE_R, 1.2, 0.6)
pts = [tuple(p) for p in TEE_R] + [tuple(p) for p in g]
out_v, _, out_f, orig_v, _, _ = delaunay_2d_cdt([Vector(p) for p in pts], [], [list(range(len(TEE_R)))], 0, 1e-6, True)
zz, gg = ground(np.array([(v.x, v.y) for v in out_v]))
bverts = [bm.verts.new((v.x, v.y, zz[i])) for i, v in enumerate(out_v)]
tris = [f for f in out_f if inside(TEE_R, np.mean([(out_v[i].x, out_v[i].y) for i in f], 0)[None])[0]]
oc = np.array(old_cols); base = oc.mean(0)
def tee_col(v):
    x, y = v.co.x, v.co.y
    n = 0.5 * math.sin(0.61 * x + 0.23 * y) + 0.35 * math.sin(0.17 * x - 0.53 * y + 1.3) + 0.25 * math.sin(0.9 * y + 0.4 * x + 2.1)
    f = (1 + 0.035 * n) * shade(np.array([x, y]), KEPT)[0]
    c = base.copy(); c[:3] = np.clip(c[:3] * f, 0, 1)
    return tuple(c)
made = add_faces(bm, tris, bverts, 1 / 3, tee_col, uvt, colt)
for f in made: f[newt] = 1
print('tee faces', len(made))
bm.to_mesh(tme); bm.free(); tme.update()
isnew = np.array([a.value for a in tme.attributes['is_new'].data], bool)
cn = np.array([n.vector[:] for n in tme.corner_normals])
lv = np.array([l.vertex_index for l in tme.loops])
pol = np.empty(len(tme.loops), int)
for p in tme.polygons: pol[p.loop_start:p.loop_start + p.loop_total] = p.index
vco = np.array([v.co[:] for v in tme.vertices])
newv = np.unique(lv[isnew[pol]])
_, gnew = ground(vco[newv, :2]); nmap = dict(zip(newv.tolist(), nrm(gnew)))
for li in np.nonzero(isnew[pol])[0]:
    cn[li] = nmap[lv[li]]
tme.normals_split_custom_set([tuple(n) for n in cn])
tme.attributes.remove(tme.attributes['is_new'])

# ---------------------------------------------------------------- ground BVH after edit
bvh_objs = [obj[n] for n in ('SURF_Rough', 'SURF_Tee')]
dg = bpy.context.evaluated_depsgraph_get()
bvhs = [BVHTree.FromObject(o, dg) for o in bvh_objs]
def zat(x, y):
    best = None
    for b in bvhs:
        h = b.ray_cast(Vector((x, y, 200)), Vector((0, 0, -1)))
        if h[0] is not None and (best is None or h[0].z > best): best = h[0].z
    return best

# ---------------------------------------------------------------- trees
# lidar trees where the aerial image and the club diagram show open grass
for n in DROP:
    bpy.data.objects.remove(obj[n], do_unlink=True)
for o in obj:
    if o.name.startswith('TREE_') and inside(TEE, np.array([[o.location.x, o.location.y]]))[0]:
        raise SystemExit('tree left inside tee: ' + o.name)

# tall-grass tufts on the new tee
gt = obj['GRASS_Tufts']
bm = bmesh.new(); bm.from_mesh(gt.data)
drop = []
for isl in islands(bm):
    c = np.mean([(v.co.x, v.co.y) for f in isl for v in f.verts], 0)
    if inside(TEE, c[None])[0] or seg_dist(TEE, c[None])[0] < 1.0:
        drop += isl
print('grass tufts removed (faces)', len(drop))
bmesh.ops.delete(bm, geom=drop, context='FACES'); bm.to_mesh(gt.data); bm.free()

# ---------------------------------------------------------------- markers, sign, camera
# aim along the line of play into the fairway (not at hole_line[1])
AIM = np.array([-math.sin(math.radians(AIM_DEG + 0.8)), math.cos(math.radians(AIM_DEG + 0.8))])
def aim_from(p):
    return AIM

def move_mesh(o, frm, to, ang):
    # rotate about frm (z axis) by ang, then translate to 'to'
    M = Matrix.Translation(Vector(to)) @ Matrix.Rotation(ang, 4, 'Z') @ Matrix.Translation(-Vector(frm))
    o.data.transform(M); o.data.update()

for colr, c in (('yellow', YELLOW), ('red', RED)):
    a = aim_from(c); ang = math.atan2(-a[0], a[1])   # rotation from +Y to aim
    left = np.array([-a[1], a[0]])
    for side, sgn in (('L', 1), ('R', -1)):
        o = obj[f'TEE_Marker_{colr}_{side}']
        vs = np.array([v.co[:] for v in o.data.vertices]); cen = vs.mean(0)
        zmin = vs[:, 2].min()
        # original ground under marker: markers stood on the old platform (z ~0.19-0.24)
        lift = zmin - 0.215
        p = c + sgn * left * 2.6
        gz = zat(*p)
        move_mesh(o, (cen[0], cen[1], zmin), (p[0], p[1], gz + lift), ang)

sign = [o for o in obj if o.name.startswith('PROP_Sign')]
allv = np.vstack([[v.co[:] for v in o.data.vertices] for o in sign])
base = np.array([allv[:, 0].mean(), allv[:, 1].mean(), allv[:, 2].min()])
sp = np.array([9.6, -11.5])
gz = zat(*sp)
for o in sign:
    move_mesh(o, tuple(base), (sp[0], sp[1], gz), 0.0)

cam = obj['CAM_Tee']
a = aim_from(YELLOW)
cp = YELLOW - a * 8.0   # 8 m back; further back is inside the tree line
cam.location = (cp[0], cp[1], zat(*cp) + 1.8)
cam.rotation_euler = (math.radians(91.2), 0.0, math.atan2(-a[0], a[1]))

# ---------------------------------------------------------------- metadata
pin = np.array([-1.477, 230.928])
def to_gltf(x, y, z): return [round(x, 3), round(z, 3), round(-y, 3)]
tees = []
for c in (YELLOW, RED):
    z = zat(*c)
    tees.append({'center_blender': [round(c[0], 2), round(c[1], 2), round(z, 2)],
                 'center_gltf': to_gltf(c[0], c[1], z),
                 'to_pin_m': round(float(np.linalg.norm(pin - c)), 1),
                 'outline_blender': [[round(x, 2), round(y, 2)] for x, y in TEE]})
meta = {'tees': tees, 'trees': sum(o.name.startswith('TREE_') for o in obj)}
json.dump(meta, open(META, 'w'))
print('tees', [(t['center_blender'], t['to_pin_m']) for t in tees], 'trees', meta['trees'])

bpy.ops.wm.save_as_mainfile(filepath=DST, compress=True)
