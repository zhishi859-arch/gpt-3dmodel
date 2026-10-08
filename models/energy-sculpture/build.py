import bpy, math, json
from mathutils import Vector
from pathlib import Path
OUT=Path(__file__).resolve().parent
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1
model=bpy.data.collections.new('WHITE_MODEL'); scene.collection.children.link(model)
studio=bpy.data.collections.new('STUDIO'); scene.collection.children.link(studio)
mat=bpy.data.materials.new('Uniform matte white'); mat.diffuse_color=(.82,.82,.82,1); mat.use_nodes=True
p=mat.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(.82,.82,.82,1); p.inputs['Roughness'].default_value=.55

def assign(obj,name,col=model):
    obj.name=name
    for c in list(obj.users_collection): c.objects.unlink(obj)
    col.objects.link(obj)
    if obj.type=='MESH':
        obj.data.materials.append(mat)
        for f in obj.data.polygons: f.use_smooth=True
    return obj

def ball(name,loc,r,scale=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,radius=r,location=loc)
    o=assign(bpy.context.object,name)
    if scale: o.scale=scale
    return o

def tube(name,points,r):
    c=bpy.data.curves.new(name,'CURVE'); c.dimensions='3D'; c.resolution_u=1; c.bevel_depth=r; c.bevel_resolution=3; c.use_fill_caps=True
    s=c.splines.new('POLY'); s.points.add(len(points)-1)
    for p,v in zip(s.points,points): p.co=(*v,1)
    o=bpy.data.objects.new(name,c); model.objects.link(o); c.materials.append(mat)
    return o

# Central solid crystal-like ovoid and axial spindle.
ball('Central ovoid core',(0,0,-.05),1, (.82,.72,1.12))
ball('Upper core',(0,0,1.0),.45,(.8,.8,1.7))
ball('Lower core',(0,0,-1.05),.42,(.82,.82,1.6))
tube('Continuous vertical axis',[(0,0,-3.93),(0,0,3.93)],.024)
# Closed thick ribbon surfaces with radial thickness; mirrored front/back twists.
N=224; W=10
for k in range(6):
    phase=k*math.tau/6
    verts=[]
    for i in range(N+1):
        t=i/N; z=-3.55+7.1*t
        env=math.sin(math.pi*t)**.82
        ang=phase+math.tau*(.72+.08*(k%3))*t+.65*math.sin(math.tau*t+phase)
        rad=env*(1.45+.52*math.sin(math.tau*t+phase))+.045
        width=(.16+.14*math.sin(math.pi*t+phase)**2)*env+.014
        for j in range(W+1):
            q=(j/W-.5)*2
            a=ang+q*width/max(rad,.12)
            zz=z+q*.16*env*math.sin(ang)
            rr=rad+.06*(1-q*q)*env
            verts.append((rr*math.cos(a),rr*.75*math.sin(a),zz))
    faces=[]
    for i in range(N):
        for j in range(W):
            a=i*(W+1)+j; faces.append((a,a+1,a+W+2,a+W+1))
    mesh=bpy.data.meshes.new('Ribbon surface'); mesh.from_pydata(verts,[],faces); mesh.update()
    o=bpy.data.objects.new('Twisting ribbon %02d'%(k+1),mesh); model.objects.link(o); o.data.materials.append(mat)
    for f in mesh.polygons:f.use_smooth=True
    sol=o.modifiers.new('Closed ribbon thickness','SOLIDIFY'); sol.thickness=.045; sol.offset=0
    bev=o.modifiers.new('Soft ribbon edges','BEVEL'); bev.width=.018; bev.segments=3
# Secondary filaments connect the two tips and weave around all sides.
for k in range(14):
    pts=[]; ph=k*math.tau/14
    for i in range(321):
        t=i/320; env=math.sin(math.pi*t)**.7; a=ph+math.tau*(1.15+(k%3)*.18)*t
        rr=(1.5+.35*math.sin(t*math.tau+ph))*env
        pts.append((rr*math.cos(a),.83*rr*math.sin(a),-3.65+7.3*t))
    tube('Weaving filament %02d'%(k+1),pts,.012+(k%3)*.004)
# Complete orbital ellipses: inclined in three dimensions, never just front arcs.
for k in range(9):
    az=.12+k*.48; incline=[.13,.38,.65,.92,1.12,1.35,.78,1.48,1.58][k]
    u=Vector((math.cos(az),math.sin(az),0))
    v=Vector((-math.sin(az)*math.cos(incline),math.cos(az)*math.cos(incline),math.sin(incline)))
    a=3.25 if k<4 else 2.48; b=1.36 if k<4 else 3.18
    center=Vector((0,0, .28*math.sin(k)))
    pts=[tuple(center+a*math.cos(t)*u+b*math.sin(t)*v) for t in [i*math.tau/400 for i in range(401)]]
    tube('Closed orbital ring %02d'%(k+1),pts,.014 if k%2 else .021)
    for j in range(3 if k<5 else 2):
        t=(j*.37+k*.113)*math.tau
        pos=center+a*math.cos(t)*u+b*math.sin(t)*v
        ball('Orbital sphere %02d_%02d'%(k+1,j+1),pos,.08+(.09 if (k+j)%3==0 else .02))
    for j in range(6):
        t=(j/8+k*.03)*math.tau
        pos=center+a*math.cos(t)*u+b*math.sin(t)*v
        ball('Orbit bead %02d_%02d'%(k+1,j+1),pos,.026)
# Finial beads and closed tapered tips.
for side in [-1,1]:
    for z,r in [(3.55,.16),(3.77,.075),(3.94,.035)]:ball('Axial finial', (0,0,side*z),r)
    bpy.ops.mesh.primitive_cone_add(vertices=48,radius1=.07 if side>0 else 0,radius2=0 if side>0 else .07,depth=.20,location=(0,0,side*3.9))
    assign(bpy.context.object,'Top tip' if side>0 else 'Bottom tip')
# Apply all geometry modifiers and curves for an independent solid mesh export.
bpy.ops.object.select_all(action='DESELECT')
for o in list(model.objects):o.select_set(True)
bpy.context.view_layer.objects.active=next(iter(model.objects))
bpy.ops.object.convert(target='MESH')
# Weld coincident curve cap/seam vertices into closed mesh surfaces.
import bmesh
for obj in model.objects:
    bm=bmesh.new(); bm.from_mesh(obj.data)
    if obj.name.startswith('Closed orbital'):
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if len(f.verts)>4], context='FACES_ONLY')
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.000001)
    boundary=[e for e in bm.edges if e.is_boundary]
    if boundary: bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data);bm.free();obj.data.update()
from mathutils import Vector
zs=[(o.matrix_world@Vector(c)).z for o in model.objects for c in o.bound_box]
s=8/(max(zs)-min(zs))
for o in model.objects:
    o.location*=s; o.scale*=s
bpy.context.view_layer.update()
bpy.ops.wm.obj_export(filepath=str(OUT/'energy_sculpture_white.obj'),export_selected_objects=True,export_materials=False)
bpy.ops.wm.stl_export(filepath=str(OUT/'energy_sculpture_white.stl'),export_selected_objects=True)
# Studio, separate collection so it can be hidden independently.
bpy.ops.object.camera_add(location=(0,-16,0)); cam=assign(bpy.context.object,'Preview camera',studio);cam.data.type='ORTHO';cam.data.ortho_scale=9.8;scene.camera=cam
for name,loc,power,size in [('Key',(-5,-6,7),1800,5),('Fill',(6,-4,1),900,4),('Rim',(2,5,5),2000,4)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=assign(bpy.context.object,name,studio);o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.055,.065,.08,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=False
scene.render.resolution_x=1000;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
bpy.ops.object.select_all(action='DESELECT')
for o in model.objects:o.select_set(True)
bpy.context.view_layer.objects.active=next(o for o in model.objects if o.name=='Central ovoid core')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D': area.spaces.active.region_3d.view_distance=12
for name,loc in [('front',(0,-16,0)),('perspective',(10,-16,7)),('back',(0,16,0)),('side',(16,0,0))]:
    cam.location=loc;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/('preview_'+name+'.png'))
    if name=='front':bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'energy_sculpture_white.blend'))
    bpy.ops.render.render(write_still=True)
# Audit loose edges and boundaries. Overlapping independent closed solids are intentional.
nonclosed=[]
for o in model.objects:
    import bmesh
    bm=bmesh.new();bm.from_mesh(o.data)
    count=sum(not e.is_manifold for e in bm.edges)
    if count:nonclosed.append((o.name,count))
    bm.free()
report={'height_m':8,'model_objects':len(model.objects),'vertices':sum(len(o.data.vertices) for o in model.objects),'non_manifold_objects':nonclosed,'note':'Separate overlapping closed parts; not Boolean-unioned for printing. Back geometry inferred from front reference.'}
(OUT/'geometry_report.json').write_text(json.dumps(report,indent=2))
print('MODEL_REPORT',json.dumps(report))
