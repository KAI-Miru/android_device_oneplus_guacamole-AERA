"""Verify the exact WLAN module and native recovery WLAN userspace."""
import hashlib
import io
import json
import stat
import xml.etree.ElementTree as ET
from pathlib import Path
from elftools.elf.elffile import ELFFile

WLAN_EXECUTABLES = ('system/bin/wpa_supplicant', 'system/bin/wpa_cli',
                    'system/bin/dhcptool', 'system/bin/rclone', 'system/bin/fusermount3')


def verify_module(data, record):
    if len(data) != record['bytes'] or hashlib.sha256(data).hexdigest() != record['sha256']:
        raise ValueError('WLAN module identity differs from the pinned WLAN artifact')
    elf = ELFFile(io.BytesIO(data))
    if elf.elfclass != 64 or elf.header['e_machine'] != 'EM_AARCH64':
        raise ValueError('WLAN module must be ARM64')
    section = elf.get_section_by_name('.modinfo')
    info = dict(item.decode().split('=', 1) for item in section.data().split(b'\0') if b'=' in item)
    if info.get('name') != 'wlan' or info.get('vermagic', '').strip() != record['vermagic']:
        raise ValueError('WLAN module kernel ABI differs from its manifest')
    return info


def verify_module_tree(root):
    root = Path(root)
    metadata = json.loads((root / 'modules/manifest.json').read_text())
    files = metadata['files']
    actual = {p.name for p in (root / 'modules').iterdir() if p.is_file()}
    if actual != set(files) | {'manifest.json'}:
        raise ValueError('Unmanifested WLAN module inputs')
    for name, record in files.items():
        verify_module((root / 'modules' / name).read_bytes(), record)
    return metadata


def verify_runtime(entries, module_metadata):
    module = 'system/lib/modules/msmnile/qca_cld3_wlan.ko'
    if module not in entries or not stat.S_ISREG(entries[module][0]):
        raise ValueError('Matched WLAN module is absent')
    verify_module(entries[module][1], module_metadata['files']['qca_cld3_wlan.ko'])
    for name in WLAN_EXECUTABLES:
        if name not in entries or not stat.S_ISREG(entries[name][0]) or not entries[name][0] & 0o111:
            raise ValueError(f'Native WLAN executable missing: {name}')
        elf = ELFFile(io.BytesIO(entries[name][1]))
        if elf.elfclass != 64 or elf.header['e_machine'] != 'EM_AARCH64':
            raise ValueError(f'Native WLAN executable must be ARM64: {name}')
    configs = ('init.recovery.wifi.rc', 'system/bin/guacamole-wlan-firmware.sh',
               'system/bin/guacamole-wlan-prepare.sh', 'system/bin/guacamole-wpa-supplicant.sh',
               'system/etc/guacamole-wpa_supplicant.conf',
               'system/etc/vintf/manifest/guacamole-wifi.xml')
    for name in configs:
        if name not in entries or not stat.S_ISREG(entries[name][0]):
            raise ValueError(f'WLAN startup configuration missing: {name}')
    manifest = ET.fromstring(entries[configs[-1]][1])
    if manifest.tag != 'manifest' or manifest.get('type') != 'framework' or not any(
            hal.findtext('name') == 'android.hardware.wifi.supplicant' and (
                'ISupplicant/default' in (hal.findtext('fqname') or '') or
                (hal.findtext('interface/name') == 'ISupplicant' and
                 hal.findtext('interface/instance') == 'default'))
            for hal in manifest.findall('hal')):
        raise ValueError('Native supplicant declaration is not visible to recovery')
    return {'module_sha256': module_metadata['files']['qca_cld3_wlan.ko']['sha256'],
            'kernel_release': module_metadata['kernel_release'], 'userspace': list(WLAN_EXECUTABLES),
            'device_wifi_tested': False}
