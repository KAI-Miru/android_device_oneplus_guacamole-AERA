#!/system/bin/sh
umask 077
exec >/tmp/guacamole-wpa-supplicant.log 2>&1
attempt=0
while [ ! -e /sys/class/net/wlan0 ] && [ "$attempt" -lt 55 ]; do
    [ "$(getprop sys.guacamole.wlan.prepare)" != failed ] || {
        echo 'Guacamole WLAN: device preparation failed' >&2
        exit 1
    }
    sleep 1
    attempt=$((attempt + 1))
done
[ -e /sys/class/net/wlan0 ] || {
    echo 'Guacamole WLAN: firmware did not create wlan0' >&2
    exit 1
}
config=/tmp/guacamole-wpa_supplicant.conf
if [ ! -f "$config" ]; then
    cp /system/etc/guacamole-wpa_supplicant.conf "$config" || exit 1
fi
# Android's native supplicant drops to the wifi UID before reading its config.
# Keep credentials private while allowing that UID to read and update the RAM file.
chown wifi:wifi "$config" || exit 1
chmod 0600 "$config" || exit 1
exec /system/bin/wpa_supplicant -Dnl80211 -iwlan0 \
    -O/tmp/recovery/sockets -c"$config"
