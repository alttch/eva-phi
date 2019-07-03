__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.2.1"
__description__ = "Denkovi relay smartDEN-IP-16R"

__api__ = 4
__required__ = ['port_get', 'port_set', 'status', 'action']
__mods_required__ = []
__lpi_default__ = 'basic'
__equipment__ = ['smartDEN-IP-16R']
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
    'name': 'retries',
    'help': 'snmp retry attemps (default: 0)',
    'type': 'int',
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
}]
__get_help__ = __config_help__[:-2]
__set_help__ = __config_help__[:-2]

__help__ = """
PHI for Denkovi smartDEN-IP-16R IP relay, uses SNMP API to control/monitor the
equipment. SNMP on relay should be enabled and configured to allow packets from
UC.

This is universal PHI which means one PHI can control either one or multiple
relays of the same type if relay config (host) is provided in unit driver
configuration.

host and communities should be specified either in driver primary configuration
or in each unit configuration which uses the driver with this PHI.

For production it is recommended to install python "python3-netsnmp" module. As
soon as it is detected, PHI report "aao_get" and "aao_set" features.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

from eva.tools import parse_host_port

import eva.uc.drivers.tools.snmp as snmp

import pysnmp.proto.rfc1902 as rfc1902

from eva.uc.driverapi import phi_constructor

try:
    import netsnmp
    __features__.append('aao_get')
    __features__.append('aao_set')
except:
    netsnmp = None


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
        self.port_shift = -1
        self.port_max = 16
        self.snmp_host, self.snmp_port = parse_host_port(
            self.phi_cfg.get('host'), 161)
        self.oid_name = 'iso.3.6.1.4.1.42505.6.1.1.0'
        self.oid_version = 'iso.3.6.1.4.1.42505.6.1.2.0'
        self.oid_work = 'iso.3.6.1.4.1.42505.6.2.3.1.3'

    def get_ports(self):
        return self.generate_port_list(
            port_max=16, description='relay port #{}')

    def get(self, port=None, cfg=None, timeout=0):
        if cfg:
            host, snmp_port = parse_host_port(cfg.get('host'), 161)
            community = cfg.get('community')
            if not community: community = cfg.get('read_community')
            tries = cfg.get('retries')
            try:
                tries = int(tries) + 1
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
        _timeout = timeout / tries
        if not port and netsnmp:
            try:
                sess = netsnmp.Session(
                    Version=2,
                    DestHost=host,
                    RemotePort=snmp_port,
                    Community=community,
                    Timeout=int(_timeout * 1000000),
                    Retries=self.snmp_tries - 1)
                oid = netsnmp.VarList(
                    '%s.%u' % (self.oid_work, self.port_shift + 1))
                sess.getbulk(0, self.port_max, oid)
                result = {}
                for i, v in enumerate(oid):
                    result[str(i + 1)] = v.val.decode()
                return result
            except Exception as e:
                self.log_error(e)
                log_traceback()
                return None
        else:
            try:
                port = int(port)
            except:
                return None
            if port < 1 or port > self.port_max: return None
            if netsnmp:
                try:
                    sess = netsnmp.Session(
                        Version=2,
                        DestHost=host,
                        RemotePort=snmp_port,
                        Community=community,
                        Timeout=int(_timeout * 1000000),
                        Retries=self.snmp_tries - 1)
                    oid = netsnmp.VarList(
                        '%s.%u' % (self.oid_work, port + self.port_shift))
                    return sess.get(oid)[0].decode()
                except Exception as e:
                    self.log_error(e)
                    log_traceback()
                    return None
            else:
                return snmp.get(
                    '%s.%u' % (self.oid_work, port + self.port_shift),
                    host,
                    snmp_port,
                    community,
                    _timeout,
                    tries - 1,
                    rf=int)

    def set(self, port=None, data=None, cfg=None, timeout=0):
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
        _timeout = timeout / self.snmp_tries
        if isinstance(port, list) and netsnmp:
            try:
                sess = netsnmp.Session(
                    Version=2,
                    DestHost=host,
                    RemotePort=snmp_port,
                    Community=community,
                    Timeout=int(_timeout * 1000000),
                    Retries=self.snmp_tries - 1)
                vts = ()
                for p, v in zip(port, data):
                    try:
                        port = int(p)
                        val = int(v)
                        if port < 1 or \
                                port > self.port_max or val < 0 or val > 1:
                            raise Exception('port out of range')
                    except Exception as e:
                        self.log_error(e)
                        log_traceback()
                        return False
                    vts += (netsnmp.Varbind(
                        '%s.%u' % (self.oid_work, port + self.port_shift), '',
                        str(v).encode(), 'INTEGER'),)
                return True if sess.set(netsnmp.VarList(*vts)) else False
            except:
                log_traceback()
                return False
        else:
            try:
                port = int(port)
                val = int(data)
            except:
                return False
            if port < 1 or port > self.port_max or val < 0 or val > 1:
                return False
            return snmp.set('%s.%u' % (self.oid_work, port + self.port_shift),
                            rfc1902.Integer(val), host, snmp_port, community,
                            _timeout, tries - 1)

    def test(self, cmd=None):
        if cmd == 'module':
            return 'default' if not netsnmp else 'netsnmp'
        if cmd == 'self' and self.snmp_host is None: return 'OK'
        if cmd == 'info' or cmd == 'self':
            if netsnmp:
                try:
                    sess = netsnmp.Session(
                        Version=2,
                        DestHost=self.snmp_host,
                        RemotePort=self.snmp_port,
                        Community=self.snmp_read_community,
                        Timeout=int(get_timeout() * 1000000),
                        Retries=self.snmp_tries - 1)
                except:
                    log_traceback()
                    sess = None
            if netsnmp:
                try:
                    name = sess.get(netsnmp.VarList(self.oid_name))[0].decode()
                except:
                    log_traceback()
                    name = None
            else:
                name = snmp.get(
                    self.oid_name,
                    self.snmp_host,
                    self.snmp_port,
                    self.snmp_read_community,
                    timeout=get_timeout(),
                    retries=self.snmp_tries - 1)
            if not name: return 'FAILED'
            if name and cmd == 'self': return 'OK'
            if netsnmp:
                try:
                    version = sess.get(netsnmp.VarList(
                        self.oid_version))[0].decode()
                except:
                    version = None
            else:
                version = snmp.get(
                    self.oid_version,
                    self.snmp_host,
                    self.snmp_port,
                    self.snmp_read_community,
                    timeout=get_timeout())
            if not version: return 'FAILED'
            return '%s %s' % (name.strip(), version.strip())
        return {
            'info': 'returns relay ip module name and version',
            'module': 'current SNMP module'
        }
