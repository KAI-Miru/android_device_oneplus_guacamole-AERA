#!/usr/bin/env python3
"""Give the pinned recovery's common installer sole ownership of terminfo."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def prepare(source_root, artifact_root, inputs_root=None):
    inputs = Path(inputs_root) if inputs_root else Path(__file__).resolve().parents[1]
    project = 'bootable/recovery'
    checkout = Path(source_root).resolve() / project
    lock = json.loads((inputs / 'sources.lock.json').read_text())
    expected = next(p['commit'] for p in lock['projects'] if p['path'] == project)
    git = ['git', '-C', str(checkout)]
    actual = subprocess.check_output(git + ['rev-parse', 'HEAD'], text=True).strip()
    if actual != expected:
        raise ValueError(f'Recovery staging requires pinned source {expected}, found {actual}')
    # The shared rule still stages the entire database, even without Nano/Bash.
    owner = checkout / 'Android.mk'
    original = subprocess.check_output(git + ['show', 'HEAD:Android.mk'])
    if owner.read_bytes() != original or original.count(
            b'cp -rf external/libncurses/lib/terminfo $(TARGET_RECOVERY_ROOT_OUT)/system/etc/;') != 1:
        raise ValueError('The common terminfo installer changed; refusing a partial repair')
    patch = inputs / 'ci/patches/recovery-terminfo-stage.patch'
    already = subprocess.run(git + ['apply', '--reverse', '--check', str(patch)],
                             capture_output=True).returncode == 0
    if not already:
        subprocess.run(git + ['apply', '--check', str(patch)], check=True)
        subprocess.run(git + ['apply', str(patch)], check=True)
    record = {'project': project, 'commit': actual,
              'patch': patch.name, 'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
              'purpose': 'Stage terminfo once through file_contexts_text; preserve Nano and Bash installers',
              'source_files': {name: hashlib.sha256((checkout / name).read_bytes()).hexdigest()
                               for name in ('Android.mk', 'prebuilt/Android.mk')}}
    artifacts = Path(artifact_root)
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / 'recovery-staging-patch.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Pinned recovery terminal-data staging repair applied and recorded')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root')
    parser.add_argument('artifact_root')
    args = parser.parse_args()
    prepare(args.source_root, args.artifact_root)
