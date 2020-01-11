__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "LoRaWAN RAK7204 sensor"

__equipment__ = 'RAK7204'
__api__ = 8
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'sensor'
__features__ = ['aao_get', 'push']
__config_help__ = []
__get_help__ = []
__set_help__ = []
__help__ = """
PHI LoraWAN RAK7204 sensor. Requires network server
(https://github.com/gotthardp/lorawan-server) between LoRa gateway and UC.

PHI should be loaded with id=DevEUI.

Data from the network server should be pushed to PHI via RESTful API:

http(s)://uc-ip:port/r/phi/{deveui}/state

You may use any prefix or devaddr instead as well.

Ports available: bat, hum, pres, temp, gas
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import handle_phi_event
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import critical
from eva.uc.driverapi import phi_constructor


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.data = {
            'bat': None,
            'hum': None,
            'pres': None,
            'temp': None,
            'gas': None
        }

    def get_ports(self):
        return [
            {
                'port': 'bat',
                'name': 'Battery',
                'description': 'Battery voltage'
            },
            {
                'port': 'hum',
                'name': 'Humidity',
                'description': 'Air humidity (0.5%) precision'
            },
            {
                'port': 'pres',
                'name': 'Pressure',
                'description': 'Air pressure'
            },
            {
                'port': 'temp',
                'name': 'Temperature',
                'description': 'Air temperature'
            },
            {
                'port': 'gas',
                'name': 'Gas',
                'description': 'Gas Resistance data'
            },
        ]

    def get(self, port=None, cfg=None, timeout=0):
        if not port: return self.data
        try:
            return self.data[port]
        except:
            return None

    def push_state(self, payload):
        try:
            data = payload['data']
            self.data['bat'] = int(data[4:8], 16) / 100
            self.data['hum'] = int(data[12:14], 16) * 0.5
            self.data['pres'] = int(data[18:22], 16) / 10
            self.data['temp'] = int(data[26:30], 16) / 10
            self.data['gas'] = int(data[34:38], 16) / 100
            handle_phi_event(self, data=self.data)
            return True
        except:
            log_traceback()
            return False

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        if cmd == 'get':
            return self.data
        return {'get': 'get port values'}
