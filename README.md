# AERA Recovery for OnePlus 7 Pro

Device tree for **guacamole**, built on AERA `aera-16.0`. The current target is
the Android 15 ColorOS port. This is an experimental build.

## Status

| Feature | Device testing |
| --- | --- |
| Display, touch and Adreno acceleration | Working |
| Storage decryption | Unlock confirmed with the persisted Gatekeeper TEE option |
| Wi-Fi | Scanning and WPA2 on 2.4 GHz confirmed with temporary services; WPA3 unresolved |
| Reboot and USB after unlock | Startup handoff and USB identity fixes need device confirmation |

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

Recovery sources come directly from the pinned
[`miru` branch](https://github.com/KAI-Miru/android_bootable_recovery/tree/miru)
of our AERA fork. Builds do not apply source patches to recovery. Generic
graphics, power handoff, Fastbootd capability and terminal staging fixes live
there with their source tests. The device overlay declares the paired shader
compiler inputs in `system.prop`; the renderer checks them before loading EGL.

The graphics fixes are under review in AERA
[PR #17](https://github.com/AERA-Recovery/android_bootable_recovery/pull/17) and
[PR #18](https://github.com/AERA-Recovery/android_bootable_recovery/pull/18).
The remaining source changes will be reviewed separately for upstream.

## Building

[Build instructions](docs/build.md) cover local checks and image builds.
GitHub runner scripts, Docker setup and their tests live on
[`ci-runner`](https://github.com/KAI-Miru/android_device_oneplus_guacamole-AERA/tree/ci-runner).
The workflows on `main` delegate to that branch.
