#! /usr/bin/env python3

import pycurl
from urllib.parse import urlparse
import sys, getopt, os
import socket
import time
try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

def get_env_var(name, default):
    if name in os.environ:
        return os.environ[name]
    return default

def calc_diff(current, running_response_time):
    if current - running_response_time < 0.0:
        return 0
    return current - running_response_time

def get_url_stats(config):
    url = config['url']
    timestamp = int(time.time())
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(pycurl.USERAGENT, config['user_agent'])
    c.setopt(c.TIMEOUT, config['timeout'])
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    if len(config['headers']) > 0:
      c.setopt(c.HTTPHEADER, [ k+': '+v for k,v in config['headers'].items() ])

    stats = {}
    stats["timedout"] = 0
    stats["error"] = 0

    try:
        c.perform()
    except Exception as e:
        if e.args[0] == c.E_OPERATION_TIMEDOUT:
            stats["timedout"] = 1
        else:
            print(e)
            stats["error"] = 1

    # deprecate these
    stats["namelookuptime"] = c.getinfo(c.NAMELOOKUP_TIME)
    stats["connecttime"] = c.getinfo(c.CONNECT_TIME)
    stats["appconnecttime"] = c.getinfo(c.APPCONNECT_TIME)
    stats["pretransfertime"] = c.getinfo(c.PRETRANSFER_TIME)
    stats["starttransfertime"] = c.getinfo(c.STARTTRANSFER_TIME)
    stats["responsetime"] = c.getinfo(c.TOTAL_TIME)
    stats["redirecttime"] = c.getinfo(c.REDIRECT_TIME)

    # calculate diffs
    running_response_time = 0.0

    stats["time.namelookup.reported"] = c.getinfo(c.NAMELOOKUP_TIME)
    stats["time.namelookup.diff"] = calc_diff(c.getinfo(c.NAMELOOKUP_TIME), running_response_time)
    running_response_time += stats["time.namelookup.diff"]

    stats["time.connect.reported"] = c.getinfo(c.CONNECT_TIME)
    stats["time.connect.diff"] = calc_diff(c.getinfo(c.CONNECT_TIME), running_response_time)
    running_response_time += stats["time.connect.diff"]

    stats["time.appconnect.reported"] = c.getinfo(c.APPCONNECT_TIME)
    stats["time.appconnect.diff"] = calc_diff(c.getinfo(c.APPCONNECT_TIME), running_response_time)
    running_response_time += stats["time.appconnect.diff"]

    stats["time.pretransfer.reported"] = c.getinfo(c.PRETRANSFER_TIME)
    stats["time.pretransfer.diff"] = calc_diff(c.getinfo(c.PRETRANSFER_TIME), running_response_time)
    running_response_time += stats["time.pretransfer.diff"]

    stats["time.starttransfer.reported"] = c.getinfo(c.STARTTRANSFER_TIME)
    stats["time.starttransfer.diff"] = calc_diff(c.getinfo(c.STARTTRANSFER_TIME), running_response_time)
    running_response_time += stats["time.starttransfer.diff"]

    stats["time.redirect.reported"] = c.getinfo(c.REDIRECT_TIME)
    stats["time.redirect.diff"] = calc_diff(c.getinfo(c.REDIRECT_TIME), running_response_time)
    running_response_time += stats["time.redirect.diff"]

    stats["time.total.reported"] = c.getinfo(c.TOTAL_TIME)
    stats["time.total.diff"] = calc_diff(c.getinfo(c.TOTAL_TIME), running_response_time)
    running_response_time += stats["time.total.diff"]

    stats["responsecode"] = c.getinfo(c.RESPONSE_CODE)
    stats["downloadbytes"] = c.getinfo(c.SIZE_DOWNLOAD)
    stats["timestamp"] = timestamp
    stats["url"] = url

    c.close()

    return stats

def build_message(stat, datatype, graphite_path, stats):
    return (("{}.{} {:" + datatype + "} {:d}\n").format(graphite_path, stat, stats[stat], stats["timestamp"]))

def build_graphite_friendly_url(url):
  return url.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_").replace("&", "_").replace(".", "_")

def send_stats(stats, config):
    graphite_path = "{}.{}".format(config['graphite_metric_prefix'], build_graphite_friendly_url(stats["url"]))

    # deprecate these
    send_single_status(build_message("namelookuptime", "f", graphite_path, stats), config)
    send_single_status(build_message("connecttime", "f", graphite_path, stats), config)
    send_single_status(build_message("appconnecttime", "f", graphite_path, stats), config)
    send_single_status(build_message("pretransfertime", "f", graphite_path, stats), config)
    send_single_status(build_message("starttransfertime", "f", graphite_path, stats), config)
    send_single_status(build_message("redirecttime", "f", graphite_path, stats), config)
    send_single_status(build_message("responsetime", "f", graphite_path, stats), config)

    send_single_status(build_message("time.namelookup.reported", "f", graphite_path, stats), config)
    send_single_status(build_message("time.namelookup.diff", "f", graphite_path, stats), config)
    send_single_status(build_message("time.connect.reported", "f", graphite_path, stats), config)
    send_single_status(build_message("time.connect.diff", "f", graphite_path, stats), config)
    send_single_status(build_message("time.appconnect.reported", "f", graphite_path, stats), config)
    send_single_status(build_message("time.appconnect.diff", "f", graphite_path, stats), config)
    send_single_status(build_message("time.pretransfer.reported", "f", graphite_path, stats), config)
    send_single_status(build_message("time.pretransfer.diff", "f", graphite_path, stats), config)
    send_single_status(build_message("time.starttransfer.reported", "f", graphite_path, stats), config)
    send_single_status(build_message("time.starttransfer.diff", "f", graphite_path, stats), config)
    send_single_status(build_message("time.redirect.reported", "f", graphite_path, stats), config)
    send_single_status(build_message("time.redirect.diff", "f", graphite_path, stats), config)
    send_single_status(build_message("time.total.reported", "f", graphite_path, stats), config)
    send_single_status(build_message("time.total.diff", "f", graphite_path, stats), config)

    send_single_status(build_message("timedout", "d", graphite_path, stats), config)
    send_single_status(build_message("error", "d", graphite_path, stats), config)
    send_single_status(build_message("responsecode", "d", graphite_path, stats), config)
    send_single_status(build_message("downloadbytes", "f", graphite_path, stats), config)

def send_single_status(msg, config):
    print('sending message to graphite: %s' % msg.replace('\n', ''), flush=True)
    sock = socket.socket()
    sock.connect((config['graphite_host'], config['graphite_port']))
    sock.sendall(msg.encode())
    sock.close()

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

    while(True):
        send_stats(get_url_stats(config), config)
        time.sleep(config['check_interval'])

main(sys.argv)
