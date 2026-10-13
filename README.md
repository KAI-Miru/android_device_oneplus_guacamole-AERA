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
Image builds also require a caller-supplied ARM64 Image URL and SHA256. The
download is verified before compilation and kept outside the Git checkout.

The assembly step combines the two checkouts in a temporary directory. It
keeps the existing build-script paths and prepared-environment fingerprint
contract, without putting runner files back into the device branch.

Prepared builds use the private immutable digest in `AERA_PREPARED_BUILDER`.
Source, toolchain and host-build inputs must match the recorded snapshot.
Changing those inputs requires **Prepare private AERA builder**; changing
device configuration usually does not. Registry credentials remain on the
disposable runner and are not copied into snapshots or artifacts.

After checking the prepared baseline, each build applies the revision-checked
recovery staging repair. It removes duplicate Nano/Bash copies of terminfo;
the common installer still copies the full database. Its patch and resulting
source hashes are saved in `recovery-staging-patch.json`.

Cold builds install Android's Linux prerequisites, check out pinned sources,
apply the recorded host patches and build `bootimage`. Disk and memory guards
stop exhausted runners before they corrupt retained outputs. Cleanup and swap
creation run only on disposable GitHub-hosted runners.

## Maintenance

The tests cover checkout recovery, snapshots, capacity limits, build graph
reuse and separation of device and runner inputs. `ci/build.sh` runs the same
device and image verification used by prepared builds. A successful build
does not replace hardware testing.
