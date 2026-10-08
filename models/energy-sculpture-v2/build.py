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
    c=bpy.data.curves.new(name,'CURVE'); c.dimensions='3D'; c.resolution_u=1; c.bevel_depth=r; c.bevel_resolution=2; c.use_fill_caps=True
    closed=(Vector(points[0])-Vector(points[-1])).length<1e-5
    if closed: points=points[:-1]
    s=c.splines.new('POLY'); s.points.add(len(points)-1); s.use_cyclic_u=closed
    for p,v in zip(s.points,points): p.co=(*v,1)
    o=bpy.data.objects.new(name,c); model.objects.link(o); c.materials.append(mat)
    return o

# Multi-view reference reconstruction: rounded, curling sheets around a visible core.
core=[]; ribbons=[]; orbital_nodes=[]
core.append(ball('Rotating central core',(0,0,0),.78,(1,1,1.14)))
# Visible core wire lattice: meridians, latitude loops, diagonal winding lines.
for k in range(10):
    a=k*math.tau/10
    pts=[]
    for j in range(193):
        t=j*math.tau/192
        pts.append((.805*math.cos(t)*math.cos(a),.805*math.cos(t)*math.sin(a),.91*math.sin(t)))
    core.append(tube('Core meridian %02d'%k,pts,.008))
for k in range(5):
    z=-.62+k*.31; rad=.805*math.sqrt(1-(z/.91)**2)
    core.append(tube('Core latitude %02d'%k,[(rad*math.cos(j*math.tau/192),rad*math.sin(j*math.tau/192),z) for j in range(193)],.008))
for k in range(6):
    pts=[]
    for j in range(161):
        t=j/160; z=-.87+1.74*t; rad=.816*math.sqrt(max(.01,1-(z/.93)**2)); a=k*math.tau/6+t*math.tau*1.4
        pts.append((rad*math.cos(a),rad*math.sin(a),z))
    core.append(tube('Core spiral relief %02d'%k,pts,.009))
for z in [-.57,0,.57]:core.append(ball('Axial core pearl',(0,-.72,z),.048))
tube('Continuous axial spine',[(0,0,-4),(0,0,4)],.015)
# Non-monotonic z and angular oscillation produce curled lobes rather than regular helices.
N=240; W=12
for k in range(5):
    ph=k*math.tau/5
    def surface(t,q):
        env=math.sin(math.pi*t)**.7
        a=ph+math.tau*(.68+.07*(k%2))*t+.9*math.sin(math.tau*t+ph)+.24*math.sin(4*math.pi*t+ph)
        r=.025+env*(1.26+.61*math.sin(3*math.pi*t+ph)+.18*math.sin(7*math.pi*t-ph))
        z=-3.76+7.52*t+.46*env*math.sin(4*math.pi*t+ph)
        hw=.025+env*(.25+.21*math.sin(2*math.pi*t+ph)**2)
        # Alternating sheet bank introduces bulging horizontal petals in top view.
        bank=.78*math.sin(3*math.pi*t+ph)+.3
        dr=q*hw*math.sin(bank)
        da=q*hw*math.cos(bank)/max(r,.18)
        rr=r+dr+.12*(1-q*q)*env
        return (rr*math.cos(a+da),rr*math.sin(a+da),z+q*hw*.68*math.cos(bank))
    verts=[surface(i/N,2*j/W-1) for i in range(N+1) for j in range(W+1)]
    faces=[]
    for i in range(N):
        for j in range(W):
            n=i*(W+1)+j;faces.append((n,n+1,n+W+2,n+W+1))
    mesh=bpy.data.meshes.new('Flowing sheet');mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new('Primary curling ribbon %02d'%(k+1),mesh);model.objects.link(o);mesh.materials.append(mat)
    for f in mesh.polygons:f.use_smooth=True
    m=o.modifiers.new('Closed sheet thickness','SOLIDIFY');m.thickness=.035;m.offset=0
    m=o.modifiers.new('Rounded sheet edges','BEVEL');m.width=.012;m.segments=2
    ribbons.append(o)
    for j,q in enumerate([-.98,-.56,0,.56,.98]):
        ribbons.append(tube('Ribbon %02d raised vein %02d'%(k+1,j+1),[surface(i/N,q) for i in range(N+1)],.008 if abs(q)<.9 else .013))
# Slender continuously flowing companion strands across the front, side and back.
for k in range(15):
    ph=k*math.tau/15; pts=[]
    for j in range(241):
        t=j/240;env=math.sin(math.pi*t)**.72
        a=ph+math.tau*(.78+.13*(k%3))*t+.7*math.sin(3*math.pi*t+ph)
        r=.035+env*(1.38+.5*math.sin(3*math.pi*t+ph))
        pts.append((r*math.cos(a),r*math.sin(a),-3.85+7.7*t+.3*env*math.sin(4*math.pi*t+ph)))
    ribbons.append(tube('Companion flowing filament %02d'%k,pts,.007+(k%3)*.003))
# Full elliptical trajectories in diverse planes, with sparse large orbiting spheres.
orbits=[]
for k in range(10):
    az=k*math.pi/5+.12
    tilt=[.12,.34,.52,.70,.9,1.1,1.28,1.4,.8,1.52][k]
    u=Vector((math.cos(az),math.sin(az),0))
    v=Vector((-math.sin(az)*math.cos(tilt),math.cos(az)*math.cos(tilt),math.sin(tilt)))
    a=3.04 if k<5 else 2.62; b=1.6 if k<5 else 3.15
    center=Vector((0,0,.12*math.sin(k)))
    def point(t):return center+a*math.cos(t)*u+b*math.sin(t)*v
    o=tube('Closed orbit %02d'%(k+1),[tuple(point(j*math.tau/240)) for j in range(240)],.009+(k%3)*.002)
    o.data.splines[0].use_cyclic_u=True;orbits.append(o)
    for j in range(2):
        t=math.tau*(.14*k+.41*j+.06)
        o=ball('Orbiting sphere %02d_%02d'%(k+1,j+1),point(t),.075+.10*((k+j)%3==0))
        orbital_nodes.append((o,center.copy(),u.copy(),v.copy(),a,b,t))
    for j in range(7):
        o=ball('Small orbit pearl %02d_%02d'%(k+1,j+1),point(math.tau*(j/7+k*.025)),.018+(j%3)*.008)
        orbits.append(o)
# Finials continue the axis above and below the major curled sheets.
for sign in [-1,1]:
    for z,r in [(3.79,.17),(4.05,.10),(4.28,.05)]:ball('Finial pearl', (0,0,sign*z),r)
    bpy.ops.mesh.primitive_cone_add(vertices=32,radius1=.038 if sign>0 else 0,radius2=0 if sign>0 else .038,depth=.14,location=(0,0,sign*4.37))
    assign(bpy.context.object,'Terminal tip')
# Convert every piece and weld curve caps into manifold surfaces.
bpy.ops.object.select_all(action='DESELECT')
for o in model.objects:o.select_set(True)
bpy.context.view_layer.objects.active=next(iter(model.objects));bpy.ops.object.convert(target='MESH')
import bmesh
for o in model.objects:
    bm=bmesh.new();bm.from_mesh(o.data)
    if o.name.startswith(('Core meridian','Core latitude')):
        bmesh.ops.delete(bm,geom=[f for f in bm.faces if len(f.verts)>4],context='FACES_ONLY')
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    edges=[e for e in bm.edges if e.is_boundary]
    if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
# Match measured world-space bounding box exactly: X 6.5, Y 6.5, Z 8 metres.
bpy.context.view_layer.update()
coords=[o.matrix_world@Vector(v) for o in model.objects for v in o.bound_box]
lo=Vector([min(v[i] for v in coords) for i in range(3)]);hi=Vector([max(v[i] for v in coords) for i in range(3)])
mid=(lo+hi)/2; factors=Vector([6.5/(hi.x-lo.x),6.5/(hi.y-lo.y),8/(hi.z-lo.z)])
for o in model.objects:
    o.location=Vector([(o.location[i]-mid[i])*factors[i] for i in range(3)])
    o.scale=Vector([o.scale[i]*factors[i] for i in range(3)])
bpy.context.view_layer.update()
bpy.ops.wm.obj_export(filepath=str(OUT/'white_model_8m.obj'),export_selected_objects=True,export_materials=False)
bpy.ops.wm.stl_export(filepath=str(OUT/'white_model_8m.stl'),export_selected_objects=True)
# Native Blender animation: separate core spin, exact ellipse traversal and breathing.
rig=bpy.data.collections.new('MOTION_CONTROLS');scene.collection.children.link(rig)
def control(name):
    o=bpy.data.objects.new(name,None);rig.objects.link(o);return o
spin=control('Core spin');breath=control('Ribbon breathing')
for o in core:
    o.parent=spin
for o in ribbons:o.parent=breath
scene.frame_start=1;scene.frame_end=241;scene.render.fps=24
for f,a in [(1,0),(241,math.tau)]:spin.rotation_euler.z=a;spin.keyframe_insert(data_path='rotation_euler',frame=f)
for f,sc in [(1,1),(61,.84),(121,1),(181,1.10),(241,1)]:
    breath.scale=(sc,sc,1);breath.keyframe_insert(data_path='scale',frame=f)
for o,center,u,v,a,b,t0 in orbital_nodes:
    for f in range(1,242,10):
        t=t0+(f-1)/240*math.tau
        pos=center+a*math.cos(t)*u+b*math.sin(t)*v
        o.location=Vector([(pos[i]-mid[i])*factors[i] for i in range(3)])
        o.keyframe_insert(data_path='location',frame=f)
for o in [spin]+[entry[0] for entry in orbital_nodes]:
    if o.animation_data:
        for fc in o.animation_data.action.fcurves:
            for k in fc.keyframe_points:k.interpolation='LINEAR'
scene.frame_set(1)
# Actual geometry audit at the reference rest pose.
bpy.context.view_layer.update()
coords=[o.matrix_world@Vector(v) for o in model.objects for v in o.bound_box]
dims=[max(v[i] for v in coords)-min(v[i] for v in coords) for i in range(3)]
non=[]
for o in model.objects:
    bm=bmesh.new();bm.from_mesh(o.data);n=sum(not e.is_manifold for e in bm.edges);bm.free()
    if n:non.append({'object':o.name,'edges':n})
report={'dimensions_xyz_m':dims,'rest_pose_frame':1,'model_objects':len(model.objects),'vertices':sum(len(o.data.vertices) for o in model.objects),'non_manifold_objects':non,'primary_ribbons':5,'raised_ribbon_veins':25,'companion_filaments':15,'closed_orbits':10,'animated_orbit_spheres':20,'animation_frames':[1,241],'note':'Multi-view concept reconstruction, independent closed solids with intersections; no manufacturing Boolean union.'}
(OUT/'geometry_report.json').write_text(json.dumps(report,indent=2))
assert not non, non
assert all(abs(x-y)<1e-4 for x,y in zip(dims,[6.5,6.5,8])),dims
# Separate neutral-white studio.
bpy.ops.object.camera_add(location=(0,-18,0));cam=assign(bpy.context.object,'Front camera',studio);cam.data.type='ORTHO';cam.data.ortho_scale=9.5;scene.camera=cam
for name,loc,power,size in [('Key',(-6,-8,8),1600,5),('Fill',(7,-3,2),700,5),('Rim',(2,6,6),2000,4)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=assign(bpy.context.object,name,studio);o.data.energy=power;o.data.size=size;o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.055,.065,.08,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False
scene.render.resolution_x=1000;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
bpy.ops.object.select_all(action='DESELECT')
for o in model.objects:o.select_set(True)
bpy.context.view_layer.objects.active=core[0]
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_distance=12
for name,loc in [('front',(0,-18,0)),('side',(18,0,0)),('top',(0,0,18)),('perspective',(11,-17,8)),('back',(0,18,0))]:
    cam.location=loc;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/('preview_'+name+'.png'))
    if name=='front':bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'white_model_8m.blend'))
    bpy.ops.render.render(write_still=True)
print('VALIDATED',json.dumps(report))
