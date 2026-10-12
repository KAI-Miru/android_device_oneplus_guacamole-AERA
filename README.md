# AERA Recovery for OnePlus 7 Pro

Device tree for **guacamole**, built on AERA `aera-16.0`. The current target is
the Android 15 ColorOS port. This is an experimental build.

## Status

| Feature | Device testing |
| --- | --- |
| Display, touch and Adreno acceleration | Working |
| Storage decryption | Unlock confirmed with the Gatekeeper TEE option applied in RAM; fresh boot with the persisted option still needs testing |
| Wi-Fi | Module and firmware startup tested; scanning and connection unverified |

## Device configuration

- ARM64 with secondary ARM support; Snapdragon 855 / Adreno 640.
- Recovery-as-boot, physical A/B slots, boot header v2 and a 96 MiB boot partition.
- DTB and recovery DTBO in `prebuilt/`; hashes are recorded alongside them.
- A compatible ARM64 Image must be supplied by the builder; no kernel binary is included.
- Legacy LZMA ramdisk compression to fit the bootloader's load window.
- Qualcomm crypto providers from the official TeamWin guacamole tree.

The recovery ramdisk and policy are built by AERA. Device-specific init, fstab,
firmware services and vendor libraries are in this tree. See
[device notes](docs/device-notes.md) for the remaining integration details and
[NOTICES.md](NOTICES.md) for sources and licensing.

Two temporary graphics patches remain in [patches/](patches/). Their shared
fixes are under review in AERA [PR #17](https://github.com/AERA-Recovery/android_bootable_recovery/pull/17)
and [PR #18](https://github.com/AERA-Recovery/android_bootable_recovery/pull/18).
The local compiler preflight is specific to this vendor. UI layout changes
belong in AERA, rather than this device tree.

## Building

[Build instructions](docs/build.md) cover local checks and image builds.
GitHub runner scripts, Docker setup and their tests live on
[`ci-runner`](https://github.com/KAI-Miru/android_device_oneplus_guacamole-AERA/tree/ci-runner).
The workflows on `main` delegate to that branch.
