import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_usb import verify_usb_configuration


class UsbTests(unittest.TestCase):
    def setUp(self):
        self.script = (ROOT / 'recovery/root/init.recovery.usb.rc').read_bytes()

    def test_native_mtp_adb_identity_and_functions(self):
        self.assertEqual(verify_usb_configuration(self.script)['mtp_adb_pid'], '4ee2')

    def test_rejects_mismatched_identity_and_missing_adb_function(self):
        changes = ((b'0x4ee2', b'0x9012'), (b'0x18d1', b'0x05c6'),
                   (b'functions/ffs.adb', b'functions/ffs.mtp'),
                   (b'property:sys.usb.ffs.ready=1', b'property:sys.usb.ffs.ready=0'),
                   (b'    start adbd', b'    stop adbd'),
                   (b'UDC "none"', b'UDC "controller"'))
        for old, new in changes:
            with self.subTest(old=old), self.assertRaises(ValueError):
                verify_usb_configuration(self.script.replace(old, new))


if __name__ == '__main__':
    unittest.main()
