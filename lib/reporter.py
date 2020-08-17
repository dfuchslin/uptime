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
        self.config = config

    def calc_diff(self, current, running_response_time):
        if current - running_response_time < 0.0:
            return 0
        return current - running_response_time

    def get_url_stats(self, url):
        timestamp = int(time.time())
        buffer = BytesIO()
        c = pycurl.Curl()
        c.setopt(pycurl.USERAGENT, self.config['user_agent'])
        c.setopt(c.TIMEOUT, self.config['timeout'])
        c.setopt(c.URL, url)
        c.setopt(c.WRITEDATA, buffer)
        if len(self.config['headers']) > 0:
          c.setopt(c.HTTPHEADER, [ k+': '+v for k,v in self.config['headers'].items() ])

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
        stats["url"] = url

        c.close()

        return stats

    def build_message(self, stat, datatype, graphite_path, stats):
        return (("{}.{} {:" + datatype + "} {:d}\n").format(graphite_path, stat, stats[stat], stats["timestamp"]))

    def build_graphite_friendly_url(self, url):
        return url.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_").replace("&", "_").replace(".", "_")

    def send_single_status(self, msg):
        logging.info('sending message to graphite: %s' % msg.replace('\n', ''))
        sock = socket.socket()
        sock.connect((self.config['graphite_host'], self.config['graphite_port']))
        sock.sendall(msg.encode())
        sock.close()

    def send_stats(self, stats):
        graphite_path = "{}.{}".format(self.config['graphite_metric_prefix'], self.build_graphite_friendly_url(stats["url"]))

        self.send_single_status(self.build_message("time.namelookup.reported", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.namelookup.diff", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.connect.reported", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.connect.diff", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.appconnect.reported", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.appconnect.diff", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.pretransfer.reported", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.pretransfer.diff", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.starttransfer.reported", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.starttransfer.diff", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.redirect.reported", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.redirect.diff", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.total.reported", "f", graphite_path, stats))
        self.send_single_status(self.build_message("time.total.diff", "f", graphite_path, stats))

        self.send_single_status(self.build_message("status.success", "d", graphite_path, stats))
        self.send_single_status(self.build_message("status.timedout", "d", graphite_path, stats))
        self.send_single_status(self.build_message("status.error", "d", graphite_path, stats))

        self.send_single_status(self.build_message("responsecode", "d", graphite_path, stats))
        self.send_single_status(self.build_message("downloadbytes", "f", graphite_path, stats))

    def analyze_url(self, url):
        self.send_stats(self.get_url_stats(url))
