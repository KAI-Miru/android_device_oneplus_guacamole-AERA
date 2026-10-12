# Copyright (C) 2018-2019 The LineageOS Project
# Copyright (C) 2026 KAI-Miru
# SPDX-License-Identifier: Apache-2.0
$(call inherit-product, $(SRC_TARGET_DIR)/product/base.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/emulated_storage.mk)
LOCAL_PATH := device/oneplus/guacamole
PRODUCT_PLATFORM := msmnile
PRODUCT_SHIPPING_API_LEVEL := 28
AB_OTA_UPDATER := true
AB_OTA_PARTITIONS := boot dtbo odm system vendor vbmeta
PRODUCT_USE_DYNAMIC_PARTITIONS := false
PRODUCT_VIRTUAL_AB_OTA := false
PRODUCT_BUILD_SUPER_PARTITION := false
PRODUCT_BUILD_RECOVERY_IMAGE := true
PRODUCT_SOONG_NAMESPACES += $(LOCAL_PATH)

PRODUCT_PACKAGES += \
    android.hardware.boot@1.0-impl:64 \
    android.hardware.boot@1.0-service \
    bootctrl.msmnile \
    bootctrl.msmnile.recovery \
    qcom_decrypt \
    qcom_decrypt_fbe \
    fastbootd \
    update_engine \
    update_engine_sideload \
    update_verifier \
    resetprop \
    libion \
    libnativewindow \
    libui

TARGET_RECOVERY_DEVICE_MODULES += libion libnativewindow libui
RECOVERY_LIBRARY_SOURCE_FILES += \
    $(TARGET_OUT_SHARED_LIBRARIES)/libion.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libnativewindow.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libui.so

PRODUCT_VENDOR_PROPERTIES += ro.hardware.egl=adreno ro.hardware.gralloc=msmnile
DEVICE_MANIFEST_FILE := $(LOCAL_PATH)/manifest.xml

# All copied init files are device-specific extensions to AERA's native init.
PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/recovery/root/init.recovery.qcom.rc:$(TARGET_COPY_OUT_RECOVERY)/root/init.recovery.qcom.rc \
    $(LOCAL_PATH)/recovery/root/init.recovery.usb.rc:$(TARGET_COPY_OUT_RECOVERY)/root/init.recovery.usb.rc \
    $(LOCAL_PATH)/recovery/root/ueventd.qcom.rc:$(TARGET_COPY_OUT_RECOVERY)/root/ueventd.qcom.rc \
    $(LOCAL_PATH)/recovery/root/system/etc/twrp.flags:$(TARGET_COPY_OUT_RECOVERY)/root/system/etc/twrp.flags \
    $(LOCAL_PATH)/recovery/root/vendor/etc/init/aera-gralloc.rc:$(TARGET_COPY_OUT_RECOVERY)/root/vendor/etc/init/aera-gralloc.rc \
    $(LOCAL_PATH)/manifest.xml:$(TARGET_COPY_OUT_RECOVERY)/root/vendor/etc/vintf/manifest.xml \
    $(TARGET_OUT_SHARED_LIBRARIES)/libnativewindow.so:$(TARGET_COPY_OUT_RECOVERY)/root/vendor/lib64/libnativewindow.so

include $(LOCAL_PATH)/proprietary-files.mk
