"""Require the exact H.40 waveforms requested by Guacamole's AW8697 driver."""
import hashlib
import json
import stat
from pathlib import Path


def verify_haptic_runtime(entries):
    source = json.loads(Path(__file__).with_name('haptic-source.json').read_text())
    for name, identity in source['files'].items():
        if name not in entries or not stat.S_ISREG(entries[name][0]):
            raise ValueError(f'Missing regular haptic firmware: {name}')
        data = entries[name][1]
        if len(data) != identity['bytes'] or hashlib.sha256(data).hexdigest() != identity['sha256']:
            raise ValueError(f'Haptic firmware differs from H.40: {name}')
    return {'source_dump': source['source_dump'], 'files': source['files']}
