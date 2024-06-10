#!/usr/bin/env python

# Poll the api until it is ready.

import requests
import subprocess
import sys
import time
import yaml


def get_dynaconf_variable(varname):
    '''Run the dynaconf get subcommand for a specific key'''
    cmd = f'dynaconf get {varname}'
    cmd = f'./compose exec -T api bash -c "{cmd}"'
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if pid.returncode != 0:
        print(f'ERROR: {pid.stderr.decode("utf-8")}')
        return None
    stdout = pid.stdout.decode('utf-8')
    return stdout.strip()


def get_compose_config():
    '''Get a dump of the running|aggregated compose config'''
    cmd = './compose config'
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = pid.stdout.decode('utf-8')
    config = yaml.safe_load(stdout)
    return config


def poll(url=None, attempts=100, wait_time=1):
    '''Wait for the API to report status or abnormal exit'''

    if url is None:

        # get the compose config
        config = get_compose_config()

        # extract the api service
        api = config['services']['api']

        # get the api's env
        env = api['environment']

        # hostname includes the prefix
        hostname = env['PULP_ANSIBLE_API_HOSTNAME']

    for i in range(attempts):
        print(f"Waiting for API to start (attempt {i + 1} of {attempts})")
        # re request the api root each time because it's not alwasy available until the
        # app boots

        if url is not None:
            this_url = url
        else:
            print(f'\tHOSTNAME: {hostname}')
            api_root = get_dynaconf_variable("API_ROOT")
            print(f'\tAPI_ROOT: {api_root}')
            if api_root is None:
                print('\tAPI_ROOT is null')
                time.sleep(wait_time)
                continue

            this_url = f"{hostname}{api_root}api/v3/status/"

        print(f'\tURL: {this_url}')
        try:
            rr = requests.get(this_url)
            print(f'\tresponse: {rr.status_code}')
            if rr.status_code == 200:
                print(f"{this_url} online after {(i * wait_time)} seconds")
                return
        except Exception as e:
            print(e)
            time.sleep(wait_time)

    raise Exception("polling the api service failed to complete in the allowed timeframe")


def main():
    url = None
    if len(sys.argv) > 1:
        url = sys.argv[1]
    poll(url=url)


if __name__ == "__main__":
    main()
