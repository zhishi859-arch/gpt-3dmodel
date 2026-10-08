import bpy,math,json,sys,bisect
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT.parent/'light-core-motion'/'light_core_motion.blend'))
scene=bpy.context.scene;scene.frame_set(1)
root=bpy.data.objects['LIGHT_CORE | buoyancy'];outer=bpy.data.objects['JELLYFISH | peripheral pulse'];bands=bpy.data.objects['Ribbon breathing'];spin=bpy.data.objects['Core spin']
# Remove coordinated object-scale pulsing entirely. Core receives only rotation and buoyancy.
for o in [outer,bands]:o.animation_data_clear();o.scale=(1,1,1)
model=bpy.data.collections['WHITE_MODEL']
for o in model.objects:
    if o.parent in [outer,bands]:o.parent=root
bpy.data.objects.remove(outer,do_unlink=True)
bpy.data.objects.remove(bands,do_unlink=True)
# Each cage has independent phased, height-dependent currents and local contraction.
cages=bpy.data.collections.new('INDEPENDENT_WATER_CURRENTS');scene.collection.children.link(cages)
P='((frame-1)*.034033920414)'
config=[]
def cage(name,k,orbit=False):
    data=bpy.data.lattices.new(name);data.points_u=3 if not orbit else 2;data.points_v=3 if not orbit else 2;data.points_w=11 if not orbit else 9
    data.interpolation_type_u='KEY_BSPLINE';data.interpolation_type_v='KEY_BSPLINE';data.interpolation_type_w='KEY_BSPLINE'
    ob=bpy.data.objects.new(name,data);cages.objects.link(ob);ob.parent=root;ob.hide_render=True
    spans=[max(pt.co[i] for pt in data.points)-min(pt.co[i] for pt in data.points) for i in range(3)]
    ob.scale=(7/spans[0],7/spans[1],8.1/spans[2])
    ph=k*.91+.11*k*k+(1.3 if orbit else 0);amp=.072+.013*(k%4) if orbit else .09+.018*(k%5)
    config.append({'name':name,'phase_rad':ph,'radial_amplitude':amp,'height_wave':True})
    for pt in data.points:
        x,y,z=[round(float(a),5) for a in pt.co];zn=round(z/spans[2],5)
        env=round(math.cos(math.pi*zn)**2,5);ph=round(ph,5);amp=round(amp,5)
        ex=f'{x}*(1+{env}*(-.035+{amp}*sin({P}+{ph}-2.4*{zn})+.024*sin(2*{P}+{ph}+4*{zn})))+{round(env*.024*spans[0],6)}*sin({P}+{ph}-5.5*{zn})'
        ey=f'{y}*(1+{env}*(-.025+{round(amp*.81,6)}*sin({P}+{ph}+.8-3.7*{zn})))+{round(env*.028*spans[1],6)}*cos({P}+{ph}-4.6*{zn})'
        ez=f'{z}+{round(env*.017*spans[2],6)}*sin({P}+{ph}-5.2*{zn})+{round(env*.007*spans[2],6)}*sin(2*{P}+{ph}+2*{zn})'
        for i,expr in enumerate([ex,ey,ez]):
            assert len(expr)<250,(len(expr),expr)
            base=round(float(pt.co[i]),5)
            expr=f'{base}+2*(({expr})-({base}))'
            assert len(expr)<255
            d=pt.driver_add('co_deform',i).driver;d.type='SCRIPTED';d.expression=expr
    return ob
band_cages=[cage('Band %02d | traveling current'%(k+1),k) for k in range(5)]
orbit_cages=[cage('Orbit %02d | asynchronous swell'%(k+1),k,True) for k in range(10)]
def attach(o,c):
    m=o.modifiers.new('Independent nonuniform water deformation','LATTICE');m.object=c
source_text=(OUT.parent/'light-core-motion'/'build_motion.py').read_text()
exec(source_text[source_text.index('# Reconstruct the exact'):source_text.index('def link(o,parent):')])
branch_cuts=[]
for k in range(5):
    a=[surface(j/600,k) for j in range(601)]
    b=[surface(1-j/600,(k+1)%5) for j in range(601)]
    table=arctable(a+b+[a[0]])
    branch_cuts.append(arctable(a)[2]/table[2])
for o in model.objects:
    n=o.name;c=None
    if n.startswith('Primary curling ribbon'):c=band_cages[int(n.split()[-1])-1]
    elif n.startswith('Ribbon ') and 'raised vein' in n:c=band_cages[int(n.split()[1])-1]
    elif n.startswith('Companion flowing filament'):c=band_cages[int(n.split()[-1])%5]
    elif n.startswith('Closed orbit'):c=orbit_cages[int(n.split()[-1])-1]
    elif n.startswith('Small orbit pearl'):c=orbit_cages[int(n.split()[-1].split('_')[0])-1]
    elif n.startswith('Orbiting sphere'):c=orbit_cages[int(n.split()[-1].split('_')[0])-1]
    elif n.startswith('Moving orbital strip'):c=orbit_cages[int(n.split()[-1])-1]
    elif n.startswith('Band flowing pearl'):
        # Pearls switch between the two adjacent band cages on their closed circuit.
        k=int(n.split()[-1].split('_')[0])-1
        first=o.modifiers.new('Upstream band deformation','LATTICE');first.object=band_cages[k]
        second=o.modifiers.new('Downstream band deformation','LATTICE');second.object=band_cages[(k+1)%5]
        # Arc distance, rather than vertical velocity, identifies the ascending path.
        phase_index=int(n.split()[-1].split('_')[1])-1
        for f in range(1,242):
            progress=((f-1)/240+phase_index/5)%1
            ascending=progress<branch_cuts[k]
            first.strength=1 if ascending else 0;second.strength=0 if ascending else 1
            first.keyframe_insert(data_path='strength',frame=f);second.keyframe_insert(data_path='strength',frame=f)
        for fc in o.animation_data.action.fcurves:
            if 'strength' in fc.data_path:
                for key in fc.keyframe_points:key.interpolation='CONSTANT'
        continue
    if c:attach(o,c)
# Refine the glowing body: subdued metallic glints and thinner light traces.
for name in ['White luminous bands','Blue-white core filigree']:
    m=bpy.data.materials.get(name)
    if m:m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=1.4 if name.startswith('White') else 2.2
m=bpy.data.materials['Satin silver shell'];m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.4
# The rendered core is still spherical and invariant; turntable-like self-spin remains.
scene.camera.location=(7,-19,3.2);scene.camera.rotation_euler=(-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.ortho_scale=10.1
scene.cycles.samples=128;scene.render.resolution_x=896;scene.render.resolution_y=1120
for action in bpy.data.actions:
    for fc in action.fcurves:
        if not any(m.type=='CYCLES' for m in fc.modifiers):fc.modifiers.new('CYCLES')
scene.frame_end=2400
scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'light_core_organic.blend'))
# Check fixed core volume/scale and independent, spatially varying ribbon deformation.
core=bpy.data.objects['Rotating central core'];body=[bpy.data.objects['Primary curling ribbon %02d'%(i+1)] for i in range(5)]
rows=[];dg=bpy.context.evaluated_depsgraph_get()
for f in [1,31,61,91,121,151,181,211,241]:
    scene.frame_set(f);bpy.context.view_layer.update()
    entry={'frame':f,'core_scale':list(core.matrix_world.to_scale()),'core_local_mesh_bounds':list(core.dimensions),'root_float_z':root.location.z,'ribbons':[]}
    for o in body:
        eo=o.evaluated_get(dg);mesh=eo.to_mesh()
        samples=[list(eo.matrix_world@mesh.vertices[i].co) for i in [0,len(mesh.vertices)//3,len(mesh.vertices)//2]]
        entry['ribbons'].append({'name':o.name,'vertex_samples':samples,'object_scale':list(o.scale)})
        eo.to_mesh_clear()
    rows.append(entry)
for r in rows:assert max(abs(a-b) for a,b in zip(r['core_scale'],rows[0]['core_scale']))<1e-5
assert all(not o.modifiers for o in [core]),'Core must remain undeformed'
assert all((Vector(rows[0]['ribbons'][i]['vertex_samples'][1])-Vector(rows[2]['ribbons'][i]['vertex_samples'][1])).length>.01 for i in range(5))
assert all(fc.is_valid for c in band_cages+orbit_cages for fc in c.data.animation_data.drivers),'Invalid water-current driver'
report={'core_fixed_scale':True,'core_deformation_modifiers':len(core.modifiers),'uniform_parent_scaling_removed':True,'independent_band_currents':5,'independent_orbit_currents':10,'peripheral_period_seconds':10/1.3,'full_repeat_seconds':100,'deformation_amplitude_multiplier':2,'peripheral_speed_multiplier':1.3,'base_height_m':8,'includes_base':False,'cages':config,'samples':rows}
(OUT/'organic_motion_report.json').write_text(json.dumps(report,indent=2));print('ORGANIC_MOTION_VALIDATED',flush=True)
if '--model-only' in sys.argv:sys.exit(0)
scene.cycles.samples=16;scene.render.resolution_x=448;scene.render.resolution_y=560
frames=OUT.parents[1]/'work'/'light-core-organic-frames';frames.mkdir(parents=True,exist_ok=True)
for i,f in enumerate(range(1,241,2)):
    scene.frame_set(f);scene.render.filepath=str(frames/('%04d.png'%i));bpy.ops.render.render(write_still=True)
print('RENDER_COMPLETE',flush=True)
