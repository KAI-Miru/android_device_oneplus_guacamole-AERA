import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_device_runtime import prepare


class DeviceRuntimePatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.checkout = self.source / 'bootable/recovery'
        self.checkout.mkdir(parents=True)
        self.device = self.root / 'device'
        (self.device / 'patches').mkdir(parents=True)
        shutil.copyfile(ROOT / 'patches/device-nativewindow.patch',
                        self.device / 'patches/device-nativewindow.patch')
        self.file = self.checkout / 'aeraui/core/gpu_renderer.cpp'
        self.file.parent.mkdir(parents=True)
        self.file.write_text('namespace {\n'
            'constexpr char kLogTag[] = "AeraGpu";\n'
            'constexpr char kEglDriver[] = "/vendor/lib64/egl/libEGL_adreno.so";\n'
            'constexpr char kGlesDriver[] = "/vendor/lib64/egl/libGLESv2_adreno.so";\n'
            'constexpr char kNativeWindowLibrary[] = "/vendor/lib64/libnativewindow.so";\n'
            "constexpr uint32_t Fourcc(char a, char b, char c, char d) {\n"
            "  return static_cast<uint32_t>(a) | (static_cast<uint32_t>(b) << 8) |\n"
            "         (static_cast<uint32_t>(c) << 16) | (static_cast<uint32_t>(d) << 24);\n")
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('add', '.')
        self.git('commit', '-qm', 'pinned fixture')
        self.revision = self.git('rev-parse', 'HEAD').strip()
        (self.device / 'sources.lock.json').write_text(json.dumps({'projects': [
            {'path': 'bootable/recovery', 'commit': self.revision}]}))

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.checkout), *args], text=True)

    def test_repeat_application_preserves_native_code_and_records_identity(self):
        before = self.file.read_text()
        for _ in range(2):
            prepare(self.source, self.root / 'reports', self.device)
        self.assertEqual(self.file.read_text(), before.replace(
            '/vendor/lib64/libnativewindow.so', '/system/lib64/libnativewindow.so'))
        record = json.loads((self.root / 'reports/device-runtime-patches.json').read_text())
        self.assertEqual(record['commit'], self.revision)
        self.assertEqual(len(record['patch_sha256']), 64)

    def test_unpinned_revision_and_changed_context_fail_without_editing(self):
        before = self.file.read_text()
        self.git('commit', '--allow-empty', '-qm', 'other revision')
        with self.assertRaisesRegex(ValueError, 'requires pinned recovery'):
            prepare(self.source, self.root / 'reports', self.device)
        self.assertEqual(self.file.read_text(), before)
        self.git('reset', '--hard', self.revision)
        altered = before.replace('/vendor/lib64/libnativewindow.so', '/other/lib.so')
        self.file.write_text(altered)
        with self.assertRaises(subprocess.CalledProcessError):
            prepare(self.source, self.root / 'reports', self.device)
        self.assertEqual(self.file.read_text(), altered)


if __name__ == '__main__':
    unittest.main()
