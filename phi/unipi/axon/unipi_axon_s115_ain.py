__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "UniPi Axon S115 AIN"

__api__ = 4
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'ssp'
__equipment__ = ['S115 AIN']
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
PHI for Axon S115 analog input. Modbus port should be created in UC before
loading.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

from eva.uc.driverapi import phi_constructor

import eva.uc.modbus as modbus
import struct


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
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

    def get(self, port=None, cfg=None, timeout=0):
        mb = modbus.get_port(self.modbus_port, timeout)
        if not mb: return None
        try:
            rr = mb.read_holding_registers(3002, 2, unit=self.unit_id)
            mb.release()
            if rr.isError():
                self.log_debug(rr)
                return None
            return {
                '1':
                    '{:.2f}'.format(
                        struct.unpack(
                            'f',
                            struct.pack('H', rr.registers[0]) +
                            struct.pack('H', rr.registers[1]))[0])
            }
        except:
            log_traceback()
            return None

    def test(self, cmd=None):
        if cmd == 'self':
            result = self.get(timeout=get_timeout())
            return 'OK' if result else 'FAILED'
        elif cmd == 'get':
            return self.get(timeout=get_timeout())
        else:
            return {'get': 'get AIN state'}
