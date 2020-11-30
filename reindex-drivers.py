#!/usr/bin/env python3

import glob
import os
import sys
import json

sys.path.append('phi')

mods = []

eva_version = {
    1: '3.1.0',
    2: '3.1.1',
    3: '3.1.2',
    4: '3.2.0',
    5: '3.2.2',
    6: '3.2.3',
    7: '3.2.4',
    8: '3.3.0',
    9: '3.3.1',
    10: '3.3.2'
}

files = sorted(os.popen('find ./phi -name "*.py"').readlines())
for f in files:
    x = f.split('/')
    mod = x[-1].strip()[:-3]
    cat = '/'.join(x[2:-1])
    code = ''
    with open(f.strip()) as m:
        s = True
        while s is not None:
            s = m.readline()
            if s[:5] == 'class':
                break
            code += s
    d = {}
    try:
        exec(code, d)
    except:
        pass
    module = {}
    module['uri'] = '/'.join(x[1:]).strip()
    module['category'] = cat
    module['name'] = os.path.basename(f.strip()).split('.')[0]
    module['version'] = d.get('__version__')
    module['description'] = d.get('__description__')
    equipment = d.get('__equipment__')
    if isinstance(equipment, list):
        equipment = ', '.join(equipment)
    module['equipment'] = equipment
    module['api'] = d.get('__api__')
    module['eva_version'] = eva_version[module['api']]
    module['author'] = d.get('__author__')
    module['license'] = d.get('__license__')
    mods.append(module)

mods = sorted(sorted(mods, key=lambda k: k['name']),
              key=lambda k: k['category'])

open('drivers.json', 'w').write(json.dumps(mods))
print('OK')
