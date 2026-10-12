# SPDX-License-Identifier: Apache-2.0
if [ "${AERA_BUILD_DEVICE:-}" = guacamole ]; then
    export AERA_AB_DEVICE=1
    export AERA_VANILLA_BUILD=1
    export AERA_VANILLA_BUILD=1
    export AERA_BUILD_STATUS=Unofficial
    export AERA_BUILD_TYPE=Alpha
    export AERA_MAINTAINER=KAI-Miru
    export AERA_TARGET_DEVICES=guacamole,OnePlus7Pro
    export AERA_ENABLE_ROOT_MANAGER=0
    export AERA_DISABLE_UPDATEZIP=1
fi
