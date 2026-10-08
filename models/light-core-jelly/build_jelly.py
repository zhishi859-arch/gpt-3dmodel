import bpy, math, random, json, sys, bisect
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT.parent/'light-core-motion'/'light_core_motion.blend'))
s=bpy.context.scene;s.frame_set(1)
model=bpy.data.collections['WHITE_MODEL'];model.name='LIGHT_CORE_JELLY'
# Retain a fixed-size blue core and its sparse rotating surface accents.
keep=[]
for o in list(model.objects):
    n=o.name
    if n=='Rotating central core' or n.startswith(('Core spiral','Axial core')) or (n.startswith('Core meridian') and int(n.split()[-1])%2==0) or (n.startswith('Core latitude') and int(n.split()[-1])%2==0):
        o.parent=None;o.animation_data_clear();keep.append(o)
    else:bpy.data.objects.remove(o,do_unlink=True)
for o in list(bpy.data.collections['MOTION_CONTROLS'].objects):bpy.data.objects.remove(o,do_unlink=True)
rig=bpy.data.collections['MOTION_CONTROLS']
root=bpy.data.objects.new('JELLY | coupled rise and recovery',None);rig.objects.link(root)
spin=bpy.data.objects.new('CORE | fixed size self rotation',None);rig.objects.link(spin);spin.parent=root
for o in keep:o.parent=spin
for o in bpy.data.objects:
    if o.name=='Core blue glow':o.parent=root;o.data.energy=12
s.frame_start=1;s.frame_end=192;s.render.fps=24
# 8-second full loop with three propulsion pulses; squeeze is faster than reopening.
def pulse(phase):
    p=(phase%math.tau)/math.tau
    if p<.24:
        q=p/.24;return q*q*(3-2*q)
    q=(p-.24)/.76;return 1-q*q*(3-2*q)
def float_z(theta):return .48*pulse(3*theta)-.20
for f in range(1,194):
    theta=(f-1)/192*math.tau
    root.location.z=float_z(theta);root.keyframe_insert(data_path='location',frame=f)
for f,a in [(1,0),(193,2*math.tau)]:spin.rotation_euler.z=a;spin.keyframe_insert(data_path='rotation_euler',frame=f)
for o in [root,spin]:
    for fc in o.animation_data.action.fcurves:
        for k in fc.keyframe_points:k.interpolation='LINEAR'
        fc.modifiers.new('CYCLES')
# Soft emission with actual transparency: individual grains remain visible through the cloud.
def glow(name,color,strength,opacity):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,opacity)
    nt=m.node_tree;nt.nodes.clear()
    out=nt.nodes.new('ShaderNodeOutputMaterial');e=nt.nodes.new('ShaderNodeEmission');e.inputs[0].default_value=(*color,1);e.inputs[1].default_value=strength
    tr=nt.nodes.new('ShaderNodeBsdfTransparent');mix=nt.nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=opacity
    nt.links.new(tr.outputs[0],mix.inputs[1]);nt.links.new(e.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],out.inputs['Surface'])
    return m
particlemat=glow('S ribbons | translucent white ice particles',(.64,.84,1),2.4,.52)
threadmat=glow('Soft trailing filaments',(.35,.62,.95),1.4,.50)
pearlmat=glow('Moving pearl accents',(.70,.90,1),4,.86)
core=bpy.data.objects['Rotating central core']
p=core.data.materials[0].node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.008,.045,.20,1);p.inputs['Metallic'].default_value=.12;p.inputs['Roughness'].default_value=.28;p.inputs['Emission Strength'].default_value=.4
for o in keep:
    if o!=core:
        o.data.materials.clear();o.data.materials.append(glow(o.name+' faint cyan',(.06,.36,1),1.5,.6))
# Analytic moving water field: a strong coherent bell contraction plus downstream lag.
def water(p,theta,k,trail=False):
    x,y,z=p;zn=max(-1,min(1,z/3.8));lag=(1-zn)*(.04 if trail=='orbit' else .09 if trail else .03)+k*(.008 if trail else .006)
    squeeze=pulse(3*theta-lag*math.tau)
    belly=.6+.4*math.cos(zn*math.pi/2)**2
    radial=1-(.38 if not trail else .34)*squeeze*belly
    phase=theta*2-3.2*zn+k*.83
    x=x*radial*(1+.045*math.sin(phase))+(.12 if not trail else .30)*(1-zn*.4)*math.sin(phase)
    y=y*radial*(1+.04*math.cos(phase+.7))+(.14 if not trail else .26)*(1-zn*.4)*math.cos(phase+.7)
    z=z*(1+.045*squeeze)+(.075 if not trail else .15)*math.sin(theta*2-4.6*zn+k*.9)*(1-abs(zn)*.7)
    return (x,y,z)
def strand(u,k,q=0):
    a=math.tau*u;z=3.66*math.sin(a)
    env=max(0,math.cos(z/7.7*math.pi))**.83
    r=.10+env*(1.55+.25*math.sin(2*a+k*.7))
    angle=a+k*math.tau/5+.70*math.sin(a+k*.7)+q*.23*env/max(r,.25)
    r+=q*.10*env
    return (r*math.cos(angle),r*math.sin(angle),z+q*.10*env)
def newmesh(name,verts,edges=()):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,edges,[]);me.update()
    ob=bpy.data.objects.new(name,me);model.objects.link(ob);ob.parent=root;return ob
# Geometry nodes keep thousands of light particles genuinely editable and lightweight.
def nodes(ob,mode,material,radii=None):
    g=bpy.data.node_groups.new(ob.name+' geometry','GeometryNodeTree')
    g.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    inp=g.nodes.new('NodeGroupInput');out=g.nodes.new('NodeGroupOutput')
    if mode=='particles':
        ico=g.nodes.new('GeometryNodeMeshIcoSphere');ico.inputs['Radius'].default_value=1;ico.inputs['Subdivisions'].default_value=1
        mat=g.nodes.new('GeometryNodeSetMaterial');mat.inputs['Material'].default_value=material;g.links.new(ico.outputs['Mesh'],mat.inputs['Geometry'])
        attr=ob.data.attributes.new('particle_radius','FLOAT','POINT')
        for v,r in zip(attr.data,radii):v.value=r
        read=g.nodes.new('GeometryNodeInputNamedAttribute');read.data_type='FLOAT';read.inputs['Name'].default_value='particle_radius'
        ins=g.nodes.new('GeometryNodeInstanceOnPoints');g.links.new(inp.outputs['Geometry'],ins.inputs['Points']);g.links.new(mat.outputs['Geometry'],ins.inputs['Instance']);g.links.new(read.outputs['Attribute'],ins.inputs['Scale']);g.links.new(ins.outputs['Instances'],out.inputs['Geometry'])
    else:
        c=g.nodes.new('GeometryNodeMeshToCurve');g.links.new(inp.outputs['Geometry'],c.inputs['Mesh'])
        prof=g.nodes.new('GeometryNodeCurvePrimitiveCircle');prof.inputs['Resolution'].default_value=6;prof.inputs['Radius'].default_value=.007
        surf=g.nodes.new('GeometryNodeCurveToMesh');g.links.new(c.outputs['Curve'],surf.inputs['Curve']);g.links.new(prof.outputs['Curve'],surf.inputs['Profile Curve'])
        mat=g.nodes.new('GeometryNodeSetMaterial');mat.inputs['Material'].default_value=material;g.links.new(surf.outputs['Mesh'],mat.inputs['Geometry']);g.links.new(mat.outputs['Geometry'],out.inputs['Geometry'])
    mod=ob.modifiers.new('Editable luminous geometry','NODES');mod.node_group=g
# Shape snapshots are native Blender data. No frame handlers or external runtime are required.
def animate(ob,fn):
    ob.shape_key_add(name='Basis')
    for j in range(1,48):
        key=ob.shape_key_add(name='Water phase %02d'%j)
        for v,co in zip(key.data,fn(j/48*math.tau)):v.co=co
        for f,value in sorted({1:0,1+(j-1)*4:0,1+j*4:1,1+(j+1)*4:0,193:0}.items()):
            key.value=value;key.keyframe_insert(data_path='value',frame=f)
    a=ob.data.shape_keys.animation_data.action
    for fc in a.fcurves:
        for key in fc.keyframe_points:key.interpolation='LINEAR'
        fc.modifiers.new('CYCLES')
    ob.data.shape_keys.name=ob.name+' | traveling water shapes'
random.seed(29)
seeds=[];radii=[]
for k in range(5):
    for i in range(192):
        for j in range(7):
            seeds.append((k,(i+random.random()*.9)/192,(j-3)/3+random.uniform(-.14,.14),random.uniform(-.028,.028)))
            radii.append(random.uniform(.009,.020) if k<2 else random.uniform(.007,.016))
tables=[]
for k in range(5):
    pp=[Vector(strand(i/1200,k)) for i in range(1201)]
    dist=[0.0]
    for a,b in zip(pp,pp[1:]):dist.append(dist[-1]+(b-a).length)
    tables.append(dist)
def arc_u(progress,k):
    dist=tables[k];d=(progress%1)*dist[-1];j=min(1199,max(0,bisect.bisect_right(dist,d)-1))
    return (j+(d-dist[j])/max(1e-9,dist[j+1]-dist[j]))/1200
def particle_positions(theta):
    result=[]
    for k,u,q,jit in seeds:
        p=list(strand(arc_u(u+theta/math.tau,k),k,q));p[2]+=jit
        result.append(water(p,theta,k))
    return result
cloud=newmesh('S_SHAPED_PARTICLE_RIBBONS | 6720 translucent grains',particle_positions(0));nodes(cloud,'particles',particlemat,radii);animate(cloud,particle_positions)
# Long compliant filaments replace the rigid cage. Lower sections respond later and bend more.
thread_specs=[]
for k in range(14):
    thread_specs.append(('long',k,160))
for k in range(6):thread_specs.append(('orbit',k,192))
def thread_positions(theta):
    pts=[]
    for typ,k,n in thread_specs:
        for i in range(n):
            u=i/(n-1) if typ=='long' else i/n
            if typ=='long':
                z=3.74-7.48*u;env=math.sin(math.pi*u)**.75
                a=k*math.tau/14+u*math.tau*.78+.40*math.sin(math.tau*u+k)
                r=.09+env*(1.85+.30*math.sin(math.tau*u+k*.8))
                p=(r*math.cos(a),r*math.sin(a),z)
            else:
                a=u*math.tau;az=k*.61;tilt=.35+k*.22
                # Non-planar wandering orbit, already curved before deformation.
                xx=2.85*math.cos(a);yy=2.30*math.sin(a)
                p=(xx*math.cos(az)-yy*math.cos(tilt)*math.sin(az),xx*math.sin(az)+yy*math.cos(tilt)*math.cos(az),yy*math.sin(tilt)+.17*math.sin(3*a+k))
            pts.append(water(p,theta,k,'orbit' if typ=='orbit' else True))
    return pts
edges=[];start=0
for typ,k,n in thread_specs:
    edges.extend((start+i,start+i+1) for i in range(n-1))
    if typ=='orbit':edges.append((start+n-1,start))
    start+=n
threads=newmesh('COMPLIANT_FILAMENTS | delayed traveling waves',thread_positions(0),edges);nodes(threads,'curves',threadmat);animate(threads,thread_positions)
# Larger accents flow on the same deforming S paths, so they cannot detach from the water field.
def accent_positions(theta):
    return [water(strand(arc_u(j/5+theta/math.tau,k),k),theta,k) for k in range(5) for j in range(5)]
accents=newmesh('FLOWING_PEARLS | attached to deforming particle ribbons',accent_positions(0));nodes(accents,'particles',pearlmat,[.041]*25);animate(accents,accent_positions)
# Soft orbiting node accents retain the navigation-core identity.
def orbit_nodes(theta):
    pts=[]
    for k in range(6):
        for j in range(2):
            a=theta+j*math.pi+k*.4;az=k*.61;tilt=.35+k*.22;xx=2.85*math.cos(a);yy=2.30*math.sin(a)
            p=(xx*math.cos(az)-yy*math.cos(tilt)*math.sin(az),xx*math.sin(az)+yy*math.cos(tilt)*math.cos(az),yy*math.sin(tilt)+.17*math.sin(3*a+k))
            pts.append(water(p,theta,k,'orbit'))
    return pts
orbnodes=newmesh('ORBITING_ACCENTS | floating nodes',orbit_nodes(0));nodes(orbnodes,'particles',pearlmat,[.06+.018*(i%3) for i in range(12)]);animate(orbnodes,orbit_nodes)
# Sparse end particles establish the retained eight-metre design envelope.
ends=newmesh('AXIAL_MIST_TIPS',[(0,0,-3.98),(0,0,3.98)]);nodes(ends,'particles',threadmat,[.02,.02])
# Soft, dark-water presentation.
s.world.node_tree.nodes['Background'].inputs[0].default_value=(.004,.012,.022,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.18
cam=s.camera;cam.location=(5,-20,2.6);cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=9.8
s.render.engine='CYCLES';s.cycles.samples=96;s.cycles.use_denoising=False;s.cycles.max_bounces=6;s.cycles.transparent_max_bounces=12
s.render.resolution_x=896;s.render.resolution_y=1120;s.render.resolution_percentage=100
if s.use_nodes:
    for n in s.node_tree.nodes:
        if n.type=='GLARE':n.threshold=.8;n.size=7
s.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'light_core_jelly.blend'))
# Verify deformation, the strong coherent pulse, fixed core scale, and all-loop closure.
report={'reference':'User-supplied 水母.mp4, duration 4.04 s. Observed fast bell squeeze, upward thrust, slower recovery and trailing strand lag.','base_height_m':8,'includes_base':False,'hard_ribbon_surfaces_removed':True,'S_band_particle_count':len(seeds),'particle_opacity':.52,'full_loop_seconds':8,'pulse_period_seconds':8/3,'squeeze_fraction_of_pulse':.24,'release_fraction_of_pulse':.76,'vertical_excursion_m':.48,'core_deformation_modifiers':len(core.modifiers),'native_fps':24,'frames':[1,192],'samples':[]}
base_scale=list(core.scale)
for f in [1,9,17,33,49,65,97,145,193]:
    s.frame_set(f);bpy.context.view_layer.update()
    assert list(core.scale)==base_scale and not core.modifiers
    theta=(f-1)/192*math.tau
    pp=particle_positions(theta)
    report['samples'].append({'frame':f,'pulse':pulse(3*theta),'float_z':root.location.z,'particle_horizontal_diameter':2*max(math.hypot(v[0],v[1]) for v in pp),'core_scale':list(core.scale)})
assert max((Vector(a)-Vector(b)).length for a,b in zip(particle_positions(0),particle_positions(math.tau)))<1e-5
assert max((Vector(a)-Vector(b)).length for a,b in zip(thread_positions(0),thread_positions(math.tau)))<1e-5
report['loop_closure_verified']=True
(OUT/'jelly_motion_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
print('JELLY_MODEL_VERIFIED',flush=True)
if '--model-only' in sys.argv:sys.exit(0)
frames=OUT.parents[1]/'work'/'light-core-jelly-frames';frames.mkdir(parents=True,exist_ok=True)
s.cycles.samples=12;s.render.resolution_x=448;s.render.resolution_y=560
for i,f in enumerate(range(1,193)):
    s.frame_set(f);s.render.filepath=str(frames/('%04d.png'%i));bpy.ops.render.render(write_still=True)
print('JELLY_RENDER_COMPLETE',flush=True)
