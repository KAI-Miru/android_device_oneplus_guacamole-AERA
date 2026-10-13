#!/usr/bin/env python3
"""Verify input identities, native ramdisk boundaries, and vendor dependencies."""
from pathlib import Path
import hashlib, json, re, sys, xml.etree.ElementTree as ET
from import_vendor import elf_info

ROOT = Path(__file__).resolve().parents[1]

def verify():
    prebuilt = json.loads((ROOT/'prebuilt/manifest.json').read_text())
    assert prebuilt['source'] == 'PRO_CI59-BOOT.img'
    assert prebuilt['source_sha256'] == '718d07ff88435d95df1c930c3ad5ff8e454b823394ffc9b05f9a4ff6ac249034'
    assert prebuilt['source_ramdisk_imported'] is False
    assert prebuilt['partition_bytes'] == 100663296
    for base, manifest in [(ROOT/'prebuilt', prebuilt), (ROOT/'proprietary', json.loads((ROOT/'proprietary/manifest.json').read_text()))]:
        for name, record in manifest['files'].items():
            data = (base/name).read_bytes()
            assert len(data) == record['bytes'], f'Size mismatch: {name}'
            assert hashlib.sha256(data).hexdigest() == record['sha256'], f'Hash mismatch: {name}'
        actual = {p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file()}
        assert actual == set(manifest['files']) | {'manifest.json'}, f'Untracked binary inputs: {actual - set(manifest["files"])}'
    assert set(prebuilt['files']) == {'dtb.img','recovery-dtbo.img'}
    blobs = json.loads((ROOT/'proprietary/manifest.json').read_text())
    crypto = json.loads((ROOT/'tools/official-crypto-source.json').read_text())
    assert blobs['official_crypto_source'] == {k: crypto[k] for k in ('repository', 'commit')}
    for dest in set(crypto['seeds'].values()) | {
            'system/lib64/libQSEEComAPI.so', 'system/lib64/libqtikeymaster4.so',
            'system/lib64/libkeymasterdeviceutils.so', 'system/lib64/libkeymasterutils.so'}:
        record = blobs['files'][dest]
        assert record['source_repository'] == crypto['repository'], f'Non-official crypto provider: {dest}'
        assert record['source_commit'] == crypto['commit'], f'Changed official crypto revision: {dest}'
    provided = {Path(n).name for n in blobs['files']} | set(blobs['platform_libraries'])
    # QSEE hard-codes listener plugins outside its DT_NEEDED dependency table.
    qsee = (ROOT/'proprietary/system/bin/qseecomd').read_bytes()
    listeners = {n.decode() for n in re.findall(rb'lib[\w.+-]+\.so', qsee)}
    assert listeners <= provided, f'Missing QSEE listener plugins: {listeners - provided}'
    for n, record in blobs['files'].items():
        if 'needed' not in record: continue
        info = elf_info(ROOT/'proprietary'/n)
        assert info['machine'] == 'EM_AARCH64', f'ARM64 recovery cannot load this vendor ELF: {n}'
        assert info['needed'] == record['needed'], f'Changed ELF dependencies: {n}'
        assert set(info['needed']) <= provided, f'Unresolved dependencies: {n}'
    board = (ROOT/'BoardConfig.mk').read_text()
    for pattern in [r'BOARD_USES_RECOVERY_AS_BOOT\s*:=\s*true', r'BOARD_BOOTIMAGE_PARTITION_SIZE\s*:=\s*100663296', r'BOARD_BOOT_HEADER_VERSION\s*:=\s*2', r'BOARD_RAMDISK_USE_LZMA\s*:=\s*true', r'AERA_INCLUDE_CRYPTO\s*:=\s*true', r'AERA_USE_FSCRYPT_POLICY\s*:=\s*1']:
        assert re.search(pattern, board), f'Wrong board setting: {pattern}'
    assert 'OPLUS_H40' not in board and 'TARGET_RECOVERY_INITRC' not in board
    fstab = (ROOT/'recovery/root/system/etc/recovery.fstab').read_text()
    rows = [s.split() for s in fstab.splitlines() if s.strip() and not s.lstrip().startswith('#')]
    vendor_rows = [r for r in rows if r[1] == '/vendor']
    assert vendor_rows and all('ro' in r[3].split(',') for r in vendor_rows), 'GPU startup must mount vendor read-only'
    data_rows = [r for r in rows if r[1] == '/data']
    assert len(data_rows) == 1 and data_rows[0][2] == 'f2fs'
    data_flags = set(data_rows[0][-1].split(','))
    assert {'fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized',
            'keydirectory=/metadata/vold/metadata_encryption',
            'metadata_encryption=aes-256-xts'} <= data_flags
    assert re.search(r'AERA_SKIP_ADDITIONAL_FSTAB\s*:=\s*false', board)
    assert re.search(r'AERA_ENABLE_WLAN\s*:=\s*1', board)
    assert re.search(r'BOARD_WPA_SUPPLICANT_DRIVER\s*:=\s*NL80211', board)
    from verify_wifi import verify_module_tree
    verify_module_tree(ROOT)
    twrp_flags = (ROOT/'recovery/root/system/etc/twrp.flags').read_text()
    assert 'fileencryption=' not in twrp_flags, 'Display flags must not override ROM encryption settings'
    assert not any('logical' in r[-1] for r in rows)
    for p in (ROOT/'recovery').rglob('*'):
        if p.is_file():
            assert p.name not in {'init.rc','sepolicy','ramdisk-stock.cpio.gz'}
            assert b'\r' not in p.read_bytes(), f'CRLF in ramdisk configuration: {p}'
    assert 'mount functionfs adb' not in (ROOT/'recovery/root/init.recovery.usb.rc').read_text()
    from verify_image import verify_crypto_service_configuration
    service_entries = {}
    for name in ('init.recovery.qcom.rc', 'init.recovery.guacamole-crypto.rc'):
        service_entries[name] = (0o100644, (ROOT/'recovery/root'/name).read_bytes())
    verify_crypto_service_configuration(service_entries)
    ET.parse(ROOT/'manifest.xml')
    lock = json.loads((ROOT/'sources.lock.json').read_text())
    assert len({p['path'] for p in lock['projects']}) == len(lock['projects'])
    assert all(re.fullmatch('[0-9a-f]{40}',p['commit']) for p in lock['projects'])
    print(f'PASS: DTB/DTBO identities, {len(blobs["files"])} vendor files, native init boundaries, official crypto configuration, {len(lock["projects"])} pinned upstream projects.')

if __name__ == '__main__': verify()
