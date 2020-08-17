#! /usr/bin/env python3

import sys, os
import time
import logging
import yaml
from lib.reporter import CurlTimeReporter


def get_env_var(name, default):
    if name in os.environ:
        return os.environ[name]
    return default

def main(argv):
    if len(argv) < 2:
        logging.error("python ./uptime.py [url]")
        sys.exit(2)

    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    config = {}
    config_file = argv[1]
    with open(config_file) as file:
      logging.info('Loading configuration from %s' % config_file)
      config = yaml.load(file, Loader=yaml.FullLoader)

    reporter = CurlTimeReporter(config)

    # threadify this!
    while(True):
        for check in config['checks']:
          host = check['host']
          path = check['path']
          interval = int(check['interval'])
          reporter.analyze_url(host, path)
          time.sleep(interval)

main(sys.argv)
