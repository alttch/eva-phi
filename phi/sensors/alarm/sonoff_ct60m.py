__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2020 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "Sonoff CT60M"

__api__ = 4
__required__ = ['port_get']
__mods_required__ = []
__lpi_default__ = 'ssp'
__equipment__ = ['ITead CT60M (Tasmota)']
__features__ = ['events']
__config_help__ = [{
    'name': 't',
    'help': 'MQTT full topic',
    'type': 'str',
    'required': True
}, {
    'name': 'i',
    'help': 'Sensor ID (Data field)',
    'type': 'str',
    'required': True
}, {
    'name': 'n',
    'help': 'MQTT notifier to use',
    'type': 'str',
    'required': False
}, {
    'name': 'e',
    'help': 'Motion expire (default: 5 sec)',
    'type': 'int',
    'required': False
}]
__get_help__ = []
__set_help__ = []
__help__ = """
PHI for ITead Sonoff CT60M. Uses one of system MQTT notifiers for
communication. Requires Tasmota firmware
"""

sleep_delay = 0.1

import json
import threading
import time

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
        self.expires = int(self.phi_cfg.get('e', 5))
        self.sensor_id = self.phi_cfg.get('i')
        self.current_state = 0
        self.state_set_time = 0
        self.state_lock = threading.RLock()
        if self.topic is None or self.mqtt is None:
            self.ready = False
        self.expiration_checker = None
        self.is_active = False

    def get(self, port=None, cfg=None, timeout=0):
        return {'1': self.current_state}

    def mqtt_state_handler(self, data, topic, qos, retain):
        try:
            state = json.loads(data)
            if state.get('RfReceived', {}).get('Data') == self.sensor_id:
                with self.state_lock:
                    self.current_state = 1
                    self.state_set_time = time.time()
                    handle_phi_event(self, 1, self.get())
        except:
            log_traceback()

    def _t_exp(self):
        while self.is_active:
            time.sleep(sleep_delay)
            if self.current_state and \
                    self.state_set_time + self.expires < time.time():
                with self.state_lock:
                    self.current_state = 0
                    handle_phi_event(self, 1, self.get())

    def start(self):
        self.mqtt.register(self.topic + '/RESULT', self.mqtt_state_handler)
        self.is_active = True
        self.expiration_checker = threading.Thread(target=self._t_exp,
                                                   daemon=True)
        self.expiration_checker.start()

    def stop(self):
        self.mqtt.unregister(self.topic + '/RESULT', self.mqtt_state_handler)
        self.is_active = False
        if self.expiration_checker:
            self.expiration_checker.join()

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        if cmd == 'get':
            return self.get()
        return {'get': 'get port status'}
