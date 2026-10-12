#!/usr/bin/env python3
"""Read boot-v2 framing without importing or executing the source ramdisk."""
from pathlib import Path
import hashlib
import struct

def digest(data):
    return hashlib.sha256(data).hexdigest()

def parse_boot(data):
    if len(data) < 1660 or data[:8] != b'ANDROID!':
        raise ValueError('Not an Android boot image')
    u32 = lambda n: struct.unpack_from('<I', data, n)[0]
    u64 = lambda n: struct.unpack_from('<Q', data, n)[0]
    if u32(40) != 2 or u32(1644) != 1660:
        raise ValueError('Only the verified boot header v2 layout is accepted')
    page = u32(36)
    if page != 4096:
        raise ValueError('Guacamole requires the verified 4096-byte pages')
    align = lambda n: (n + page - 1) // page * page
    ramdisk_offset = page + align(u32(8))
    dtbo_offset = ramdisk_offset + align(u32(16)) + align(u32(24))
    if u32(24) != 0 or u64(1636) != dtbo_offset:
        raise ValueError('Unexpected second stage or recovery DTBO offset')
    pieces = {}
    for name, size, offset in [
        ('kernel', u32(8), page), ('ramdisk', u32(16), ramdisk_offset),
        ('recovery-dtbo.img', u32(1632), dtbo_offset),
        ('dtb.img', u32(1648), dtbo_offset + align(u32(1632))),
    ]:
        if size <= 0 or offset + size > len(data):
            raise ValueError(f'Invalid {name} bounds')
        pieces[name] = data[offset:offset + size]
    cmdline = data[64:576].split(b'\0')[0] + data[608:1632].split(b'\0')[0]
    return {
        'header_version': 2, 'page_size': page,
        'kernel_address': u32(12), 'ramdisk_address': u32(20),
        'second_address': u32(28), 'tags_address': u32(32),
        'dtb_address': u64(1652), 'cmdline': cmdline.decode('ascii'),
    }, pieces

def extract(source, destination):
    import json
    image = Path(source).read_bytes()
    if len(image) != 100663296:
        raise ValueError('Expected the tested 96 MiB source boot image')
    header, pieces = parse_boot(image)
    out = Path(destination); out.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in ('dtb.img', 'recovery-dtbo.img'):
        (out / name).write_bytes(pieces[name])
        files[name] = {'bytes': len(pieces[name]), 'sha256': digest(pieces[name])}
    metadata = {
        'source': Path(source).name, 'source_sha256': digest(image),
        'partition_bytes': 100663296, 'header': header, 'files': files,
        'source_ramdisk_imported': False,
    }
    (out / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8', newline='\n')
    return metadata

if __name__ == '__main__':
    import argparse, json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source'); p.add_argument('destination'); a = p.parse_args()
    print(json.dumps(extract(a.source, a.destination), indent=2))
