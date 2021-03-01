import pycurl
from urllib.parse import urlparse
import sys, getopt, os
import socket
import time
import logging
try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

class CurlTimeReporter:

    def __init__(self, config):
        self.graphite_host = 'graphite'
        self.graphite_port = 2003
        self.graphite_prefix = 'uptime'
        graphite = config.get('graphite')
        if graphite:
          if graphite.get('host'):
            self.graphite_host = graphite['host']
          if graphite.get('port'):
            self.graphite_port = int(graphite['port'])
          if graphite.get('prefix'):
            self.graphite_prefix = graphite['prefix']

        self.user_agent = self.set_or_default(config, 'user_agent', 'libcurl (custom uptime check)')
        self.timeout = int(self.set_or_default(config, 'timeout', 30))
        self.headers = self.set_or_default(config, 'headers', {})

        logging.info('Configured reporter:')
        logging.info('  Graphite:')
        logging.info('    host     : %s' % self.graphite_host)
        logging.info('    port     : %d' % self.graphite_port)
        logging.info('    prefix   : %s' % self.graphite_prefix)
        logging.info('  user_agent : %s' % self.user_agent)
        logging.info('  timeout    : %d' % self.timeout)
        logging.info('  headers    : %s' % self.headers)

    def set_or_default(self, config, key, default):
      if config.get(key):
        return config[key]
      return default

    def calc_diff(self, current, running_response_time):
        if current - running_response_time < 0.0:
            return 0
        return current - running_response_time

    def get_url_stats(self, host, path):
        timestamp = int(time.time())
        url = f'{host}{path}'
        buffer = BytesIO()
        c = pycurl.Curl()
        c.setopt(pycurl.USERAGENT, self.user_agent)
        c.setopt(c.TIMEOUT, self.timeout)
        c.setopt(c.URL, url)
        c.setopt(c.WRITEDATA, buffer)
        if len(self.headers) > 0:
          c.setopt(c.HTTPHEADER, [ k+': '+v for k,v in self.headers.items() ])

        stats = {}
        stats["status.success"] = 1
        stats["status.timedout"] = 0
        stats["status.error"] = 0

        try:
            c.perform()
        except Exception as e:
            if e.args[0] == c.E_OPERATION_TIMEDOUT:
                stats["status.timedout"] = 1
                stats["status.success"] = 0
            else:
                logging.error(e)
                stats["status.error"] = 1
                stats["status.success"] = 0

        # calculate diffs
        running_response_time = 0.0

        stats["time.namelookup.reported"] = c.getinfo(c.NAMELOOKUP_TIME)
        stats["time.namelookup.diff"] = self.calc_diff(c.getinfo(c.NAMELOOKUP_TIME), running_response_time)
        running_response_time += stats["time.namelookup.diff"]

        stats["time.connect.reported"] = c.getinfo(c.CONNECT_TIME)
        stats["time.connect.diff"] = self.calc_diff(c.getinfo(c.CONNECT_TIME), running_response_time)
        running_response_time += stats["time.connect.diff"]

        stats["time.appconnect.reported"] = c.getinfo(c.APPCONNECT_TIME)
        stats["time.appconnect.diff"] = self.calc_diff(c.getinfo(c.APPCONNECT_TIME), running_response_time)
        running_response_time += stats["time.appconnect.diff"]

        stats["time.pretransfer.reported"] = c.getinfo(c.PRETRANSFER_TIME)
        stats["time.pretransfer.diff"] = self.calc_diff(c.getinfo(c.PRETRANSFER_TIME), running_response_time)
        running_response_time += stats["time.pretransfer.diff"]

        stats["time.starttransfer.reported"] = c.getinfo(c.STARTTRANSFER_TIME)
        stats["time.starttransfer.diff"] = self.calc_diff(c.getinfo(c.STARTTRANSFER_TIME), running_response_time)
        running_response_time += stats["time.starttransfer.diff"]

        stats["time.redirect.reported"] = c.getinfo(c.REDIRECT_TIME)
        stats["time.redirect.diff"] = self.calc_diff(c.getinfo(c.REDIRECT_TIME), running_response_time)
        running_response_time += stats["time.redirect.diff"]

        stats["time.total.reported"] = c.getinfo(c.TOTAL_TIME)
        stats["time.total.diff"] = self.calc_diff(c.getinfo(c.TOTAL_TIME), running_response_time)
        running_response_time += stats["time.total.diff"]

        stats["responsecode"] = c.getinfo(c.RESPONSE_CODE)
        stats["downloadbytes"] = c.getinfo(c.SIZE_DOWNLOAD)
        stats["timestamp"] = timestamp
        stats["host"] = host
        stats["path"] = path

        c.close()

        return stats

    def build_message(self, stat, datatype, graphite_path, stats):
        return (("{}.{} {:" + datatype + "} {:d}\n").format(graphite_path, stat, stats[stat], stats["timestamp"]))

    def build_graphite_friendly_url(self, host, path):
        host_cleaned = host.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_").replace("&", "_").replace(".", "_")
        path_cleaned = path.replace("/", "_").replace("?", "_").replace("&", "_").replace(".", "_")
        return f'{host_cleaned}.{path_cleaned}'

    def send_multi_stats(self, msgs):
        msg = ''.join(msgs)
        logging.debug('sending message to graphite: %s' % msg.replace('\n', '|'))
        conn = socket.create_connection((self.graphite_host, self.graphite_port), timeout=self.timeout)
        conn.sendall(msg.encode('ascii'))
        conn.close()

    def send_stats(self, stats):
        graphite_path = "{}.{}".format(self.graphite_prefix, self.build_graphite_friendly_url(stats['host'], stats['path']))

        msgs = []

        msgs.append(self.build_message("time.namelookup.reported", "f", graphite_path, stats))
        msgs.append(self.build_message("time.namelookup.diff", "f", graphite_path, stats))
        msgs.append(self.build_message("time.connect.reported", "f", graphite_path, stats))
        msgs.append(self.build_message("time.connect.diff", "f", graphite_path, stats))
        msgs.append(self.build_message("time.appconnect.reported", "f", graphite_path, stats))
        msgs.append(self.build_message("time.appconnect.diff", "f", graphite_path, stats))
        msgs.append(self.build_message("time.pretransfer.reported", "f", graphite_path, stats))
        msgs.append(self.build_message("time.pretransfer.diff", "f", graphite_path, stats))
        msgs.append(self.build_message("time.starttransfer.reported", "f", graphite_path, stats))
        msgs.append(self.build_message("time.starttransfer.diff", "f", graphite_path, stats))
        msgs.append(self.build_message("time.redirect.reported", "f", graphite_path, stats))
        msgs.append(self.build_message("time.redirect.diff", "f", graphite_path, stats))
        msgs.append(self.build_message("time.total.reported", "f", graphite_path, stats))
        msgs.append(self.build_message("time.total.diff", "f", graphite_path, stats))

        msgs.append(self.build_message("status.success", "d", graphite_path, stats))
        msgs.append(self.build_message("status.timedout", "d", graphite_path, stats))
        msgs.append(self.build_message("status.error", "d", graphite_path, stats))

        msgs.append(self.build_message("responsecode", "d", graphite_path, stats))
        msgs.append(self.build_message("downloadbytes", "f", graphite_path, stats))

        self.send_multi_stats(msgs)

    def analyze_url(self, host, path):
        self.send_stats(self.get_url_stats(host, path))
