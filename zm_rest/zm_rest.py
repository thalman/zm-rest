import os
import sqlite3
import json
import sys

from flask import Flask, request, session, g, redirect, url_for, abort

import _native
import zm_proto_cffi as zm_proto

class MlmClient ():
    """Simple wrapper around mlm_client_t - to make memory management easier"""
    def __init__ (self):
        self._client = zm_proto.lib.mlm_client_new ()

    def __del__ (self):
        if not hasattr (self, "_client"):
            return
        client_p = zm_proto.ffi.new ("mlm_client_t *[1]")
        client_p [0] = self._client
        zm_proto.lib.mlm_client_destroy (client_p)
        del client_p
        del self._client

    @property
    def lib (self):
        return self._client

class ZmProto ():
    """Simple wrapper around zm_proto_t - to make memory management easier"""
    def __init__ (self):
        self._proto = zm_proto.lib.zm_proto_new ()

    def __del__ (self):
        if not hasattr (self, "_proto"):
            return
        proto_p = zm_proto.ffi.new ("zm_proto_t *[1]")
        proto_p [0] = self._proto
        zm_proto.lib.zm_proto_destroy (proto_p)
        del proto_p
        del self._proto

    @property
    def lib (self):
        return self._proto

### Flask init
app = Flask("zm_rest")
app.config.from_object(__name__) # load config from this file , zm_rest.py

### Configuration files
# Load default config and override config from an environment variable
app.config.update(dict(
    ENDPOINT=b"inproc://zm_rest",
    VERBOSE=True
))
app.config.from_envvar('ZM_REST_SETTINGS', silent=True)


### Connect DB
def mlm_server ():
    if not hasattr (g, 'mlm_server'):
        g.mlm_server = _native.lib.start_malamute_server (
            app.config ["ENDPOINT"],
            False
        )
    return g.mlm_server

def devices_actor ():
    print ("D: Python:devices_actor: START", file=sys.stderr)
    if not hasattr (g, 'devices_actor'):
        g.devices_actor = _native.lib.start_devices_server (
            app.config ["ENDPOINT"],
            app.config ["VERBOSE"]
        )
    return g.devices_actor

@app.before_request
def mlm_connect ():
    print ("D: Python:mlm_client_name=rest.%d" % id (request))
    g.mlm_client = MlmClient ()
    zm_proto.lib.mlm_client_connect (g.mlm_client.lib, app.config ["ENDPOINT"], 5000, b"rest.%d" % id (request))
    g.msg = ZmProto ()
    return None

@app.after_request
def mlm_disconnect (r):
    g.mlm_client.__del__()
    g.msg.__del__()
    del g.mlm_client
    del g.msg
    return r

with app.app_context() as app_context:
    print ("#### 1", file=sys.stderr)
    print (dir (app_context))

    mlm_server ()
    devices_actor ()

def td ():
    _app = app
    print ("TEARDOWN!!!", file=sys.stderr)

#app.teardown_appcontext (td)

@app.route ('/')
def slash ():
    return json.dumps (["/devices", ])

@app.route ('/devices')
def devices ():

    msg = g.msg.lib
    mlm_client = g.mlm_client.lib

    zm_proto.lib.zm_proto_sendto (msg, mlm_client, b"devices", b"DEVICES-ALL");

    ret = list ()
    for i in range (2):
        zm_proto.lib.zm_proto_recv_mlm (msg, mlm_client)
        ret.append (zm_proto.ffi.string (zm_proto.lib.zm_proto_device (msg)))

    return json.dumps ([x.decode ("utf-8") for x in ret]) + "\n"

@app.route ('/devices/<device>')
def devices_device (device):
    return json.dumps ({
        "device" : device,
        "foo" : "bar"})
