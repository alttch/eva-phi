__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.1.2"
__description__ = "1-Wire OWFS universal sensor driver"

__equipment__ = ['Any 1-Wire sensor']
__api__ = 5
__required__ = ['port_get', 'value', 'aao_get']
__mods_required__ = []
__lpi_default__ = 'ssp'
__features__ = ['universal']
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

from eva.uc.driverapi import phi_constructor


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
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
            value = bus.read(path, attr)
            if not value:
                raise Exception('can not obtain value')
            return {attr: value}
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
