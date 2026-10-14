#!/system/bin/sh
set -e
umask 077
exec >/tmp/guacamole-wlan-domains.log 2>&1
setprop sys.guacamole.wlan.domains preparing
trap 'status=$?; if [ "$status" -ne 0 ]; then setprop sys.guacamole.wlan.domains failed; fi' EXIT

# ICNSS requests its domain once during kernel probe. Populate the mapper
# before that request times out, independently of the Wi-Fi UI or CE unlock.
attempt=0
while [ "$attempt" -lt 45 ]; do
    if grep -q ' /vendor ' /proc/mounts && [ -d /vendor/firmware_mnt ] &&
            [ -d /firmware/image ]; then
        break
    fi
    sleep 1
    attempt=$((attempt + 1))
done
# Binding below the ramdisk's vendor directory would be hidden when native
# partition startup mounts the installed vendor. Wait for that parent first.
grep -q ' /vendor ' /proc/mounts || exit 1
[ -d /vendor/firmware_mnt ] && [ -d /firmware/image ] || exit 1
if [ ! -d /vendor/firmware_mnt/image ]; then
    mount -o bind /firmware /vendor/firmware_mnt
fi
[ -r /vendor/firmware_mnt/image/modemuw.jsn ] || {
    echo 'Guacamole WLAN: missing the installed WLAN firmware-domain descriptor' >&2
    exit 1
}

start_service() {
    setprop ctl.start "$1"
    service_attempt=0
    while [ "$service_attempt" -lt 100 ]; do
        [ "$(getprop "init.svc.$1")" != running ] || return 0
        sleep 0.1
        service_attempt=$((service_attempt + 1))
    done
    echo "Guacamole WLAN: domain service did not start: $1" >&2
    return 1
}
start_service guacamole-qrtr-ns
start_service guacamole-pd-mapper
setprop sys.guacamole.wlan.domains ready
