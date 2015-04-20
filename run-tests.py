#!/usr/bin/env python

from __future__ import absolute_import, print_function, unicode_literals

import subprocess
import sys
import time

from tornado import httpclient

RETRY_EVERY = 1  # seconds
RETRY_DURATION = 60  # seconds


def start_solr():
    solr_proc = subprocess.Popen("./start-test-solr.sh",
                                 stdout=open("test-solr.stdout.log", "wb"),
                                 stderr=open("test-solr.stderr.log", "wb"))

    solr_retries = 0
    print('Waiting for Solr to start...')

    while True:
        my_client = httpclient.HTTPClient()
        try:
            status_code = my_client.fetch("http://localhost:8983/solr/core0/select/?q=startup").code
        except:
            status_code = 0
        finally:
            my_client.close()

        if status_code == 200:
            break
        elif (solr_retries * RETRY_EVERY) < RETRY_DURATION:
            solr_retries += 1
            time.sleep(RETRY_EVERY)
        else:
            print('Solr took too long to start ({} retries in {} seconds)'.format(solr_retries, RETRY_DURATION), file=sys.stderr)
            sys.exit(1)

    print('Solr started! (waited {} seconds)'.format(solr_retries * RETRY_EVERY))

    return solr_proc


def main():
    solr_proc = start_solr()

    if sys.version_info >= (3, 3):
        cmd = ['python', '-m', 'unittest', 'tests']
    elif sys.version_info >= (2, 7):
        cmd = ['python', '-m', 'unittest2', 'tests']
    else:
        cmd = ['unit2', 'discover', '-s', 'tests', '-p', '[a-z]*.py']

    try:
        subprocess.check_call(cmd)
    finally:
        solr_proc.terminate()
        solr_proc.wait()

if __name__ == "__main__":
    main()
