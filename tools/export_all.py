import bpy,sys,os,json
src,outdir,name,mode=sys.argv[-4:]
bpy.ops.wm.open_mainfile(filepath=src)
common=dict(export_cameras=False,export_lights=False,export_yup=True,export_apply=True)
draco=dict(export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6,export_draco_position_quantization=16)
os.makedirs(outdir,exist_ok=True)
if mode in('plain','all'):
    bpy.ops.export_scene.gltf(filepath=f"{outdir}/{name}_plain.glb",export_format='GLB',export_draco_mesh_compression_enable=False,**common)
if mode=='all':
    bpy.ops.export_scene.gltf(filepath=f"{outdir}/{name}.glb",export_format='GLB',**common,**draco)
    os.makedirs(f"{outdir}/shared/holes",exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=f"{outdir}/shared/holes/{name}.gltf",export_format='GLTF_SEPARATE',export_texture_dir='../_tex',**common,**draco)
