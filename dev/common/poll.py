#!/usr/bin/env python

# Poll the api until it is ready.

import json
import re
import requests
import subprocess
import time
import yaml

from json import JSONEncoder


class DynaConfEncoder(JSONEncoder):
    '''Special encoder for a dynaconf structure'''
    def default(self, o):
        if isinstance(o, PosixPath):
            return o.path
        return o.__dict__


class PosixPath:
    '''Evalable class for dynaconf posixpath thingies'''
    def __init__(self, path):
        self.path = path

    def toJSON(self):
        return self.path


def parse_dynaconf_list(rawtxt):
    '''Parse the magical dynaconf list output'''

    ds = {}

    # get rid of color codes ...
    rawtxt = rawtxt.replace('\x1b[37m\x1b[100m', '')
    rawtxt = rawtxt.replace('\x1b[97m\x1b[104m\x1b[1m', '')
    rawtxt = rawtxt.replace('\x1b[97m\x1b[45m', '')
    rawtxt = rawtxt.replace('\x1b[0m\x1b[97m\x1b[100m', '')
    rawtxt = rawtxt.replace('\x1b[0m', '')
    rawtxt = rawtxt.replace('Working in development environment', '')
    rawtxt = rawtxt.replace('Django app detected', '')

    # split all the key&vals
    lines = rawtxt.split('\n')
    bits = ['']
    for idx,x in enumerate(lines):
        if '<' in x and '>' in x:
            bits.append('')
        bits[-1]+= x

    # parse all the key&vals
    bits = [x.strip() for x in bits if x.strip()]
    for bit in bits:
        var_name = bit.split('<', 1)[0]
        var_type = bit.replace(var_name, '').split('>', 1)[0].replace('<', '')

        var_raw = bit.split('>', 1)[-1].strip()

        val = None
        if var_type in ['str']:
            val = var_raw.replace("'", '')
        elif var_type == 'NoneType':
            val = None
        elif var_type in ['int', 'list', 'bool', 'dict', 'PosixPath']:
            val = eval(var_raw)
        else:
            raise Exception(f'{var_name} is {var_type} which is not yet parseable')
        ds[var_name] = {
            'name': var_name,
            'type': var_type,
            'value': val
        }

    # force back to stdlib types
    ds = json.dumps(ds, cls=DynaConfEncoder)
    ds = json.loads(ds)

    return ds


def get_dynaconf_variable(varname):
    '''Run the dynaconf list command and get a specific key'''
    cmd = 'dynaconf list'
    cmd = f'./compose exec api bash -c "{cmd}"'
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = pid.stdout.decode('utf-8')
    parsed = parse_dynaconf_list(stdout)
    return parsed[varname]['value']


def get_compose_config():
    '''Get a dump of the running|aggregated compose config'''
    cmd = './compose config'
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = pid.stdout.decode('utf-8')
    config = yaml.safe_load(stdout)
    return config


def poll(attempts=100, wait_time=1):
    '''Wait for the API to report status or abnormal exit'''
    # get the compose config
    config = get_compose_config()

    # extract the api service
    api = config['services']['api']

    # get the api's env
    env = api['environment']

    # hostname includes the prefix
    hostname = env['PULP_ANSIBLE_API_HOSTNAME']

    for i in range(attempts):
        print(f"Waiting for API to start (attempt {i+1} of {attempts})")
        # re request the api root each time because it's not alwasy available until the
        # app boots
        api_root = get_dynaconf_variable("API_ROOT")
        url = f"{hostname}{api_root}api/v3/status/"
        print(f'\tenumerated url: {url}')
        try:
            rr = requests.get(url)
            print(f'\tresponse: {rr.status_code}')
            if rr.status_code == 200:
                print(f"{url} online after {(i * wait_time)} seconds")
                return
        except Exception as e:
            print(e)
            time.sleep(wait_time)

    raise Exception(f"polling the api service failed to complete in the allowed timeframe")


def main():
    poll()


if __name__ == "__main__":
    main()
