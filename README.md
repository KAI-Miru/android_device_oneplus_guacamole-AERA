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

## Kernel containers and WLAN compatibility

Kernel intake identifies ARM64 Image, gzip Image or boot-v2 payloads by content,
not archive or member names. A ZIP may contain one candidate payload or one
inner ZIP containing it. Multiple candidates, extra ZIP nesting, unsafe paths,
symlinks and oversized inputs are rejected. The exact caller-supplied kernel
SHA256 remains mandatory; ramdisks and device trees in containers are ignored.

WLAN startup reads `modinfo -F vermagic` from the actual bundled module and
compares its release with the running kernel before starting radio helpers.
Normal `insmod` retains the kernel's vermagic and symbol-version checks; modules
are never force-loaded. Rebuilding with a different kernel/module pair also
requires updating the module manifest and passing the existing image/ABI audits.
