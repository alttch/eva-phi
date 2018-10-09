__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "1.0.0"
__description__ = "Sonoff Basic WiFi relay"

__id__ = 'sonoff_basic'
__equipment__ = 'ITead 1-port (Tasmota)'
__api__ = 2
__required__ = ['port_get', 'port_set']
__mods_required__ = []
__lpi_default__ = 'usp'
__features__ = ['port_get', 'port_set']
__config_help__ = [{
    'name': 't',
    'help': 'MQTT full topic',
    'type': 'str',
    'required': True
}, {
    'name': 'n',
    'help': 'MQTT notifier to use',
    'type': 'str',
    'required': False
}]
__get_help__ = []
__set_help__ = []
__help__ = """
PHI for ITead Sonoff Basic. Uses one of system MQTT notifiers for
communication. Requires Tasmota firmware (compatible with all single port
devices)
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
        self.current_status = None
        if self.topic is None or self.mqtt is None:
            self.ready = False

    def get(self, port=None, cfg=None, timeout=0):
        return {'1': self.current_status}

    def set(self, port=None, data=None, cfg=None, timeout=0):
        try:
            state = int(data)
            if state > 1 or state < 0: return False
        except:
            return False
        self.mqtt.send(self.topic + '/cmnd/POWER', 'ON' if state else 'OFF')
        return True

    def mqtt_handler(self, data, topic=None, qos=None, retain=None):
        self.current_status = 1 if data == 'ON' else 0
        handle_phi_event(self, 1, self.get())

    def mqtt_state_handler(self, data, topic, qos, retain):
        try:
            state = json.loads(data)
            self.mqtt_handler(state.get('POWER'))
        except:
            pass

    def start(self):
        self.mqtt.register(self.topic + '/POWER', self.mqtt_handler)
        self.mqtt.register(self.topic + '/STATE', self.mqtt_state_handler)

    def stop(self):
        self.mqtt.unregister(self.topic + '/POWER', self.mqtt_handler)
        self.mqtt.unregister(self.topic + '/STATE', self.mqtt_state_handler)

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        if cmd == 'get':
            return self.get()
        return {'get': 'get relay ports status'}
