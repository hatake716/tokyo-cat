"""Smoothly union anatomical volumes, then bind continuous skin to articulated joints."""
import math
import numpy as np
from skimage.measure import marching_cubes

def build(g,b,fur_mesh,cream_mesh):
 nodes=g.j['nodes'];parent={child:i for i,n in enumerate(nodes) for child in n.get('children',[])}
 def translation(i):
  t=np.array(nodes[i].get('translation',[0,0,0]),dtype=float)
  return t+translation(parent[i]) if i in parent else t
 joint_names={'cat','torso','haunch','shoulders','neck','chest','head','front_left','front_right','rear_left','rear_right','tail0','tail1','tail2','front_left_knee','front_right_knee','rear_left_knee','rear_right_knee'}
 joint_names.update({leg+'_paw' for leg in ['front_left','front_right','rear_left','rear_right']})
 joints=[i for i,n in enumerate(nodes) if n['name'] in joint_names];ji={n:i for i,n in enumerate(joints)}
 def bone(i):
  if nodes[i]['name']=='toe':
   paw_name=nodes[parent[i]]['name'].replace('_knee','_paw')
   return ji[next(k for k,n in enumerate(nodes) if n['name']==paw_name)]
  while i not in ji:i=parent[i]
  return ji[i]
 shapes=[]
 for i,n in enumerate(nodes):
  if n.get('mesh') in [fur_mesh,cream_mesh]:
   shapes.append((translation(i),np.array(n['scale']),bone(i),n['mesh']==cream_mesh));del n['mesh']
 step=.0055
 lo=np.array([-.68,-.025,-.19]);hi=np.array([.44,.64,.19]);axes=[np.arange(a,z+step,step,dtype=np.float32) for a,z in zip(lo,hi)]
 xyz=np.stack(np.meshgrid(*axes,indexing='ij'),-1)
 field=np.full(xyz.shape[:-1],10,dtype=np.float32)
 def sdf(points,c,r):
  p=(points-c)/r;k0=np.linalg.norm(p,axis=-1);k1=np.linalg.norm(p/r,axis=-1)
  return k0*(k0-1)/np.maximum(k1,.00001)
 k=.016
 for c,r,j,w in shapes:
  d=sdf(xyz,c,r);h=np.maximum(k-np.abs(field-d),0)/k;field=np.minimum(field,d)-h*h*k*.25
 verts,faces,normals,_=marching_cubes(field,0,spacing=(step,step,step),gradient_direction='ascent');verts+=lo;normals=-normals;faces=faces[:,[0,2,1]]
 influences=np.zeros((len(verts),len(joints)),dtype=np.float32);white=np.zeros(len(verts),dtype=np.float32)
 for c,r,j,w in shapes:
  weight=np.exp(-np.clip(sdf(verts,c,r),-.015,1)/.009);influences[:,j]+=weight
  if w:white+=weight
 order=np.argsort(influences,axis=1)[:,-4:];weights=np.take_along_axis(influences,order,axis=1);weights/=weights.sum(axis=1,keepdims=True)
 white=np.clip(white/np.maximum(influences.sum(axis=1),1e-12),0,1)
 rgb=np.array([int(b['color'][i:i+2],16) for i in [1,3,5]])/255
 x,y,z=verts.T;noise=np.random.default_rng(12).normal(0,.025,len(verts));factor=1+noise
 if b['id'] in ['mixed','american','siberian','norwegian']:
  stripes=np.maximum(0,np.sin(x*112+np.sin(y*31)*1.8+np.cos(z*37)))**12
  factor-=stripes*.46
 col=np.clip(factor[:,None]*rgb,0,1)
 if b['id'] in ['ragdoll','ragamuffin']:
  point=np.clip((x-.30)*18,0,.75)+np.clip((.12-y)*5,0,.45)+np.clip((-x-.3)*3,0,.5)
  col*=np.maximum(.3,1-point[:,None]*.65)
 # Brighter underbody and muzzle, a natural light chin rather than a ring seam.
 under=np.clip((.31-y)*4,0,.14);col=np.clip(col+under[:,None],0,1)
 col=col*(1-white[:,None])+np.array([.86,.84,.77])*white[:,None]
 # Material color factors are linear; convert authored sRGB coat samples.
 linear=np.where(col<=.04045,col/12.92,((col+.055)/1.055)**2.4)
 material=g.material('continuous_coat',[1,1,1],.94)
 attrs={'POSITION':g.acc(verts,'VEC3'),'NORMAL':g.acc(normals,'VEC3'),'COLOR_0':g.acc(linear,'VEC3'),'JOINTS_0':g.acc(order,'VEC4',5123),'WEIGHTS_0':g.acc(weights,'VEC4')}
 mesh=len(g.j['meshes']);g.j['meshes'].append({'name':'continuous_anatomical_skin','primitives':[{'attributes':attrs,'indices':g.acc(faces.reshape(-1),'SCALAR',5125),'material':material}]})
 inv=[]
 for i in joints:
  m=np.eye(4,dtype=np.float32);scale=np.array(nodes[i].get('scale',[1,1,1]));m[:3,:3]=np.diag(1/scale);m[:3,3]=-translation(i)/scale;inv.append(m.T.reshape(16))
 g.j['skins']=[{'name':'quadruped_rig','inverseBindMatrices':g.acc(inv,'MAT4'),'skeleton':0,'joints':joints}]
 node=g.node('continuous_skin',mesh);nodes[node]['skin']=0
 g.j.setdefault('extras',{})['surface']={'method':'smooth implicit union, marching cubes, weighted skin','vertices':len(verts),'triangles':len(faces),'joints':len(joints)}
