#!/usr/bin/env python3
"""Verify host inputs, allowing only the known transient-FIFO reader repair."""
import argparse
import json
from pathlib import Path
from environment_fingerprint import INPUTS, fingerprint

LEGACY = {'8a153e824e269074134835be9031a8f0ebf5b90ebcb4134e282985231a20d7aa'}
READER_INPUTS = {'tools/prepared_snapshot.py', 'ci/use-prepared.sh'}


def verify(device, source, artifacts, legacy=LEGACY):
    device, source = Path(device), Path(source)
    recorded = json.loads((source / '.aera-prepared-environment.json').read_text())['fingerprint']
    expected = fingerprint(device)
    changed = []
    if recorded != expected:
        retained = source / 'device/oneplus/guacamole'
        if recorded not in legacy or fingerprint(retained) != recorded:
            raise ValueError('Unknown or altered prepared environment; prepare again')
        changed = [name for name in INPUTS
                   if (device / name).read_bytes() != (retained / name).read_bytes()]
        if not changed or not set(changed) <= READER_INPUTS:
            raise ValueError(f'Prepared source/tool inputs changed; prepare again: {changed}')
    result = {'prepared_fingerprint': recorded, 'current_fingerprint': expected,
              'compatible_reader_repair': changed,
              'source_toolchain_host_build_inputs_match': True}
    artifacts = Path(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / 'prepared-environment-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device')
    parser.add_argument('source')
    parser.add_argument('artifacts')
    args = parser.parse_args()
    verify(args.device, args.source, args.artifacts)
