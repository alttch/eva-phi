__author__ = 'Altertech, https://www.altertech.com/'
__copyright__ = 'Altertech'
__license__ = 'GNU GPL v3'
__version__ = '1.1.0'
__description__ = 'Ethernet/IP sensors generic'
__api__ = 9
__required__ = ['port_get', 'value']
__mods_required__ = ''
__lpi_default__ = 'sensor'
__equipment__ = ['Ethernet/IP']
__features__ = ['aao_get']
__config_help__ = [{
    'name': 'host',
    'help': 'Ethernet/IP controller host',
    'type': 'str',
    'required': True
}, {
    'name': 'port',
    'help': 'Ethernet/IP controller port',
    'type': 'int',
    'default': 44818,
    'required': True
}, {
    'name': 'simple',
    'help': 'Disable route/send path',
    'type': 'bool',
    'required': False
}, {
    'name': 'timeout',
    'help': 'Timeout',
    'type': 'int',
    'required': False
}, {
    'name': 'route_path',
    'help': 'Route path (X/Y, e.g. 1/0)',
    'type': 'str',
    'required': False
}, {
    'name': 'send_path',
    'help': 'Send path (@X/Y, e.g. @6/1)',
    'type': 'str',
    'required': False
}, {
    'name': 'taglist',
    'help': 'Ethernet/IP tag list file',
    'type': 'str',
    'required': False
}, {
    'name': 'fp',
    'help': 'Float precision',
    'type': 'int',
    'default': 4,
    'required': True
}]
__get_help__ = []
__set_help__ = []

__help__ = """
Ethernet/IP sensors driver

If timeout it specified, it MUST be small enough, otherwise PHI will
not even try to connect to En/IP equipment (default is core timeout - 2 sec).

Tag list file: text file with one tag per line. Should be specified for bulk
updates.
"""

import os

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback, get_timeout, phi_constructor
from eva.exceptions import InvalidParameter


class PHI(GenericPHI):

    @phi_constructor
    def __init__(self, **kwargs):

        def _get_timeout():
            t = get_timeout() - 2
            return t if t > 0 else 1

        xkv = {}
        if self.phi_cfg.get('simple'):
            xkv['route_path'] = False
            xkv['send_path'] = ''
        else:
            xkv['route_path'] = self.phi_cfg.get('route_path')
            xkv['send_path'] = self.phi_cfg.get('send_path')
        from eva.uc.drivers.tools.cpppo_enip import SafeProxy
        self.proxy = SafeProxy(host=self.phi_cfg.get('host'),
                               port=self.phi_cfg.get('port'),
                               timeout=self.phi_cfg.get('timeout',
                                                        _get_timeout()),
                               **xkv)
        self.tags = []
        self.fp = self.phi_cfg.get('fp')
        if 'taglist' in self.phi_cfg:
            try:
                with open(self.phi_cfg.get('taglist')) as fh:
                    for tag in fh.readlines():
                        tag = tag.strip()
                        if tag:
                            self.tags.append(tag.rsplit(':', 1)[0])
            except:
                log_traceback()
                self.ready = False

    def get(self, port=None, cfg=None, timeout=0):
        try:
            result = {}
            if port:
                port = port.rsplit(':', 1)[0]
                ttg = [port]
            else:
                ttg = self.tags
            if not ttg:
                return None
            data = self.proxy.operate('read', ttg)
            for i, v in enumerate(data):
                if v is not None:
                    try:
                        value = round(v[0], self.fp)
                    except:
                        value = v[0]
                    result[ttg[i]] = str(value)
                else:
                    self.log_error(f'Unable to read {ttg[i]}')
            if not result:
                return None
            elif port:
                return result[port]
            else:
                return result
        except:
            log_traceback()
            return None

    def get_ports(self):
        return [{
            'port': tag,
            'name': tag,
            'description': ''
        } for tag in self.tags]

    def validate_config(self, config={}, config_type='config'):
        self.validate_config_whi(config=config, config_type=config_type)
        if 'taglist' in config and not os.path.isfile(config['taglist']):
            raise InvalidParameter('taglist file not found')

    def test(self, cmd=None):
        if cmd == 'self':
            try:
                identity = self.proxy.operate('list_identity')
                return 'OK'
            except:
                log_traceback()
                return 'FAILED'
        elif cmd == 'info':
            identity = self.proxy.operate('list_identity')
            return {
                'product_name': str(identity.get('product_name')),
                'serial_number': str(identity.get('serial_number'))
            }
        elif cmd == 'get':
            if self.tags:
                return self.get(timeout=get_timeout())
            else:
                return 'tag list not specified'
        elif cmd == 'help':
            return {
                'info': 'get equpment identity',
                'get': 'get all tags',
                '<TAG>': 'get tag value'
            }
        else:
            return self.get(port=cmd, timeout=get_timeout())
