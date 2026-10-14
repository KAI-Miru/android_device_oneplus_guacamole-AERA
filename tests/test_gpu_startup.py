import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_image import verify_gpu_startup_configuration


class GpuStartupTests(unittest.TestCase):
    def renderer(self):
        return (b'/system/lib64/libnativewindow.so\0'
                b'ro.aera.gpu.required_libraries\0'
                b'GPU runtime: required library unavailable: %s\0'
                b'Native UI: vendor runtime mount unavailable\n\0')

    def properties(self):
        return b'ro.aera.gpu.required_libraries=/vendor/lib64/libllvm-qgl.so:/vendor/lib64/libllvm-qcom.so\n'

    def test_paired_compiler_preflight_and_mount_are_required(self):
        report = verify_gpu_startup_configuration(self.renderer(), self.properties())
        self.assertTrue(report['vendor_mount_before_ui'])
        self.assertFalse(report['cold_boot_tested'])
        for absent in (b'ro.aera.gpu.required_libraries\0', b'GPU runtime: required library unavailable',
                       b'Native UI: vendor runtime mount unavailable'):
            with self.assertRaises(ValueError):
                verify_gpu_startup_configuration(self.renderer().replace(absent, b''), self.properties())

    def test_old_buffer_path_fix_alone_is_not_a_startup_fix(self):
        with self.assertRaises(ValueError):
            verify_gpu_startup_configuration(b'/system/lib64/libnativewindow.so\0', self.properties())

    def test_device_compiler_inputs_cannot_be_omitted(self):
        with self.assertRaises(ValueError):
            verify_gpu_startup_configuration(self.renderer(), b'')


if __name__ == '__main__':
    unittest.main()
