import io
import lzma
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from lzma_ramdisk import compress, DICTIONARY_BYTES


class RamdiskCompressionTests(unittest.TestCase):
    def test_native_stream_is_lossless_legacy_lzma(self):
        raw = bytes(range(256)) * 10000
        output = io.BytesIO()
        compress(io.BytesIO(raw), output)
        encoded = output.getvalue()
        self.assertEqual(struct.unpack_from('<I', encoded, 1)[0], DICTIONARY_BYTES)
        self.assertEqual(lzma.decompress(encoded, format=lzma.FORMAT_ALONE), raw)


if __name__ == '__main__':
    unittest.main()
