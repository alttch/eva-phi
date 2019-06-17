__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.3"
__description__ = "Philips HUE LEDs"

__equipment__ = 'Philips HUE LEDs'
__api__ = 5
__required__ = ['port_get', 'port_set', 'value', 'status', 'action']
__mods_required__ = []
__lpi_default__ = 'basic'
__features__ = []
__config_help__ = [{
    'name': 'host',
    'help': 'hue bridge host/ip[:port]',
    'type': 'str',
    'required': True
}, {
    'name': 'user',
    'help': 'User',
    'type': 'str',
    'required': False
}]
__get_help__ = []
__set_help__ = []
__help__ = """
Philips HUE LEDs control.

If user is not specified, the link button on the hue bridge must be pressed and
PHI loaded within 30 seconds.

'get' method doesn't return LED values, so only unit status can be updated.

To set LED color/brigthness, set action 'value' to RGB hex.

To let the bridge search new LEDs, execute 'exec scan' command. To obtain list
of new lights, execute 'test new'.

To delete light, execute 'exec delete <light_id>'
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import phi_constructor
from eva.uc.driverapi import get_timeout
from eva.uc.driverapi import get_system_name

import requests


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.host = self.phi_cfg.get('host')
        if not self.host:
            self.ready = False
            self.log_error('host is not specified')
            return
        self.api_uri = 'http://{}/api'.format(self.host)
        self.user = self.phi_cfg.get('user')
        if not self.user:
            try:
                result = requests.post(
                    self.api_uri,
                    json={
                        'devicetype':
                        'eva_philips_hue_leds#{}'.format(get_system_name())
                    },
                    timeout=get_timeout()).json()
                self.user = result[0]['success']['username']
                self.phi_cfg['user'] = self.user
            except:
                self.log_error('unable to create user')
                log_traceback()
                self.ready = False
        self.api_uri += '/{}'.format(self.user)

    @staticmethod
    def discover(interface=None, timeout=0):
        import eva.uc.drivers.tools.ssdp as ssdp
        result = []
        data = ssdp.discover(
            'upnp:rootdevice',
            interface=interface,
            timeout=timeout,
            discard_headers=[
                'Cache-control', 'Ext', 'Location', 'Host', 'Usn', 'St',
                'Server'
            ])
        if data:
            for i, d in data:
                if 'Hue-bridgeid' in d:
                    r = {
                        '!load': {
                            'host': d['IP']
                        },
                        'IP': d['IP'],
                        'ID': d['Hue-bridgeid']
                    }
            result = [{
                '!opt': 'cols',
                'value': ['IP', 'ID']
            }] + result
        return result

    def get(self, port=None, cfg=None, timeout=0):
        try:
            result = requests.get(
                '{}/lights/{}'.format(self.api_uri, port),
                timeout=timeout).json()
            if 'state' in result:
                return 1 if result['state'].get('on') else 0
        except:
            self.log_error('unable to get state, port {}'.format(port))
            log_traceback()
            return None

    def set(self, port=None, data=None, cfg=None, timeout=0):
        status, value = data
        params = {
            'on': True if status else False,
        }
        try:
            if value:
                x, y, b = self.rgb_to_xy_b(value)
                params.update({'xy': [x, y], 'bri': b, 'effect': 'none'})
            result = requests.put(
                '{}/lights/{}/state'.format(self.api_uri, port),
                json=params,
                timeout=timeout)
            return True
        except:
            self.log_error('unable to set state, port {}'.format(port))
            log_traceback()
            return False

    def test(self, cmd=None):
        if cmd in ['self', 'get', 'new']:
            c = 'lights'
            if cmd == 'new':
                c = 'lights/new'
            try:
                result = requests.get(
                    '{}/{}'.format(self.api_uri, c),
                    timeout=get_timeout()).json()
                if isinstance(result, list):
                    raise Exception
                return 'OK' if cmd == 'self' else result
            except:
                log_traceback()
                return 'FAILED' if cmd == 'self' else None
        else:
            return {'get': 'get state of all lights', 'new': 'get new lights'}

    def exec(self, cmd=None, args=None):
        try:
            if cmd == 'scan':
                result = requests.post(
                    '{}/lights'.format(self.api_uri),
                    timeout=get_timeout()).json()
                return result
            elif cmd == 'delete':
                result = requests.delete(
                    '{}/lights/{}'.format(self.api_uri, int(args)),
                    timeout=get_timeout()).json()
                return result
            else:
                return {
                    'scan': 'scan for a new lights',
                    'delete': 'delete light'
                }
        except:
            log_traceback()
            return None

    def unload(self):
        try:
            result = requests.delete(
                '{}/config/whitelist/{}'.format(self.api_uri, self.user),
                timeout=get_timeout()).json()
            if 'success' not in result[0]:
                raise Exception
        except:
            self.log_warning('unable to delete user from the bridge')
            log_traceback()

    @staticmethod
    def rgb_to_xy_b(rgb, correct_gamma=True):
        try:
            if isinstance(rgb, str):
                s_in = rgb
                if s_in.startswith('#'):
                    s_in = s_in[1:]
                red = int(s_in[:2], 16)
                green = int(s_in[2:4], 16)
                blue = int(s_in[4:], 16)
            else:
                red, green, blue = rgb
        except:
            return None, None, None
        red = red / 255
        green = green / 255
        blue = blue / 255
        if correct_gamma:
            red = pow((red + 0.055) / (1.0 + 0.055),
                      2.4) if red > 0.04045 else (red / 12.92)
            green = pow((green + 0.055) / (1.0 + 0.055),
                        2.4) if green > 0.04045 else (green / 12.92)
            blue = pow((blue + 0.055) / (1.0 + 0.055),
                       2.4) if blue > 0.04045 else (blue / 12.92)
        X = red * 0.4124564 + green * 0.3575761 + blue * 0.1804375
        Y = red * 0.2126729 + green * 0.7151522 + blue * 0.0721750
        Z = red * 0.0193339 + green * 0.1191920 + blue * 0.9503041
        try:
            x = X / (X + Y + Z)
            y = Y / (X + Y + Z)
            brigthness = round(254.0 * max(red, green, blue))
            # brigthness = round(Y * 254.0)
            if brigthness > 254:
                brigthness = 254
        except ZeroDivisionError:
            x, y, brigthness = 0.3, 0.3, 1
        return x, y, brigthness
