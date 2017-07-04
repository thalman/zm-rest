import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort
import json

import _native
import malamute_cffi as mlm
import zm_proto_cffi as zm_proto

### Flask init
app = Flask(__name__)
app.config.from_object(__name__) # load config from this file , flaskr.py

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
            app.config ["VERBOSE"]
        )
    return g.mlm_server

def devices_actor ():
    if not hasattr (g, 'devices_actor'):
        g.devices_actor = _native.lib.start_devices_server (
            app.config ["ENDPOINT"],
            app.config ["VERBOSE"]
        )
    return g.devices_actor

def mlm_connect ():
    if not hasattr (g, 'mlm_client'):
        g.mlm_client = mlm.lib.mlm_client_new()
        mlm.lib.mlm_client_connect (g.mlm_client, app.config ["ENDPOINT"], 5000, b"rest")
        g.msg = zm_proto.lib.zm_proto_new ()
    return g.mlm_client

@app.route ('/')
def slash ():
    return json.dumps (["/devices", app.config ["ENDPOINT"]])

@app.route ('/devices')
def devices ():
    mlm_server ()
    devices_actor ()
    client = mlm_connect ()

    zm_proto.lib.zm_proto_sendto (g.msg, g.mlm_client, b"devices", b"DEVICES-ALL");

    ret = list ()
    zm_proto.lib.zm_proto_recv_mlm (g.msg, g.mlm_client)
    ret.append (ffi.string (zm_proto.lib.zm_proto_device (msg)))
    zm_proto.lib.zm_proto_recv_mlm (g.msg, g.mlm_client)
    ret.append (ffi.string (zm_proto.lib.zm_proto_device (msg)))

    return json.dumps ([x.decode ("utf-8") for x in ret])

@app.route ('/devices/<device>')
def devices_device (device):
    return json.dumps ({
        "device" : device,
        "foo" : "bar"})

