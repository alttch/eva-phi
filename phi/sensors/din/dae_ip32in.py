__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.1.2"
__description__ = "Denkovi smartDEN IP-32IN (DINs)"

__api__ = 4
__required__ = ['value', 'events']
__mods_required__ = []
__lpi_default__ = 'sensor'
__equipment__ = 'smartDEN IP-32IN'
__features__ = []
__config_help__ = [{
    'name': 'host',
    'help': 'module host/ip',
    'type': 'str',
    'required': True
}]
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

from eva.uc.driverapi import phi_constructor


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.snmp_host = self.phi_cfg.get('host')
        self.port_state = {}
        if not self.snmp_host:
            self.log_error('no host specified')
            self.ready = False

    def start(self):
        eva.traphandler.subscribe(self)

    def stop(self):
        eva.traphandler.unsubscribe(self)

    def get_ports(self):
        return self.generate_port_list(
            port_max=16,
            name='DIN port #{}',
            description='digital input port #{}')

    def process_snmp_trap(self, host, data):
        if host != self.snmp_host: return
        if data.get('1.3.6.1.6.3.1.1.4.1.0') != '1.3.6.1.4.1.42505.7.0.1':
            return
        for i in range(16):
            value = data.get('1.3.6.1.4.1.42505.7.2.1.1.7.{}'.format(i))
            if value:
                port = 'din{}'.format(i + 1)
                self.log_debug('event {} = {}'.format(port, value))
                self.port_state[port] = value
                handle_phi_event(self, port, {port: value})
        return

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        return {'-': 'self test only'}
