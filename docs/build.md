# Building and checking

## Device checks

On Linux, from this tree:

```sh
python3 -m pip install -r tools/requirements.txt
python3 tools/verify_tree.py
python3 -m unittest discover -s tests -v
```

The checks cover boot components, vendor identities, init configuration,
encryption settings, the WLAN module and image parsing. Image verification also
checks the loader window, native runtime dependencies and AVB structure.

## Image builds

Use **Guacamole native AERA recovery** in GitHub Actions and select the device
ref to build. Supply an HTTPS URL and SHA256 for your compatible ARM64 Image.
With a private checkpoint, the URL can be blank to reuse a retained Image with
the exact supplied SHA256.
The launcher on `main` calls the runner workflow on `ci-runner`.
Every build records the resolved device and runner commits separately.

For a local Linux build, check out the runner branch alongside this device tree:

```sh
git clone --branch ci-runner --single-branch \
  https://github.com/KAI-Miru/android_device_oneplus_guacamole-AERA.git ../guacamole-runner
python3 ../guacamole-runner/ci/assemble_inputs.py \
  --device "$PWD" --runner ../guacamole-runner --output /tmp/guacamole-build-inputs
export AERA_DEVICE_REVISION=$(git rev-parse HEAD)
export AERA_PREBUILT_KERNEL=/absolute/path/to/your/Image
export AERA_SOURCE_DIR=/path/to/dedicated/aera-source
export AERA_ARTIFACT_DIR=/path/to/artifacts
export BUILD_JOBS=4
bash /tmp/guacamole-build-inputs/ci/build.sh
```

Install the Android Linux build prerequisites and Google's `repo` tool first.
The runner branch documents the prepared environment and runner maintenance.
`sources.lock.json` pins recovery to our AERA fork¡¯s `miru` commit and keeps
the other source revisions fixed. Recovery source is checked for a clean Git
state; no Python tool rewrites it during the build.
The Image must support legacy LZMA ramdisks and match the bundled DTB/DTBO and
WLAN module. Its hash is recorded for each build and checked against the final
boot image. It is not added to this repository.

A verified build is still a device-test candidate. Boot, storage unlock and
Wi-Fi need physical testing before release.
