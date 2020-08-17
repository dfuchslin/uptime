#! /usr/bin/env python3

import sys, os
import time
from lib.reporter import CurlTimeReporter

def get_env_var(name, default):
    if name in os.environ:
        return os.environ[name]
    return default

def main(argv):
    if len(argv) < 2:
        print("python ./uptime.py [url]")
        sys.exit(2)

    config = {}
    config['url'] = argv[1]
    config['graphite_metric_prefix'] = get_env_var("GRAPHITE_METRIC_PREFIX", "uptime")
    config['graphite_host'] = get_env_var("GRAPHITE_HOST", "graphite")
    config['graphite_port'] = int(get_env_var("GRAPHITE_PORT", "2003"))
    config['timeout'] = int(get_env_var("TIMEOUT", "30"))
    config['check_interval'] = int(get_env_var("CHECK_INTERVAL", "5"))
    config['user_agent'] = get_env_var("USER_AGENT", "Mozilla/5.0 (X11; Linux i686 on x86_64; rv:10.0)")
    config['headers'] = {}

    if get_env_var("USE_GZIP", "true").lower() == "true":
        config['headers'] = { "accept-encoding": "gzip, deflate" }

    reporter = CurlTimeReporter(config)

    while(True):
        reporter.send_stats(reporter.get_url_stats())
        time.sleep(config['check_interval'])

main(sys.argv)
