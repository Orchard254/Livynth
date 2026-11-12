"""Synthetic GLB morph semantics and two-character QA; Blender not required."""
import json
import math
import struct
import tempfile
import unittest
from pathlib import Path

from tools.measure_glb_topology import read_accessor,_primitive_report
from tools.glb_morph_qa import (delta_statistics,MorphSignalError,
                                 compare_existing_glbs,REQUIRED_MOTION)

def _make_glb(path,*,shift=0.0,zero_target=None):
    count=120
    names=list(REQUIRED_MOTION)+[f'optional_{i:02d}' for i in range(67-len(REQUIRED_MOTION))]
    positions=[(i*0.002+shift,0.0,1.4) for i in range(count)]
    views=[];accessors=[];data=bytearray()
    def add(values,fmt='f',type_name='VEC3',components=3):
        start=len(data)
        data.extend(struct.pack('<'+str(len(values)*components)+fmt,
                                *(v for record in values for v in record)))
        views.append({'buffer':0,'byteOffset':start,'byteLength':len(data)-start})
        accessors.append({'bufferView':len(views)-1,
                          'componentType':5126,'count':len(values),'type':type_name})
        return len(accessors)-1
    pos=add(positions)
    targets=[]
    for name in names:
        active=name in REQUIRED_MOTION and name!=zero_target
        delta=[(.002,0,0) if active and i<30 else (0,0,0) for i in range(count)]
        targets.append({'POSITION':add(delta)})
    # QA checks skin/UV attribute existence; these attributes are semantically
    # fake metadata in the test and MUST NOT be used as a true rig-motion demo.
    js={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(data)}],
        'bufferViews':views,'accessors':accessors,
        'meshes':[{'name':'head','extras':{'targetNames':names},
                   'primitives':[{'attributes':{'POSITION':pos,
                                                'JOINTS_0':pos,'WEIGHTS_0':pos,
                                                'TEXCOORD_0':pos},'targets':targets}]}],
        'nodes':[{'name':'root','children':[1]},{'name':'character','mesh':0,'skin':0}]
                +[{'name':f'joint_{i}'} for i in range(163)],
        'skins':[{'joints':list(range(2,165))}],
        'scenes':[{'nodes':[0]}], 'scene':0}
    body=json.dumps(js,separators=(',',':')).encode('utf-8')
    body+=b' '*((-len(body))%4)
    data+=b'\x00'*((-len(data))%4)
    blob=(struct.pack('<II',len(body),0x4E4F534A)+body
          +struct.pack('<II',len(data),0x004E4942)+data)
    path.write_bytes(struct.pack('<III',0x46546C67,2,12+len(blob))+blob)


class DeltaSemanticsTests(unittest.TestCase):
    def test_empty_delta_is_not_motion(self):
        base=struct.pack('<9f',0,0,0,1,0,0,0,1,0)
        zero=struct.pack('<9f',*[0]*9)
        moving=struct.pack('<9f',.005,0,0,0,0,0,0,0,0)
        bin_chunk=base+zero+moving
        js={'bufferViews':[{'byteOffset':i*len(base),'byteLength':len(base)}
                           for i in range(3)],
            'accessors':[{'bufferView':i,'componentType':5126,
                          'count':3,'type':'VEC3'} for i in range(3)]}
        prim={'attributes':{'POSITION':0},'targets':[{'POSITION':1},{'POSITION':2}]}
        rep=_primitive_report(js,bin_chunk,prim)
        self.assertEqual(rep['morph_targets'][0]['vertices_moved'],0)
        self.assertEqual(rep['morph_targets'][1]['vertices_moved'],1)
        self.assertEqual(rep['morph_targets'][1]['max_displacement'],0.005)

    def test_sparse_delta_accessor_is_applied(self):
        # No dense view; one sparse displacement at vertex 1.
        index_bytes=struct.pack('<H',1)+b'\x00\x00'
        delta_bytes=struct.pack('<3f',.008,0,0)
        js={'bufferViews':[{'byteOffset':0},{'byteOffset':4}],
            'accessors':[{'componentType':5126,'count':3,'type':'VEC3',
                          'sparse':{'count':1,
                             'indices':{'bufferView':0,'componentType':5123},
                             'values':{'bufferView':1}}}]}
        arr=read_accessor(js,index_bytes+delta_bytes,0)
        self.assertEqual(arr[0],(0,0,0))
        self.assertAlmostEqual(arr[1][0],.008,places=6)
        self.assertEqual(arr[2],(0,0,0))

    def test_nonfinite_delta_fails(self):
        with self.assertRaisesRegex(MorphSignalError,'E_MORPH_NONFINITE'):
            delta_statistics([(0,0,0),(math.nan,0,0),(0,0,0)],3)

    def test_zero_motion_detected(self):
        report=delta_statistics([(0,0,0)]*40,40)
        self.assertEqual(report['moved_vertices'],0)

class ExistingGLBTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.a=Path(self.tmp.name)/'a.glb'
        self.b=Path(self.tmp.name)/'b.glb'
        _make_glb(self.a,shift=0)
        _make_glb(self.b,shift=.003)
    def test_two_distinct_glbs_with_shared_morph_contract(self):
        result=compare_existing_glbs(self.a,self.b)
        self.assertIn('NOT_VISUAL_ANIMATION',result['status'])
        self.assertEqual(result['joint_count'],163)
        self.assertEqual(result['morph_count'],67)
        self.assertGreater(result['different_export_vertices_gt_0_1_mm'],100)
    def test_identical_geometry_rejected(self):
        _make_glb(self.b,shift=0)
        with self.assertRaisesRegex(MorphSignalError,'E_NO_MEANINGFUL_IDENTITY_DIFFERENCE'):
            compare_existing_glbs(self.a,self.b)
    def test_inert_blink_rejected(self):
        _make_glb(self.b,shift=.003,zero_target='eyeBlinkLeft')
        with self.assertRaisesRegex(MorphSignalError,'E_INERT_REQUIRED_MORPH_eyeBlinkLeft'):
            compare_existing_glbs(self.a,self.b)

if __name__=='__main__':unittest.main()
