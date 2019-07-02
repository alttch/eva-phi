__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.2.0"
__description__ = "AKCP THSXX temperature and humidity sensor"

__api__ = 4
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'sensor'
__equipment__ = 'AKCP THSXX'
__features__ = ['events']
__config_help__ = [{
    'name': 'host',
    'help': 'AKCP controller ip[:port]',
    'type': 'str',
    'required': True
}, {
    'name': 'sp',
    'help': 'controller port where sensor is located (1..X)',
    'type': 'int',
    'required': True
}, {
    'name': 'community',
    'help': 'snmp community (default: public)',
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
PHI for AKCP THS00/THS01 temperature and humidity sensors, uses SNMP API to
monitor the equipment. SNMP on controller should be enabled and configured to
allow packets from UC.

Sensor port should be specified 't' for temperature or 'h' for humidity.

Some pysnmp versions have a bug which throws ValueConstraintError exception
when sensor data is processed despite the data is good. Quick and dirty fix is
to turn on debug, perform PHI self test, get an exception trace and disable the
value testing in pysnmp or pyasn1.

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
        self.community = self.phi_cfg.get('community') if self.phi_cfg.get(
            'community') else 'public'
        try:
            self.snmp_tries = int(self.phi_get('retries')) + 1
        except:
            self.snmp_tries = 1
        self.snmp_host, self.snmp_port = parse_host_port(
            self.phi_cfg.get('host'), 161)
        try:
            self.sensor_port = int(self.phi_cfg.get('sp'))
            if self.sensor_port < 1: self.sensor_port = None
        except:
            self.sensor_port = None
        if not self.snmp_host:
            self.log_error('no host specified')
            self.ready = False
        if not self.sensor_port:
            self.log_error('no sensor port specified')
            self.ready = False

    def get(self, port=None, cfg=None, timeout=0):
        work_oids = {'t': 16, 'h': 17}
        wo = work_oids.get(port)
        if wo is None: return None
        snmp_oid = 'iso.3.6.1.4.1.3854.1.2.2.1.%u.1.3.%u' % (
            wo, self.sensor_port - 1)
        _timeout = timeout / self.snmp_tries
        if netsnmp:
            try:
                sess = netsnmp.Session(
                    Version=1,
                    DestHost=self.snmp_host,
                    RemotePort=self.snmp_port,
                    Community=self.community,
                    Timeout=int(_timeout * 1000000),
                    Retries=self.snmp_tries - 1)
                return sess.get(netsnmp.VarList(snmp_oid))[0].decode()
            except:
                log_traceback()
                return None
        else:
            return snmp.get(
                snmp_oid,
                self.snmp_host,
                self.snmp_port,
                self.community,
                _timeout,
                self.snmp_tries - 1,
                rf=int,
                snmp_ver=1)

    def start(self):
        eva.traphandler.subscribe(self)

    def stop(self):
        eva.traphandler.unsubscribe(self)

    def process_snmp_trap(self, host, data):
        if host != self.snmp_host: return
        if data.get('1.3.6.1.4.1.3854.1.7.4.0') != str(self.sensor_port - 1):
            return
        d = data.get('1.3.6.1.4.1.3854.1.7.1.0')
        if d == '7':
            handle_phi_event(self, ['t', 'h'], {'t': False, 'h': False})
        elif d == '2':
            t = self.get('t', timeout=get_timeout())
            h = self.get('h', timeout=get_timeout())
            handle_phi_event(self, ['t', 'h'], {'t': t, 'h': h})
        return

    def test(self, cmd=None):
        if cmd == 'module':
            return 'default' if not netsnmp else 'netsnmp'
        elif cmd == 'info':
            name = snmp.get(
                '.1.3.6.1.4.1.3854.1.1.8.0',
                self.snmp_host,
                self.snmp_port,
                self.community,
                timeout=get_timeout(),
                snmp_ver=1)
            if not name: return 'FAILED'
            vendor = snmp.get(
                '.1.3.6.1.4.1.3854.1.1.6.0',
                self.snmp_host,
                self.snmp_port,
                self.community,
                timeout=get_timeout(),
                snmp_ver=1)
            if not vendor: return 'FAILED'
            return '%s %s' % (vendor.strip(), name.strip())
        if cmd == 'self':
            t = self.get('t', timeout=get_timeout())
            h = self.get('h', timeout=get_timeout())
            return 'OK' if t and h else 'FAILED'
        return {
                'info': 'returns relay ip module name and version',
                'module': 'current SNMP module'
                }
