import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_image import verify_gpu_startup_configuration


class GpuStartupTests(unittest.TestCase):
    def renderer(self):
        return (b'/system/lib64/libnativewindow.so\0'
                b'/vendor/lib64/libllvm-qgl.so\0'
                b'/vendor/lib64/libllvm-qcom.so\0'
                b'Guacamole GPU runtime: mounted read-only vendor before UI\n\0')

    def test_paired_compiler_preflight_and_mount_are_required(self):
        report = verify_gpu_startup_configuration(self.renderer())
        self.assertTrue(report['vendor_mount_before_ui'])
        self.assertFalse(report['cold_boot_tested'])
        for absent in (b'/vendor/lib64/libllvm-qgl.so\0', b'/vendor/lib64/libllvm-qcom.so\0',
                       b'Guacamole GPU runtime: mounted read-only vendor before UI'):
            with self.assertRaises(ValueError):
                verify_gpu_startup_configuration(self.renderer().replace(absent, b''))

    def test_old_buffer_path_fix_alone_is_not_a_startup_fix(self):
        with self.assertRaises(ValueError):
            verify_gpu_startup_configuration(b'/system/lib64/libnativewindow.so\0')


if __name__ == '__main__':
    unittest.main()
