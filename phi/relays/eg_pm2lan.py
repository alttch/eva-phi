__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.1.4"
__description__ = "EG-PM2-LAN smart PDU"

__api__ = 5
__required__ = ['aao_get', 'port_set', 'status', 'action']
__mods_required__ = []
__lpi_default__ = 'basic'
__equipment__ = 'EG-PM2-LAN'
__features__ = ['cache']

__config_help__ = [{
    'name': 'host',
    'help': 'device ip/host[:port]',
    'type': 'str',
    'required': True
}, {
    'name': 'pw',
    'help': 'device password',
    'type': 'str',
    'required': True,
}, {
    'name': 'skip_logout',
    'help': 'skip logout after command',
    'type': 'bool',
    'required': False
}]
__get_help__ = []
__set_help__ = []

__help__ = """
PHI for Energenie (Gembird) EG-PM2-LAN smart PDU. You may use 'skip_logout'
param to let PHI skip logout procedure after the requests. This speed up the
functions however may cause the equipment to be locked to UC IP only.
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import handle_phi_event
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

from eva.tools import val_to_boolean

import requests
import re
import threading

from time import time

from eva.uc.driverapi import phi_constructor


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.host = self.phi_cfg.get('host')
        self.pw = self.phi_cfg.get('pw')
        # set logout='skip' to speed up the operations
        # but keep device bound to UC ip address
        self.skip_logout = val_to_boolean(self.phi_cfg.get('skip_logout'))
        self.re_ss = re.compile('sockstates = \[([01,]+)\]')
        if not self.host or not self.pw:
            self.ready = False
        self.lock = threading.Lock()

    def _login(self, timeout):
        r = requests.post(
            'http://%s/login.html' % self.host,
            data={'pw': self.pw},
            timeout=timeout)
        if r.status_code != 200:
            raise Exception('remote http code %s' % r.status_code)
        return r.text

    def _logout(self, timeout):
        return requests.get('http://%s/login.html' % self.host, timeout=timeout)

    def _parse_response(self, data):
        m = re.search(self.re_ss, data)
        if not m:
            raise Exception('sockstats not found')
        data = m.group(1).split(',')
        result = {}
        if len(data) != 4:
            raise Exception('bad sockstats data')
        for i in range(0, 4):
            result[str(i + 1)] = int(data[i])
        self.set_cached_state(result)
        return result

    def get_ports(self):
        return self.generate_port_list(
            port_max=4, description='power socket #{}')

    def get(self, port=None, cfg=None, timeout=0):
        # trying to get cached state before
        state = self.get_cached_state()
        if state is not None:
            return state
        t_start = time()
        if not self.lock.acquire(int(timeout)):
            return None
        logged_in = False
        try:
            res = self._login(timeout=(t_start - time() + timeout))
            result = self._parse_response(res)
            try:
                if not self.skip_logout:
                    self._logout(timeout=(t_start - time() + timeout))
            except:
                log_traceback()
                pass
            self.lock.release()
            return result
        except:
            try:
                if not self.skip_logout:
                    self._logout(timeout=(t_start - time() + timeout))
            except:
                log_traceback()
            self.lock.release()
            log_traceback()
            return None

    def set(self, port=None, data=None, cfg=None, timeout=0):
        if not port or data is None: return False
        t_start = time()
        try:
            socket = int(port)
        except:
            return False
        if not self.lock.acquire(int(timeout)):
            return False
        try:
            self._login(timeout=(t_start - time() + timeout))
            self.clear_cache()
            r = requests.post(
                'http://%s/status.html?sn=%u' % (self.host, socket),
                data={"cte%u" % socket: data},
                timeout=(t_start - time() + timeout))
            if r.status_code != 200:
                raise Exception(
                    'remote http code %s on port set' % r.status_code)
            # the remote doesn't return any errors, so just check the socket
            result = self._parse_response(r.text)
            if result.get(str(port)) != data:
                raise Exception('port %s set failed' % port)
            try:
                if not self.skip_logout:
                    self._logout(timeout=(t_start - time() + timeout))
            except:
                log_traceback()
                pass
            self.lock.release()
            return True
        except:
            try:
                if not self.skip_logout:
                    self._logout(timeout=(t_start - time() + timeout))
            except:
                log_traceback()
                pass
            self.lock.release()
            log_traceback()
            return False

    def test(self, cmd=None):
        if cmd == 'get' or cmd == 'self':
            result = self.get(timeout=get_timeout())
            if cmd == 'self':
                return 'OK' if result else 'FAILED'
            return result
        return {'get': 'get socket status'}
