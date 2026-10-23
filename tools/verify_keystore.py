"""Require the recovery-specific entrypoint under the standard keystore service."""
import io
import shlex
import stat
from elftools.elf.elffile import ELFFile


def verify_keystore_runtime(entries):
    executable = 'system/bin/aera_keystore2'
    init = 'system/etc/init/keystore2.rc'
    for name in (executable, init):
        if name not in entries or not stat.S_ISREG(entries[name][0]):
            raise ValueError(f'Missing recovery keystore runtime: {name}')
    lines = [shlex.split(line) for line in entries[init][1].decode().splitlines()
             if line.strip() and not line.lstrip().startswith('#')]
    declaration = ['service', 'keystore2', '/' + executable, '/tmp/misc/keystore']
    if declaration not in lines or ['start', 'keystore2'] not in lines:
        raise ValueError('Recovery keystore must use its entrypoint and temporary database')
    if any(line[:2] == ['setprop', 'sys.boot_completed'] for line in lines):
        raise ValueError('Recovery keystore must not spoof Android boot completion')
    mode, blob = entries[executable]
    elf = ELFFile(io.BytesIO(blob))
    if not mode & 0o111 or elf.elfclass != 64 or elf.header['e_machine'] != 'EM_AARCH64':
        raise ValueError('Recovery keystore entrypoint must be executable ARM64')
    return {'executable': executable, 'database': '/tmp/misc/keystore',
            'android_boot_watcher': False, 'platform_crypto_unchanged': True}
