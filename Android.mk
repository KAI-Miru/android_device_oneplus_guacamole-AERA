# SPDX-License-Identifier: Apache-2.0
LOCAL_PATH := $(call my-dir)
ifeq ($(TARGET_DEVICE),guacamole)
include $(call all-makefiles-under,$(LOCAL_PATH))

# This standalone prebuilt-kernel tree has no kernel makefile to install DTB.
# Preserve the complete extracted CI59 payload, including its original padding.
$(PRODUCT_OUT)/dtb.img: $(TARGET_PREBUILT_DTB)
	$(hide) mkdir -p $(dir $@)
	$(hide) cp -f $< $@

# Generated libraries must be staged after the platform output paths exist.
# PRODUCT_COPY_FILES is evaluated earlier while the product is being parsed.
include $(CLEAR_VARS)
LOCAL_MODULE := guacamole_recovery_graphics
LOCAL_MODULE_TAGS := optional
LOCAL_MODULE_CLASS := ETC
LOCAL_MODULE_PATH := $(TARGET_RECOVERY_ROOT_OUT)
LOCAL_REQUIRED_MODULES := libnativewindow
LOCAL_ADDITIONAL_DEPENDENCIES := $(TARGET_OUT_SHARED_LIBRARIES)/libnativewindow.so
LOCAL_POST_INSTALL_CMD := mkdir -p $(TARGET_RECOVERY_ROOT_OUT)/vendor/lib64 && \
    cp -f $(TARGET_OUT_SHARED_LIBRARIES)/libnativewindow.so $(TARGET_RECOVERY_ROOT_OUT)/vendor/lib64/libnativewindow.so
include $(BUILD_PHONY_PACKAGE)

# Physical vendor remains mounted for graphics. Stage the native supplicant's
# own generated declaration where recovery's service manager can see it,
# retaining its exact interface/version instead of inventing a vendor ABI.
guacamole_wifi_manifest := $(TARGET_RECOVERY_ROOT_OUT)/system/etc/vintf/manifest/guacamole-wifi.xml
$(guacamole_wifi_manifest): $(TARGET_OUT_VENDOR_ETC)/vintf/manifest/android.hardware.wifi.supplicant.xml
	$(hide) mkdir -p $(dir $@)
	$(hide) sed 's/type="device"/type="framework"/' $< > $@
ALL_DEFAULT_INSTALLED_MODULES += $(guacamole_wifi_manifest)
endif
