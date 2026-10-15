#!/usr/bin/env python3
"""Compress a legacy LZMA ramdisk with a bounded 32 MiB dictionary."""
import lzma
import sys

DICTIONARY_BYTES = 32 * 1024 * 1024


def compress(source, target):
    encoder = lzma.LZMACompressor(format=lzma.FORMAT_ALONE, filters=[{
        'id': lzma.FILTER_LZMA1, 'preset': 9 | lzma.PRESET_EXTREME,
        'dict_size': DICTIONARY_BYTES,
    }])
    while chunk := source.read(1024 * 1024):
        target.write(encoder.compress(chunk))
    target.write(encoder.flush())


if __name__ == '__main__':
    # Android's native ramdisk rule invokes LZMA with these two flags.
    if sys.argv[1:] != ['-f', '-c']:
        raise SystemExit('Usage: lzma_ramdisk.py -f -c < ramdisk.cpio > ramdisk.lzma')
    compress(sys.stdin.buffer, sys.stdout.buffer)
