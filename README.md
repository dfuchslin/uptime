# uptime

Script to periodically check a specific website for response times

```
pip3 install -U pycurl
```


```
./uptime.py https://gyttja.com uptime
```

The following options can be set with environment variables:

| environment variable | description | default |
|----------|-------------|---------|
| GRAPHITE_HOST | Hostname of graphite server | graphite |
| GRAPHITE_PORT | Port of graphite server| 2003 |
| GRAPHITE_METRIC_PREFIX | Metric prefix, see below | uptime |
| TIMEOUT | Connection timeout (c.setopt(c.TIMEOUT)), in seconds | 30 |
| CHECK_INTERVAL | How often to request the URL, in seconds | 5 |
| USER_AGENT | User agent sent in the curl request | Mozilla/5.0 (X11; Linux i686 on x86_64; rv:10.0) |
| USE_GZIP | Request gzip/compressed response, true/false | true |


## graphite

Start a localhost graphite for testing:

```
docker run -d --name graphite --restart=always -p 8080:80 -p 2003:2003 graphiteapp/graphite-statsd
```
