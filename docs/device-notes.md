# Device notes

## Boot layout

The DTB and recovery DTBO identities are in `prebuilt/manifest.json`.

The boot partition is 96 MiB. The image verifier calculates the smaller runtime
load window from the supplied Image header, the DTB reservation and guard pages.
The firmware layout is in `config/bootloader-layout.json`. The supplied Image
must support legacy LZMA ramdisks and match the device's DTB, firmware and WLAN
module. The tested firmware did not complete `fastboot boot`.
Fastbootd is disabled. Its native menu, startup argument and userspace transitions
check the build capability before changing USB or logical partitions.

## Graphics and input

The ramdisk includes the platform task profiles and VINTF declarations needed
by logd, hwservicemanager and the graphics allocator. `runatboot.sh` and
`postscreenunblank.sh` send the OEM display notification after the renderer is
ready, which also restores touch.

The pinned recovery fork loads AERA's matching native-buffer runtime from system
and mount vendor before UI initialization. The installed vendor supplies the
paired Adreno shader compilers. The device declares those files in `ro.aera.gpu.required_libraries`.
The native preflight checks them before
entering the driver; its absence check retains AERA's software renderer.

Reboot and power-off actions hand their result to the recovery backend while
the early graphics thread stays alive. Waiting for that thread to exit first
can block inside vendor EGL thread-local cleanup before init receives the
power request. Startup can also enter a legacy page before the main UI call;
the power result must survive that later call rather than open another renderer.
The device trace confirmed this second loop during a stalled Recovery reboot.
Native tests cover all terminal destinations and repeated startup entry;
the repaired image still needs device confirmation.

## USB

The configfs MTP+ADB profile uses Google's `18d1:4ee2` identity, matching the
native recovery default. The former `18d1:9012` pair enumerated after unlock
without an ADB interface registration on the test host. The device extension
keeps both MTP and ADB FunctionFS interfaces; native init owns the ADB mount.
The MTP profiles wait for MTP descriptors, and the combined profile also waits
for ADB descriptors, before binding the controller. Waiting only for ADB can
leave USB detached when MTP starts later after storage unlock.
Native `none` cleanup owns the disconnect; the ready handler links the
functions and binds without detaching them again.

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
The device owner confirmed unlock both after applying this option in RAM and
after booting the image with the persisted setting.

## Wi-Fi

The bundled `qca_cld3_wlan.ko` has its source artifact, vermagic and hash in
`modules/manifest.json`. Builds reject a supplied Image whose reported release
does not match the module. Release matching alone does not prove full module
compatibility; runtime testing is required.

QRTR, PD mapper and CNSS services prepare the ICNSS firmware path asynchronously.
Firmware is mounted read-only; CNSS and supplicant runtime files use tmpfs.
PD mapper waits for the installed vendor mount and firmware bind during early
recovery startup, so its
initial domain list is populated before ICNSS's five-minute registration timeout.
This stage leaves the modem/ADSP power references and WLAN module to the Wi-Fi
enable path.
Stock `rmt_storage` and `tftp_server` start before the radio. The modem needs
these backends to complete firmware startup. Remote storage serves the installed
modem NV partitions. TFTP's writable RFS directories use RAM mirrors of the
read-only persist files; the mirrors remain available across Wi-Fi toggles.
QRTR, PD mapper and the stock backends stay registered while Wi-Fi is off.
The modem/ADSP power references and CNSS process stop with the supplicant.

The native supplicant reads its private RAM configuration as the `wifi` user.
The configuration enables PMF negotiation and both SAE methods, including H2E.
Startup diagnostics stay in `/tmp` on the phone.

Temporary-service device tests confirmed scanning and WPA2 on 2.4 GHz. WPA3
on 5 GHz still failed with PMF and H2E enabled. The integrated image and its
Off/On lifecycle still need device testing; configuration alone did not resolve
the WPA3 failure.
