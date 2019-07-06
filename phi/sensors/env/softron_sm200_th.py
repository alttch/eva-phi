__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "0.1.0"
__description__ = "Softron SM-200 temperature/humidity sensor"

__api__ = 4
__required__ = ['aao_get', 'value']
__mods_required__ = []
__lpi_default__ = 'sensor'
__equipment__ = ['Softron SM-200']
__features__ = []
__config_help__ = [{
    'name': 'port',
    'help': 'ModBus port ID',
    'type': 'str',
    'required': True
}, {
    'name': 'addr',
    'help': 'modbus addr',
    'type': 'int',
    'required': True
}]
__get_help__ = []
__set_help__ = []

__help__ = """
PHI for Softron (http://www.softron.com.ua/) SM-200 Modbus temperature/humidity
sensor. Ports: "t", "h"
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

from eva.uc.driverapi import phi_constructor

import eva.uc.modbus as modbus


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.modbus_port = self.phi_cfg.get('port')
        if not modbus.is_port(self.modbus_port):
            self.log_error('modbus port ID not specified or invalid')
            self.ready = False
            return
        try:
            self.addr = int(self.phi_cfg.get('addr'))
        except:
            self.log_error('modbus addr not specified or invalid')
            self.ready = False
            return

    def get_ports(self):
        return [{
            'port': 't',
            'name': 'temperature',
            'description': ''
        }, {
            'port': 'h',
            'name': 'humidity',
            'description': ''
        }]

    def get(self, port=None, cfg=None, timeout=0):
        mb = modbus.get_port(self.modbus_port, timeout)
        if not mb: return None
        try:
            rr = mb.read_input_registers(30002, 2, addr=self.addr)
            mb.release()
            if rr.isError():
                self.log_debug(rr)
                return None
            temp = rr.registers[0]
            if temp > 32767: temp = temp - 65536
            return {'t': temp / 100, 'h': rr.registers[1] / 100}
        except:
            log_traceback()
            return None

    def test(self, cmd=None):
        if cmd == 'self':
            mb = modbus.get_port(self.modbus_port, get_timeout())
            rr = mb.read_input_registers(30000, 1, addr=self.addr)
            mb.release()
            try:
                if rr.isError():
                    raise Exception(str(rr))
                if rr.registers[0] != 1:
                    raise Exception('status: {}'.format(rr.registers[0]))
                return 'OK'
            except Exception as e:
                self.log_error(e)
                return 'FAILED'
        elif cmd == 'fwver':
            mb = modbus.get_port(self.modbus_port, get_timeout())
            rr = mb.read_input_registers(30001, 1, addr=self.addr)
            mb.release()
            if rr.isError():
                self.log_error(rr)
                return None
            return rr.registers[0]
        else:
            return {'fwver': 'Get firmware version'}
