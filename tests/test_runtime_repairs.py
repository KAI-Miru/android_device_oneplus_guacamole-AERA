"""Regressions for observed Health, haptic and stable-MAC startup failures."""
import json
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from import_vendor import haptic_inputs
from verify_health import verify_health_startup, verify_health_runtime
from verify_haptics import verify_haptic_runtime
from verify_wifi import verify_startup_configuration
from verify_keystore import verify_keystore_runtime
from verify_recovery_source import verify_keystore_source


def elf(machine=183):
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    return struct.pack('<16sHHIQQQIHHHHHH', ident, 2, machine, 1, 0, 0, 0, 0, 64, 0, 0, 0, 0, 0)


class RuntimeRepairTests(unittest.TestCase):
    def test_keystore_image_requires_the_recovery_entrypoint(self):
        name = 'system/bin/aera_keystore2'
        init = 'system/etc/init/keystore2.rc'
        text = b'on late-init\n    start keystore2\nservice keystore2 /system/bin/aera_keystore2 /tmp/misc/keystore\n'
        entries = {name: (0o100755, elf()), init: (0o100644, text)}
        self.assertEqual(verify_keystore_runtime(entries)['android_boot_watcher'], False)
        for old, new in ((b'/aera_keystore2 ', b'/keystore2 '),
                         (b'/tmp/misc/keystore', b'/data/misc/keystore')):
            changed = dict(entries)
            changed[init] = (0o100644, text.replace(old, new))
            with self.assertRaises(ValueError):
                verify_keystore_runtime(changed)
        entries[init] = (0o100644, text + b'    setprop sys.boot_completed 1\n')
        with self.assertRaises(ValueError):
            verify_keystore_runtime(entries)

    def test_keystore_source_pin_cannot_drift_without_entrypoint_review(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkout = root / 'bootable/recovery'
            (checkout / 'aera_keystore').mkdir(parents=True)
            source = root / 'system/security/keystore2/src/keystore2_main.rs'
            source.parent.mkdir(parents=True)
            source.write_bytes(b'fixture upstream source\n')
            origin = {'commit': '1' * 40, 'repository': 'https://example.invalid/security',
                      'path': 'keystore2/src/keystore2_main.rs',
                      'upstream_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
            (checkout / 'aera_keystore/source.json').write_text(json.dumps(origin))
            project = {'path': 'system/security', 'commit': origin['commit'],
                       'url': origin['repository'] + '.git'}
            lock = {'projects': [project]}
            self.assertTrue(verify_keystore_source(root, lock, checkout)['platform_crypto_unchanged'])
            project['commit'] = '2' * 40
            with self.assertRaisesRegex(ValueError, 'requires review'):
                verify_keystore_source(root, lock, checkout)
            project['commit'] = origin['commit']
            source.write_bytes(b'changed source\n')
            with self.assertRaisesRegex(ValueError, 'identity differs'):
                verify_keystore_source(root, lock, checkout)

    def health_entries(self):
        return {
            'init.recovery.qcom.rc': (0o100644, (ROOT / 'recovery/root/init.recovery.qcom.rc').read_bytes()),
            'system/etc/init/hw/init.rc': (0o100644, b'import /init.recovery.${ro.hardware}.rc\n'),
            'system/etc/init/android.hardware.health@2.1-service.rc': (0o100644,
                b'service health-hal-2-1 /system/bin/android.hardware.health@2.1-service\n    disabled\n'),
            'system/bin/android.hardware.health@2.1-service': (0o100755, elf()),
            'system/lib64/hw/android.hardware.health@2.0-impl-2.1.so': (0o100644, elf()),
            'vendor/etc/vintf/manifest/android.hardware.health@2.1.xml': (0o100644,
                b'<manifest type="device"><hal><name>android.hardware.health</name>'
                b'<transport>hwbinder</transport><fqname>@2.1::IHealth/default</fqname>'
                b'</hal></manifest>')}

    def test_health_requires_import_and_unconditional_boot_start(self):
        text = (ROOT / 'recovery/root/init.recovery.qcom.rc').read_text()
        self.assertEqual(verify_health_startup(text)['service'], 'health-hal-2-1')
        for old, new in (
                ('import /system/etc/init/android.hardware.health@2.1-service.rc', '# missing import'),
                ('    start health-hal-2-1', '    # missing start'),
                ('on boot', 'on property:test.health.ready=1')):
            with self.subTest(old=old), self.assertRaises(ValueError):
                verify_health_startup(text.replace(old, new))

    def test_health_image_rejects_missing_runtime_or_unreachable_init(self):
        entries = self.health_entries()
        verify_health_runtime(entries)
        for name in entries:
            changed = dict(entries)
            del changed[name]
            with self.subTest(name=name), self.assertRaises(ValueError):
                verify_health_runtime(changed)
        changed = dict(entries)
        name = 'system/bin/android.hardware.health@2.1-service'
        for value in ((0o100644, elf()), (0o100755, elf(62))):
            changed[name] = value
            with self.assertRaises(ValueError):
                verify_health_runtime(changed)

    def test_health_image_rejects_wrong_service_or_manifest(self):
        for name, old, new in (
                ('system/etc/init/android.hardware.health@2.1-service.rc', b'health-hal-2-1', b'wrong-service'),
                ('vendor/etc/vintf/manifest/android.hardware.health@2.1.xml', b'@2.1', b'@1.0')):
            entries = self.health_entries()
            mode, data = entries[name]
            entries[name] = (mode, data.replace(old, new))
            with self.assertRaises(ValueError):
                verify_health_runtime(entries)

    def test_haptic_image_requires_every_exact_h40_waveform(self):
        source = json.loads((ROOT / 'tools/haptic-source.json').read_text())
        entries = {name: (0o100644, (ROOT / 'proprietary' / name).read_bytes())
                   for name in source['files']}
        self.assertEqual(verify_haptic_runtime(entries)['source_dump'], '7Pro_H40')
        for name in entries:
            changed = dict(entries)
            del changed[name]
            with self.subTest(name=name), self.assertRaises(ValueError):
                verify_haptic_runtime(changed)
            changed[name] = (0o100644, b'wrong waveform')
            with self.assertRaises(ValueError):
                verify_haptic_runtime(changed)

    def test_haptic_import_cannot_select_a_different_dump_or_changed_bytes(self):
        source = json.loads((ROOT / 'tools/haptic-source.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            dump = Path(temp) / '7Pro_H40'
            for name in source['files']:
                path = dump / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / 'proprietary' / name).read_bytes())
            self.assertEqual(len(haptic_inputs(dump, source)), 4)
            with self.assertRaises(ValueError):
                haptic_inputs(Path(temp) / 'wrong-model', source)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                haptic_inputs(dump, source)

    def test_wifi_requires_only_the_enabled_mac_file_option(self):
        names = ('init.recovery.wifi.rc', 'system/bin/guacamole-wlan-domains.sh',
                 'system/bin/guacamole-wlan-prepare.sh', 'system/bin/guacamole-wpa-supplicant.sh',
                 'system/bin/guacamole-wlan-storage.sh', 'system/etc/guacamole-wpa_supplicant.conf',
                 'vendor/etc/wifi/WCNSS_qcom_cfg.ini')
        entries = {name: (0o100644, (ROOT / 'recovery/root' / name).read_bytes()) for name in names}
        verify_startup_configuration(entries)
        name = names[-1]
        for blob in (b'read_mac_addr_from_mac_file=0\nEND\n', b'END\n',
                     b'read_mac_addr_from_mac_file=1\nIntf0MacAddress=BAD\nEND\n'):
            changed = dict(entries)
            changed[name] = (0o100644, blob)
            with self.assertRaises(ValueError):
                verify_startup_configuration(changed)
        del entries[name]
        with self.assertRaises(ValueError):
            verify_startup_configuration(entries)


if __name__ == '__main__':
    unittest.main()
