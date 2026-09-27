"""Byneset South hull 1, rettet på en enklere måte enn fix_south_01.py.

To feil i originalen:
  * fairwayen slutter brått 11,9 m foran greenen. På de 26 andre hullene går den
    helt inn (0–0,8 m).
  * det fremre teestedet er 8 m². Median for teeputene på anlegget er 164 m²,
    og de røde markørene står allerede utenfor puta.

I stedet for å rive opp bakken og bygge den på nytt (tregt, og skjøtene mot
green og forgreen ryker lett), bruker vi at bakken alt har 0,87 m trekanter i
området: flatene flyttes bare fra ett objekt til et annet, slik at gresset blir
klippet annerledes. Punktene blir stående der de står, så det kan ikke bli glipe
mellom flatene. Teeputa løftes lokalt, med en liten voll ut mot kanten, og bare
inne i teeputas eget omriss.

    blender -b --python h1_fast.py -- inn.blend hull.json dtm.npy dtm.json ut.blend meta.json
"""
import bpy, bmesh, json, math, sys
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.validation import make_valid
from shapely.ops import unary_union
from shapely.prepared import prep
from mathutils.kdtree import KDTree

SRC, HOLE, DTM, DTMJ, DST, META = sys.argv[-6:]
bpy.ops.wm.open_mainfile(filepath=SRC)
obj = bpy.data.objects
H = json.load(open(HOLE))
Z = np.load(DTM); ZJ = json.load(open(DTMJ))
O = np.array(H['coordinates']['geo_origin_utm33'])
TH = math.radians(H['coordinates']['plusY_true_bearing_deg'])
Z0 = H['model']['elevation_tee_masl']
log = []
def say(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); log.append(s)


# ------------------------------------------------------------------ hjelpefunksjoner
def dtm(xy):
    xy = np.atleast_2d(np.asarray(xy, float)); r = ZJ['res']
    E = O[0] + xy[:, 0] * math.cos(TH) + xy[:, 1] * math.sin(TH)
    N = O[1] - xy[:, 0] * math.sin(TH) + xy[:, 1] * math.cos(TH)
    c = (E - ZJ['E0']) / r - 0.5; rr = (ZJ['N1'] - N) / r - 0.5
    c0 = np.clip(np.floor(c).astype(int), 0, Z.shape[1] - 2)
    r0 = np.clip(np.floor(rr).astype(int), 0, Z.shape[0] - 2)
    fc = np.clip(c - c0, 0, 1); fr = np.clip(rr - r0, 0, 1)
    return (Z[r0, c0] * (1 - fc) * (1 - fr) + Z[r0, c0 + 1] * fc * (1 - fr) +
            Z[r0 + 1, c0] * (1 - fc) * fr + Z[r0 + 1, c0 + 1] * fc * fr) - Z0


def poly(p):
    P = Polygon(np.asarray(p))
    if not P.is_valid: P = make_valid(P)
    if P.geom_type == 'GeometryCollection':
        P = unary_union([g for g in P.geoms if g.geom_type in ('Polygon', 'MultiPolygon')])
    return None if P.is_empty else P


def ring(P):
    if P.geom_type == 'MultiPolygon':
        P = max(P.geoms, key=lambda g: g.area)
    return np.array(P.exterior.coords)[:-1]


def biggest(P):
    return max(P.geoms, key=lambda g: g.area) if P.geom_type == 'MultiPolygon' else P


def resample(p, step):
    p = np.vstack([p, p[:1]]); seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)]); n = max(8, int(round(cum[-1] / step)))
    t = np.linspace(0, cum[-1], n, endpoint=False)
    return np.stack([np.interp(t, cum, p[:, 0]), np.interp(t, cum, p[:, 1])], 1)


def inside(pol, pts):
    pts = np.atleast_2d(pts); x, y = pts[:, 0], pts[:, 1]
    res = np.zeros(len(pts), bool); j = len(pol) - 1
    for i in range(len(pol)):
        xi, yi = pol[i]; xj, yj = pol[j]
        res ^= ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi); j = i
    return res


def seg_dist(pol, pts):
    pts = np.atleast_2d(pts); d = np.full(len(pts), np.inf)
    for p0, p1 in zip(pol, np.roll(pol, -1, 0)):
        v = p1 - p0; w = pts - p0; t = np.clip((w @ v) / (v @ v), 0, 1)
        d = np.minimum(d, np.linalg.norm(w - np.outer(t, v), axis=1))
    return d


def uv_fit(me):
    """UV-en er verdenskoordinat ganget med en fast skala. Den hentes ut her."""
    uv = me.uv_layers.active.data; L = []; U = []
    for p in me.polygons[:4000]:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            L.append([v.x, v.y, 1]); U.append(uv[li].uv[:])
    return np.linalg.lstsq(np.array(L), np.array(U), rcond=None)[0]


def mesh_poly(name, near, r=40.0):
    """Nøyaktig omriss av en flate, satt sammen av selve trekantene."""
    o = obj.get(name)
    if o is None: return None
    me = o.data; V = np.array([v.co[:2] for v in me.vertices]); tri = []
    for f in me.polygons:
        idx = list(f.vertices)
        if np.linalg.norm(V[idx].mean(0) - near) > r: continue
        for k in range(1, len(idx) - 1):
            t = Polygon(V[[idx[0], idx[k], idx[k + 1]]])
            if t.is_valid and t.area > 1e-9: tri.append(t)
    if not tri: return None
    u = unary_union(tri).buffer(0.001).buffer(-0.001)
    return None if u.is_empty else u


def centers(o):
    V = np.array([v.co[:] for v in o.data.vertices])
    return np.array([V[list(f.vertices)].mean(0) for f in o.data.polygons]) if len(o.data.polygons) \
        else np.zeros((0, 3))


# ------------------------------------------------------------------ omriss
PIN = np.array(H['pin']['blender'][:2])
GREEN = mesh_poly('SURF_Green', PIN, 30.0)
FRINGE = mesh_poly('SURF_Fringe', PIN, 30.0)
SAND = [p for p in (mesh_poly('SURF_Sand', PIN, 45.0),) if p]
BLOCK = unary_union([g for g in [GREEN, FRINGE] + SAND if g])
FW_OLD = biggest(mesh_poly('SURF_Fairway', np.array([8.4, 177.7]), 220.0))
say('gammel fairway %.0f m2, slutter y=%.1f, green starter y=%.1f, gap %.1f m'
    % (FW_OLD.area, ring(FW_OLD)[:, 1].max(), ring(GREEN)[:, 1].min(), FW_OLD.distance(GREEN)))

# Innspillet fra fairwayenden opp til forgreenen: midtlinja følger spillelinja,
# og bredden smalner av slik den gjør på de andre hullene.
SPINE = [(258, -1.5, 13.0), (263, -1.0, 11.2), (268, -0.4, 9.6),
         (272, 0.1, 8.6), (276, 0.5, 7.8), (281, 0.9, 7.0), (284, 1.0, 6.4)]
left = [(cx - w, y) for y, cx, w in SPINE]
right = [(cx + w, y) for y, cx, w in SPINE][::-1]
APPROACH = biggest(poly(resample(np.array(left + right), 1.5)).difference(BLOCK))
FW_ADD = APPROACH.difference(FW_OLD)
SEMI_ADD = APPROACH.buffer(3.0).difference(APPROACH).difference(BLOCK).difference(FW_OLD)
say('innspill %.0f m2, hvorav %.0f m2 er ny fairway, semikant %.0f m2'
    % (APPROACH.area, FW_ADD.area, SEMI_ADD.area))

# Fremre teested: puta legges rundt de røde markørene som alt står der.
MARK = [o for o in obj if o.name.startswith('TEE_Marker_red')]
MC = np.array([np.array([v.co[:] for v in o.data.vertices]).mean(0)[:2] for o in MARK]).mean(0)
say('røde markører i', np.round(MC, 2).tolist())
TC = np.array([1.5, 34.0]); TW, TL, TR = 7.0, 17.0, 2.0
ang = math.radians(-1.9)                      # langs spillelinja ved teestedet
cs, sn = math.cos(ang), math.sin(ang)
hw, hl = TW / 2 - TR, TL / 2 - TR
pp = []
for cx, cy, a0 in ((hw, hl, 0), (-hw, hl, 90), (-hw, -hl, 180), (hw, -hl, 270)):
    for k in range(9):
        a = math.radians(a0 + k * 90 / 8)
        pp.append((cx + TR * math.cos(a), cy + TR * math.sin(a)))
P = np.array(pp)
TEE_RING = np.stack([TC[0] + cs * P[:, 0] - sn * P[:, 1],
                     TC[1] + sn * P[:, 0] + cs * P[:, 1]], 1)
TEE = poly(TEE_RING)
say('nytt fremre teested %.0f m2 i %s (%.1f x %.1f m)'
    % (TEE.area, np.round(TC, 1).tolist(), TW, TL))
assert TEE.contains(Point(*MC)), 'markørene havnet utenfor puta'
for o in obj:
    if o.name.startswith('TREE_') and TEE.buffer(0.5).contains(Point(o.location.x, o.location.y)):
        say('ADVARSEL tre inne på teestedet:', o.name)

# ------------------------------------------------------------------ flytte flater
GROUND = ('SURF_Rough', 'SURF_Semi', 'SURF_Fairway', 'SURF_Hay', 'SURF_Field',
          'SURF_Gravel', 'SURF_Road', 'SURF_Tee')
UVFIT = {n: uv_fit(obj[n].data) for n in GROUND if n in obj}


def move_faces(dst_name, region, srcs):
    """Flytter flatene som ligger inne i region over til dst_name.

    Geometrien røres ikke: punktene står der de står, og kantpunktene finnes
    etterpå i begge objektene med samme posisjon. Fargene (med innbakt skygge)
    og normalene følger med, mens UV-en regnes om til den nye teksturskalaen.
    """
    dst = obj[dst_name]; pr = prep(region)
    moved = 0
    for sn_ in srcs:
        if sn_ not in obj or sn_ == dst_name: continue
        src = obj[sn_]
        C = centers(src)
        if not len(C): continue
        sel = [i for i, c in enumerate(C) if pr.contains(Point(c[0], c[1]))]
        if not sel: continue
        for o in bpy.context.selected_objects: o.select_set(False)
        src.select_set(True); bpy.context.view_layer.objects.active = src
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(src.data)
        bm.faces.ensure_lookup_table()
        for f in bm.faces: f.select_set(False)
        for v in bm.verts: v.select_set(False)
        for e in bm.edges: e.select_set(False)
        for i in sel: bm.faces[i].select_set(True)
        bmesh.update_edit_mesh(src.data)
        before = set(bpy.data.objects.keys())
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        new = [obj[k] for k in bpy.data.objects.keys() if k not in before]
        assert len(new) == 1, 'separate ga %d objekt' % len(new)
        part = new[0]
        assert len(part.data.polygons) == len(sel), 'fikk %d av %d flater' % (
            len(part.data.polygons), len(sel))
        part.data.materials.clear(); part.data.materials.append(dst.data.materials[0])
        a = part.data.attributes.new('mv', 'INT', 'FACE')
        for d in a.data: d.value = 1
        for o in bpy.context.selected_objects: o.select_set(False)
        dst.select_set(True); part.select_set(True)
        with bpy.context.temp_override(active_object=dst,
                                       selected_editable_objects=[dst, part]):
            bpy.ops.object.join()
        moved += len(sel)
        say('  flyttet %d flater fra %s til %s' % (len(sel), sn_, dst_name))
    if not moved: return 0
    # UV-en må følge den nye teksturen, ellers blir gresset i feil målestokk.
    me = dst.data; U = UVFIT[dst_name]; uv = me.uv_layers.active.data
    mv = me.attributes.get('mv')
    n = 0
    if mv is not None:
        flag = np.array([d.value for d in mv.data], bool)
        for p in me.polygons:
            if not flag[p.index]: continue
            for li in p.loop_indices:
                v = me.vertices[me.loops[li].vertex_index].co
                uv[li].uv = tuple(np.array([v.x, v.y, 1]) @ U); n += 1
        me.attributes.remove(me.attributes['mv'])
    me.update()
    say('  regnet om UV på %d hjørner i %s' % (n, dst_name))
    return moved


say('fairway:')
n_fw = move_faces('SURF_Fairway', FW_ADD, ['SURF_Rough', 'SURF_Semi', 'SURF_Hay', 'SURF_Field'])
say('semikant:')
n_sm = move_faces('SURF_Semi', SEMI_ADD, ['SURF_Rough', 'SURF_Hay', 'SURF_Field'])

# Teestedet: først antall punkt i den gamle puta, så flyttes bakken inn.
tee = obj['SURF_Tee']
N0 = len(tee.data.vertices)
say('teested:')
n_te = move_faces('SURF_Tee', TEE, ['SURF_Rough', 'SURF_Semi', 'SURF_Fairway',
                                    'SURF_Hay', 'SURF_Field'])

# ------------------------------------------------------------------ løfte teeputa
# De andre teeputene på anlegget er helt plane (målt ujevnhet 0,000 m), har
# 0,2–0,5 % fall og ligger 0,135–0,150 m over terrenget. Den nye puta lages likt:
# et plan, ikke en flate som følger terrenget.
LIFT = 0.148; BANK = 2.0; MAXSLOPE = 0.005
me = tee.data
V = np.array([v.co[:] for v in me.vertices])

g = []
for x in np.arange(TEE.bounds[0], TEE.bounds[2], 0.5):
    for y in np.arange(TEE.bounds[1], TEE.bounds[3], 0.5):
        if TEE.contains(Point(x, y)): g.append((x, y))
g = np.array(g); gz = dtm(g)
A = np.c_[g[:, 0], g[:, 1], np.ones(len(g))]
a, b, c = np.linalg.lstsq(A, gz, rcond=None)[0]
s = math.hypot(a, b)
if s > MAXSLOPE:                                  # puta skal ikke være brattere enn de andre
    a, b = a * MAXSLOPE / s, b * MAXSLOPE / s
c = float(np.mean(gz) - (a * g[:, 0] + b * g[:, 1]).mean())
def plane(xy):
    return a * xy[:, 0] + b * xy[:, 1] + c + LIFT
cutfill = plane(g) - gz
say('putetoppen: plan med %.2f %% fall, %.3f m over terrenget i snitt '
    '(fylling %.2f–%.2f m)'
    % (100 * math.hypot(a, b), LIFT, cutfill.min(), cutfill.max()))

# Høyden er én funksjon av posisjonen: planet inne på puta, og utenfor trappes
# det ned til terrenget over BANK meter. Den samme funksjonen brukes på alle
# bakkeflatene, så punkter som deles mellom to flater får samme høyde og
# skjøtene holder av seg selv. Vollen havner dermed i roughen, slik den ligger
# rundt de andre teeputene.
def lift_at(xy, z):
    """Ny høyde for punktene. z er dagens høyde, som beholdes utenfor vollen."""
    d = seg_dist(TEE_RING, xy)                     # avstand til omrisset
    ins = inside(TEE_RING, xy)
    u = np.where(ins, 1.0, np.clip(1.0 - d / BANK, 0.0, 1.0))
    w = u * u * (3 - 2 * u)
    return z + (plane(xy) - z) * w

REGION = TEE.buffer(BANK + 0.01)
n_lift = 0; zmax = 0.0; changed = {}
for n in GROUND:
    if n not in obj: continue
    m_ = obj[n].data
    V_ = np.array([v.co[:] for v in m_.vertices])
    sel_ = np.array([REGION.contains(Point(x, y)) for x, y in V_[:, :2]])
    if not sel_.any(): continue
    zn = lift_at(V_[sel_][:, :2], V_[sel_][:, 2])
    idx_ = np.nonzero(sel_)[0]
    ch = np.abs(zn - V_[sel_][:, 2]) > 1e-6
    for k, i in enumerate(idx_):
        if ch[k]: m_.vertices[i].co.z = float(zn[k])
    m_.update()
    n_lift += int(ch.sum()); zmax = max(zmax, float(np.max(np.abs(zn - V_[sel_][:, 2]))) if len(zn) else 0)
    if ch.any():
        say('  %s: endret høyde på %d punkt' % (n, int(ch.sum())))
        mk = np.zeros(len(V_), bool); mk[idx_[ch]] = True; changed[n] = mk
say('vollen: endret høyde på %d punkt i alt, maks %.3f m' % (n_lift, zmax))

# Normalene på flatene som ble endret, regnes om, ellers blir lyset feil.
for n, mk in changed.items():
    m_ = obj[n].data
    touched = np.zeros(len(m_.polygons), bool)
    for p_ in m_.polygons:
        if mk[list(p_.vertices)].any(): touched[p_.index] = True
    cn = np.array([q.vector[:] for q in m_.corner_normals])
    vn = np.array([q.vector[:] for q in m_.vertex_normals])
    lv = np.array([l.vertex_index for l in m_.loops])
    pol_ = np.empty(len(m_.loops), int)
    for p_ in m_.polygons: pol_[p_.loop_start:p_.loop_start + p_.loop_total] = p_.index
    idx = np.nonzero(touched[pol_])[0]
    cn[idx] = vn[lv[idx]]
    m_.normals_split_custom_set([tuple(x) for x in cn])
    say('regnet om normaler på %d flater i %s' % (int(touched.sum()), n))

# Trærne i vollen følger bakken opp, ellers blir de stående for dypt.
for o in obj:
    if not o.name.startswith('TREE_'): continue
    xy = np.array([[o.location.x, o.location.y]])
    if not REGION.contains(Point(o.location.x, o.location.y)): continue
    g0 = dtm(xy); dz = float(lift_at(xy, g0)[0] - g0[0])
    if abs(dz) > 1e-3:
        o.location.z += dz
        say('hevet %s %.3f m med vollen' % (o.name, dz))

# Markørene settes ned på den nye putetoppen.
for o in MARK + [obj[n] for n in ('PROP_SignBoard', 'PROP_SignPost') if n in obj
                 and TEE.buffer(2.0).contains(Point(obj[n].location.x, obj[n].location.y))]:
    cs_ = [o.matrix_world @ v.co for v in o.data.vertices]
    x = sum(c.x for c in cs_) / len(cs_); y = sum(c.y for c in cs_) / len(cs_)
    zmin = min(c.z for c in cs_)
    gz = float(plane(np.array([[x, y]]))[0])
    o.location.z += gz - zmin
    say('satte %s ned på putetoppen (%.3f m)' % (o.name, gz - zmin))

for o in bpy.context.selected_objects: o.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=DST)

FWN = unary_union([FW_OLD, FW_ADD])
json.dump(dict(hole='byneset_south_01',
               fairway_added_m2=round(FW_ADD.area, 1),
               fairway_faces_moved=n_fw, semi_faces_moved=n_sm, tee_faces_moved=n_te,
               fairway_gap_to_green_m=round(FWN.distance(GREEN), 2),
               tee_front_m2=round(TEE.area, 1), tee_front_center=[float(TC[0]), float(TC[1])],
               tee_front_size_m=[TW, TL], tee_lift_m=LIFT, tee_bank_m=BANK,
               log=log), open(META, 'w'), indent=1)
say('lagret', DST)
