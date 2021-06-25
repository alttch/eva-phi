__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "Modbus sensors generic"

__api__ = 10
__required__ = ['port_get', 'value']
__mods_required__ = []
__lpi_default__ = 'sensor'
__equipment__ = ['Modbus']
__features__ = []
__config_help__ = [{
    'name': 'port',
    'help': 'ModBus port ID',
    'type': 'str',
    'required': True
}, {
    'name': 'unit',
    'help': 'modbus unit ID',
    'type': 'int',
    'required': True
}, {
    'name': 'ttl',
    'help': 'bit cache TTL',
    'type': 'float',
    'default': 0.5,
    'required': True
}]
__get_help__ = []
__set_help__ = []

__help__ = """
Modbus sensors driver

Generic driver for Modbus sensor equipment.

When loaded, requires port = Modbus virtual port id and equipment Modbus unit
id.

When assigned to items, the following config parameters are used:

    port = Modbus register (c = coil, d = discrete, i = input, h = holding)

    For a single register bit, set port as <h|i><reg>/<offset>, e.g.  h1000/0
    for the 0th bit of holding register 1000. Such register values are cached
    for max "ttl" (default 0.5) seconds.

Optionally:
    _type = register type
    _multiply = value multiplier
    _divide = value divisor
    _round = round value to digits after comma

valid types: u16 (default for inputs and holdings), i16, u32, i32, u64, i64,
f32 (IEEE 754a 32-bit float)

coils are returned as integers (0/1)

E.g. assigning driver to sensor:

    driver assign sensor:tests/s1 <PHI_ID>.default -c port=h4,_type=u32,_divide=10,_round=2

will set PHI to sync 32-bit integer value from holding register 4 (+5,
big-endian), divide it by 10 and round to 2 digits after comma
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout
from eva.uc.driverapi import transform_value

from eva.uc.driverapi import phi_constructor

import eva.uc.drivers.tools.modbus as modbus

from cachetools import TTLCache

MAX_CACHE_SIZE = 8192


class PHI(GenericPHI):

    _getter_functions = {
        'u16': modbus.read_u16,
        'i16': modbus.read_i16,
        'u32': modbus.read_u32,
        'i32': modbus.read_i32,
        'u64': modbus.read_u64,
        'i64': modbus.read_i64,
        'f32': modbus.read_f32
    }

    @phi_constructor
    def __init__(self, **kwargs):
        self.modbus_port = self.phi_cfg.get('port')
        self.cache = TTLCache(maxsize=MAX_CACHE_SIZE,
                              ttl=self.phi_cfg.get('ttl'))
        if not modbus.is_port(self.modbus_port):
            self.log_error('modbus port ID not specified or invalid')
            self.ready = False
            return
        try:
            self.unit_id = int(self.phi_cfg.get('unit'))
        except:
            self.log_error('modbus unit ID not specified or invalid')
            self.ready = False
            return

    def get(self, port=None, cfg=None, timeout=0):
        try:
            modbus_port = modbus.get_port(self.modbus_port, timeout)
        except Exception as e:
            self.log_error(e)
            log_traceback()
            return None
        try:
            if port[0] in ['c', 'd']:
                return 1 if modbus.read_bool(
                    modbus_port, port, unit=self.unit_id)[0] else 0
            else:
                data_type = cfg.get('type', 'u16')
                try:
                    fn = self._getter_functions[data_type]
                except KeyError:
                    self.log_error(f'Invalid register data type: {data_type}')
                    raise
                if '/' in port:
                    reg, offset = port.split('/', 1)
                    offset = int(offset)
                    try:
                        b = self.cache[reg]
                    except KeyError:
                        b = fn(modbus_port, reg, unit=self.unit_id)[0]
                        self.cache[reg] = b
                    return b >> offset & 1
                else:
                    return str(
                        transform_value(fn(modbus_port, port,
                                           unit=self.unit_id)[0],
                                        multiply=cfg.get('multiply'),
                                        divide=cfg.get('divide'),
                                        round_to=cfg.get('round')))
        except:
            log_traceback()
            return None
        finally:
            modbus_port.release()

    def validate_config(self, config={}, config_type='config'):
        self.validate_config_whi(config=config, config_type=config_type)

    def test(self, cmd=None):
        if cmd == 'self':
            try:
                modbus_port = modbus.get_port(self.modbus_port, get_timeout())
                return 'OK'
            except Exception as e:
                self.log_error(e)
                log_traceback()
                return 'FAILED'
            finally:
                modbus_port.release()
        elif cmd == 'help':
            return {'reg[:type]': 'get register value'}
        else:
            cfg = {}
            tt = cmd.split(':')
            try:
                cfg['type'] = tt[1]
            except IndexError:
                pass
            return self.get(tt[0], cfg=cfg, timeout=get_timeout())
