import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_image import verify_native_service_configuration


class NativeServiceTests(unittest.TestCase):
    def entries(self):
        return {
            'system/etc/task_profiles.json': (0o100644, json.dumps({'Profiles': [],
                'AggregateProfiles': [{'Name': 'SCHED_SP_FOREGROUND'},
                                      {'Name': 'SCHED_SP_BACKGROUND'}]}).encode()),
            'system/etc/vintf/manifest.xml': (0o100644, b'<manifest type="framework"/>'),
            'system/etc/vintf/manifest/hwservicemanager.xml': (0o100644,
                b'<manifest type="framework"><hal><name>android.hidl.manager</name>'
                b'<transport>hwbinder</transport><version>1.2</version><interface>'
                b'<name>IServiceManager</name><instance>default</instance></interface>'
                b'</hal></manifest>'),
        }

    def test_native_configuration_and_split_framework_fragment(self):
        self.assertEqual(len(verify_native_service_configuration(self.entries())), 3)

    def test_missing_file_or_symlink_is_rejected(self):
        for name in self.entries():
            for mode in (None, 0o120777):
                entries = self.entries()
                if mode is None:
                    del entries[name]
                else:
                    entries[name] = (mode, entries[name][1])
                with self.subTest(name=name, mode=mode), self.assertRaises(ValueError):
                    verify_native_service_configuration(entries)

    def test_logger_requires_scheduling_profiles(self):
        entries = self.entries()
        entries['system/etc/task_profiles.json'] = (0o100644, b'{"Profiles":[]}')
        with self.assertRaisesRegex(ValueError, 'scheduling profiles'):
            verify_native_service_configuration(entries)

    def test_hidl_requires_framework_type_and_manager_declaration(self):
        name = 'system/etc/vintf/manifest/hwservicemanager.xml'
        for old, new in ((b'framework', b'device'), (b'IServiceManager', b'Other'),
                         (b'hwbinder', b'passthrough'), (b'1.2', b'1.0')):
            entries = self.entries()
            entries[name] = (0o100644, entries[name][1].replace(old, new))
            with self.subTest(old=old), self.assertRaises(ValueError):
                verify_native_service_configuration(entries)


if __name__ == '__main__':
    unittest.main()
