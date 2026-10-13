"""Reject wrong/failed build receipts before the physical entry can run."""
import copy,unittest
from mac_native_gate import validate_receipt

class GateTests(unittest.TestCase):
    def setUp(self):
        self.manifest={'native_source_sha256':{'src/a.cpp':'source'}}
        self.receipt={'passed':True,'source_unchanged':True,
            'image':'sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb',
            'native_source_sha256':self.manifest['native_source_sha256'],
            'native_install_sha256':{'install/a.so':'compiled'}}
    def test_exact_receipt(self):
        validate_receipt(self.receipt,self.manifest)
    def test_reject_failed_drifted_or_empty_receipt(self):
        for key,value in [('passed',False),('source_unchanged',False),('image','wrong'),
            ('native_source_sha256',{'src/a.cpp':'changed'}),('native_install_sha256',{})]:
            with self.subTest(key=key):
                receipt=copy.deepcopy(self.receipt);receipt[key]=value
                with self.assertRaises(ValueError):validate_receipt(receipt,self.manifest)

if __name__=='__main__':unittest.main()
