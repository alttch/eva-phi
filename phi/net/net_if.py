__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.1.0"
__description__ = "Bandwidth meter/interface monitor"

__api__ = 6
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'sensor'
__equipment__ = ['NET-IF']
__features__ = []
__config_help__ = [{
    'name': 'host',
    'help': 'equipment host/ip[:port]',
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

try:
    import netsnmp
    __features__.append('aao_get')
except:
    netsnmp = None

__get_help__ = []
__set_help__ = []

__help__ = """
SNMPv2 bandwidth meter/interface status monitoring. Works with any SNMPv2
compatible equipment: routers, switches etc.

Use "phi ports <phi>" command to get list of available ports to monitor.

For production it is recommended to install python "python3-netsnmp" module. As
soon as it is detected, PHI report "aao_get" feature and use this module to
quickly obtain states of all interfaces of the specified host.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import phi_constructor
from eva.uc.driverapi import get_timeout
from eva.tools import parse_host_port

import eva.uc.drivers.tools.snmp as snmp

from functools import partial
from time import perf_counter

import threading


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        host, port = parse_host_port(self.phi_cfg.get('host'), 161)
        community = self.phi_cfg.get('community')
        if not community:
            community = 'public'
        if not host:
            self.log_error('Host not specified')
            self.ready = False
            return
        try:
            retries = int(self.phi_get('retries'))
        except:
            retries = 0
        self.t_data = {}
        self.t_lock = threading.Lock()
        self.snmp_get = partial(snmp.get,
                                host=host,
                                port=port,
                                community=community,
                                retries=retries)
        self.host = host
        self.port = port
        self.community = community
        self.retries = retries

    def create_session(self, timeout):
        return netsnmp.Session(Version=2,
                               DestHost=self.host,
                               RemotePort=self.port,
                               Community=self.community,
                               Timeout=int(timeout * 1000000),
                               Retries=self.retries)

    def get_ports(self):
        ports = {}
        # get ports
        for p in self.snmp_get(oid='1.3.6.1.2.1.2.2.1.1',
                               timeout=get_timeout(),
                               walk=True):
            port_number = int(p[1])
            ports[port_number] = {'port': str(port_number)}
        # get port names
        for p in self.snmp_get(oid='1.3.6.1.2.1.2.2.1.2',
                               timeout=get_timeout(),
                               walk=True):
            port_number = int(str(p[0].getOid()).rsplit('.', 1)[1])
            if port_number in ports:
                ports[port_number]['name'] = str(p[1])
        # get port speeds
        for p in self.snmp_get(oid='1.3.6.1.2.1.2.2.1.5',
                               timeout=get_timeout(),
                               walk=True):
            port_number = int(str(p[0].getOid()).rsplit('.', 1)[1])
            if port_number in ports:
                ports[port_number]['description'] = 'speed: {}'.format(p[1])
        result = []
        for p in sorted(ports):
            for x in ['in', 'out']:
                port = ports[p].copy()
                port['port'] = '{}_{}'.format(x, port['port'])
                port['name'] = '{} {}put'.format(port['name'], x)
                result.append(port)
        return result

    def get(self, port=None, cfg=None, timeout=0):

        def calc_bw(port, v, rtime, calc64bit):
            self.t_lock.acquire()
            try:
                if port in self.t_data:
                    v_prev = self.t_data[port]['oc']
                    ptime = self.t_data[port]['t']
                    t_delta = rtime - ptime
                    if v >= v_prev:
                        v_delta = v - v_prev
                    else:
                        mx = 18446744073709551615 if calc64bit else 4294967295
                        v_delta = mx - v_prev + v
                    bw = v_delta / t_delta
                else:
                    bw = 0
                self.t_data[port] = {'oc': v, 't': rtime}
                return round(bw * 8)
            finally:
                self.t_lock.release()

        try:
            if port is None and netsnmp:
                oid = netsnmp.VarList('.1.3.6.1.2.1.2.2.1.7',
                                      '.1.3.6.1.2.1.2.2.1.10',
                                      '.1.3.6.1.2.1.2.2.1.16')
                rtime = perf_counter()
                data = self.create_session(timeout).walk(oid)
                result = {}
                for v in oid:
                    if v.tag.startswith('iso.') or v.tag.startswith(
                            '1.') or v.tag.startswith('.1.'):
                        o, p = v.tag.rsplit('.', 1)
                    else:
                        o = v.tag
                        p = v.iid
                    if o == 'ifAdminStatus' or o.endswith('.7'):
                        if v.val.decode() not in ['1', '3']:
                            result[p + '_in'] = None
                            result[p + '_out'] = None
                    elif p not in result:
                        port = ('in' if o == 'ifInOctets' or o.endswith('.10')
                                else 'out') + '_' + p
                        result[port] = calc_bw(port, int(v.val.decode()), rtime,
                                               v.type == 'COUNTER64')
                return result
            elif port is None:
                self.log_warning('netsnmp required for bulk updates')
                return None
            else:
                time_start = perf_counter()
                dr, n = port.split('_')
                # is port up?
                if self.snmp_get(oid='1.3.6.1.2.1.2.2.1.7.{}'.format(n),
                                 timeout=timeout,
                                 rf=int) not in [1, 3]:
                    self.log_warning('port {} is not operational'.format(port))
                    return None
                if dr == 'in':
                    o = '10'
                elif dr == 'out':
                    o = '16'
                t2 = timeout - perf_counter() + time_start
                if t2 <= 0:
                    raise Exception('operation timeout')
                data = self.snmp_get(oid='1.3.6.1.2.1.2.2.1.{}.{}'.format(o, n),
                                     timeout=t2,
                                     rf=None)
                rtime = perf_counter()
                tp = data[1].prettyPrintType().rsplit(' ', 1)[1]
                if tp not in ['Counter32', 'Counter64']:
                    return None
                v = int(data[1])
                return calc_bw(port, v, rtime, tp == 'Counter64')
        except:
            log_traceback()
            return None

    def test(self, cmd=None):
        if cmd == 'module':
            return 'default' if not netsnmp else 'netsnmp'
        elif cmd in ['self', 'info']:
            o = 'iso.3.6.1.2.1.1.1.0'
            if netsnmp:
                try:
                    result = self.create_session(get_timeout()).get(
                        netsnmp.VarList(o))[0].decode()
                except:
                    log_traceback()
                    result = None
            else:
                result = self.snmp_get(oid=o, timeout=get_timeout(), rf=str)
            if result:
                return 'OK' if cmd == 'self' else result
            else:
                return 'FAILED' if cmd == 'self' else None
        else:
            return {
                'info': 'get equipment model/vendor',
                'module': 'current SNMP module'
            }

    def validate_config(self, config={}, config_type='config'):
        self.validate_config_whi(config=config, config_type=config_type)
