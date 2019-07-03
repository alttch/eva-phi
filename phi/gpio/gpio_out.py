__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "GPIO out"

__api__ = 5
__required__ = ['port_get', 'port_set', 'status', 'action']
__mods_required__ = 'gpiozero'
__lpi_default__ = 'basic'
__equipment__ = 'GPIO'
__features__ = ['aao_get', 'aao_set']
__config_help__ = [{
    'name': 'port',
    'help': 'gpio port(s) to control',
    'type': 'list:int',
    'required': False
}]

__get_help__ = []
__set_help__ = []
__help__ = """
GPIO ports control. A list of ports must be specified in PHI loading
configuration.
"""

__shared_namespaces__ = ['gpiozero']

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback

import os
import importlib

from eva.uc.driverapi import phi_constructor


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.ports = self.phi_cfg.get('port')
        self.devices = {}
        try:
            gpiozero = importlib.import_module('gpiozero')
        except:
            self.log_error('gpiozero python module not found')
            self.ready = False
            return
        if self.ports:
            if not isinstance(self.ports, list):
                self.ports = [self.ports]
            for p in self.ports:
                try:
                    if hasattr(self, 'get_shared_namespace'):
                        gpios = self.get_shared_namespace('gpiozero')
                        if not hasattr(gpios, 'pins'):
                            gpios.pins = {}
                    else:
                        gpios = None
                        self.log_warning(
                            'Driver API below v7, PHI set/reload is unavailable'
                        )
                    p = int(p)
                    if gpios and p in gpios.pins:
                        d = gpios.pins[p]
                    else:
                        d = gpiozero.DigitalOutputDevice(p)
                        if gpios:
                            gpios.pins[p] = d
                    self.devices[str(p)] = d
                except Exception as e:
                    log_traceback()
                    self.log_error('can not append gpio port {}: {}'.format(
                        p, e))
                    self.ready = False

    def get(self, port=None, cfg=None, timeout=0):
        if port:
            try:
                return self.devices[str(port)].value
            except:
                return None
        else:
            result = {}
            for p, v in self.devices.items():
                result[p] = v.value
            return result

    def set(self, port=None, data=None, cfg=None, timeout=0):
        if isinstance(port, list):
            _port = port
            _data = data
        else:
            _port = [port]
            _data = [data]
        for p, dt in zip(port, data):
            try:
                d = self.devices[str(p)]
                if dt:
                    d.on()
                else:
                    d.off()
            except:
                self.log_error('port {} not initialized in PHI'.format(p))
                return False
        return True

    def unload(self):
        for p, d in self.devices.items():
            try:
                d.close()
            except:
                log_traceback()
        self.devices = []

    def test(self, cmd=None):
        if cmd == 'self':
            try:
                if not os.path.isdir('/sys/bus/gpio'):
                    raise Exception('gpio bus not found')
                else:
                    return 'OK'
            except:
                log_traceback()
                return 'FAILED'
        return {'-': 'only self test command available'}
