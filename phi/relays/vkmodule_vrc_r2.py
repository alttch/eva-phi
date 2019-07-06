__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "0.0.1"
__description__ = "VKModule ModBus relay VRC-R2"

__api__ = 5
__equipment__ = 'VKModule VRC-R2'
__required__ = ['aao_get', 'port_set', 'status', 'action']
__mods_required__ = []
__lpi_default__ = 'basic'
__features__ = []
__config_help__ = [{
    'name': 'port',
    'help': 'ModBus port ID',
    'type': 'str',
    'required': True
}, {
    'name': 'addr',
    'help': 'modbus addr',
    'type': 'aint',
    'required': True
}]
__get_help__ = []
__set_help__ = []

__help__ = """
PHI for VKModule ModBus relay VRC-R2. ModBus port should be created in UC
before loading.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

import eva.uc.modbus as modbus

from eva.uc.driverapi import phi_constructor

from eva.tools import safe_int


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.port_max = 2
        self.modbus_port = self.phi_cfg.get('port')
        if not modbus.is_port(self.modbus_port):
            self.log_error('modbus port ID not specified or invalid')
            self.ready = False
            return
        try:
            self.addr = safe_int(self.phi_cfg.get('addr'))
        except:
            self.log_error('modbus addr not specified or invalid')
            self.ready = False
            return

    def get_ports(self):
        return self.generate_port_list(
            port_max=2, description='relay port #{}')

    def get(self, port=None, cfg=None, timeout=0):
        mb = modbus.get_port(self.modbus_port, timeout)
        if not mb: return None
        rr = mb.read_coils(0, 2, unit=self.addr)
        mb.release()
        if rr.isError(): return None
        result = {}
        try:
            for i in range(2):
                result[str(i + 1)] = 1 if rr.bits[i] else 0
        except:
            result = None
        return result

    def set(self, port=None, data=None, cfg=None, timeout=0):
        try:
            p = int(port)
            val = int(data)
        except:
            return False
        if p < 1 or p > self.port_max or val < 0 or val > 1: return False
        mb = modbus.get_port(self.modbus_port, timeout)
        if not mb: return None
        result = mb.write_coil(p - 1, True if val else False, unit=self.addr)
        mb.release()
        return not result.isError()

    def test(self, cmd=None):
        if cmd == 'self':
            mb = modbus.get_port(self.modbus_port)
            if not mb: return 'FAILED'
            mb.release()
            return 'OK'
        if cmd == 'get': return self.get(timeout=get_timeout() * 10)
        return {
            'get': 'get current relay state'
        }
