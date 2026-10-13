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
    patch = device / 'patches/device-nativewindow.patch'
    already = subprocess.run(git + ['apply', '--reverse', '--check', str(patch)],
                             capture_output=True).returncode == 0
    if not already:
        subprocess.run(git + ['apply', '--check', str(patch)], check=True)
        subprocess.run(git + ['apply', str(patch)], check=True)
    artifacts = Path(artifact_root)
    artifacts.mkdir(parents=True, exist_ok=True)
    record = {'project': project, 'commit': actual, 'patch': patch.name,
              'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
              'purpose': 'Use native AERA libnativewindow with its native libui for GPU buffer allocation'}
    (artifacts / 'device-runtime-patches.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Pinned native GPU runtime path repaired and recorded')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root')
    parser.add_argument('artifact_root')
    args = parser.parse_args()
    prepare(args.source_root, args.artifact_root)
