__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "Xiaomi Yeelight LEDs"

__equipment__ = 'Yeelight bulb'
__api__ = 5
__required__ = ['port_get', 'port_set', 'value', 'status', 'action']
__mods_required__ = []
__lpi_default__ = 'usp'
__features__ = []
__config_help__ = [{
    'name': 'host',
    'help': 'bulb host/ip[:port]',
    'type': 'str',
    'required': True
}, {
    'name': 'smooth',
    'help': 'smooth time (ms)',
    'type': 'int',
    'required': False
}]
__get_help__ = []
__set_help__ = []
__help__ = """
Xiaomi Yeelight LED control. Bulb LAN control must be turned on
(https://www.yeelight.com/en_US/developer)

Unit value = RGB hex.
"""
__discover__ = 'net'
__discover_help__ = 'Set timeout at least to 3 seconds'

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import phi_constructor
from eva.uc.driverapi import get_timeout

import json
import socket
from time import time


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.host = self.phi_cfg.get('host')
        self.smooth = self.phi_cfg.get('smooth')
        if not self.host:
            self.ready = False
            self.log_error('host is not specified')

    @staticmethod
    def discover(interface=None, timeout=0):
        import eva.uc.drivers.tools.ssdp as ssdp
        result = ssdp.discover(
            'wifi_bulb',
            port=1982,
            interface=interface,
            timeout=timeout,
            discard_headers=[
                'Color_mode', 'Ct', 'Power', 'Hue', 'Server', 'Location',
                'Date', 'Rgb', 'Support', 'Sat', 'IP', 'Bright',
                'Cache-control', 'Ext'
            ])
        if result:
            for r in result:
                r['!load'] = {'host': r['IP']}
        return result

    def get(self, port=None, cfg=None, timeout=0):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            time_start = time()
            s.connect((self.host, 55443))
            if time_start + timeout < time():
                raise Exception('operation timeout')
            s.send('{ "id": 1, "method": "get_prop", "params": ["power"] }\r\n'.
                   encode())
            data = s.recv(1024).decode()
            status = 1 if json.loads(data)['result'][0] == 'on' else 0
            if time_start + timeout < time():
                raise Exception('operation timeout')
            s.send('{ "id": 2, "method": "get_prop", "params": ["rgb"] }\r\n'.
                   encode())
            data = s.recv(1024).decode()
            value = hex(int(json.loads(data)['result'][0]))[2:]
            return status, value
        except:
            log_traceback()
            return None
        finally:
            try:
                s.close()
            except:
                pass

    def set(self, port=None, data=None, cfg=None, timeout=0):
        time_start = time()
        status, value = data
        if value:
            try:
                s_in = value[1:] if value.startswith('#') else value
                red = int(s_in[:2], 16)
                green = int(s_in[2:4], 16)
                blue = int(s_in[4:], 16)
                value = red * 65536 + green * 256 + blue
            except:
                self.log_error('Invalid value: {}'.format(value))
                return False
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            time_start = time()
            s.connect((self.host, 55443))
            if time_start + timeout < time():
                raise Exception('operation timeout')
            if value:
                c = {'id': 1, 'method': 'set_rgb', 'params': [value]}
                if self.smooth:
                    c['params'] += ['smooth', self.smooth]
                s.send((json.dumps(c) + '\r\n').encode())
                data = s.recv(1024).decode()
                if json.loads(data)['result'][0] != 'ok':
                    raise Exception('Unable to set value')
            if time_start + timeout < time():
                raise Exception('operation timeout')
            c = {
                'id': 2,
                'method': 'set_power',
                'params': ['on' if status else 'off']
            }
            if self.smooth:
                c['params'] += ['smooth', self.smooth]
            s.send((json.dumps(c) + '\r\n').encode())
            data = s.recv(1024).decode()
            if json.loads(data)['result'][0] != 'ok':
                raise Exception('Unable to set status')
            return True
        except:
            log_traceback()
            return False
        finally:
            try:
                s.close()
            except:
                pass

    def test(self, cmd=None):
        if cmd in ['self', 'get']:
            result = self.get(timeout=get_timeout())
            if result is not None:
                return 'OK' if cmd == 'self' else {
                    'status': result[0],
                    'value': result[1]
                }
            else:
                return 'FAILED' if cmd == 'self' else None
        else:
            return {'get': 'get bulb status and color'}
