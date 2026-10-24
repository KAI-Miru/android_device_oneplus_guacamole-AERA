# Guacamole build runners

This branch contains GitHub Actions, source checkout helpers and the private
prepared-builder tooling. Device configuration and recovery fixes live on
[`main`](https://github.com/KAI-Miru/android_device_oneplus_guacamole-AERA/tree/main).

Runner changes belong on `ci-runner`. Pushes and pull requests run the runner
tests together with the selected device tree's checks. The small launchers on
`main` call the workflows here.

## Builds

**Guacamole native AERA recovery** accepts a device branch, tag or commit. The
validation job resolves that ref once; build jobs use the exact device and
runner commits it checked. Both identities are included in the diagnostics.
Image builds verify the original H.40 kernel, header, reference ramdisk and
device trees bundled by the selected device revision, together with its matching
WLAN module. There are no external kernel inputs, downloads or kernel secrets.

The assembly step combines the two checkouts in a temporary directory. It
keeps the existing build-script paths and prepared-environment fingerprint
contract, without putting runner files back into the device branch.

Prepared builds use the private immutable digest in `AERA_PREPARED_BUILDER`.
The other source projects, toolchains and host-build inputs must match the
recorded snapshot. Recovery can advance to another pinned commit on our AERA
fork¡¯s `miru` branch. Builds check out that commit directly and require clean
tracked sources; they do not apply patches to recovery.

Successful prepared builds retain the complete compiled `out/` tree, Ninja¡¯s
dependency state, source files and nanosecond timestamps in a new private
checkpoint. The diagnostics record its immutable digest in
`compiled-checkpoint-published.json`. Select that digest with
`AERA_PREPARED_BUILDER` for the next build. Ninja rebuilds changed inputs and
their dependent outputs, then the image passes the full audit again.

The first checkpoint needs one device build because the original prepared
environment retained only host outputs. Checkpoints use the existing private
package; the workflow verifies its visibility before publishing. Registry
credentials stay on the runner. The flattened runtime excludes build inputs
and rejects credential files before packaging.

Cold builds install Android's Linux prerequisites, check out pinned sources,
apply the recorded host patches and build `bootimage`. Disk and memory guards
stop exhausted runners before they corrupt retained outputs. Cleanup and swap
creation run only on disposable GitHub-hosted runners.

## Maintenance

The tests cover checkout recovery, snapshots, capacity limits, build graph
reuse and separation of device and runner inputs. `ci/build.sh` runs the same
device and image verification used by prepared builds. A successful build
does not replace hardware testing.

## Bundled boot input policy

`main` owns the original H.40 boot blobs and their manifests. Cold builds,
preparation and prepared builds all run the same bundled-input verifier before
compilation. The original stock ramdisk is a reference blob; AERA compiles its
native ramdisk. No external Image or retained compiled-image fallback is used.

Prepared-environment fingerprints include the boot and WLAN module manifests.
Old CI59 environments remain stored but are rejected for H.40 builds. Fresh
builds are the default. The archive selector remains a standalone tested tool;
it is not part of Guacamole's bundled-input build path.
