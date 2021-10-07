__author__ = 'Altertech, https://www.altertech.com/'
__copyright__ = 'Altertech'
__license__ = 'GNU GPL v3'
__version__ = '1.2.4'
__description__ = 'Ethernet/IP units generic'
__api__ = 9
__required__ = ['port_get', 'port_set', 'action']
__mods_required__ = ''
__lpi_default__ = 'basic'
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
    'name': 'taglist',
    'help': 'Ethernet/IP tag list file',
    'type': 'str',
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

Tag list file: text file with one tag per line. Should be specified for bulk
updates.

In case of problems, it's highly recommended to specify tag variable type, as
TAG:TYPE. Valid types are:

REAL, SINT, USINT, INT, UINT, DINT, UDINT, BOOL, WORD, DWORD, IPADDR, STRING,
SSTRING

Tag types can be specified either in the tag list file (if defined) or as
type (_type) in the unit driver configuration.

If timeout it specified, it MUST be small enough, otherwise PHI will
not even try to connect to En/IP equipment (default is core timeout - 2 sec).

Arrays: specify port as TAG[x] for a single value or TAG[x-y] for the value
range (will be get/set as a list, splitted with commas)

For bit-set operations requires bitman (https://github.com/alttch/bitman)
executable to be put in EVA ICS runtime dir. Ports should have format
TAG[bit-index].
"""

import os, subprocess

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback, get_timeout, phi_constructor
from eva.exceptions import InvalidParameter
from eva.core import dir_runtime


class PHI(GenericPHI):

    @staticmethod
    def _parse_tag(tag):
        if ':' in tag:
            tag, tt = tag.rsplit(':', 1)
            if '[' in tt:
                tt, sfx = tt.split('[', 1)
                tag = tag + '[' + sfx
            return tag, tt
        else:
            return tag, None

    @phi_constructor
    def __init__(self, **kwargs):

        def _get_timeout():
            t = (get_timeout() - 1) / 2
            return t if t > 0 else 1

        xkv = {}
        self.bitman = [f'{dir_runtime}/bitman']
        if self.phi_cfg.get('simple'):
            xkv['route_path'] = False
            xkv['send_path'] = ''
        else:
            route_path = self.phi_cfg.get('route_path')
            xkv['route_path'] = route_path
            if route_path:
                self.bitman.append(xkv['route_path'].replace('/', ','))
            xkv['send_path'] = self.phi_cfg.get('send_path')
        from eva.uc.drivers.tools.cpppo_enip import SafeProxy
        host = self.phi_cfg.get('host')
        port = self.phi_cfg.get('port')
        self.proxy = SafeProxy(host=host,
                               port=port,
                               timeout=self.phi_cfg.get('timeout',
                                                        _get_timeout()),
                               **xkv)
        self.bitman.append(f'{host}:{port}')
        self.tags = []
        self.tag_types = {}
        self.fp = self.phi_cfg.get('fp')
        if self.phi_cfg.get('xv'):
            self._has_feature.value = True
            self._is_required.value = True
        if 'taglist' in self.phi_cfg:
            try:
                with open(self.phi_cfg.get('taglist')) as fh:
                    for tag in fh.readlines():
                        tag = tag.strip()
                        if tag:
                            tag, tag_type = self._parse_tag(tag)
                            self.tags.append(tag)
                            if tag_type:
                                self.tag_types[tag] = tag_type
            except:
                log_traceback()
                self.ready = False

    def get(self, port=None, cfg=None, timeout=0):
        try:
            result = {}
            if port:
                ttg = [self._parse_tag(port)[0]]
            else:
                ttg = self.tags
            if not ttg:
                return None
            data = self.proxy.operate('read', ttg)
            for i, v in enumerate(data):
                try:
                    if v is not None:
                        if self._has_feature.value:
                            values = []
                            for val in v if isinstance(v, list) else [v]:
                                try:
                                    values.append(round(val, self.fp))
                                except:
                                    values.append(val)
                            value = ','.join([str(val) for val in values])
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

    def set(self, port=None, data=None, cfg=None, timeout=0):
        try:
            ops = []
            bitman_ops = []
            for p, v in zip(port if isinstance(port, list) else [port],
                            data if isinstance(data, list) else [data]):
                tp = cfg.get('type') if cfg else None
                if not tp:
                    tp = self.tag_types.get(p)
                if tp == 'BOOL':
                    if p.endswith(']'):
                        tag, bit = p.rsplit('[', 1)
                        bit = bit[:-1]
                    else:
                        tag = p
                        bit = '0'
                    val = v[1] if isinstance(v, tuple) or isinstance(
                        v, list) else v
                    bitman_ops.append([tag, bit, val])
                else:
                    op = f'{port}='
                    if tp:
                        op += f'({tp.upper()})'
                    op += str(v[1]) if isinstance(v, tuple) or isinstance(
                        v, list) else str(v)
                    ops.append(op)
            success = True
            if ops:
                self.log_debug(f'EnIP OP {" ".join(ops)}')
                result = self.proxy.operate('write', ops)
                for op, r in zip(ops, result):
                    if r is not True:
                        self.log_error(f'tag set {op} error')
                        success = False
            if bitman_ops:
                for op in bitman_ops:
                    args = self.bitman + op + ['--timeout', str(timeout)]
                    self.log_debug(f'executing {" ".join(args)}')
                    p = subprocess.run(args,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
                    if p.returncode != 0:
                        self.log_error(p.stderr)
                        success = False
            return success
        except:
            log_traceback()
            return False

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
