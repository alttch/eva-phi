__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "1-Wire OWFS temperature sensor driver"

__equipment__ = ['DS18S20', 'DS18B20']
__api__ = 4
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'ssp'
__features__ = ['port_get', 'aao_get']
__config_help__ = [{
    'name': 'owfs',
    'help': 'OWFS virtual bus',
    'type': 'str',
    'required': True
}, {
    'name': 'path',
    'help': 'Equpment path',
    'type': 'str',
    'required': True
}]
__get_help__ = __config_help__
__set_help__ = __config_help__

__help__ = """
PHI for Maxim Integrated 1-Wire temperature sensors (DS18S20, DS20B20) working
via OWFS.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback

import eva.uc.owfs as owfs

from eva.uc.driverapi import phi_constructor


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.owfs_bus = self.phi_cfg.get('owfs')
        self.path = self.phi_cfg.get('path')
        self.aao_get = True
        if not self.owfs_bus or not self.path:
            self.log_error('owfs/path not specified')
            self.ready = False
        else:
            bus = owfs.get_bus(self.owfs_bus)
            if bus:
                bus.release()
            else:
                self.log_error('unable to get owfs bus {}'.format(
                    self.owfs_bus))
                self.ready = False

    def get(self, port=None, cfg=None, timeout=0):
        bus = owfs.get_bus(self.owfs_bus)
        if not bus: return None
        try:
            value = bus.read(self.path, 'temperature')
            if not value:
                raise Exception('can not obtain value')
            return {'temperature': value}
        except:
            return None
        finally:
            bus.release()

    def test(self, cmd=None):
        if cmd == 'self':
            bus = owfs.get_bus(self.owfs_bus)
            if not bus: return 'FAILED'
            try:
                s = bus.read(self.path, 'temperature')
                if not s: return 'FAILED'
            except:
                return 'FAILED'
            finally:
                bus.release()
            return 'OK'
        elif cmd == 'get':
            return self.get()
        else:
            return {'get': 'Get value'}
