#!/usr/bin/env python

from __future__ import absolute_import, print_function, unicode_literals

from os import environ
import subprocess
import sys
import time

from tornado import httpclient

RETRY_EVERY = 1  # seconds
RETRY_DURATION = 60  # seconds

KEEP_WAITING_STATII = (503,)  # if Solr returns one of these HTTP status codes, keep waiting for it

# if there's no default SOLR_VERSION set (by Travis-CI) then set it here
if 'SOLR_VERSION' not in environ:
    environ['SOLR_VERSION'] = '4.10.4'


def start_solr():
    solr_proc = subprocess.Popen("./start-solr-test-server.sh",
                                 stdout=open("test-solr.stdout.log", "wb"),
                                 stderr=open("test-solr.stderr.log", "wb"))

    solr_retries = 0
    print('Waiting for Solr to start...')

    while True:
        my_client = httpclient.HTTPClient()
        try:
            status_code = my_client.fetch("http://localhost:8983/solr/collection1/select/?q=startup?df=id").code
        except httpclient.HTTPError as err:
            if err.code not in KEEP_WAITING_STATII:
                print('Tornado reports an HTTP error while starting Solr: ({}) {}'.format(err.code, err.response.reason))
                solr_proc.terminate()
                solr_proc.wait()
                sys.exit(1)
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
            solr_proc.terminate()
            solr_proc.wait()
            sys.exit(1)

    print('Solr started! (waited {} seconds)'.format(solr_retries * RETRY_EVERY))

    return solr_proc


def main():
    solr_proc = start_solr()

    if sys.version_info >= (3, 3) or sys.version_info >= (2, 7):
        cmd = ['python', '-m', 'unittest', 'tests']
    else:
        cmd = ['unit2', 'discover', '-s', 'tests', '-p', '[a-z]*.py']

    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        raise SystemExit(1)
    finally:
        solr_proc.terminate()
        solr_proc.wait()

if __name__ == "__main__":
    main()
