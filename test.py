import os
import sys
import glob

sys.path.append('/opt/eva/lib')
from eva.client.apiclient import APIClientLocal

for fname in glob.glob('/opt/eva-phi/phi/**/*.py', recursive=True):

    # os.system('/opt/eva-phi/convert_v4.py {} i'.format(fname))
    os.system('yapf -i --style google {}'.format(fname))

    mod = os.path.basename(fname).split('.')[0]

    content = open(fname).read()

    api = APIClientLocal('uc')

    code, result = api.call('put_phi_mod', {
        'm': mod,
        'c': content,
        'force': True
    })
    if code != 0:
        print(result)
        exit(1)

    code, result = api.call('modinfo_phi', {'m': mod})
    if code != 0:
        print(result)
        exit(1)

    if result.get('mod') != mod:
        print('no mod in result')
        exit(1)

    if not result.get('lpi_default'):
        print('no default LPI is set')
        exit(1)

    if result.get('description') == 'Generic PHI, don\'t use':
        print('serialize error')
        exit(1)

    code, result = api.call('unlink_phi_mod', {'m': mod})
    if code != 0:
        print(result)
        exit(1)
