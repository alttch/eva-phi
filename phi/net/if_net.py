__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "Bandwidth meter/interface monitor"

__api__ = 4
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'esensor'
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

__get_help__ = []
__set_help__ = []

__help__ = """
SNMPv2 bandwidth meter/interface status monitoring. Works with any SNMPv2
compatible equipment: routers, switches etc.

Use "phi ports <phi>" command to get list of available ports to monitor.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import phi_constructor
from eva.uc.driverapi import get_timeout
from eva.tools import parse_host_port

import eva.uc.drivers.tools.snmp as snmp

from functools import partial
from time import time


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        host, port = parse_host_port(self.phi_cfg.get('host'), 161)
        if not host:
            self.log_error('Host not specified')
            self.ready = False
            return
        try:
            retries = int(self.phi_get('retries'))
        except:
            retries = 0
        self.t_data = {}
        self.snmp_get = partial(
            snmp.get,
            host=host,
            port=port,
            community=self.phi_cfg.get('community')
            if self.phi_cfg.get('community') else 'public',
            retries=retries)

    def get_ports(self):
        ports = {}
        # get ports
        for p in self.snmp_get(
                oid='1.3.6.1.2.1.2.2.1.1', timeout=get_timeout(), walk=True):
            port_number = int(p[1])
            ports[port_number] = {'port': str(port_number)}
        # get port names
        for p in self.snmp_get(
                oid='1.3.6.1.2.1.2.2.1.2', timeout=get_timeout(), walk=True):
            port_number = int(str(p[0].getOid()).rsplit('.', 1)[1])
            if port_number in ports:
                ports[port_number]['name'] = str(p[1])
        # get port speeds
        for p in self.snmp_get(
                oid='1.3.6.1.2.1.2.2.1.5', timeout=get_timeout(), walk=True):
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
        time_start = time()
        try:
            dr, n = port.split('_')
            # is port up?
            if self.snmp_get(
                    oid='1.3.6.1.2.1.2.2.1.7.{}'.format(n), timeout=timeout,
                    rf=int) not in [1, 3]:
                self.log_warning('port {} is not operational'.format(port))
                return None
            if dr == 'in':
                o = '10'
            elif dr == 'out':
                o = '16'
            t2 = timeout - time() + time_start
            if t2 <= 0:
                raise Exception('operation timeout')
            data = self.snmp_get(
                oid='1.3.6.1.2.1.2.2.1.{}.{}'.format(o, n), timeout=t2, rf=None)
            rtime = time()
            tp = data[1].prettyPrintType().rsplit(' ', 1)[1]
            if tp not in ['Counter32', 'Counter64']:
                return None
            v = int(data[1])
            if port in self.t_data:
                v_prev = self.t_data[port]['oc']
                ptime = self.t_data[port]['t']
                t_delta = rtime - ptime
                if v >= v_prev:
                    v_delta = v - v_prev
                else:
                    mx = 4294967295 if tp == 'Counter32' else \
                            18446744073709551615
                    v_delta = mx - v_prev + v
                bw = v_delta / t_delta
            else:
                bw = 0
            self.t_data[port] = {'oc': v, 't': rtime}
            return round(bw * 8)
        except:
            log_traceback()
            return None

    def test(self, cmd=None):
        if cmd in ['self', 'info']:
            result = self.snmp_get(
                oid='1.3.6.1.2.1.1.1.0', timeout=get_timeout(), rf=str)
            if result:
                return 'OK' if cmd == 'self' else result
            else:
                return 'FAILED' if cmd == 'self' else None
        else:
            return {'info': 'get equipment model/vendor'}
