__author__ = 'Altertech, https://www.altertech.com/'
__copyright__ = 'Altertech'
__license__ = 'GNU GPL v3'
__version__ = '1.0.1'
__description__ = 'Ethernet/IP units generic'
__api__ = 9
__required__ = ['port_get', 'port_set', 'action']
__mods_required__ = ''
__lpi_default__ = 'basic'
__equipment__ = ['Ethernet/IP']
__features__ = ['aao_get', 'aao_set']
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
}, {
    'name': 'xv',
    'help': 'Sync tags and unit values only',
    'type': 'bool',
    'required': False
}]
__get_help__ = []
__set_help__ = []

__help__ = """
Ethernet/IP units driver

Tag list file: text file with one tag per line

In case of problems, it's highly recommended to specify tag variable type, as
TAG:TYPE. Valid types are:

REAL, SINT, USINT, INT, UINT, DINT, UDINT, BOOL, WORD, DWORD, IPADDR, STRING,
SSTRING

If timeout it specified, it MUST be small enough, otherwise PHI will
not even try to connect to En/IP equipment (default is core timeout - 2 sec).
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
        from eva.uc.drivers.tools.cpppo_enip import SafeProxy
        self.proxy = SafeProxy(host=self.phi_cfg.get('host'),
                               port=self.phi_cfg.get('port'),
                               timeout=self.phi_cfg.get('timeout',
                                                        _get_timeout()),
                               **xkv)
        self.tags = []
        self.tags_t = {}
        self.fp = self.phi_cfg.get('fp')
        if self.phi_cfg.get('xv'):
            self._has_feature.value = True
            self._is_required.value = True
        try:
            with open(self.phi_cfg.get('taglist')) as fh:
                for tag in fh.readlines():
                    tag = tag.strip()
                    if tag:
                        tt = tag.rsplit(':', 1)
                        if len(tt) < 2:
                            tt.append(None)
                        self.tags.append(tt[0])
                        self.tags_t[tt[0]] = tt[1]
        except:
            log_traceback()
            self.ready = False

    def set(self, port=None, data=None, cfg=None, timeout=0):
        try:
            ops = []
            for p, v in zip(port if isinstance(port, list) else [port],
                            data if isinstance(data, list) else [data]):
                op = f'{p}='
                tp = self.tags_t.get(p)
                if tp:
                    op += f'({tp})'
                op += str(v[1]) if self._has_feature.value else str(v)
                ops.append(op)
            self.log_debug(f'EnIP OP {" ".join(ops)}')
            result = self.proxy.operate('write', ops)
            success = True
            for op, r in zip(ops, result):
                if r is not True:
                    self.log_error(f'tag set {op} error')
                    success = False
            return success
        except:
            log_traceback()
            return False

    def get(self, port=None, cfg=None, timeout=0):
        try:
            result = {}
            ttg = [port] if port else self.tags
            if not ttg:
                return None
            data = self.proxy.operate('read', ttg)
            for i, v in enumerate(data):
                try:
                    if v is not None:
                        if self._has_feature.value:
                            try:
                                value = round(v[0], self.fp)
                            except:
                                value = v[0]
                        else:
                            value = v[0]
                        result[ttg[i]] = (1, str(
                            value)) if self._has_feature.value else int(value)
                    else:
                        raise Exception
                except:
                    self.log_error(f'Unable to read {ttg[i]}')
                    log_traceback()
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
        try:
            if not os.path.isfile(config['taglist']):
                raise InvalidParameter('taglist file not found')
        except KeyError:
            raise InvalidParameter('taglist file not specified')

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
            return self.get(timeout=get_timeout())
        elif cmd == 'help':
            return {
                'info': 'get equpment identity',
                'get': 'get all tags',
                '<TAG>': 'get/set tag opts (<TAG>=<VALUE> for set)'
            }
        else:
            if '=' in cmd:
                ops = cmd.split(',')
                ports = []
                data = []
                for o in ops:
                    p, v = o.split('=', 1)
                    ports.append(p)
                    data.append(v)
                return 'OK' if self.set(
                    port=ports, data=data, timeout=get_timeout()) else 'FAILED'
            else:
                return self.get(port=cmd, timeout=get_timeout())
