#!/usr/bin/python
from flup.server.fcgi import WSGIServer
from ffshmon import app

if __name__ == '__main__':
    WSGIServer(app, bindAddress='/var/run/ffshmon.sock').run()