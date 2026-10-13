# Device notes

## Boot layout

The DTB and recovery DTBO identities are in `prebuilt/manifest.json`.

The boot partition is 96 MiB. The image verifier calculates the smaller runtime
load window from the supplied Image header, the DTB reservation and guard pages.
The firmware layout is in `config/bootloader-layout.json`. The supplied Image
must support legacy LZMA ramdisks and match the device's DTB, firmware and WLAN
module. The tested firmware did not complete `fastboot boot`.
Fastbootd is disabled for this physical partition layout.

## Graphics and input

The ramdisk includes the platform task profiles and VINTF declarations needed
by logd, hwservicemanager and the graphics allocator. `runatboot.sh` and
`postscreenunblank.sh` send the OEM display notification after the renderer is
ready, which also restores touch.

The two source patches load AERA's matching native-buffer runtime from system
and mount vendor before UI initialization. The installed vendor supplies the
paired Adreno shader compilers. The local preflight checks those files before
entering the driver; its absence check retains AERA's software renderer.

## Decryption

QSEE, Keymaster and Gatekeeper use the official TeamWin guacamole crypto set at
`abef9b8a105c9feee847a6b4ed0903bda8ffb5f9`. The importer records each blob's
origin and hash in `proprietary/manifest.json`.

The target ROM uses F2FS with fscrypt policy v2 and AES-256-XTS metadata
encryption. AERA reads the installed data and metadata fstab entries;
`twrp.flags` supplies display flags without replacing encryption options.
prepdecrypt loads the installed Android version before the Qualcomm services
start. Boot-control 1.1 handles the metadata checkpoint query.

`vendor.gatekeeper.disable_spu=true` selects the working Qualcomm TEE path.
The device owner confirmed unlock after applying this option in RAM and
restarting Gatekeeper. A fresh boot of the persisted setting still needs a
device test.

## Wi-Fi

The bundled `qca_cld3_wlan.ko` has its source artifact, vermagic and hash in
`modules/manifest.json`. Builds reject a supplied Image whose reported release
does not match the module. Release matching alone does not prove full module
compatibility; loading and Wi-Fi still need a device test.

QRTR, PD mapper and CNSS services prepare the ICNSS firmware path asynchronously.
Firmware is mounted read-only; CNSS and supplicant runtime files use tmpfs.
Scanning and connection still need device testing.
