#!/usr/bin/env python3
"""Validate actual packaged skin, joint indices, buffers and provenance, no GL required."""
import json,struct,hashlib
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]/'app/src/main/assets/game/models'
for info in json.loads((root/'manifest.json').read_text()):
 data=(root/info['file']).read_bytes();assert hashlib.sha256(data).hexdigest()==info['sha256']
 assert data[:4]==b'glTF';assert struct.unpack_from('<I',data,8)[0]==len(data)
 n=struct.unpack_from('<I',data,12)[0];j=json.loads(data[20:20+n]);binary=data[28+n:]
 def accessor(i):
  a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];width={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']]
  offset=v.get('byteOffset',0)+a.get('byteOffset',0);arr=np.frombuffer(binary,dtype=dtype,count=a['count']*width,offset=offset).reshape(-1,width)
  assert np.isfinite(arr).all();assert offset+arr.nbytes<=len(binary);return arr
 for i in range(len(j['accessors'])):accessor(i)
 skin=j['skins'][0];assert len(skin['joints'])>=15;assert accessor(skin['inverseBindMatrices']).shape[0]==len(skin['joints'])
 assert all(any(j['nodes'][i]['name']==leg+'_paw' for i in skin['joints']) for leg in ['front_left','front_right','rear_left','rear_right']), 'Paws need deforming joints for foot IK'
 for i,node in enumerate(j['nodes']):
  if node['name']=='coat_silhouette':assert any(parent['name']=='torso' and i in parent.get('children',[]) for parent in j['nodes']), 'Fur must follow torso deformation'
 mesh=next(m for m in j['meshes'] if m.get('name')=='continuous_anatomical_skin')['primitives'][0];attrs=mesh['attributes'];weights=accessor(attrs['WEIGHTS_0']);joints=accessor(attrs['JOINTS_0']);assert np.allclose(weights.sum(axis=1),1,atol=1e-5);assert joints.max()<len(skin['joints']);assert accessor(mesh['indices']).max()<len(weights)
 normals=accessor(attrs['NORMAL']);assert np.allclose(np.linalg.norm(normals,axis=1),1,atol=.01)
 positions=accessor(attrs['POSITION']);triangles=accessor(mesh['indices']).reshape(-1,3)
 face_normals=np.cross(positions[triangles[:,1]]-positions[triangles[:,0]],positions[triangles[:,2]]-positions[triangles[:,0]])
 areas=np.linalg.norm(face_normals,axis=1);dots=np.einsum('ij,ij->i',face_normals,normals[triangles].mean(axis=1))
 assert np.all(dots[areas>1e-10]>0), 'Surface winding must agree with outward normals'
 assert all('uri' not in image for image in j['images'])
 assert j['extras']['reference']=='https://www.youtube.com/watch?v=Jxv0e1VXSR0'
 print(f"PASS {info['id']}: {len(weights)} vertices, {len(skin['joints'])} joints, embedded materials, valid weights/buffers/SHA256")
