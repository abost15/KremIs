"""Byneset-verktøy for Blender 5.2.

Legger til en fane «Byneset» i sidepanelet i 3D-vinduet med knapper for de
tingene som er lette å gjøre feil manuelt: å klippe gresset om (flytte flater
mellom green, fairway, semi, rough og tee), å bygge et teested, å sette ting ned
på bakken, å kopiere trær, og å eksportere med de samme innstillingene som
originalfilene.

Slik tar du det i bruk:
  1. Åpne hullfila i Blender.
  2. Gå til fanen «Scripting» øverst.
  3. Trykk «Open» og velg denne fila, og trykk så på play-knappen (Run Script).
  4. Gå tilbake til «Layout» og trykk N for å få fram sidepanelet.
     Fanen «Byneset» ligger der.

Du må kjøre skriptet på nytt hver gang du åpner Blender.
"""

bl_info = {
    "name": "Byneset-verktøy",
    "author": "Byneset golfmodell",
    "version": (1, 0),
    "blender": (5, 2, 0),
    "location": "3D-vindu > sidepanel (N) > Byneset",
    "category": "Object",
}

import bpy, bmesh, math, random, os
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# Flatene som regnes som «bakken» å sette ting oppå
GROUND = ('SURF_Rough', 'SURF_Fairway', 'SURF_Semi', 'SURF_Green', 'SURF_Fringe',
          'SURF_Tee', 'SURF_Sand', 'SURF_Hay', 'SURF_Field', 'SURF_Gravel',
          'SURF_Road', 'SURF_Far')

# Flatene som kan klippes om til hverandre. Green, forgreen og bunkere er med,
# men de har egne kanter mot resten, så vær forsiktig der.
MOWABLE = ('SURF_Fairway', 'SURF_Semi', 'SURF_Rough', 'SURF_Tee', 'SURF_Hay',
           'SURF_Field', 'SURF_Green', 'SURF_Fringe', 'SURF_Sand')

# Teeputene på anlegget er målt til helt plane flater med 0,2–0,5 % fall, som
# ligger 0,135–0,150 m over terrenget rundt.
TEE_LIFT = 0.148
TEE_SLOPE = 0.005

# Trærne står med vilje litt ned i bakken, så stammefoten ikke svever på ujevnt
# underlag. Målt på flere hull: ca. 25 cm.
SINK = 0.25


def _sink(obj):
    return SINK if obj.name.startswith('TREE_') else 0.0


def _group(obj):
    """Ting som hører sammen og må flyttes samlet (pinne, skilt, nett)."""
    n = obj.name
    if n.startswith('PIN_'):
        return 'PIN'
    if n.startswith('PROP_Sign'):
        return 'SIGN'
    if n.startswith('NET_'):
        return 'NET_' + n.rsplit('_', 1)[-1]
    return n


def _ground_trees(context):
    dg = context.evaluated_depsgraph_get()
    out = []
    for n in GROUND:
        o = bpy.data.objects.get(n)
        if o and o.type == 'MESH':
            try:
                out.append(BVHTree.FromObject(o, dg))
            except Exception:
                pass
    return out


def _ground_z(trees, x, y):
    """Høyden på bakken i punktet (x, y), eller None om det ikke er bakke der."""
    best = None
    for t in trees:
        hit = t.ray_cast(Vector((x, y, 500.0)), Vector((0, 0, -1)))
        if hit[0] is not None and (best is None or hit[0].z > best):
            best = hit[0].z
    return best


def _world_bounds(obj):
    cs = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return (min(c.x for c in cs) + max(c.x for c in cs)) / 2, \
           (min(c.y for c in cs) + max(c.y for c in cs)) / 2, \
           min(c.z for c in cs)


def _pin(context):
    for n in ('PIN_Cup', 'PIN_Stick', 'PIN_Flag'):
        o = bpy.data.objects.get(n)
        if o and o.type == 'MESH' and len(o.data.vertices):
            cs = [o.matrix_world @ v.co for v in o.data.vertices]
            return Vector((sum(c.x for c in cs) / len(cs), sum(c.y for c in cs) / len(cs), 0))
    return None


# ---------------------------------------------------------------- klippe om
# Bakken består av 0,3–1 m store trekanter. Å klippe gresset om er derfor bare å
# flytte flater fra ett objekt til et annet. Punktene blir stående der de står,
# så det kan ikke bli glipe mellom flatene. Fargene (med innbakt skygge fra
# trærne) og normalene følger med, mens UV-en regnes om til den nye teksturen.

def _uv_fit(me):
    """Finner sammenhengen UV = posisjon * skala for en flate."""
    uv = me.uv_layers.active.data; L = []; U = []
    for p in me.polygons[:4000]:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            L.append([v.x, v.y, 1]); U.append(uv[li].uv[:])
    return np.linalg.lstsq(np.array(L), np.array(U), rcond=None)[0]


def _transfer(src, dst, idxs):
    """Flytter flatene med disse numrene fra src til dst. Krever objektmodus."""
    if not idxs:
        return 0
    U = _uv_fit(dst.data)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    src.select_set(True); bpy.context.view_layer.objects.active = src
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(src.data); bm.faces.ensure_lookup_table()
    for f in bm.faces: f.select_set(False)
    for e in bm.edges: e.select_set(False)
    for v in bm.verts: v.select_set(False)
    for i in idxs: bm.faces[i].select_set(True)
    bmesh.update_edit_mesh(src.data)
    before = set(bpy.data.objects.keys())
    bpy.ops.mesh.separate(type='SELECTED')
    bpy.ops.object.mode_set(mode='OBJECT')
    part = [bpy.data.objects[k] for k in bpy.data.objects.keys() if k not in before]
    if len(part) != 1:
        return 0
    part = part[0]
    part.data.materials.clear(); part.data.materials.append(dst.data.materials[0])
    a = part.data.attributes.new('mv', 'INT', 'FACE')
    for d in a.data: d.value = 1
    with bpy.context.temp_override(active_object=dst, selected_editable_objects=[dst, part]):
        bpy.ops.object.join()
    me = dst.data; mv = me.attributes.get('mv')
    if mv is not None:
        flag = [d.value for d in mv.data]; uv = me.uv_layers.active.data
        for p in me.polygons:
            if not flag[p.index]: continue
            for li in p.loop_indices:
                v = me.vertices[me.loops[li].vertex_index].co
                uv[li].uv = (v.x * U[0][0] + v.y * U[1][0] + U[2][0],
                             v.x * U[0][1] + v.y * U[1][1] + U[2][1])
        me.attributes.remove(me.attributes['mv'])
    me.update()
    return len(idxs)


class BYNESET_OT_remow(bpy.types.Operator):
    """Klipper de valgte flatene som en annen gresstype"""
    bl_idname = "byneset.remow"
    bl_label = "Klipp valgte flater som"
    bl_options = {'REGISTER', 'UNDO'}

    target: bpy.props.EnumProperty(
        name="Klipp som",
        items=[(n, n[5:], "") for n in MOWABLE])

    def execute(self, context):
        src = context.edit_object
        if src is None or src.name not in MOWABLE:
            self.report({'WARNING'}, "Gå i Edit-modus på en bakkeflate og velg noen flater")
            return {'CANCELLED'}
        if src.name == self.target:
            self.report({'WARNING'}, "Flatene er alt klippet slik")
            return {'CANCELLED'}
        dst = bpy.data.objects.get(self.target)
        if dst is None:
            self.report({'ERROR'}, self.target + " finnes ikke i denne fila")
            return {'CANCELLED'}
        bm = bmesh.from_edit_mesh(src.data)
        idxs = [f.index for f in bm.faces if f.select]
        if not idxs:
            self.report({'WARNING'}, "Ingen flater er valgt")
            return {'CANCELLED'}
        if len(idxs) == len(bm.faces):
            self.report({'WARNING'}, "Kan ikke flytte alle flatene i " + src.name)
            return {'CANCELLED'}
        bpy.ops.object.mode_set(mode='OBJECT')
        n = _transfer(src, dst, idxs)
        for o in context.selected_objects: o.select_set(False)
        src.select_set(True); context.view_layer.objects.active = src
        bpy.ops.object.mode_set(mode='EDIT')
        self.report({'INFO'}, "Klippet %d flater som %s" % (n, self.target[5:]))
        return {'FINISHED'}


# ---------------------------------------------------------------- teested
def _rounded_rect(cx, cy, w, l, r, ang, step=1.0):
    """Omrisset av en teepute: rektangel med avrundede hjørner, som de andre."""
    r = min(r, w / 2 - 0.01, l / 2 - 0.01)
    hw, hl = w / 2 - r, l / 2 - r
    pts = []
    for ox, oy, a0 in ((hw, hl, 0), (-hw, hl, 90), (-hw, -hl, 180), (hw, -hl, 270)):
        for k in range(9):
            a = math.radians(a0 + k * 90 / 8)
            pts.append((ox + r * math.cos(a), oy + r * math.sin(a)))
    P = np.array(pts); cs, sn = math.cos(ang), math.sin(ang)
    R = np.stack([cx + cs * P[:, 0] - sn * P[:, 1],
                  cy + sn * P[:, 0] + cs * P[:, 1]], 1)
    q = np.vstack([R, R[:1]]); seg = np.linalg.norm(np.diff(q, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)]); n = max(16, int(round(cum[-1] / step)))
    t = np.linspace(0, cum[-1], n, endpoint=False)
    return np.stack([np.interp(t, cum, q[:, 0]), np.interp(t, cum, q[:, 1])], 1)


def _area(pol):
    x, y = pol[:, 0], pol[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def _inside(pol, pts):
    pts = np.atleast_2d(pts); x, y = pts[:, 0], pts[:, 1]
    res = np.zeros(len(pts), bool); j = len(pol) - 1
    for i in range(len(pol)):
        xi, yi = pol[i]; xj, yj = pol[j]
        res ^= ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi); j = i
    return res


def _seg_dist(pol, pts):
    pts = np.atleast_2d(pts); d = np.full(len(pts), np.inf)
    for p0, p1 in zip(pol, np.roll(pol, -1, 0)):
        v = p1 - p0; w = pts - p0; t = np.clip((w @ v) / (v @ v), 0, 1)
        d = np.minimum(d, np.linalg.norm(w - np.outer(t, v), axis=1))
    return d


def _ground_objs():
    return [bpy.data.objects[n] for n in GROUND
            if n in bpy.data.objects and bpy.data.objects[n].type == 'MESH']


class BYNESET_OT_tee_pad(bpy.types.Operator):
    """Bygger et teested der 3D-markøren står"""
    bl_idname = "byneset.tee_pad"
    bl_label = "Bygg teested her"
    bl_options = {'REGISTER', 'UNDO'}

    width: bpy.props.FloatProperty(name="Bredde", default=7.0, min=2.0, max=40.0, unit='LENGTH')
    length: bpy.props.FloatProperty(name="Lengde", default=17.0, min=2.0, max=60.0, unit='LENGTH')
    angle: bpy.props.FloatProperty(name="Retning", default=0.0, min=-180.0, max=180.0,
                                   description="Grader fra retningen mot pinnen")
    to_pin: bpy.props.BoolProperty(name="Langs retningen mot pinnen", default=True)
    corner: bpy.props.FloatProperty(name="Hjørnerunding", default=2.0, min=0.0, max=10.0, unit='LENGTH')
    lift: bpy.props.FloatProperty(name="Høyde over terrenget", default=TEE_LIFT, min=0.0, max=1.5,
                                  unit='LENGTH')
    bank: bpy.props.FloatProperty(name="Voll ut i roughen", default=2.0, min=0.3, max=8.0, unit='LENGTH')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        tee = bpy.data.objects.get('SURF_Tee')
        if tee is None:
            self.report({'ERROR'}, "Fila har ingen SURF_Tee")
            return {'CANCELLED'}
        c = context.scene.cursor.location
        ang = math.radians(self.angle)
        if self.to_pin:
            pin = _pin(context)
            if pin is not None:
                ang += math.atan2(pin.y - c.y, pin.x - c.x) - math.pi / 2
        ringpts = _rounded_rect(c.x, c.y, self.width, self.length, self.corner, ang)

        # 1) bakken inne i omrisset klippes som teested
        moved = 0
        for o in _ground_objs():
            if o.name == 'SURF_Tee' or o.name not in MOWABLE: continue
            V = np.array([v.co[:] for v in o.data.vertices])
            if not len(V): continue
            idxs = []
            for f in o.data.polygons:
                m = V[list(f.vertices)].mean(0)
                if _inside(ringpts, m[None])[0]: idxs.append(f.index)
            if idxs and len(idxs) < len(o.data.polygons):
                moved += _transfer(o, tee, idxs)
        if not moved:
            self.report({'WARNING'}, "Fant ingen bakkeflater under markøren")
            return {'CANCELLED'}

        # 2) putetoppen: et plan som følger terrenget, men høyst 0,5 % fall
        V = np.array([v.co[:] for v in tee.data.vertices])
        ins = _inside(ringpts, V[:, :2])
        if ins.sum() < 3:
            self.report({'WARNING'}, "For få punkt inne i omrisset")
            return {'CANCELLED'}
        Q = V[ins]; A = np.c_[Q[:, 0], Q[:, 1], np.ones(len(Q))]
        a, b, k = np.linalg.lstsq(A, Q[:, 2], rcond=None)[0]
        sl = math.hypot(a, b)
        if sl > TEE_SLOPE:
            a, b = a * TEE_SLOPE / sl, b * TEE_SLOPE / sl
        k = float(Q[:, 2].mean() - (a * Q[:, 0] + b * Q[:, 1]).mean())

        def plane(xy):
            return a * xy[:, 0] + b * xy[:, 1] + k + self.lift

        # 3) høyden er én funksjon av posisjonen, brukt på alle bakkeflatene. Da
        #    får punkter som deles mellom to flater samme høyde, og skjøtene
        #    holder. Vollen havner i roughen, som rundt de andre teeputene.
        changed = {}
        for o in _ground_objs():
            me = o.data
            W = np.array([v.co[:] for v in me.vertices])
            if not len(W): continue
            dd = _seg_dist(ringpts, W[:, :2])
            sel = _inside(ringpts, W[:, :2]) | (dd < self.bank)
            if not sel.any(): continue
            u = np.where(_inside(ringpts, W[:, :2]), 1.0, np.clip(1.0 - dd / self.bank, 0, 1))
            wgt = u * u * (3 - 2 * u)
            zn = W[:, 2] + (plane(W[:, :2]) - W[:, 2]) * wgt
            ch = sel & (np.abs(zn - W[:, 2]) > 1e-6)
            for i in np.nonzero(ch)[0]:
                me.vertices[i].co.z = float(zn[i])
            if ch.any():
                me.update(); changed[o.name] = ch

        # 4) normalene på de endrede flatene regnes om, ellers blir lyset feil
        for n, ch in changed.items():
            me = bpy.data.objects[n].data
            if not me.has_custom_normals: continue
            touched = np.zeros(len(me.polygons), bool)
            for p in me.polygons:
                if ch[list(p.vertices)].any(): touched[p.index] = True
            cn = np.array([q.vector[:] for q in me.corner_normals])
            vn = np.array([q.vector[:] for q in me.vertex_normals])
            lv = np.array([l.vertex_index for l in me.loops])
            pol = np.empty(len(me.loops), int)
            for p in me.polygons: pol[p.loop_start:p.loop_start + p.loop_total] = p.index
            idx = np.nonzero(touched[pol])[0]
            cn[idx] = vn[lv[idx]]
            me.normals_split_custom_set([tuple(x) for x in cn])

        # 5) markører, skilt og trær i vollen settes ned på nytt
        context.view_layer.update()
        trees = _ground_trees(context)
        for o in bpy.data.objects:
            if o.type != 'MESH' or o.name.startswith(('SURF_', 'FAR_', 'BLD_', 'PIN_')): continue
            x, y, zmin = _world_bounds(o)
            if not (_inside(ringpts, np.array([[x, y]]))[0]
                    or _seg_dist(ringpts, np.array([[x, y]]))[0] < self.bank):
                continue
            gz = _ground_z(trees, x, y)
            if gz is not None:
                o.location.z += gz - _sink(o) - zmin
        context.view_layer.update()
        self.report({'INFO'}, "Teested på %.0f m2: klippet om %d flater, %.1f %% fall"
                    % (_area(ringpts), moved,
                       100 * math.hypot(a, b)))
        return {'FINISHED'}


class BYNESET_OT_drop(bpy.types.Operator):
    """Setter det som er valgt ned på bakken, uten å flytte det sidelengs"""
    bl_idname = "byneset.drop"
    bl_label = "Sett ned på bakken"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sel = [o for o in context.selected_objects if o.type in ('MESH', 'EMPTY')]
        if not sel:
            self.report({'WARNING'}, "Velg noe først")
            return {'CANCELLED'}
        context.view_layer.update()
        trees = _ground_trees(context)
        if not trees:
            self.report({'ERROR'}, "Fant ingen bakkeflater i fila")
            return {'CANCELLED'}
        groups = {}
        blocked = False
        for o in sel:
            if o.name.startswith(('SURF_', 'FAR_', 'CAM_', 'SUN_')):
                continue        # bakken og kameraene skal ikke settes ned
            if o.name.startswith('PIN_'):
                blocked = True  # koppen ligger nedsenket i greenen, og posisjonen
                continue        # styres av hulldataene
            groups.setdefault(_group(o), []).append(o)
        if blocked:
            self.report({'WARNING'}, "Pinnen hoppet jeg over: den styres av hulldataene")
        n = miss = 0
        for members in groups.values():
            pts = [_world_bounds(o) for o in members]
            x = sum(p[0] for p in pts) / len(pts)
            y = sum(p[1] for p in pts) / len(pts)
            zmin = min(p[2] for p in pts)
            gz = _ground_z(trees, x, y)
            if gz is None:
                miss += 1
                continue
            dz = gz - _sink(members[0]) - zmin
            for o in members:
                o.location.z += dz
            n += len(members)
        context.view_layer.update()
        msg = f"Satte ned {n} objekt"
        if miss:
            msg += f" ({miss} hadde ingen bakke under seg)"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class BYNESET_OT_dup_tree(bpy.types.Operator):
    """Lager en kopi av det valgte treet der 3D-markøren står"""
    bl_idname = "byneset.dup_tree"
    bl_label = "Kopier tre hit"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        src = context.active_object
        if src is None or not src.name.startswith('TREE_'):
            self.report({'WARNING'}, "Velg et tre (TREE_...) først")
            return {'CANCELLED'}
        c = context.scene.cursor.location
        new = src.copy()             # deler mesh med originalen, så fila vokser lite
        base = '_'.join(src.name.split('_')[:2])
        i = 1
        while f"{base}_ny{i:03d}" in bpy.data.objects:
            i += 1
        new.name = f"{base}_ny{i:03d}"
        for col in src.users_collection:
            col.objects.link(new)
        new.location = (c.x, c.y, src.location.z)
        new.rotation_euler = (src.rotation_euler.x, src.rotation_euler.y,
                              random.uniform(0, 2 * math.pi))
        s = random.uniform(0.9, 1.12)
        new.scale = (src.scale.x * s, src.scale.y * s, src.scale.z * s)
        context.view_layer.update()
        trees = _ground_trees(context)
        x, y, zmin = _world_bounds(new)
        gz = _ground_z(trees, x, y)
        if gz is not None:
            new.location.z += gz - SINK - zmin
        context.view_layer.update()
        for o in context.selected_objects:
            o.select_set(False)
        new.select_set(True)
        context.view_layer.objects.active = new
        self.report({'INFO'}, f"Laget {new.name}")
        return {'FINISHED'}


class BYNESET_OT_export(bpy.types.Operator):
    """Eksporterer GLB med de samme innstillingene som originalfilene"""
    bl_idname = "byneset.export"
    bl_label = "Eksporter GLB"
    bl_options = {'REGISTER'}

    def execute(self, context):
        p = bpy.data.filepath
        if not p:
            self.report({'ERROR'}, "Lagre .blend-fila først")
            return {'CANCELLED'}
        d = os.path.dirname(p)
        name = os.path.splitext(os.path.basename(p))[0]
        common = dict(export_cameras=False, export_lights=False, export_yup=True,
                      export_apply=True)
        bpy.ops.export_scene.gltf(
            filepath=os.path.join(d, name + '.glb'), export_format='GLB',
            export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=6,
            export_draco_position_quantization=16, **common)
        bpy.ops.export_scene.gltf(
            filepath=os.path.join(d, name + '_plain.glb'), export_format='GLB',
            export_draco_mesh_compression_enable=False, **common)
        self.report({'INFO'}, f"Eksporterte {name}.glb og {name}_plain.glb")
        return {'FINISHED'}


class BYNESET_PT_panel(bpy.types.Panel):
    bl_label = "Byneset"
    bl_idname = "BYNESET_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Byneset"

    def draw(self, context):
        L = self.layout
        o = context.active_object

        box = L.box()
        box.label(text="Valgt objekt", icon='OBJECT_DATA')
        if o is None:
            box.label(text="ingenting valgt")
        else:
            box.label(text=o.name)
            x, y, zmin = _world_bounds(o)
            box.label(text=f"x {x:.1f} m,  y {y:.1f} m")
            pin = _pin(context)
            if pin is not None:
                box.label(text=f"{(Vector((x, y, 0)) - pin).length:.0f} m til pinnen")
            gz = None if o.name.startswith(('SURF_', 'FAR_', 'CAM_', 'SUN_', 'PIN_')) \
                else _ground_z(_ground_trees(context), x, y)
            if gz is None:
                box.label(text="—")
            else:
                d = zmin - (gz - _sink(o))
                box.label(text=("står riktig" if abs(d) < 0.06 else
                                f"{abs(d):.2f} m for {'høyt' if d > 0 else 'lavt'}"),
                          icon='CHECKMARK' if abs(d) < 0.06 else 'ERROR')

        L.separator()
        box = L.box()
        box.label(text="Klippe om gresset", icon='BRUSH_DATA')
        if context.mode == 'EDIT_MESH' and o is not None and o.name in MOWABLE:
            box.label(text="Valgte flater i " + o.name[5:] + " klippes som:")
            for n in ('SURF_Fairway', 'SURF_Semi', 'SURF_Rough', 'SURF_Tee'):
                if n == o.name or n not in bpy.data.objects: continue
                box.operator("byneset.remow", text=n[5:]).target = n
            r = box.row()
            for n in ('SURF_Green', 'SURF_Fringe', 'SURF_Sand'):
                if n == o.name or n not in bpy.data.objects: continue
                r.operator("byneset.remow", text=n[5:]).target = n
        else:
            box.label(text="Velg en bakkeflate og trykk Tab")
            box.label(text="for å komme i Edit-modus")
        L.operator("byneset.tee_pad", icon='MESH_PLANE')

        L.separator()
        L.operator("byneset.drop", icon='TRIA_DOWN_BAR')
        L.operator("byneset.dup_tree", icon='DUPLICATE')
        L.separator()
        L.operator("byneset.export", icon='EXPORT')
        L.label(text="Husk å lagre (Ctrl+S) først")


CLASSES = (BYNESET_OT_remow, BYNESET_OT_tee_pad, BYNESET_OT_drop, BYNESET_OT_dup_tree,
           BYNESET_OT_export, BYNESET_PT_panel)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    try:
        unregister()
    except Exception:
        pass
    register()
    print("Byneset-verktøy er lastet. Trykk N i 3D-vinduet og velg fanen «Byneset».")
