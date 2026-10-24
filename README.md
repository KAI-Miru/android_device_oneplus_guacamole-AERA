# AERA Recovery for OnePlus 7 Pro

Device tree for **guacamole**, built on AERA `aera-16.0`. The current target is
the Android 15 ColorOS port. This is an experimental build.

## Status

| Feature | Device testing |
| --- | --- |
| Display, touch and Adreno acceleration | Previous runtime confirmed; bundled H.40 replacement needs testing |
| Storage decryption | Unlock confirmed with the persisted Gatekeeper TEE option |
| Wi-Fi | Scanning and WPA2 on 2.4 GHz confirmed with temporary services; WPA3 unresolved |
| Reboot and USB after unlock | Startup handoff and USB identity fixes need device confirmation |
| Screen timeout, Android screen lock and rotation | Confirmed on the previous alpha |

## Device configuration

- ARM64-only recovery; Snapdragon 855 / Adreno 640.
- Recovery-as-boot, physical A/B slots, boot header v2 and a 96 MiB boot partition.
- Original H.40 boot header, kernel, stock ramdisk, DTB and recovery DTBO are versioned in `prebuilt/`.
- Builds use the bundled H.40 kernel and matching stock WLAN module; no kernel URL, artifact secret or user-supplied image is required.
- The stock ramdisk is a verified reference; the final ramdisk is built natively by AERA.
- Legacy LZMA ramdisk with a 32 MiB dictionary to fit the bootloader's load window.
- Complete H.40 Adreno EGL/GLES runtime in the ramdisk, including its shader compiler.
- Qualcomm crypto providers from the official TeamWin guacamole tree.

The recovery ramdisk and policy are built by AERA. Device-specific init, fstab,
firmware services and vendor libraries are in this tree. See
[device notes](docs/device-notes.md) for the remaining integration details and
[NOTICES.md](NOTICES.md) for sources and licensing.

Recovery sources come directly from the pinned
[`miru` branch](https://github.com/KAI-Miru/android_bootable_recovery/tree/miru)
of our AERA fork. Builds do not apply source patches to recovery. Generic
graphics, power handoff, Fastbootd capability and terminal staging fixes live
there with their source tests. The device overlay declares the bundled shader
compiler in `system.prop`; the renderer checks it before loading EGL.
Graphics startup does not require mounting the installed vendor partition.

The fork adds screen timeout beside Brightness and an optional Android owner
credential screen lock after successful storage unlock. It uses a native
verification-only path and opens the PIN, pattern or password screen directly.
The lock, swipe-unlock rotation and landscape backgrounds passed device testing
on the previous alpha. The screen lock does not restrict ADB.
New labels are available in English and both Chinese languages.

Wipe also includes filesystem selection for eligible writable partitions.
Available choices depend on the running kernel and packaged formatters.
Changing `/data` erases internal storage and resets encryption. The chooser
requires typing `yes` and pressing the format button; host checks passed, but
physical formatting has not been tested.

The native-buffer loader change is under review in AERA
[PR #17](https://github.com/AERA-Recovery/android_bootable_recovery/pull/17).
The vendor-mount proposal was closed in favor of a self-contained graphics runtime.

## Building

[Build instructions](docs/build.md) cover local checks and image builds.
GitHub runner scripts, Docker setup and their tests live on
[`ci-runner`](https://github.com/KAI-Miru/android_device_oneplus_guacamole-AERA/tree/ci-runner).
The workflows on `main` delegate to that branch.
