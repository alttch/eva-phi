__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "1.0.0"
__description__ = "Modbus sensors generic"

__api__ = 10
__required__ = ['port_get', 'port_set', 'action']
__mods_required__ = []
__lpi_default__ = 'basic'
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
}, {
    'name': 'xv',
    'help': 'Sync registers and unit values only',
    'type': 'bool',
    'required': False
}]
__get_help__ = []
__set_help__ = []

__help__ = """
Modbus unit driver

Generic driver for Modbus control equipment.

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

When action is executed, a value is divided/multiplied counterclockwise.

valid types: u16 (default for inputs and holdings), i16, u32, i32, u64, i64,
f32 (IEE 754a 32-bit float)

coils are returned/set as integers (0/1)

E.g. assigning driver to unit:

    driver assign unit:tests/u1 <PHI_ID>.default -c port=h2,_type=u32

will set PHI to sync 32-bit integer value from holding register 2 (+5,
big-endian)
"""

from eva.uc.drivers.phi.generic_phi import PHI as GenericPHI
from eva.uc.driverapi import log_traceback
from eva.uc.driverapi import get_timeout
from eva.uc.driverapi import transform_value
from eva.tools import val_to_boolean

from eva.uc.driverapi import phi_constructor

import eva.uc.drivers.tools.modbus as modbus

from cachetools import TTLCache

import threading

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

    _setter_functions = {
        'u16': modbus.write_u16,
        'i16': modbus.write_i16,
        'u32': modbus.write_u32,
        'i32': modbus.write_i32,
        'u64': modbus.write_u64,
        'i64': modbus.write_i64,
        'f32': modbus.write_f32
    }

    @phi_constructor
    def __init__(self, **kwargs):
        self.modbus_port = self.phi_cfg.get('port')
        self.cache = TTLCache(maxsize=MAX_CACHE_SIZE,
                              ttl=self.phi_cfg.get('ttl'))
        self.bitlock = threading.RLock()
        if self.phi_cfg.get('xv'):
            self._has_feature.value = True
            self._is_required.value = True
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
                result = 1 if modbus.read_bool(
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
                    result = b >> offset & 1
                else:
                    result = transform_value(fn(modbus_port,
                                                port,
                                                unit=self.unit_id)[0],
                                             multiply=cfg.get('multiply'),
                                             divide=cfg.get('divide'),
                                             round_to=cfg.get('round'))
            return (1, str(result)) if self._has_feature.value else int(result)
        except:
            log_traceback()
            return None
        finally:
            modbus_port.release()

    def set(self, port=None, data=None, cfg=None, timeout=0):
        value = data[1] if isinstance(data, tuple) else data
        try:
            modbus_port = modbus.get_port(self.modbus_port, timeout)
        except Exception as e:
            self.log_error(e)
            log_traceback()
            return None
        try:
            if port[0] in ['c', 'd']:
                modbus.write_bool(modbus_port, port, [value], unit=self.unit_id)
            else:
                data_type = cfg.get('type', 'u16')
                try:
                    fn_set = self._setter_functions[data_type]
                    value = float(value) if data_type == 'f32' else int(value)
                except KeyError:
                    self.log_error(f'Invalid register data type: {data_type}')
                    raise
                if '/' in port:
                    try:
                        fn_get = self._getter_functions[data_type]
                        value = float(value) if data_type == 'f32' else int(
                            value)
                    except KeyError:
                        self.log_error(
                            f'Invalid register data type: {data_type}')
                        raise
                    reg, offset = port.split('/', 1)
                    offset = int(offset)
                    with self.bitlock:
                        try:
                            b = self.cache[reg]
                        except KeyError:
                            b = fn_get(modbus_port, reg, unit=self.unit_id)[0]
                            self.cache[reg] = b
                        if val_to_boolean(value):
                            b = b | 1 << offset
                        else:
                            if b >> offset & 1:
                                b = b ^ 1 << offset
                        fn_set(modbus_port, reg, [b], unit=self.unit_id)
                else:
                    value = transform_value(value,
                                            multiply=cfg.get('divide'),
                                            divide=cfg.get('multiply'))
                    if data_type != 'f32':
                        value = int(value)
                    fn_set(modbus_port, port, [value], unit=self.unit_id)
            return True
        except:
            log_traceback()
            return False
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
