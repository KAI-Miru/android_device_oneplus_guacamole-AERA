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
ref to build. The original H.40 boot blobs and matching WLAN module come from
that device revision. No external kernel, download URL or kernel secret is used.
Fresh builds are the default; old environments with different boot/module manifests
are rejected before reuse.
The launcher on `main` calls the runner workflow on `ci-runner`.
Every build records the resolved device and runner commits separately.

For a local Linux build, check out the runner branch alongside this device tree:

```sh
git clone --branch ci-runner --single-branch \
  https://github.com/KAI-Miru/android_device_oneplus_guacamole-AERA.git ../guacamole-runner
python3 ../guacamole-runner/ci/assemble_inputs.py \
  --device "$PWD" --runner ../guacamole-runner --output /tmp/guacamole-build-inputs
export AERA_DEVICE_REVISION=$(git rev-parse HEAD)
export AERA_SOURCE_DIR=/path/to/dedicated/aera-source
export AERA_ARTIFACT_DIR=/path/to/artifacts
export BUILD_JOBS=4
bash /tmp/guacamole-build-inputs/ci/build.sh
```

Install the Android Linux build prerequisites and Google's `repo` tool first.
The runner branch documents the prepared environment and runner maintenance.
`sources.lock.json` pins recovery and platform `system/security` to our forks'
`miru` commits and keeps the other source revisions fixed. Keystore uses the
standard executable with `--recovery` to omit only its Android boot-completion
watcher; its crypto library and boot-completion/GC protection are unchanged.
Recovery source is checked for a clean Git state; no Python tool rewrites it
during the build.
The Image must support legacy LZMA ramdisks and match the bundled DTB/DTBO and
WLAN module. Its hash is recorded for each build and checked against the final
boot image. It is not added to this repository.

This configuration builds ARM64 only. Device-owned `tools/lzma_ramdisk.py`
compresses the native ramdisk with a 32 MiB dictionary. The final loader-window
check remains mandatory. Existing compiled checkpoints may retain unused ARM32
objects from older builds; their presence is not evidence of new ARM32 compilation.

To reproduce the proprietary inputs from the supplied dumps:

```sh
python3 tools/import_vendor.py /path/to/C15_PORT_GUAC_4G \
  --official-crypto-tree /path/to/pinned-TeamWin-guacamole \
  --gpu-dump /path/to/7Pro_H40 \
  --rmt-storage-dump /path/to/7Pro_H40
```

`tools/official-crypto-source.json` pins the TeamWin revision, and
`tools/gpu-source.json` lists the H.40 graphics entry points. The importer records
the complete non-platform dependency set and checks every official crypto blob
against its Git revision. Native platform libraries are built from pinned source.

`tools/rmt-storage-source.json` pins the original H40 remote-storage binary.
The importer requires that exact stock input, and tree/image verification rejects
the C15 port's incompatible OEM CNV implementation even if the vendor manifest
is regenerated. The build uses the bundled blob and needs no external dump.

A verified build is still a device-test candidate. Boot, storage unlock and
Wi-Fi need physical testing before release.

### Native NAS source update

The pinned recovery now uses `aera-netfs` for SMB/SFTP. The source lock includes
its `libsmb2` and `libssh2` projects and the manifest that declares them. Image
verification checks the new executable and its ABI alongside the WLAN runtime.

An older compiled checkpoint has a different manifest/source plan and will be
rejected by the prepared-environment verifier. The first image build with this
lock needs fresh preparation (`use_prepared=false`); its resulting checkpoint
can then be reused. Recovery-only incremental updates remain supported once
that compatible checkpoint exists.

## Original H.40 boot inputs

`prebuilt/manifest.json` records the original 96 MiB boot-image source hash,
all five extracted component hashes, and the exactly reconstructible stock
boot payload hash. `tools/kernel_input.py` verifies every blob, the original
payload, legacy LZMA support, and the matching bundled WLAN module before source
checkout. The stock header supplies geometry/provenance; Android generates the
new AERA boot header. The stock ramdisk is retained for reference and is never
copied into the native AERA ramdisk.

Image verification checks the exact bundled kernel, original DTB/DTBO, actual
kernel/BSS load bounds, native runtime and all existing ABI/AVB constraints.
Boot and module manifests are part of prepared-environment identity; an old
CI59 compiled environment cannot silently supply a kernel or be treated as a
compatible H.40 checkpoint. Existing caches are not deleted.

WLAN startup validates the actual bundled module metadata, and normal insmod
retains the kernel's vermagic and symbol-version checks. It never force-loads
modules. New H.40-based builds still require physical device testing.

### Stock TFTP RFS layout

WLAN preparation restores the original H40/F22 `/vendor/rfs` links only after
installed vendor has been released. Firmware links resolve to read-only stock
firmware; writable links resolve through guarded RAM mirrors. The private RAM
roots and newly created subsystem directories belong to TFTP's dropped-privilege
account `2903:2903` with mode `0700`. Existing persist files are never chowned
or modified by this preparation, and RAM state survives Wi-Fi toggles. Incorrect
links, foreign mounts, or ownership failures stop startup before the backends
and radio. This configuration still requires hardware Wi-Fi validation.

### Upstream BusyBox

`AERA_USE_BUSYBOX_BINARY=1` enables the pinned AERA vendor hook, which installs
its original static ARM64 prebuilt as `/sbin/busybox` with mode `0755`. Native
Toybox and its command links remain selected. The device forwards the resolved
flag after the hook imports cached settings and checks the staged binary before
native ramdisk compression. The final image audit requires the exact upstream
hash and the applet table, including `ip`, `nc`, `nslookup`, `ping`, `sh`,
`timeout`, `udhcpc` and `wget`. Source identities are recorded in
`tools/busybox-source.json`; there is no duplicate BusyBox blob in this tree.

Packaging supplies the tool used by AERA's connection test. It does not make
one hardcoded internet endpoint universally reachable or repair WPA3/driver
issues. No global ping socket permissions are changed.

The device also supplies an exact `sbin/busybox` filesystem permission rule
and requires `fs_config_files_system` for recovery. Native mkbootfs reads that
generated table before writing the CPIO; without the rule an unlisted `/sbin`
file would fall back to mode `0644`. The pre-pack guard checks the generated
record and the final image audit checks actual executable mode.

## Haptic duration coverage and System probing

The stock-device dump passed as `--rmt-storage-dump` also supplies haptic firmware.
`tools/haptic-source.json` pins all 75 AW8697 duration waveforms (20–500 ms in
20 ms steps, at 166/170/174 Hz), stock RAM calibration variants and the generic RTP
waveform. Guacamole uses H40 and Hotdog uses F22. Import, tree and final-image
checks require the complete range and exact hashes; a different slider position
must not silently request an unpackaged waveform. UI durations remain unchanged.

System keeps one canonical fstab row with filesystem-neutral `ro` options.
Recovery probes ext4 versus EROFS; ext4-only barrier/discard options must not be
passed to an EROFS mount. Read-only ext4 retains its normal default behavior.
The other per-filesystem profiles and userdata encryption flags stay unchanged.
