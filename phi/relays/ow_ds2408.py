__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "1-Wire OWFS DS2408 relay"

__id__ = 'ow_ds2408'
__equipment__ = ['DS2408']
__api__ = 3
__required__ = ['port_get', 'status', 'action']
__mods_required__ = []
__lpi_default__ = 'basic'
__features__ = ['port_get', 'port_set', 'aao_get', 'aao_set', 'universal']
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
        self.owfs_bus = self.phi_cfg.get('owfs')
        self.path = self.phi_cfg.get('path')

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
            s = bus.ow.sensor(path)
            if port:
                return int(getattr(s, 'PIO.{}'.format(_port - 1)))
            else:
                v = getattr(s, 'PIO.ALL').split(',')
                return {str(a + 1): int(v[a - 1]) for a in range(8)}
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
            s = bus.ow.sensor(path)
            if port:
                setattr(s, 'PIO.{}'.format(_port + 1), data)
            else:
                setattr(s, 'PIO.ALL', ','.join([str(x) for x in data]))
            return True
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
                        s = bus.ow.sensor(self.path)
                        if not s: return 'FAILED'
                        getattr(s, 'PIO.ALL')
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
