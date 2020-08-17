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
      config = yaml.full_load(file)

    for item, doc in config.items():
        print(item, ":", doc)

    reporter = CurlTimeReporter(config)

    while(True):
        reporter.analyze_url('https://gyttja.com', '/')
        time.sleep(5)

main(sys.argv)
