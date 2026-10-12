# Copyright (C) 2019 The LineageOS Project
# Copyright (C) 2026 KAI-Miru
# SPDX-License-Identifier: Apache-2.0
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, vendor/twrp/config/common.mk)
$(call inherit-product, device/oneplus/guacamole/device.mk)
PRODUCT_NAME := twrp_guacamole
PRODUCT_DEVICE := guacamole
PRODUCT_BRAND := OnePlus
PRODUCT_MODEL := GM1917
PRODUCT_MANUFACTURER := OnePlus
PRODUCT_RELEASE_NAME := guacamole
AERA_MAINTAINER := KAI-Miru
TARGET_OTA_ASSERT_DEVICE := guacamole,OnePlus7Pro
