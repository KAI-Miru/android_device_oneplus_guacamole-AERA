#!/usr/bin/env python3
"""Verify the actual boot image and its native AERA ramdisk before upload."""
import argparse, gzip, hashlib, io, json, lzma, stat
from pathlib import Path, PurePosixPath
from boot_v2 import parse_boot
from elftools.elf.elffile import ELFFile

def unpack_newc(data):
    entries = {}; offset = 0
    while True:
        h = data[offset:offset+110]
        if len(h) != 110 or h[:6] not in (b'070701', b'070702'):
            raise ValueError('Malformed CPIO header')
        fields = [int(h[6+i*8:14+i*8],16) for i in range(13)]
        mode, size, namesize = fields[1], fields[6], fields[11]
        name_start = offset+110; name_end = name_start+namesize
        if namesize < 1 or name_end > len(data) or data[name_end-1] != 0:
            raise ValueError('Invalid CPIO name bounds')
        name = data[name_start:name_end-1].decode('utf-8')
        begin = (name_end+3)//4*4; end = begin+size
        if end > len(data): raise ValueError('Truncated CPIO entry')
        if name == 'TRAILER!!!': break
        if name.startswith('./'): name = name[2:]
        if name not in ('', '.'):
            if name.startswith('/') or '..' in PurePosixPath(name).parts or name in entries:
                raise ValueError(f'Unsafe or duplicate CPIO path: {name}')
            entries[name] = (mode, data[begin:end])
        offset = (end+3)//4*4
    return entries

def verify_native_init(entries):
    # Pinned AERA's init_recovery.rc module installs under system/etc/init/hw.
    # Its Makefile removes root init.rc and creates this native init symlink.
    script = 'system/etc/init/hw/init.rc'
    for name in ('init', 'system/bin/init', script, 'init.recovery.service.rc'):
        if name not in entries:
            raise ValueError(f'Missing native AERA init file: {name}')
    mode, target = entries['init']
    if not stat.S_ISLNK(mode) or target != b'/system/bin/init':
        raise ValueError('Root init must point to the native /system/bin/init')
    mode, binary = entries['system/bin/init']
    if not stat.S_ISREG(mode) or not mode & 0o111:
        raise ValueError('Native init must be a regular executable')
    elf = ELFFile(io.BytesIO(binary))
    if elf.elfclass != 64 or elf.header['e_machine'] != 'EM_AARCH64':
        raise ValueError('Native init must be an ARM64 ELF')
    for name in (script, 'init.recovery.service.rc'):
        if not stat.S_ISREG(entries[name][0]):
            raise ValueError(f'Native init script must be a regular file: {name}')
    if b'import /init.recovery.service.rc' not in entries[script][1]:
        raise ValueError('Native AERA service init import is missing')
    if b'service recovery /system/bin/recovery' not in entries['init.recovery.service.rc'][1]:
        raise ValueError('Native AERA recovery service is missing')
    return script

def verify(image, report, kernel=None):
    root = Path(__file__).resolve().parents[1]
    expected = json.loads((root/'prebuilt/manifest.json').read_text())
    import os
    from kernel_input import verify_image_kernel
    supplied = kernel or os.environ.get('AERA_PREBUILT_KERNEL')
    if not supplied:
        raise ValueError('Set AERA_PREBUILT_KERNEL to the supplied Image before verifying an image')
    raw = Path(image).read_bytes(); header, pieces = parse_boot(raw)
    module = None
    if (root / 'modules/manifest.json').exists():
        module = json.loads((root / 'modules/manifest.json').read_text())['files']['qca_cld3_wlan.ko']
    kernel_record = verify_image_kernel(pieces['kernel'], supplied, module)
    if len(raw) != expected['partition_bytes']:
        raise ValueError('Final AVB-padded image must equal the actual 96 MiB partition')
    for key in ('kernel_address','ramdisk_address','second_address','tags_address','dtb_address'):
        if header[key] != expected['header'][key]: raise ValueError(f'Changed boot address: {key}')
    for n, record in expected['files'].items():
        if hashlib.sha256(pieces[n]).hexdigest() != record['sha256']:
            raise ValueError(f'Changed device boot component: {n}')
    compressed = pieces['ramdisk']
    data = gzip.decompress(compressed) if compressed[:2] == b'\x1f\x8b' else lzma.decompress(compressed)
    entries = unpack_newc(data)
    required = ['system/bin/recovery','system/etc/recovery.fstab',
                'init.recovery.qcom.rc','init.recovery.usb.rc','init.recovery.qcom_decrypt.rc',
                'system/bin/qseecomd','system/bin/android.hardware.keymaster@4.0-service-qti',
                'system/bin/android.hardware.gatekeeper@1.0-service-qti']
    missing = [p for p in required if p not in entries]
    if missing: raise ValueError(f'Missing ramdisk files: {missing}')
    forbidden = ['system/bin/oplus_h40_credential_helper','system/bin/phoenix','ramdisk-stock.cpio.gz']
    if any(p in entries for p in forbidden): raise ValueError('Stock/custom recovery runtime was imported')
    native_init = verify_native_init(entries)
    inputs = json.loads((root/'proprietary/manifest.json').read_text())
    for n, record in inputs['files'].items():
        if n not in entries or hashlib.sha256(entries[n][1]).hexdigest() != record['sha256']:
            raise ValueError(f'Packaged vendor input differs or is absent: {n}')
    # Check the compiled provider closure, not just dependency names in the tree.
    libraries = {}
    for n, (mode, blob) in entries.items():
        if '/lib64/' in n and n.endswith('.so') and blob[:5] == b'\x7fELF\x02':
            libraries[PurePosixPath(n).name] = blob
    abi_errors = []
    def dynamic(blob):
        elf = ELFFile(io.BytesIO(blob)); dyn = elf.get_section_by_name('.dynamic')
        deps = [t.needed for t in dyn.iter_tags() if t.entry.d_tag == 'DT_NEEDED'] if dyn else []
        symbols = elf.get_section_by_name('.dynsym')
        defined, undefined = set(), set()
        if symbols:
            for s in symbols.iter_symbols():
                if s.entry.st_shndx != 'SHN_UNDEF': defined.add(s.name)
                elif s.entry.st_info.bind == 'STB_GLOBAL': undefined.add(s.name)
        return deps, defined, undefined
    for n, record in inputs['files'].items():
        if 'needed' not in record: continue
        deps, defined, undefined = dynamic(entries[n][1]); seen = set(); todo = list(deps)
        while todo:
            name = todo.pop()
            if name in seen: continue
            seen.add(name)
            if name not in libraries:
                abi_errors.append(f'{n}: missing {name}'); continue
            children, exports, _ = dynamic(libraries[name]); defined |= exports; todo += children
        absent = sorted(undefined - defined - {'__cxa_finalize'})
        if absent: abi_errors.append(f'{n}: unresolved strong symbols {absent[:12]}')
    result = {'kernel_input':kernel_record,'image_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
              'ramdisk_bytes':len(compressed),'ramdisk_entries':len(entries),
              'native_init_script':native_init,'native_init_target':'/system/bin/init',
              'vendor_inputs':len(inputs['files']),'abi_errors':abi_errors}
    target = Path(report); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+'\n')
    if abi_errors: raise ValueError('Vendor/AERA ABI audit failed; see verification report')
    print(json.dumps(result,indent=2))

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('image'); p.add_argument('--report',required=True)
    a=p.parse_args(); verify(a.image,a.report)
