#! /usr/bin/env python3

import sys, os
import time
import logging
import yaml
import math
from lib.reporter import CurlTimeReporter

from pytz import utc

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor


def get_env_var(name, default):
    if name in os.environ:
        return os.environ[name]
    return default

def main(argv):
    if len(argv) < 2:
        logging.error("python ./uptime.py [path-to-config]")
        sys.exit(2)

    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    config = {}
    config_file = argv[1]
    with open(config_file) as file:
      logging.info('Loading configuration from %s' % config_file)
      config = yaml.load(file, Loader=yaml.SafeLoader)

    reporter = CurlTimeReporter(config)

    max_simultaneous_threads = 0
    for check in config['checks']:
        interval = int(check['interval'])
        max_simultaneous_threads += math.ceil(reporter.timeout / interval)
    logging.info("Configure scheduler for %d threads" % max_simultaneous_threads)

    executors = {
        'default': ThreadPoolExecutor(max_simultaneous_threads + 1),
        'processpool': ProcessPoolExecutor(max_simultaneous_threads)
    }
    job_defaults = {
        'coalesce': False,
        'max_instances': max_simultaneous_threads
    }
    scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults, timezone=utc)

    for check in config['checks']:
        host = check['host']
        path = check['path']
        interval = int(check['interval'])
        scheduler.add_job(reporter.analyze_url, 'interval', kwargs={'host':host, 'path':path}, seconds=interval)

    scheduler.start()

    while(True):
        time.sleep(1)

main(sys.argv)
