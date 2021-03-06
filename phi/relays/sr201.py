__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.1.0"
__description__ = "SR-201 relay"

__api__ = 5
__required__ = ['aao_get', 'port_set', 'status', 'action']
__mods_required__ = []
__lpi_default__ = 'basic'
__equipment__ = 'SR-201'
__features__ = ['universal']
__config_help__ = [{
    'name': 'host',
    'help': 'relay host/ip[:port]',
    'type': 'str',
    'required': False
}]

__get_help__ = []
__set_help__ = []
__help__ = """
PHI for SR-201 relay,

This is universal PHI which means one PHI can control either one or multiple
relays of the same type if relay config (host) is provided in unit driver
configuration.

host should be specified either in driver primary configuration or in each unit
configuration which uses the driver with this PHI.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

from eva.tools import parse_host_port

import socket

from eva.uc.driverapi import phi_constructor


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.port_max = 8
        self.relay_host, self.relay_port = parse_host_port(
            self.phi_cfg.get('host'), 6722)

    def get(self, port=None, cfg=None, timeout=0):
        if cfg:
            relay_host, relay_port = parse_host_port(cfg.get('host'), 6722)
        else:
            relay_host = None
        if not relay_host:
            relay_host = self.relay_host
            relay_port = self.relay_port
        if not relay_host:
            self.log_error('no host specified')
            return None
        server = (relay_host, relay_port)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            try:
                sock.connect(server)
                sock.send('00'.encode())
                res = sock.recv(8).decode()
                sock.close()
            except:
                sock.close()
                raise
            if len(res) < 8: raise Exception('bad data received')
            result = {}
            for i in range(8):
                result[str(i + 1)] = int(res[i])
            return result
        except:
            log_traceback()
            return None

    def set(self, port=None, data=None, cfg=None, timeout=0):
        try:
            _port = int(port)
        except:
            return False
        try:
            _data = int(data)
        except:
            return False
        if cfg:
            relay_host, relay_port = parse_host_port(cfg.get('host'), 6722)
        else:
            relay_host = None
        if not relay_host:
            relay_host = self.relay_host
            relay_port = self.relay_port
        if not relay_host:
            self.log_error('no host specified')
            return False
        if _port < 0 or _port > self.port_max:
            self.log_error('port not in range 1..%s' % _port)
            return False
        if _data == 0: _dts = 2
        else: _dts = 1
        server = (relay_host, relay_port)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            try:
                sock.connect(server)
                sock.send(('%s%s' % (_dts, _port)).encode())
                result = sock.recv(8).decode()
                sock.close()
            except:
                sock.close()
                raise
            if result[_port - 1] != str(_data): return False
        except:
            log_traceback()
            return False
        return True

    def test(self, cmd=None):
        if cmd == 'self' and self.relay_host is None: return 'OK'
        if cmd == 'get' or cmd == 'self':
            result = self.get(timeout=get_timeout())
            if cmd == 'self':
                return 'OK' if result else 'FAILED'
            return result if result else 'FAILED'
        return {'get': 'returns current relay state'}
