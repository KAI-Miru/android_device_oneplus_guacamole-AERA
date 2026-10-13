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
        for name in ('device-nativewindow.patch', 'device-vendor-gpu-startup.patch'):
            shutil.copyfile(ROOT / 'patches' / name, self.device / 'patches' / name)
        self.file = self.checkout / 'aeraui/core/gpu_renderer.cpp'
        self.file.parent.mkdir(parents=True)
        self.file.write_text('namespace {\n'
            'constexpr char kLogTag[] = "AeraGpu";\n'
            'constexpr char kEglDriver[] = "/vendor/lib64/egl/libEGL_adreno.so";\n'
            'constexpr char kGlesDriver[] = "/vendor/lib64/egl/libGLESv2_adreno.so";\n'
            'constexpr char kNativeWindowLibrary[] = "/vendor/lib64/libnativewindow.so";\n'
            "constexpr uint32_t Fourcc(char a, char b, char c, char d) {\n"
            "  return static_cast<uint32_t>(a) | (static_cast<uint32_t>(b) << 8) |\n"
            "         (static_cast<uint32_t>(c) << 16) | (static_cast<uint32_t>(d) << 24);\n"
            '}\n}\n\n'
            'bool GpuRenderer::Initialize(int32_t width, int32_t height) {\n'
            '  Shutdown();\n  width_ = width;\n  height_ = height;\n\n'
            '  egl_library_ = dlopen(kEglDriver, RTLD_NOW | RTLD_GLOBAL);\n'
            '  if (egl_library_ == nullptr) {\n'
            '    __android_log_print(ANDROID_LOG_WARN, kLogTag,\n'
            '                        "Adreno EGL unavailable: %s", dlerror());\n'
            '    return false;\n  }\n}\n')
        self.startup = self.checkout / 'twrp.cpp'
        self.startup.write_text('int main(int argc, char **argv) {\n'
            '\t// Set the props for OrangeFox dynamic partitions\n'
            '\t//PartitionManager.Fox_Set_Dynamic_Partition_Props();\n\n'
            '\t// start the UI\n\tprintf("Starting the UI...\\n");\n\tgui_init();\n}\n')
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
        prepare(self.source, self.root / 'reports', self.device)
        applied = self.file.read_text()
        startup = self.startup.read_text()
        prepare(self.source, self.root / 'reports', self.device)
        self.assertEqual(self.file.read_text(), applied)
        self.assertEqual(self.startup.read_text(), startup)
        self.assertEqual(applied.split('bool GpuRenderer::Initialize')[0],
                         before.split('bool GpuRenderer::Initialize')[0].replace(
            '/vendor/lib64/libnativewindow.so', '/system/lib64/libnativewindow.so'))
        self.assertLess(applied.index('access(compiler, R_OK)'), applied.index('dlopen(kEglDriver'))
        self.assertLess(startup.index('Mount_By_Path("/vendor", false)'), startup.index('gui_init();'))
        self.assertIn('/vendor/lib64/libllvm-qgl.so', applied)
        self.assertIn('/vendor/lib64/libllvm-qcom.so', applied)
        record = json.loads((self.root / 'reports/device-runtime-patches.json').read_text())
        self.assertEqual(record['commit'], self.revision)
        self.assertEqual({p['patch'] for p in record['patches']},
                         {'device-nativewindow.patch', 'device-vendor-gpu-startup.patch'})
        self.assertTrue(all(len(p['patch_sha256']) == 64 for p in record['patches']))

    def test_changed_startup_context_does_not_apply_partial_gpu_patch(self):
        before = self.file.read_text()
        altered = self.startup.read_text().replace('gui_init();', 'different_init();')
        self.startup.write_text(altered)
        with self.assertRaises(subprocess.CalledProcessError):
            prepare(self.source, self.root / 'reports', self.device)
        self.assertEqual(self.file.read_text(), before)
        self.assertEqual(self.startup.read_text(), altered)

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
