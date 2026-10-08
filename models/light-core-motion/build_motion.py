import bpy, math, json, bisect, sys
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
SOURCE=OUT.parent/'energy-sculpture-v2'/'white_model_8m.blend'
FRAMES=OUT.parents[1]/'work'/'light-core-frames';FRAMES.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;scene.frame_set(1)
model=bpy.data.collections['WHITE_MODEL'];rig=bpy.data.collections['MOTION_CONTROLS']
for o in list(model.objects)+list(rig.objects):o.animation_data_clear()
# All five motions share a ten-second seamless period.
scene.frame_start=1;scene.frame_end=240;scene.render.fps=24
root=bpy.data.objects.new('LIGHT_CORE | buoyancy',None);rig.objects.link(root)
outer=bpy.data.objects.new('JELLYFISH | peripheral pulse',None);rig.objects.link(outer);outer.parent=root
spin=bpy.data.objects['Core spin'];spin.parent=root
bands=bpy.data.objects['Ribbon breathing'];bands.parent=root
for o in model.objects:
    if o.parent is None:o.parent=root
    if o.name.startswith(('Closed orbit','Small orbit pearl','Companion flowing filament')):o.parent=outer
# Temporal drivers are continuous beyond the visible timeline.
def drive(obj,path,index,expr):
    d=obj.driver_add(path,index).driver;d.type='SCRIPTED';d.expression=expr
phase='((frame-1)/240*6.283185307179586)'
drive(root,'location',2,f'0.13*sin({phase})')
drive(spin,'rotation_euler',2,f'{phase}*2')
# Fast squeeze / slower relaxation: a second harmonic makes the pulse asymmetric.
pulse=f'(0.92+0.11*sin({phase})+0.035*sin(2*{phase}+0.7))'
for i in [0,1]:drive(outer,'scale',i,pulse)
drive(outer,'scale',2,f'(1.0-0.045*sin({phase}))')
for i in [0,1]:drive(bands,'scale',i,f'(0.97+0.045*sin({phase}+0.5))')
# Silver body, white luminous ribs and saturated blue core.
def material(name,color,metal=0,rough=.3,emission=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=rough
    n.inputs['Emission Color'].default_value=(*color,1);n.inputs['Emission Strength'].default_value=emission
    return m
silver=material('Satin silver shell',(.52,.58,.67),.82,.27)
white=material('White luminous bands',(.8,.9,1),.15,.28,2.5)
line=material('Silver-white orbital threads',(.55,.67,.8),.65,.35,.35)
blue=material('Blue rotating core',(.015,.12,.65),.5,.22,.65)
blue_line=material('Blue-white core filigree',(.12,.55,1),.15,.2,3)
pearl=material('Flowing pearl lights',(.8,.93,1),.2,.18,5)
def setmat(o,m):o.data.materials.clear();o.data.materials.append(m)
for o in model.objects:
    n=o.name
    if n=='Rotating central core':m=blue
    elif n.startswith(('Core ','Axial core')):m=blue_line
    elif n.startswith('Primary curling'):m=silver
    elif 'raised vein' in n:m=white
    elif n.startswith('Orbiting sphere'):m=blue_line
    elif n.startswith(('Closed orbit','Small orbit','Companion')):m=line
    else:m=silver
    setmat(o,m)
# Reconstruct the exact centre trajectories from v2 and use its saved affine transform.
ref=bpy.data.objects['Ribbon 01 raised vein 03'];scale=ref.scale.copy();offset=ref.location.copy()
def mapped(p):return Vector([p[i]*scale[i]+offset[i] for i in range(3)])
def surface(t,k):
    ph=k*math.tau/5;env=math.sin(math.pi*t)**.7
    a=ph+math.tau*(.68+.07*(k%2))*t+.9*math.sin(math.tau*t+ph)+.24*math.sin(4*math.pi*t+ph)
    r=.025+env*(1.26+.61*math.sin(3*math.pi*t+ph)+.18*math.sin(7*math.pi*t-ph))+.12*env
    z=-3.76+7.52*t+.46*env*math.sin(4*math.pi*t+ph)
    return mapped((r*math.cos(a),r*math.sin(a),z))
def arctable(points):
    cum=[0.0]
    for a,b in zip(points,points[1:]):cum.append(cum[-1]+(b-a).length)
    return points,cum,cum[-1]
def at(tab,fraction):
    p,c,total=tab;s=(fraction%1)*total
    j=min(len(p)-2,max(0,bisect.bisect_right(c,s)-1))
    return p[j].lerp(p[j+1],(s-c[j])/max(c[j+1]-c[j],1e-9))
def link(o,parent):
    for c in list(o.users_collection):c.objects.unlink(o)
    model.objects.link(o);o.parent=parent

def sphere(name,r,parent):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=12,radius=r)
    o=bpy.context.object;o.name=name;link(o,parent);setmat(o,pearl)
    for f in o.data.polygons:f.use_smooth=True
    return o

def linear(o):
    for fc in o.animation_data.action.fcurves:
        for k in fc.keyframe_points:k.interpolation='LINEAR'
flow=[];loops=[]
# Each pearl rises on one white centre vein and returns on the next, closing at the tips.
for k in range(5):
    pts=[surface(j/600,k) for j in range(601)]+[surface(1-j/600,(k+1)%5) for j in range(601)]
    pts.append(pts[0]);tab=arctable(pts);loops.append(tab)
    for j in range(5):
        o=sphere('Band flowing pearl %02d_%02d'%(k+1,j+1),.044,bands)
        for f in range(1,242):
            o.location=at(tab,(f-1)/240+j/5);o.keyframe_insert(data_path='location',frame=f)
        linear(o);flow.append(o)
# Orbital spheres and bright short strips progress around their closed ellipses by arc length.
orbital=[];strips=[]
for k in range(10):
    az=k*math.pi/5+.12;tilt=[.12,.34,.52,.70,.9,1.1,1.28,1.4,.8,1.52][k]
    u=Vector((math.cos(az),math.sin(az),0));v=Vector((-math.sin(az)*math.cos(tilt),math.cos(az)*math.cos(tilt),math.sin(tilt)))
    a=3.04 if k<5 else 2.62;b=1.6 if k<5 else 3.15;center=Vector((0,0,.12*math.sin(k)))
    tab=arctable([mapped(center+a*math.cos(j*math.tau/1200)*u+b*math.sin(j*math.tau/1200)*v) for j in range(1201)])
    for j in range(2):
        o=bpy.data.objects['Orbiting sphere %02d_%02d'%(k+1,j+1)];o.parent=outer
        for f in range(1,242):
            o.location=at(tab,(f-1)/240+k*.14+j*.41+.06);o.keyframe_insert(data_path='location',frame=f)
        linear(o);orbital.append(o)
    # A segmented luminous strip follows the actual curved route, never a straight chord.
    c=bpy.data.curves.new('Traveling orbital light strip','CURVE');c.dimensions='3D';c.bevel_depth=.026;c.bevel_resolution=2;c.use_fill_caps=True
    s=c.splines.new('POLY');s.points.add(12)
    o=bpy.data.objects.new('Moving orbital strip %02d'%(k+1),c);model.objects.link(o);o.parent=outer;c.materials.append(pearl)
    for f in range(1,242):
        for j,p in enumerate(s.points):
            pos=at(tab,(f-1)/240+k*.097+(j/12-.5)*.035)
            p.co=(*pos,1);p.keyframe_insert(data_path='co',frame=f)
    strips.append(o)
# Point light tracks the core glow without introducing coloured body materials.
bpy.ops.object.light_add(type='POINT',location=(0,-.4,0));o=bpy.context.object;o.name='Core blue glow';o.data.color=(.05,.28,1);o.data.energy=50;o.data.shadow_soft_size=.7;o.parent=root
# Dark neutral background and a subtle post-render glow.
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.012,.018,.03,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
scene.use_nodes=True;nt=scene.node_tree;nt.nodes.clear()
r=nt.nodes.new('CompositorNodeRLayers');g=nt.nodes.new('CompositorNodeGlare');g.glare_type='FOG_GLOW';g.quality='MEDIUM';g.threshold=1.2;g.size=7
comp=nt.nodes.new('CompositorNodeComposite');nt.links.new(r.outputs['Image'],g.inputs['Image']);nt.links.new(g.outputs['Image'],comp.inputs['Image'])
cam=scene.camera;cam.location=(9,-18,5);cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=10.0
scene.render.engine='CYCLES';scene.cycles.use_denoising=False;scene.cycles.samples=16
scene.render.resolution_x=512;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'light_core_motion.blend'))
# Verify all five motions, closure, and arc-length flow at the reference path.
checks=[]
for f in [1,61,121,181,241]:
    scene.frame_set(f);bpy.context.view_layer.update()
    checks.append({'frame':f,'float_z_m':root.location.z,'core_angle_rad':spin.rotation_euler.z,'peripheral_scale':list(outer.scale),'first_pearl_local':list(flow[0].location),'first_strip_center_local':list(strips[0].data.splines[0].points[6].co)})
assert abs(checks[0]['float_z_m']-checks[-1]['float_z_m'])<1e-5
assert abs(checks[-1]['core_angle_rad']-4*math.pi)<1e-4
assert max(x['float_z_m'] for x in checks)-min(x['float_z_m'] for x in checks)>.25
assert max(x['peripheral_scale'][0] for x in checks)-min(x['peripheral_scale'][0] for x in checks)>.2
assert (Vector(checks[0]['first_pearl_local'])-Vector(checks[-1]['first_pearl_local'])).length<1e-5
assert (Vector(checks[0]['first_strip_center_local'])-Vector(checks[-1]['first_strip_center_local'])).length<1e-5
# Flow speeds measured in undeformed band-local coordinates, avoiding parameter-speed variation.
speeds=[]
for f in range(1,241):
    scene.frame_set(f);a=flow[0].location.copy();scene.frame_set(f+1);b=flow[0].location.copy();speeds.append((b-a).length*24)
report={'period_seconds':10,'fps':24,'play_frames':[1,240],'closure_frame':241,'core_revolutions_per_period':2,'vertical_float_amplitude_m':.13,'moving_light_strips':10,'flowing_band_pearls':25,'orbiting_spheres':20,'nominal_band_pearl_speed_m_per_s':loops[0][2]/10,'measured_band_speed_min_max': [min(speeds),max(speeds)],'samples':checks,'note':'Arc-length flow is constant along undeformed local paths; breathing alters world-space path lengths. Rest geometry based on 8m v2 model; animated dimensions vary.'}
(OUT/'motion_report.json').write_text(json.dumps(report,indent=2));print('MOTION_VALIDATED',flush=True)
if '--model-only' in sys.argv: sys.exit(0)
# Movie uses a sample every third native frame: eight unique frames per second.
for i,f in enumerate(range(1,241,3)):
    scene.frame_set(f);scene.render.filepath=str(FRAMES/('%04d.png'%i));bpy.ops.render.render(write_still=True)
print('RENDER_COMPLETE',flush=True)
