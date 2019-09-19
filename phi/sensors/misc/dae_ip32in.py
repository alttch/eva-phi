__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "2.0.0"
__description__ = "Denkovi smartDEN IP-32IN"

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
}, {
    'name': 'community',
    'help': 'snmp default community (default: public)',
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
PHI for Denkovi smartDEN IP-32IN

Sensors should have port set 1-16 for digital inputs, a1-a8 for analog inputs,
t1-8 for temperature inputs.

DIN events can be received by SNMP traps.

For production it is recommended to install python "python3-netsnmp" module.
"""

try:
    import netsnmp
except:
    netsnmp = None

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
        self.snmp_host, self.snmp_port = parse_host_port(
            self.phi_cfg.get('host'), 161)
        self.port_state = {}
        if not self.snmp_host:
            self.log_error('no host specified')
            self.ready = False
        self.community = self.phi_cfg.get('community') if self.phi_cfg.get(
            'community') else 'public'
        try:
            self.snmp_tries = int(self.phi_get('retries')) + 1
        except:
            self.snmp_tries = 1
        self.oid_din = '.1.3.6.1.4.1.42505.7.2.1.1.7'
        self.oid_ain = '.1.3.6.1.4.1.42505.7.2.2.1.6'
        self.oid_temp = '.1.3.6.1.4.1.42505.7.2.3.1.7'
        self.oid_name = '.1.3.6.1.4.1.42505.7.1.1.0'
        self.oid_version = '.1.3.6.1.4.1.42505.7.1.2.0'

    def start(self):
        eva.traphandler.subscribe(self)

    def stop(self):
        eva.traphandler.unsubscribe(self)

    def get(self, port=None, cfg=None, timeout=0):
        if cfg:
            host, snmp_port = parse_host_port(cfg.get('host'), 161)
            community = cfg.get('community')
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
            community = self.community
        if tries is None: tries = self.snmp_tries
        if not host or not community: return None
        _timeout = timeout / tries
        port = str(port)
        if port.startswith('a'):
            oid = self.oid_ain
            port_max = 8
            port = port[1:]
            ret = 1
        elif port.startswith('t'):
            oid = self.oid_temp
            port_max = 8
            port = port[1:]
            ret = 2
        else:
            oid = self.oid_din
            port_max = 16
            ret = 0
        try:
            port = int(port)
        except:
            return None
        if port < 1 or port > port_max: return None
        if netsnmp:
            try:
                sess = netsnmp.Session(Version=2,
                                       DestHost=host,
                                       RemotePort=snmp_port,
                                       Community=community,
                                       Timeout=int(_timeout * 1000000),
                                       Retries=self.snmp_tries - 1)
                o = netsnmp.VarList('%s.%u' % (oid, port - 1))
                result = sess.get(o)[0].decode()
            except Exception as e:
                self.log_error(e)
                log_traceback()
                return None
        else:
            result = snmp.get('%s.%u' % (oid, port - 1),
                              host,
                              snmp_port,
                              community,
                              _timeout,
                              tries - 1,
                              rf=int)
        if ret == 0:
            return result
        elif ret == 1:
            return int(result) / 100
        elif ret == 2:
            return None if result == '---' else result

    def get_ports(self):
        l = self.generate_port_list(port_max=16,
                                    name='DIN port #{}',
                                    description='digital input port #{}')
        for i in range(1, 9):
            l.append({
                'port': 'a{}'.format(i),
                'name': 'AIN port #{}'.format(i),
                'description': 'analog input port #{}'.format(i)
            })
        for i in range(1, 9):
            l.append({
                'port': 't{}'.format(i),
                'name': 'Temp port #{}'.format(i),
                'description': 'temperature input port #{}'.format(i)
            })
        return l

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
        if cmd == 'module':
            return 'default' if not netsnmp else 'netsnmp'
        if cmd == 'self' and self.snmp_host is None: return 'OK'
        if cmd == 'info' or cmd == 'self':
            if netsnmp:
                try:
                    sess = netsnmp.Session(Version=2,
                                           DestHost=self.snmp_host,
                                           RemotePort=self.snmp_port,
                                           Community=self.community,
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
                name = snmp.get(self.oid_name,
                                self.snmp_host,
                                self.snmp_port,
                                self.community,
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
                version = snmp.get(self.oid_version,
                                   self.snmp_host,
                                   self.snmp_port,
                                   self.community,
                                   timeout=get_timeout())
            if not version: return 'FAILED'
            return '%s %s' % (name.strip(), version.strip())
        return {
            'info': 'returns relay ip module name and version',
            'module': 'current SNMP module'
        }
