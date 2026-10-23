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

Boot-control 1.1 needs the stock HIDL passthrough wrapper as well as the service
executable. The ramdisk includes `android.hardware.boot@1.0-impl-1.1-qti.so`,
`libboot_control_qti.so` and `librecovery_updater.so` from the recorded C15 dump.
Without that dlopened provider, slot switching and the metadata-mount checkpoint
query can wait indefinitely for the service. These three providers passed a live
RAM repair; the image verifier now requires them explicitly.

Before formatting encrypted Data, `miru` unmounts it and synchronously removes
the `userdata` device-mapper mapping through native libdm. A failed removal
stops formatting before recovery clears its encryption state. It never force-
removes or defers the mapping. Removing the leftover mapping resolved the
observed F2FS formatter error, "In use by the system!".

## Graphics and input

The ramdisk includes the platform task profiles and VINTF declarations needed
by logd, hwservicemanager and the graphics allocator. `runatboot.sh` and
`postscreenunblank.sh` send the OEM display notification after the renderer is
ready, which also restores touch.

The ramdisk includes a matching H.40 Adreno 640 EGL/GLES, gralloc and shader
compiler dependency set. Per-file sources and hashes are recorded in the
proprietary manifest. The H.40 shader compiler is self-contained; it does not
load the separate `libllvm-qgl.so` or OpenCL compiler used by newer stacks.
AERA supplies the native `libui` and `libnativewindow` providers. Kernel-facing
GPU firmware remains the set supplied with the tested firmware environment.
The renderer checks the bundled compiler declared in
`ro.aera.gpu.required_libraries` before entering EGL. Missing inputs retain the
software-renderer fallback. No UI startup hook pins installed vendor.

The build uses ARM64 only. It compresses the complete ramdisk with legacy LZMA
and a 32 MiB dictionary. The image audit checks the dictionary, actual loader
clearance and every GPU provider against the manifest; a size estimate alone
does not make an image suitable for flashing.

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
PD mapper waits for native partition discovery to release installed vendor,
then uses the ramdisk's `/vendor/firmware_mnt` symlink to read-only `/firmware`.
It creates no child bind that would keep installed vendor busy. Its initial
domain list must be populated before ICNSS's five-minute registration timeout.
This stage leaves the modem/ADSP power references and WLAN module to the Wi-Fi
enable path.
Stock `rmt_storage` and `tftp_server` start before the radio. The modem needs
these backends to complete firmware startup. Remote storage serves the installed
modem NV partitions. TFTP's writable RFS directories use RAM mirrors of the
persist files; the mirrors remain available across Wi-Fi toggles. Persist may
remain read-only or be remounted writable by recovery for Qualcomm SFS when
RPMB reports that its key is not provisioned. TFTP still writes to RAM mirrors.
QRTR, PD mapper and the stock backends stay registered while Wi-Fi is off.
The modem/ADSP power references and CNSS process stop with the supplicant.

The native supplicant reads its private RAM configuration as the `wifi` user.
The configuration enables PMF negotiation and both SAE methods, including H2E.
Startup diagnostics stay in `/tmp` on the phone.

Temporary-service device tests confirmed scanning and WPA2 on 2.4 GHz. WPA3
on 5 GHz still failed with PMF and H2E enabled. The integrated image and its
Off/On lifecycle still need device testing; configuration alone did not resolve
the WPA3 failure.


The bundled Health 2.1 service is explicitly imported and started on boot.
Its executable, provider and VINTF declaration alone do not start the service.
Image verification requires its reachable startup and ARM64 runtime inputs.

AW8697 base and 170 Hz short-pulse waveforms come from the same supplied
`7Pro_H40` reference. `tools/haptic-source.json` records their exact identities;
imports and image checks reject missing or changed firmware. No calibration
or persist files are included.

The ramdisk includes a minimal `WCNSS_qcom_cfg.ini` enabling the existing
recovery-only deterministic MAC firmware. All other driver options keep their
defaults. The MAC helper updates only RAM-backed configuration and firmware;
it does not change the factory MAC or require installed vendor to stay mounted.

The recovery pin includes a scoped metadata-mount checkpoint query. An
unmarked boot slot alone must not put recovery userdata writes into rollback
mode: recovery has no Android boot-success commit sequence. When mounted
metadata has no pending checkpoint record, the mount keeps normal durable
writes. Active or unverifiable Android transactions retain Vold's original
decision. The device and installed-ROM `checkpoint=fs` entries are retained;
the fix does not mark a slot successful, commit an OTA or edit its records.
Source validation checks the reviewed Vold and fs_mgr identities. Host tests
cover the policy and linkage; a rebuilt image still needs a retention test.
