__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.1.4"
__description__ = "Sonoff multi-channel WiFi relay"

__api__ = 5
__required__ = ['port_get', 'port_set', 'aao_get', 'action']
__mods_required__ = []
__lpi_default__ = 'basic'
__equipment__ = ['ITead multi-port (Tasmota)']
__features__ = ['events']
__config_help__ = [{
    'name': 't',
    'help': 'MQTT full topic',
    'type': 'str',
    'required': True
}, {
    'name': 'c',
    'help': 'Number of channels (default: 2)',
    'type': 'int',
    'required': False
}, {
    'name': 'n',
    'help': 'MQTT notifier to use',
    'type': 'str',
    'required': False
}]
__get_help__ = []
__set_help__ = []
__help__ = """
PHI for ITead Sonoff multi-port devices. Uses one of system MQTT notifiers for
communication. Requires Tasmota firmware (compatible with all multi port
devices, for the single port devices use sonoff_basic)
"""

import json

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import handle_phi_event
from eva.uc.driverapi import log_traceback
from eva.uc.drivers.tools.mqtt import MQTT

from eva.uc.driverapi import phi_constructor


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.topic = self.phi_cfg.get('t')
        self.mqtt = MQTT(self.phi_cfg.get('n'))
        try:
            self.channels = int(self.phi_cfg.get('c'))
        except:
            self.channels = 2
        self.current_status = {}
        if self.topic is None or self.mqtt is None:
            self.ready = False
        else:
            for ch in range(1, self.channels + 1):
                self.current_status[str(ch)] = None

    def get_ports(self):
        return self.generate_port_list(port_max=4)

    def get(self, port=None, cfg=None, timeout=0):
        return self.current_status

    def set(self, port=None, data=None, cfg=None, timeout=0):
        try:
            state = int(data)
            if state > 1 or state < 0: return False
            _port = int(port)
            if _port < 1 or _port > self.channels: return False
        except:
            return False
        self.mqtt.send(self.topic + '/cmnd/POWER%u' % _port, 'ON'
                       if state else 'OFF')
        return True

    def mqtt_handler(self, data, topic=None, qos=None, retain=None):
        try:
            port = int(topic.split('/')[-1][5:])
            if port < 0 or port > self.channels:
                raise Exception
        except:
            return
        self.current_status[str(port)] = 1 if data == 'ON' else 0
        handle_phi_event(self, port, {str(port): 1 if data == 'ON' else 0})

    def mqtt_state_handler(self, data, topic, qos, retain):
        try:
            obtained_status = {}
            state = json.loads(data)
            for ch in range(1, self.channels + 1):
                st = state.get('POWER%u' % ch)
                if st is not None:
                    st = 1 if st == 'ON' else 0
                    self.current_status[str(ch)] = st
                    obtained_status[str(ch)] = st
            handle_phi_event(self, 'all', obtained_status)
        except:
            pass

    def start(self):
        for ch in range(1, self.channels + 1):
            self.mqtt.register(self.topic + '/POWER%u' % ch, self.mqtt_handler)
        self.mqtt.register(self.topic + '/STATE', self.mqtt_state_handler)

    def stop(self):
        for ch in range(1, self.channels + 1):
            self.mqtt.unregister(self.topic + '/POWER%u' % ch,
                                 self.mqtt_handler)
        self.mqtt.unregister(self.topic + '/STATE', self.mqtt_state_handler)

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        if cmd == 'get':
            return self.get()
        return {'get': 'get relay ports status'}
