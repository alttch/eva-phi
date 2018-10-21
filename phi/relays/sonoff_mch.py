__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.1"
__description__ = "Sonoff multi-channel WiFi relay"

__id__ = 'sonoff_mch'
__equipment__ = 'ITead multi-port (Tasmota)'
__api__ = 2
__required__ = ['port_get', 'port_set']
__mods_required__ = []
__lpi_default__ = 'basic'
__features__ = ['port_get', 'port_set', 'events']
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


class PHI(GenericPHI):

    def __init__(self, phi_cfg=None, info_only=False):
        super().__init__(phi_cfg=phi_cfg, info_only=info_only)
        self.phi_mod_id = __id__
        self.__author = __author__
        self.__license = __license__
        self.__description = __description__
        self.__version = __version__
        self.__api_version = __api__
        self.__equipment = __equipment__
        self.__features = __features__
        self.__required = __required__
        self.__mods_required = __mods_required__
        self.__lpi_default = __lpi_default__
        self.__config_help = __config_help__
        self.__get_help = __get_help__
        self.__set_help = __set_help__
        self.__help = __help__
        if info_only: return
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
