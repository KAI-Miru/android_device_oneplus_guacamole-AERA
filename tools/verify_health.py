"""Verify the reachable bundled Health HAL, including its runtime inputs."""
import io
import shlex
import stat
import xml.etree.ElementTree as ET
from elftools.elf.elffile import ELFFile
HEALTH_INIT = 'system/etc/init/android.hardware.health@2.1-service.rc'
HEALTH_BINARY = 'system/bin/android.hardware.health@2.1-service'
HEALTH_PROVIDER = 'system/lib64/hw/android.hardware.health@2.0-impl-2.1.so'
HEALTH_MANIFEST = 'vendor/etc/vintf/manifest/android.hardware.health@2.1.xml'


def verify_health_startup(text):
    """Require an explicit import and boot start, not just installed HAL files."""
    imports = []
    boot_commands = []
    action = None
    for raw in text.splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        words = shlex.split(line)
        if not raw[0].isspace():
            action = words[1:] if words[0] == 'on' else None
            if words[0] == 'import':
                imports.append(words[1:])
        elif action == ['boot']:
            boot_commands.append(words)
    if ['/' + HEALTH_INIT] not in imports:
        raise ValueError('Health HAL service init import is missing')
    if ['start', 'health-hal-2-1'] not in boot_commands:
        raise ValueError('Health HAL must start on boot before recovery requests battery data')
    return {'service': 'health-hal-2-1', 'startup_event': 'boot'}


def verify_health_runtime(entries):
    qcom = 'init.recovery.qcom.rc'
    for name in (qcom, HEALTH_INIT, HEALTH_BINARY, HEALTH_PROVIDER, HEALTH_MANIFEST):
        if name not in entries or not stat.S_ISREG(entries[name][0]):
            raise ValueError(f'Missing regular Health HAL input: {name}')
    result = verify_health_startup(entries[qcom][1].decode())
    native_init = entries.get('system/etc/init/hw/init.rc', (0, b''))[1]
    if b'import /init.recovery.${ro.hardware}.rc' not in native_init.splitlines():
        raise ValueError('Native init must import the Qualcomm startup script')
    service = entries[HEALTH_INIT][1].decode()
    declarations = [shlex.split(line) for line in service.splitlines()
                    if line and not line[0].isspace() and not line.startswith('#')]
    if ['service', 'health-hal-2-1', '/' + HEALTH_BINARY] not in declarations:
        raise ValueError('Health HAL service name or executable does not match startup')
    for name in (HEALTH_BINARY, HEALTH_PROVIDER):
        mode, data = entries[name]
        if name == HEALTH_BINARY and not mode & 0o111:
            raise ValueError('Health HAL service must be executable')
        elf = ELFFile(io.BytesIO(data))
        if elf.elfclass != 64 or elf.header['e_machine'] != 'EM_AARCH64':
            raise ValueError(f'Health HAL input must be ARM64: {name}')
    manifest = ET.fromstring(entries[HEALTH_MANIFEST][1])
    if manifest.get('type') != 'device' or not any(
            hal.findtext('name') == 'android.hardware.health' and
            hal.findtext('transport') == 'hwbinder' and
            '@2.1::IHealth/default' in [node.text for node in hal.findall('fqname')]
            for hal in manifest.findall('hal')):
        raise ValueError('Health HAL 2.1 default hwbinder declaration is missing')
    return dict(result, executable=HEALTH_BINARY, provider=HEALTH_PROVIDER,
                manifest=HEALTH_MANIFEST)
