__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "Denkovi smartDEN IP-32IN (DINs)"

__id__ = 'dae_ip32in'
__equipment__ = ['SmartDEN-IP-32IN']
__api__ = 1
__required__ = ['value']
__mods_required__ = []
__lpi_default__ = 'sensor'
__features__ = ['events']
__config_help__ = [{
    'name': 'host',
    'help': 'module host/ip',
    'type': 'str',
    'required': True
}
]
__get_help__ = []
__set_help__ = []

__help__ = """
PHI for Denkovi smartDEN IP-32IN (digltal inputs only)
sensor should have "port" set to dinX (eg din1) in driver config.

PHI doesn't provide any control/monitoring functions, events are received by
SNMP traps only.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout
from eva.uc.driverapi import handle_phi_event

from eva.tools import parse_host_port

import eva.uc.drivers.tools.snmp as snmp
import eva.traphandler


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
        self.snmp_host = self.phi_cfg.get('host')
        self.port_state = {}
        if not self.snmp_host:
            self.log_error('no host specified')
            self.ready = False

    def start(self):
        eva.traphandler.subscribe(self)

    def stop(self):
        eva.traphandler.unsubscribe(self)

    def process_snmp_trap(self, host, data):
        if host != self.snmp_host: return
        if data.get('1.3.6.1.6.3.1.1.4.1.0') != '1.3.6.1.4.1.42505.7.0.1':
            return
        for i in range(16):
            value = data.get('1.3.6.1.4.1.42505.7.2.1.1.7.{}'.format(i))
            if value:
                port = 'din{}'.format(i+1)
                self.log_debug('event {} = {}'.format(port, value))
                self.port_state[port] = value
                handle_phi_event(self, port, { port: value })
        return

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        return {'-': 'self test only'}
