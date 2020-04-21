__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.2"
__description__ = "Network watchdog"

__api__ = 5
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'sensor'
__equipment__ = 'NET-IP'
__features__ = []
__config_help__ = [{
    'name': 'url',
    'help': 'HTTP requst URL',
    'type': 'url',
    'required': False
}, {
    'name': 'response',
    'help': 'HTTP response',
    'type': 'str',
    'required': False
}, {
    'name': 'retries',
    'help': 'retries (default: 2)',
    'type': 'int',
    'required': False
}, {
    'name': 'timeout',
    'help': 'timeout (in seconds)',
    'type': 'int',
    'required': False
}]
__get_help__ = []
__set_help__ = []

__help__ = """
Network watchdog. Monitors hosts with ping (requires fping tool). If "url"
parameter is used, monitors hosts with HTTP request. If response is used,
compares HTTP response body.

When assigned to sensors, "port" must contain host name or IP address.

url: should be filled as https://{port}/...., where {port} is automatically
replaced with host name.

response: if response is in format "sha256:CHECKSUM", response checksum is
compared instead of response body.

timeout: default timeout is 1 second
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout

import os
import requests
import hashlib
import time

from eva.uc.driverapi import phi_constructor


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):
        self.url = self.phi_cfg.get('url')
        self.response = self.phi_cfg.get('response')
        try:
            self.timeout = float(self.phi_cfg.get('timeout', 1))
        except:
            self.log_error('Invalid timeout value')
            self.ready = False
            return
        try:
            self.tries = int(self.phi_cfg.get('retries', 2)) + 1
        except:
            self.log_error('Invalid retries value')
            self.ready = False

    def get(self, port=None, cfg=None, timeout=0):

        def ping(host, timeout=1000, count=1):
            return os.system('fping -t {} -c {} {}'.format(
                timeout, count, host)) == 0

        def check(port):
            if self.url:
                url = self.url.format(port=port)
                try:
                    r = requests.get(url, timeout=self.timeout)
                    if not r.ok:
                        raise Exception
                except:
                    return None
                if self.response:
                    if self.response.startswith('sha256:'):
                        h = hashlib.sha256(r.content).hexdigest()
                        hr = self.response[7:]
                        self.log_debug('{} sha256: {}, required: {}'.format(
                            url, h, hr))
                        return h == hr
                    else:
                        return self.response == r.text.strip()
                else:
                    return True
            else:
                return ping(port, timeout=self.timeout * 1000)

        try:
            t_start = time.time()
            for tr in range(0, self.tries):
                if t_start + timeout < time.time():
                    return None
                if check(port):
                    return 1
                time.sleep(self.timeout)
            return None
        except:
            log_traceback()
            return None

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        else:
            return {'-': 'Dummy self test only'}
