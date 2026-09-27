"""Byneset-verktøy for Blender 5.2.

Legger til en fane «Byneset» i sidepanelet i 3D-vinduet med knapper for de
tingene som er lette å gjøre feil manuelt: å sette ting ned på bakken, å
kopiere trær, og å eksportere med de samme innstillingene som originalfilene.

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

import bpy, math, random, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# Flatene som regnes som «bakken» å sette ting oppå
GROUND = ('SURF_Rough', 'SURF_Fairway', 'SURF_Semi', 'SURF_Green', 'SURF_Fringe',
          'SURF_Tee', 'SURF_Sand', 'SURF_Hay', 'SURF_Field', 'SURF_Gravel',
          'SURF_Road', 'SURF_Far')

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
        L.operator("byneset.drop", icon='TRIA_DOWN_BAR')
        L.operator("byneset.dup_tree", icon='DUPLICATE')
        L.separator()
        L.operator("byneset.export", icon='EXPORT')
        L.label(text="Husk å lagre (Ctrl+S) først")


CLASSES = (BYNESET_OT_drop, BYNESET_OT_dup_tree, BYNESET_OT_export, BYNESET_PT_panel)


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
