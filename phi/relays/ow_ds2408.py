__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.1.1"
__description__ = "1-Wire OWFS DS2408 relay"

__equipment__ = ['DS2408']
__api__ = 4
__required__ = ['port_get', 'port_set', 'status', 'action']
__mods_required__ = []
__lpi_default__ = 'basic'
__features__ = ['aao_get', 'aao_set', 'universal']
__config_help__ = [{
    'name': 'owfs',
    'help': 'OWFS virtual bus',
    'type': 'str',
    'required': False
}, {
    'name': 'path',
    'help': 'Equpment path',
    'type': 'str',
    'required': False
}]
__get_help__ = __config_help__
__set_help__ = __config_help__

__help__ = """
PHI for Maxim Integrated 1-Wire DS2408 relay working via OWFS.

This is universal PHI, owfs bus and path can be specified in EVA ICS unit
configuration. Unit port can be in range 1-8
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

    def get_ports(self):
        return self.generate_port_list(port_max=8, description='relay port #{}')

    def get(self, port=None, cfg=None, timeout=0):
        if port:
            try:
                _port = int(port)
            except:
                return False
        owfs_bus = self.owfs_bus
        path = self.path
        if cfg:
            if 'owfs' in cfg: owfs_bus = cfg['owfs']
            if 'path' in cfg: path = cfg['path']
        bus = owfs.get_bus(owfs_bus)
        if not bus: return None
        try:
            if port:
                return int(bus.read(path, 'PIO.{}'.format(_port - 1)))
            else:
                v = bus.read(path, 'PIO.ALL').split(',')
                return {str(a + 1): int(v[a]) for a in range(8)}
        except:
            return None
        finally:
            bus.release()

    def set(self, port=None, data=None, cfg=None, timeout=0):
        if port:
            try:
                _port = int(port)
            except:
                return False
        owfs_bus = self.owfs_bus
        path = self.path
        if cfg:
            if 'owfs' in cfg: owfs_bus = cfg['owfs']
            if 'path' in cfg: path = cfg['path']
        bus = owfs.get_bus(owfs_bus)
        if not bus: return False
        try:
            if port:
                return bus.write(path, 'PIO.{}'.format(_port - 1), data)
            else:
                return bus.write(path, 'PIO.ALL',
                                 ','.join([str(x) for x in data]))
        except:
            return False
        finally:
            bus.release()

    def test(self, cmd=None):
        if cmd == 'self':
            if self.owfs_bus:
                bus = owfs.get_bus(self.owfs_bus)
                if not bus: return 'FAILED'
                try:
                    if self.path:
                        if not bus.read(self.path, 'PIO.ALL'): return 'FAILED'
                except:
                    return 'FAILED'
                finally:
                    bus.release()
            return 'OK'
        elif cmd == 'get':
            return self.get()
        else:
            return {
                'get':
                'Get port values (if owfs and path are defined in PHI config)'
            }
