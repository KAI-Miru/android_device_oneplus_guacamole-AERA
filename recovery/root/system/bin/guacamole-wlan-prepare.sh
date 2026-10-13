#!/system/bin/sh
set -e
expected_kernel=4.14.357-openela-ColorOS15-ci59+
module=/system/lib/modules/msmnile/qca_cld3_wlan.ko
[ "$(uname -r)" = "$expected_kernel" ] || {
    echo 'Guacamole WLAN: refusing a module for a different kernel' >&2
    exit 1
}
[ -r "$module" ] || exit 1

# Native crypto mounts vendor and initializes DE storage. Wait outside init's
# main thread; credential-encrypted user storage is not needed for WLAN.
attempt=0
while [ "$attempt" -lt 45 ]; do
    if [ -d /data/vendor/wifi ] && [ -d /vendor/firmware_mnt ] &&
            [ -d /firmware/image ]; then
        break
    fi
    sleep 1
    attempt=$((attempt + 1))
done
[ -d /data/vendor/wifi ] && [ -d /vendor/firmware_mnt ] && [ -d /firmware/image ] || exit 1

# Mounting physical vendor hides the early ramdisk symlink. Reuse the already
# read-only firmware mount rather than copying firmware or calibration data.
if [ ! -d /vendor/firmware_mnt/image ]; then
    mount -o bind /firmware /vendor/firmware_mnt
fi

socket_dir=/data/vendor/wifi/sockets
runtime_dir=/tmp/guacamole-cnss-sockets
if [ ! -d "$socket_dir" ]; then
    mkdir "$socket_dir"
    chmod 0770 "$socket_dir"
    chown system:wifi "$socket_dir"
fi
mkdir -p "$runtime_dir"
chmod 0770 "$runtime_dir"
chown system:wifi "$runtime_dir"
if ! grep -q " $socket_dir " /proc/mounts; then
    mount -o bind "$runtime_dir" "$socket_dir"
fi

if ! grep -q '^wlan ' /proc/modules; then
    # Normal insmod preserves the kernel's module-version/CRC enforcement.
    insmod "$module"
fi
setprop ctl.start guacamole-cnss-daemon
