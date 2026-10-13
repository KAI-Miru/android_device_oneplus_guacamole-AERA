#!/system/bin/sh
attempt=0
while [ ! -e /sys/class/net/wlan0 ] && [ "$attempt" -lt 55 ]; do
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
    chmod 0600 "$config"
fi
exec /system/bin/wpa_supplicant -Dnl80211 -iwlan0 \
    -O/tmp/recovery/sockets -c"$config"
