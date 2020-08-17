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

def get_url_stats(config):
    url = config['url']
    ip = config['ip']
    timestamp = int(time.time())
    buffer = BytesIO()
    c = pycurl.Curl()
    if len(ip) > 0:
        o = urlparse(url)
        resolve_to = o.netloc + ":443:" + ip
        print("resolving to: [" + resolve_to + "]")
        print("RUNNING INSECURE TLS NEGOTIATION")
        c.setopt(pycurl.RESOLVE, [ resolve_to ])
        c.setopt(pycurl.SSL_VERIFYPEER, 0)
        c.setopt(pycurl.SSL_VERIFYHOST, 0)
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

    stats["responsecode"] = c.getinfo(c.RESPONSE_CODE)
    stats["responsetime"] = c.getinfo(c.TOTAL_TIME)
    stats["namelookuptime"] = c.getinfo(c.NAMELOOKUP_TIME)
    stats["connecttime"] = c.getinfo(c.CONNECT_TIME)
    stats["appconnecttime"] = c.getinfo(c.APPCONNECT_TIME)
    stats["pretransfertime"] = c.getinfo(c.PRETRANSFER_TIME)
    stats["starttransfertime"] = c.getinfo(c.STARTTRANSFER_TIME)
    stats["redirecttime"] = c.getinfo(c.REDIRECT_TIME)
    stats["downloadbytes"] = c.getinfo(c.SIZE_DOWNLOAD)
    stats["timestamp"] = timestamp
    if len(ip) > 0:
      o = urlparse(url)
      stats["url"] = url.replace(o.netloc, o.netloc + "-" + ip)
    else:
      stats["url"] = url

    c.close()

    return stats

def build_message(stat, datatype, graphite_path, stats):
    return (("{}.{} {:" + datatype + "} {:d}\n").format(graphite_path, stat, stats[stat], stats["timestamp"]))

def build_graphite_friendly_url(url):
  return url.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_").replace("&", "_").replace(".", "_")

def send_stats(stats, config):
    graphite_path = "{}.{}".format(config['graphite_metric_prefix'], build_graphite_friendly_url(stats["url"]))

    send_single_status(build_message("responsetime", "f", graphite_path, stats), config)
    send_single_status(build_message("responsecode", "d", graphite_path, stats), config)
    send_single_status(build_message("namelookuptime", "f", graphite_path, stats), config)
    send_single_status(build_message("connecttime", "f", graphite_path, stats), config)
    send_single_status(build_message("appconnecttime", "f", graphite_path, stats), config)
    send_single_status(build_message("pretransfertime", "f", graphite_path, stats), config)
    send_single_status(build_message("starttransfertime", "f", graphite_path, stats), config)
    send_single_status(build_message("redirecttime", "f", graphite_path, stats), config)
    send_single_status(build_message("timedout", "d", graphite_path, stats), config)
    send_single_status(build_message("error", "d", graphite_path, stats), config)
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
