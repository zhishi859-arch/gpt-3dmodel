import bpy
from mathutils import Vector
from pathlib import Path
out=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1, location=(0,0,0))
sphere=bpy.context.object
sphere.name='Sphere'
for p in sphere.data.polygons: p.use_smooth=True
mat=bpy.data.materials.new('Pearl White')
mat.diffuse_color=(0.72,0.76,0.82,1)
mat.use_nodes=True
bsdf=mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value=(0.72,0.76,0.82,1)
bsdf.inputs['Roughness'].default_value=0.28
sphere.data.materials.append(mat)
# Export only the editable sphere mesh.
bpy.ops.wm.obj_export(filepath=str(out/'sphere.obj'), export_selected_objects=True, export_materials=False)
bpy.ops.object.camera_add(location=(3,-5,2.5))
cam=bpy.context.object
cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO'
cam.data.ortho_scale=3.2
bpy.context.scene.camera=cam
for name,loc,power,size in [('Key',(-3,-4,5),600,4),('Fill',(4,-2,2),250,3),('Rim',(1,3,4),450,3)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    light=bpy.context.object
    light.name=name
    light.data.energy=power
    light.data.size=size
    light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
scene=bpy.context.scene
scene.world.color=(0.12,0.12,0.12)
scene.render.engine='CYCLES'; scene.cycles.samples=32; scene.cycles.use_denoising=False
scene.render.resolution_x=800
scene.render.resolution_y=800
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(out/'sphere_preview.png')
bpy.ops.object.select_all(action='DESELECT')
sphere.select_set(True)
bpy.context.view_layer.objects.active=sphere
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=4
            area.spaces.active.region_3d.view_location=(0,0,0)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'sphere.blend'))
assert len(sphere.data.vertices)==1986
assert all(abs(v.co.length-1)<1e-5 for v in sphere.data.vertices)
bpy.ops.render.render(write_still=True)
print('SPHERE_OK', len(sphere.data.vertices), len(sphere.data.polygons))
