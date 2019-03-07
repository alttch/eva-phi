__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "1-Wire OWFS universal sensor driver"

__id__ = 'ow_sensor'
__equipment__ = ['Any 1-Wire sensor']
__api__ = 3
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'ssp'
__features__ = ['port_get', 'universal']
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
}, {
    'name': 'attr',
    'help': 'Equpment attribute',
    'type': 'str',
    'required': False
}]
__get_help__ = __config_help__
__set_help__ = __config_help__

__help__ = """
PHI for Maxim Integrated 1-Wire equipment working via OWFS.

Can be used for various types of sensors as attr (e.g. "temperature" or
"voltage") is specified by user. This is universal PHI, owfs bus, path and attr
can be specified in EVA ICS sensor configuration.
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
        self.attr = self.phi_cfg.get('attr')

    def get(self, port=None, cfg=None, timeout=0):
        owfs_bus = self.owfs_bus
        path = self.path
        attr = self.attr
        if cfg:
            if 'owfs' in cfg: owfs_bus = cfg['owfs']
            if 'path' in cfg: path = cfg['path']
            if 'attr' in cfg: attr = cfg['attr']
        bus = owfs.get_bus(owfs_bus)
        if not bus: return None
        try:
            return {attr: bus.read(path, attr)}
        except:
            return None
        finally:
            bus.release()

    def test(self, cmd=None):
        if cmd == 'self':
            if self.owfs_bus:
                bus = owfs.get_bus(self.owfs_bus)
                if not bus: return 'FAILED'
                try:
                    if self.path:
                        a = self.attr if self.attr else 'type'
                        s = bus.read(self.path, a)
                        if not s: return 'FAILED'
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
                'Get value (if owfs, path and attr are defined in PHI config)'
            }
