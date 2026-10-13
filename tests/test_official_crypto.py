import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from import_vendor import official_crypto_root, select_library
from verify_image import verify_crypto_service_configuration


class OfficialCryptoTests(unittest.TestCase):
    def services(self):
        text = ''
        for name, exe in (('qseecomd', 'qseecomd'),
                          ('keymaster-4-0-qti', 'android.hardware.keymaster@4.0-service-qti'),
                          ('gatekeeper-1-0-qti', 'android.hardware.gatekeeper@1.0-service-qti')):
            text += (f'service {name} /system/bin/{exe}\n'
                     '    override\n    user root\n    group root\n    disabled\n'
                     '    seclabel u:r:recovery:s0\n'
                     '    setenv LD_LIBRARY_PATH /system/lib64:/vendor/lib64:/system/lib:/vendor/lib:/sbin\n\n')
        return {
            'init.recovery.guacamole-crypto.rc': (0o100644, text.encode()),
            'init.recovery.qcom.rc': (0o100644,
                b'import /init.recovery.qcom_decrypt.rc\nimport /init.recovery.guacamole-crypto.rc\n'),
        }

    def test_standard_services_keep_official_providers_when_vendor_is_mounted(self):
        self.assertEqual(len(verify_crypto_service_configuration(self.services())), 3)

    def test_vendor_shadowing_and_wrong_import_order_are_rejected(self):
        entries = self.services()
        name = 'init.recovery.guacamole-crypto.rc'
        entries[name] = (0o100644, entries[name][1].replace(
            b'/system/lib64:/vendor/lib64', b'/vendor/lib64:/system/lib64'))
        with self.assertRaisesRegex(ValueError, 'shadowed'):
            verify_crypto_service_configuration(entries)
        entries = self.services()
        entries['init.recovery.qcom.rc'] = (0o100644,
            b'import /init.recovery.guacamole-crypto.rc\nimport /init.recovery.qcom_decrypt.rc\n')
        with self.assertRaisesRegex(ValueError, 'imported before'):
            verify_crypto_service_configuration(entries)

    def test_blob_import_requires_the_pinned_official_revision(self):
        source = {'commit': '1' * 40}
        with patch('import_vendor.subprocess.check_output', return_value='2' * 40 + '\n'):
            with self.assertRaisesRegex(ValueError, 'Official crypto checkout must be'):
                official_crypto_root(Path('/tmp/official-test'), source)

    def test_library_selection_ignores_extracted_symlink_placeholders(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / 'placeholder', root / 'real'
            first.mkdir(); second.mkdir()
            (first / 'provider.so').write_bytes(b'../real/provider.so')
            (second / 'provider.so').write_bytes(b'\x7fELF' + bytes(64))
            self.assertEqual(select_library('provider.so', [first, second]), second / 'provider.so')
            with self.assertRaises(FileNotFoundError):
                select_library('missing.so', [first, second])


if __name__ == '__main__':
    unittest.main()
