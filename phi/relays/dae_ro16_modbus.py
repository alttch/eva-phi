__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.1.2"
__description__ = "Denkovi ModBus relay DAE-RO16"

__api__ = 5
__equipment__ = 'DAE-RO16-MODBUS'
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
    'name': 'unit',
    'help': 'modbus unit ID',
    'type': 'int',
    'required': True
}]
__get_help__ = []
__set_help__ = []

__help__ = """
PHI for Denkovi DAE-RO16-MODBUS relay. ModBus port should be created in UC
before loading. Uses coils for the relay state control/monitoring.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

import eva.uc.modbus as modbus

from eva.uc.driverapi import phi_constructor


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.port_max = 16
        self.modbus_port = self.phi_cfg.get('port')
        if not modbus.is_port(self.modbus_port):
            self.log_error('modbus port ID not specified or invalid')
            self.ready = False
            return
        try:
            self.unit_id = int(self.phi_cfg.get('unit'))
        except:
            self.log_error('modbus unit ID not specified or invalid')
            self.ready = False
            return

    def exec(self, cmd=None, args=None):
        if cmd == 'id':
            try:
                new_id = int(args)
                if new_id < 1 or new_id > 247:
                    raise Exception('id not in range 1..247')
                mb = modbus.get_port(self.modbus_port)
                if not mb:
                    raise Exception('unable to get modbus port {}'.format(
                        self.modbus_port))
                try:
                    result = mb.write_register(18, new_id, unit=self.unit_id)
                except:
                    log_traceback()
                    result = None
                mb.release()
                if not result or result.isError(): return 'FAILED'
                self.unit_id = new_id
                self.phi_cfg['unit'] = new_id
                return 'OK'
            except:
                log_traceback()
                return 'FAILED'
        else:
            return {
                'id': 'change relay slave ID (1..247), relay reboot required'
            }

    def get_ports(self):
        return self.generate_port_list(port_max=16, description='relay port #{}')

    def get(self, port=None, cfg=None, timeout=0):
        mb = modbus.get_port(self.modbus_port, timeout)
        if not mb: return None
        rr = mb.read_coils(0, 16, unit=self.unit_id)
        mb.release()
        if rr.isError(): return None
        result = {}
        try:
            for i in range(16):
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
        result = mb.write_coil(p - 1, True if val else False, unit=self.unit_id)
        mb.release()
        return not result.isError()

    def test(self, cmd=None):
        if cmd == 'self':
            mb = modbus.get_port(self.modbus_port)
            if not mb: return 'FAILED'
            mb.release()
            return 'OK'
        if cmd == 'info':
            mb = modbus.get_port(self.modbus_port)
            if not mb: return 'FAILED'
            if mb.client_type in ['tcp', 'udp']:
                reg = 22
            else:
                reg = 21
            rr = mb.read_holding_registers(reg, 1, unit=self.unit_id)
            mb.release()
            if rr.isError(): return 'FAILED'
            try:
                return '{:.2f}'.format(float(rr.registers[0]) / 100.0)
            except:
                log_traceback()
                return 'FAILED'
        if cmd == 'get': return self.get(timeout=get_timeout() * 10)
        return {
            'info': 'returns relay firmware version',
            'get': 'get current relay state'
        }
