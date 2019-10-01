__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2019 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
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

    def get(self, port=None, cfg=None, timeout=0):

        def ping(host, timeout=1000, count=1):
            return os.system('fping -t {} -c {} {}'.format(
                timeout, count, host)) == 0

        try:
            if self.url:
                url = self.url.format(port=port)
                r = requests.get(url, timeout=self.timeout)
                if not r.ok:
                    return None
                if self.response:
                    if self.response.startswith('sha256:'):
                        h = hashlib.sha256(r.content).hexdigest()
                        hr = self.response[7:]
                        self.log_debug('{} sha256: {}, required: {}'.format(
                            url, h, hr))
                        return 1 if h == hr else None
                    else:
                        return 1 if self.response == r.text else None
                else:
                    return 1
            else:
                return 1 if ping(port, timeout=self.timeout * 1000) else None
        except:
            log_traceback()
            return None

    def test(self, cmd=None):
        if cmd == 'self':
            return 'OK'
        else:
            return {'-': 'Dummy self test only'}
