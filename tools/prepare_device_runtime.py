#!/usr/bin/env python3
"""Apply and record the guacamole runtime fix against the pinned native source."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def prepare(source_root, artifact_root, device_root=None):
    device = Path(device_root) if device_root else Path(__file__).resolve().parents[1]
    lock = json.loads((device / 'sources.lock.json').read_text())
    project = 'bootable/recovery'
    expected = next(p['commit'] for p in lock['projects'] if p['path'] == project)
    git = ['git', '-C', str(Path(source_root).resolve() / project)]
    actual = subprocess.check_output(git + ['rev-parse', 'HEAD'], text=True).strip()
    if actual != expected:
        raise ValueError(f'Device runtime patch requires pinned recovery {expected}, found {actual}')
    descriptions = {
        'device-nativewindow.patch': 'Use native AERA libnativewindow with its native libui for GPU buffer allocation',
        'device-vendor-gpu-startup.patch': 'Mount read-only paired vendor shader compilers before native UI and check their availability',
    }
    # Preflight the entire set before editing: a drifted second patch must not
    # leave a partial runtime repair behind.
    pending, records = [], []
    for name, purpose in descriptions.items():
        patch = device / 'patches' / name
        already = subprocess.run(git + ['apply', '--reverse', '--check', str(patch)],
                                 capture_output=True).returncode == 0
        if not already:
            subprocess.run(git + ['apply', '--check', str(patch)], check=True)
            pending.append(patch)
        records.append({'patch': name, 'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
                        'purpose': purpose})
    for patch in pending:
        subprocess.run(git + ['apply', str(patch)], check=True)
    artifacts = Path(artifact_root)
    artifacts.mkdir(parents=True, exist_ok=True)
    record = {'project': project, 'commit': actual, 'patches': records}
    (artifacts / 'device-runtime-patches.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Pinned native GPU buffer and vendor startup repairs applied and recorded')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root')
    parser.add_argument('artifact_root')
    args = parser.parse_args()
    prepare(args.source_root, args.artifact_root)
