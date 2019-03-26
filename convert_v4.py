#!/usr/bin/env python3

import sys

data = open(sys.argv[1]).readlines()
result = []

i = 0
while True:
    l = data[i]
    if l.startswith('class PHI('):
        if result[-1] != '\n':
            result.append('\n')
        result.append('from eva.uc.driverapi import phi_constructor\n')
        result.append('\n')
    if l.startswith('__api__'):
        api_ver = int(l.split('=')[1].strip())
        if api_ver >= 4:
            print('{}: API version is {}, conversion not required'.format(
                sys.argv[1], api_ver))
            exit()
        result.append('__api__ = 4\n')
    elif l.startswith('__id__'):
        i += 1
    elif l.startswith('__version__'):
        ver = l.split('=')[1].strip().replace('"', '')
        major, minor, release = ver.split('.')
        minor = int(minor) + 1
        result.append('__version__ = "{}.{}.{}"\n'.format(
            major, minor, release))
    elif l.find('__init__(self,') != -1:
        indent = len(l) - len(l.lstrip())
        result.append(' ' * indent + '@phi_constructor\n')
        result.append(' ' * indent + 'def __init__(self, **kwargs):\n')
        while data[i].find('if info_only') == -1:
            i += 1
            if data[i].strip() == 'return':
                i += 1
    else:
        result.append(l)

    i += 1
    if i >= len(data): break

content = ''.join(result)
if len(sys.argv) > 2 and sys.argv[2] == 'i':
    print("{} - converted".format(sys.argv[1]))
    open(sys.argv[1], 'w').write(content)
else:
    print(content)
