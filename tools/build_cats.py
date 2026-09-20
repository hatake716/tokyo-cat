#!/usr/bin/env python3
"""Original anatomical development meshes, metres, +X forward, +Y up.
No frames or textures from the reference video are embedded.
Analytical geometry is deliberately labelled authored, not photogrammetry.
Requires numpy, Pillow, scipy and scikit-image. Emits self-contained GLB with joint hierarchies + clips.
"""
import json,math,struct,io,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'app/src/main/assets/game/models';OUT.mkdir(exist_ok=True)
BREEDS=json.loads((OUT.parent/'catalog.json').read_text())['breeds']
class GLB:
 def __init__(self):
  self.binary=bytearray();self.j={'asset':{'version':'2.0','generator':'TOKYO-CAT authored cat generator 0.1'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'name':'cat','children':[]}],'meshes':[],'materials':[],'bufferViews':[],'accessors':[],'textures':[],'images':[],'samplers':[{'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497}],'animations':[]}
 def blob(self,b):
  while len(self.binary)%4:self.binary.append(0)
  v=len(self.j['bufferViews']);self.j['bufferViews'].append({'buffer':0,'byteOffset':len(self.binary),'byteLength':len(b)});self.binary+=b;return v
 def acc(self,a,kind,component=5126):
  a=np.asarray(a,dtype=np.float32 if component==5126 else (np.uint16 if component==5123 else np.uint32));i=len(self.j['accessors']);d={'bufferView':self.blob(a.tobytes()),'componentType':component,'count':len(a),'type':kind}
  if kind=='VEC3':d.update(min=a.min(axis=0).tolist(),max=a.max(axis=0).tolist())
  if kind=='SCALAR':d.update(min=[float(a.min())],max=[float(a.max())])
  self.j['accessors'].append(d);return i
 def material(self,name,rgb,rough=.85,texture=None):
  p={'baseColorFactor':[*rgb,1],'metallicFactor':0,'roughnessFactor':rough}
  if texture is not None:
   im=len(self.j['images']);self.j['images'].append({'bufferView':self.blob(texture),'mimeType':'image/png'});tex=len(self.j['textures']);self.j['textures'].append({'source':im,'sampler':0});p['baseColorTexture']={'index':tex}
  i=len(self.j['materials']);self.j['materials'].append({'name':name,'pbrMetallicRoughness':p,'doubleSided':True});return i
 def mesh(self,pos,norm,uv,indices,mat):
  mesh={'primitives':[{'attributes':{'POSITION':self.acc(pos,'VEC3'),'NORMAL':self.acc(norm,'VEC3'),'TEXCOORD_0':self.acc(uv,'VEC2')},'indices':self.acc(indices,'SCALAR',5125),'material':mat}]};i=len(self.j['meshes']);self.j['meshes'].append(mesh);return i
 def node(self,name,mesh=None,pos=(0,0,0),scale=None,parent=0,rotation=None):
  i=len(self.j['nodes']);n={'name':name,'translation':list(pos)}
  if mesh is not None:n['mesh']=mesh
  if scale:n['scale']=list(scale)
  if rotation:n['rotation']=rotation
  self.j['nodes'].append(n);self.j['nodes'][parent].setdefault('children',[]).append(i);return i
 def write(self,path):
  while len(self.binary)%4:self.binary.append(0)
  self.j['buffers']=[{'byteLength':len(self.binary)}];raw=json.dumps(self.j,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4)
  out=struct.pack('<4sII',b'glTF',2,28+len(raw)+len(self.binary))+struct.pack('<I4s',len(raw),b'JSON')+raw+struct.pack('<I4s',len(self.binary),b'BIN\0')+self.binary;path.write_bytes(out)

def sphere(g,mat,nu=24,nv=16):
 p=[];n=[];uv=[];ix=[]
 for j in range(nv+1):
  phi=math.pi*j/nv
  for i in range(nu+1):
   theta=2*math.pi*i/nu;v=[math.sin(phi)*math.cos(theta),math.cos(phi),math.sin(phi)*math.sin(theta)];p.append(v);n.append(v);uv.append([i/nu,j/nv])
 for j in range(nv):
  for i in range(nu):
   a=j*(nu+1)+i;ix.extend([a,a+1,a+nu+1,a+1,a+nu+2,a+nu+1])
 return g.mesh(p,n,uv,ix,mat)

def coat(b):
 rng=np.random.default_rng(20260920);w,h=512,256;u,v=np.meshgrid(np.linspace(0,1,w),np.linspace(0,1,h));rgb=np.array([int(b['color'][i:i+2],16) for i in [1,3,5]])/255
 noise=rng.normal(0,.032,(h,w));hair=.035*np.sin(u*2100+np.sin(v*35)*3)
 stripe=np.maximum(0,np.cos(u*math.pi*22+np.sin(v*19)*1.7))**10
 factor=1+noise+hair
 if b['id'] in ['mixed','american','siberian','norwegian']:factor-=stripe*.42
 if b['id'] in ['ragdoll','minuet','ragamuffin']:factor+=.13*np.cos(v*4)
 col=np.clip(factor[:,:,None]*rgb[None,None,:],0,1)
 if b['id']=='mixed':
  patch=np.sin(u*15)*np.cos(v*9)>.48;col[patch]*=.42
 im=Image.fromarray(np.uint8(col*255));buf=io.BytesIO();im.save(buf,format='PNG');return buf.getvalue()

def make(b):
 g=GLB();fur=g.material('authored_coat',[1,1,1],texture=coat(b));cream=g.material('chin',[.83,.81,.74]);pink=g.material('ear_nose',[.38,.20,.19]);dark=g.material('pupil',[.012,.016,.012],.3);iris=g.material('iris',[.29,.53,.27] if b['id']!='ragdoll' else [.20,.44,.64],.24);glint=g.material('catchlight',[.98,.99,1],.12);whisker=g.material('whisker',[.6,.59,.53]);sp={m:sphere(g,m) for m in [fur,cream,pink,dark,iris,glint,whisker]}
 bulk=b['body'];leg=b['legs'];y=.28*leg+.008;long=b['id'] in ['ragdoll','minuet','siberian','norwegian','ragamuffin'];fluff=1.10 if long else 1
 body=g.node('torso',sp[fur],(-.025,y+.035,0),(.255,.105*bulk,.090*bulk))
 g.node('haunch',sp[fur],(-.185,y-.012,0),(.117,.135*bulk,.095*bulk))
 g.node('shoulders',sp[fur],(.15,y+.029,0),(.1,.117,.092))
 g.node('chest',sp[fur],(.215,y+.017,0),(.078,.127*fluff,.081*fluff))
 g.node('neck',sp[fur],(.24,y+.105,0),(.072,.099*fluff,.072*fluff))
 head=g.node('head',None,(.28,y+.16,0))
 roundness=1.15 if b['id'] in ['british','scottish','minuet'] else 1
 g.node('cranium',sp[fur],(.015,0,0),(.086,.077*roundness,.074*roundness),head)
 g.node('face',sp[fur],(.069,-.023,0),(.062,.047,.056),head)
 for z in [-1,1]:
  g.node('muzzle',sp[cream],(.099,-.038,z*.022),(.031,.025,.027),head)
  g.node('eye-rim',sp[dark],(.072,.016,z*.052),(.018,.015,.019),head)
  g.node('eye',sp[iris],(.084,.017,z*.053),(.010,.012,.014),head)
  g.node('pupil',sp[dark],(.093,.017,z*.054),(.002,.010,.0035),head)
  g.node('eye-light',sp[glint],(.096,.021,z*.056),(.0015,.002,.0015),head)
  # A tapered, gently curved triangular ear surface rather than a cone.
  eh=.047 if b['fold'] else .091
  vertices=[[-.042,.048,z*.026],[.025,.058,z*.044],[-.012,.066+eh,z*.074],[-.045,.046,z*.067]]
  normals=[[.5,.3,z*.7]]*4;uv=[[0,0],[1,0],[.5,1],[0,1]]
  ear=g.mesh(vertices,normals,uv,[0,1,2,0,2,3],fur);g.node('ear',ear,parent=head)
  inner=[[v[0]+.001,v[1]-.006,v[2]-z*.002] for v in vertices[:3]];earinner=g.mesh(inner,[[1,0,0]]*3,uv[:3],[0,1,2],pink);g.node('inner-ear',earinner,parent=head)
  for k in range(5):
   # Whisker tapers are triangular tubes, not painted texture lines.
   start=np.array([.111,-.035+k*.003,z*.031]);end=np.array([.084-k*.007,-.029+(k-2)*.014,z*(.10+k*.008)])
   d=end-start;mid=(start+end)/2;length=np.linalg.norm(d);axis=np.cross([0,1,0],d/length);axis_len=np.linalg.norm(axis);angle=math.acos(d[1]/length);axis=axis/axis_len if axis_len else np.array([1,0,0]);q=[*(axis*math.sin(angle/2)),math.cos(angle/2)]
   g.node('whisker',sp[whisker],mid,(.0005,length/2,.0005),head,q)
 g.node('nose',sp[pink],(.124,-.025,0),(.009,.008,.012),head)
 g.node('chin',sp[cream],(.081,-.058,0),(.035,.014,.033),head)
 joints={}
 for prefix,x in [('front',.16),('rear',-.18)]:
  for side,z in [('left',-.061),('right',.061)]:
   name=prefix+'_'+side;hip=g.node(name,None,(x,y,z));joints[name]=hip
   a=.13*leg;bb=.15*leg
   g.node(name+'_upper',sp[fur],(-.012,-a/2,0),(.036 if prefix=='front' else .059,a*.72,.033 if prefix=='front' else .05),hip)
   knee=g.node(name+'_knee',None,(0,-a,0),parent=hip);joints[name+'_knee']=knee
   g.node(name+'_shin',sp[fur],(.007,-bb/2,0),(.022,bb*.63,.023),knee)
   paw=g.node(name+'_paw',sp[fur],(.025,-bb+.013,0),(.044,.024,.031),knee)
   for toe in [-1,0,1]:g.node('toe',sp[fur],(.047,-bb+.010,toe*.016),(.023,.017,.011),knee)
 tail0=g.node('tail0',None,(-.27,y+.04,0));joints['tail0']=tail0
 for i in range(3):
  parent=tail0 if i==0 else tail
  if i:tail=g.node('tail'+str(i),None,(-.1,0,0),parent=parent);joints['tail'+str(i)]=tail
  else:tail=tail0
  g.node('tail_fur',sp[fur],(-.055,0,0),(.074,.024*(1-i*.24)*fluff,.024*(1-i*.24)*fluff),tail)
 from skin_surface import build
 build(g,b,sp[fur],sp[cream])
 # A low-opacity grounding decal. This is approximate contact shading, not a
 # physically simulated sun shadow; kept separate from the articulated skin.
 u,v=np.meshgrid(np.linspace(-1,1,128),np.linspace(-1,1,128));alpha=np.clip(1-u*u-v*v,0,1)**3*.22
 rgba=np.zeros((128,128,4),dtype=np.uint8);rgba[:,:,:3]=20;rgba[:,:,3]=np.uint8(alpha*255)
 buf=io.BytesIO();Image.fromarray(rgba).save(buf,format='PNG')
 shadowmat=g.material('soft_contact_shading',[1,1,1],texture=buf.getvalue());g.j['materials'][shadowmat].update(alphaMode='BLEND',extensions={'KHR_materials_unlit':{}});g.j['extensionsUsed']=['KHR_materials_unlit']
 shadow=g.mesh([[-.50,.002,-.23],[.39,.002,-.23],[.39,.002,.23],[-.50,.002,.23]],[[0,1,0]]*4,[[0,0],[1,0],[1,1],[0,1]],[0,2,1,0,3,2],shadowmat);g.node('contact_shading',shadow)
 # Silhouette strands are original deterministic geometry, limited to longhair breeds.
 if long:
  rng=np.random.default_rng(17);pos=[];norm=[];uv=[];ix=[]
  for i in range(600):
   theta=rng.uniform(0,math.tau);phi=rng.uniform(.15,math.pi-.15);n=np.array([math.sin(phi)*math.cos(theta),math.cos(phi),math.sin(phi)*math.sin(theta)])
   s=np.array([-.025,y+.035,0])+n*np.array([.255,.105*bulk,.09*bulk]);end=s+n*rng.uniform(.004,.019);tangent=np.cross(n,[1,0,0]);tangent/=max(.01,np.linalg.norm(tangent));base=len(pos);pos.extend([s-tangent*.0007,s+tangent*.0007,end]);norm.extend([n,n,n]);uv.extend([[0,0],[1,0],[.5,1]]);ix.extend([base,base+1,base+2])
  body_pos=np.asarray(g.j['nodes'][body]['translation']);body_scale=np.asarray(g.j['nodes'][body]['scale'])
  pos=(np.asarray(pos)-body_pos)/body_scale;norm=np.asarray(norm)*body_scale;norm/=np.linalg.norm(norm,axis=1,keepdims=True)
  g.node('coat_silhouette',g.mesh(pos,norm,uv,ix,fur),parent=body)
 # Independently viewable sample clips; runtime blends articulation with actual speed.
 for clip,period,amp in [('Idle',3,.025),('Walk',1,.43),('Trot',.56,.6),('Greet',2,.12)]:
  samplers=[];channels=[];ts=np.linspace(0,period,33);timeacc=g.acc(ts,'SCALAR')
  for name,node in joints.items():
   if 'knee' in name:continue
   phase=0 if name in ['front_left','rear_right'] else math.pi
   a=[math.sin(t/period*math.tau+phase)*(amp if not name.startswith('tail') else .12) for t in ts]
   rots=[[0,0,math.sin(v/2),math.cos(v/2)] for v in a]
   samplers.append({'input':timeacc,'output':g.acc(rots,'VEC4'),'interpolation':'LINEAR'});channels.append({'sampler':len(samplers)-1,'target':{'node':node,'path':'rotation'}})
  g.j['animations'].append({'name':clip,'samplers':samplers,'channels':channels})
 g.j['extras']={**g.j.get('extras',{}),'provenance':'Original analytical development model; not scan or CGTrader asset','reference':'https://www.youtube.com/watch?v=Jxv0e1VXSR0','unit':'metre','forward':'+X','quality':'development; requires anatomical and motion refinement'}
 f=OUT/(b['id']+'.glb');g.write(f);return {'id':b['id'],'file':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size,'nodes':len(g.j['nodes']),'triangles':sum(g.j['accessors'][m['primitives'][0]['indices']]['count']//3 for m in g.j['meshes'])}
if __name__=='__main__':
 manifest=[make(b) for b in BREEDS];(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
