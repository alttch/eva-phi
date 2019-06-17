__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.1.2"
__description__ = "Denkovi relay DAE-PB-RO5-DAEnetIP4"

__api__ = 4
__required__ = ['port_get', 'port_set', 'status', 'action']
__mods_required__ = []
__lpi_default__ = 'basic'
__equipment__ = 'DAE-PB-RO5-DAEnetIP4'
__features__ = ['universal']
__config_help__ = [{
    'name': 'host',
    'help': 'relay host/ip[:port]',
    'type': 'str',
    'required': False
}, {
    'name': 'community',
    'help': 'snmp default community (default: private)',
    'type': 'str',
    'required': False
}, {
    'name': 'read_community',
    'help': 'snmp read community',
    'type': 'str',
    'required': False
}, {
    'name': 'write_community',
    'help': 'snmp write community',
    'type': 'str',
    'required': False
}, {
    'name': 'retries',
    'help': 'snmp retry attemps (default: 0)',
    'type': 'int',
    'required': False
}]
__get_help__ = []
__set_help__ = []
__help__ = """
PHI for Denkovi relay DAE-PB-RO5-DAEnetIP4, uses SNMP API to control/monitor
the equipment. SNMP on relay should be enabled and configured to allow packets
from UC.

This is universal PHI which means one PHI can control either one or multiple
relays of the same type if relay config (host) is provided in unit driver
configuration.

host and communities should be specified either in driver primary configuration
or in each unit configuration which uses the driver with this PHI.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

from eva.tools import parse_host_port

import eva.uc.drivers.tools.snmp as snmp

import pysnmp.proto.rfc1902 as rfc1902

from eva.uc.driverapi import phi_constructor


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        c = self.phi_cfg.get('community') if self.phi_cfg.get(
            'community') else 'private'
        self.snmp_read_community = c
        self.snmp_write_community = c
        if 'read_community' in self.phi_cfg:
            self.snmp_read_community = self.phi_cfg.get('read_community')
        if 'write_community' in self.phi_cfg:
            self.snmp_read_community = self.phi_cfg.get('write_community')
        try:
            self.snmp_tries = int(self.phi_get('retries')) + 1
        except:
            self.snmp_tries = 1
        self.port_shift = 7
        self.port_max = 5
        self.snmp_host, self.snmp_port = parse_host_port(
            self.phi_cfg.get('host'), 161)
        self.oid_name = '.1.3.6.1.4.1.42505.1.1.1.0'
        self.oid_version = '.1.3.6.1.4.1.42505.1.1.2.0'
        self.oid_work = '.1.3.6.1.4.1.42505.1.2.3.1.11'

    def get_ports(self):
        return self.generate_port_list(port_max=5, description='relay port #{}')

    def get(self, port=None, cfg=None, timeout=0):
        try:
            port = int(port)
        except:
            return None
        if cfg:
            host, snmp_port = parse_host_port(cfg.get('host'), 161)
            community = cfg.get('community')
            if not community: community = cfg.get('read_community')
            tries = cfg.get('retries')
            try:
                tries = int(tries)
            except:
                tries = None
        else:
            host = None
            community = None
            tries = None
        if not host:
            host = self.snmp_host
            snmp_port = self.snmp_port
        if not community:
            community = self.snmp_read_community
        if tries is None: tries = self.snmp_tries
        if not host or not community: return None
        if port < 1 or port > self.port_max: return None
        _timeout = timeout / tries
        return snmp.get(
            '%s.%u' % (self.oid_work, port + self.port_shift),
            host,
            snmp_port,
            community,
            _timeout,
            tries - 1,
            rf=int)

    def set(self, port=None, data=None, cfg=None, timeout=0):
        try:
            port = int(port)
            val = int(data)
        except:
            return False
        if cfg:
            host, snmp_port = parse_host_port(cfg.get('host'), 161)
            community = cfg.get('community')
            if not community: community = cfg.get('write_community')
            tries = cfg.get('retries')
            try:
                tries = int(tries)
            except:
                tries = None
        else:
            host = None
            community = None
            tries = None
        if not host:
            host = self.snmp_host
            snmp_port = self.snmp_port
        if not community:
            community = self.snmp_write_community
        if tries is None: tries = self.snmp_tries
        if not host or not community: return False
        if port < 1 or port > self.port_max or val < 0 or val > 1: return False
        _timeout = timeout / self.snmp_tries
        return snmp.set('%s.%u' % (self.oid_work, port + self.port_shift),
                        rfc1902.Integer(val), host, snmp_port, community,
                        _timeout, tries - 1)

    def test(self, cmd=None):
        if cmd == 'self' and self.snmp_host is None: return 'OK'
        if cmd == 'info' or cmd == 'self':
            name = snmp.get(
                self.oid_name,
                self.snmp_host,
                self.snmp_port,
                self.snmp_read_community,
                timeout=get_timeout() - 0.5)
            if not name: return 'FAILED'
            if name and cmd == 'self': return 'OK'
            version = snmp.get(
                self.oid_version,
                self.snmp_host,
                self.snmp_port,
                self.snmp_read_community,
                timeout=get_timeout() - 0.5)
            if not version: return 'FAILED'
            return '%s %s' % (name.strip(), version.strip())
        return {'info': 'returns relay ip module name and version'}
