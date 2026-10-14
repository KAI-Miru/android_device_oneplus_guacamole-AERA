"""Check the configfs MTP+ADB identity and FunctionFS handoff."""
import shlex


def verify_usb_configuration(script):
    rules = {}
    trigger = None
    for line in script.decode('utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('on '):
            trigger = line[3:]
            rules[trigger] = []
        elif trigger:
            rules[trigger].append(shlex.split(line))
    ready = 'property:sys.usb.config=mtp,adb && property:sys.usb.ffs.ready=1 && property:sys.usb.configfs=1'
    commands = rules.get(ready, [])
    base = '/config/usb_gadget/g1'
    writes = {args[1]: args[2] for args in commands if args[0] == 'write'}
    try:
        identity = (int(writes[base + '/idVendor'], 16), int(writes[base + '/idProduct'], 16))
    except (KeyError, ValueError) as error:
        raise ValueError('MTP+ADB must explicitly select its USB identity') from error
    if identity != (0x18d1, 0x4ee2):
        raise ValueError('MTP+ADB must pair the Google VID with the native Google product ID')
    start = rules.get('property:sys.usb.config=mtp,adb && property:sys.usb.configfs=1', [])
    if ['start', 'adbd'] not in start:
        raise ValueError('MTP+ADB must start adbd before waiting for FunctionFS readiness')
    links = {args[2]: args[1] for args in commands if args[0] == 'symlink'}
    if links.get(base + '/configs/b.1/f1') != base + '/functions/ffs.mtp' or \
       links.get(base + '/configs/b.1/f2') != base + '/functions/ffs.adb':
        raise ValueError('MTP+ADB must preserve both FunctionFS interfaces')
    detach = ['write', base + '/UDC', 'none']
    bind = ['write', base + '/UDC', '${sys.usb.controller}']
    if detach not in commands or bind not in commands or commands.index(detach) >= commands.index(bind):
        raise ValueError('MTP+ADB must detach before rebinding the USB controller')
    if any(args[:3] == ['mount', 'functionfs', 'adb'] for values in rules.values() for args in values):
        raise ValueError('The device extension must leave the ADB FunctionFS mount to native init')
    return {'mtp_adb_vid': '18d1', 'mtp_adb_pid': '4ee2', 'adb_function_preserved': True}
