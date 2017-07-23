import os
import sqlite3
import json
import sys

from flask import Flask, request, session, g, redirect, url_for, abort

import _native
import zm_proto_cffi as zm_proto

def _raise (exc):
    raise exc

class VoidWrapper ():
    """Universal wrapper arount void to make Python gc comaptible with CLASS variables"""

    c_type = "void"
    ffi = None
    constructor = lambda self: _raise (NotImplementedError ("VoidWrapper have no constructor"))
    destructor = lambda self, client_p: _raise (NotImplementedError ("VoidWrapper have no destructor"))

    def __init__ (self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._ptr = self.__class__.constructor (self)

    def __del__ (self):
        if self._ptr is None:
            return

        ptr_p = self.__class__.ffi.new ("%s *[1]" % self.__class__.c_type)
        ptr_p [0] = self._ptr
        self.__class__.destructor (self, ptr_p)
        del ptr_p
        self._ptr = None

    @property
    def ptr (self):
        return self._ptr

class MlmClient (VoidWrapper):
    c_type = "mlm_client_t"
    ffi = zm_proto.ffi
    constructor = lambda self: zm_proto.lib.mlm_client_new ()
    destructor = lambda self, ptr_p: zm_proto.lib.mlm_client_destroy (ptr_p)

class ZmProto (VoidWrapper):
    c_type = "zm_proto_t"
    ffi = zm_proto.ffi
    constructor = lambda self: zm_proto.lib.zm_proto_new ()
    destructor = lambda self, ptr_p: zm_proto.lib.zm_proto_destroy (ptr_p)

class MlmServer (VoidWrapper):
    c_type = "zactor_t"
    ffi = _native.ffi
    constructor = lambda self: _native.lib.start_malamute_server (self._kwargs ["endpoint"], self._kwargs ["verbose"])
    destructor = lambda self, ptr_p: _native.lib.zactor_destroy (ptr_p)
    
    def __init__ (self, *args, **kwargs):
        super ().__init__(*args, **kwargs)

class DevicesServer (VoidWrapper):
    c_type = "zactor_t"
    ffi = _native.ffi
    constructor = lambda self: _native.lib.start_devices_server (self._kwargs ["endpoint"], self._kwargs ["verbose"])
    destructor = lambda self, ptr_p: _native.lib.zactor_destroy (ptr_p)

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
        g.mlm_server = MlmServer (
            endpoint=app.config ["ENDPOINT"],
            verbose=False
        )
    return g.mlm_server

def devices_actor ():
    if not hasattr (g, 'devices_actor'):
        g.devices_actor = DevicesServer (
            endpoint=app.config ["ENDPOINT"],
            verbose=app.config ["VERBOSE"]
        )
    return g.devices_actor

with app.app_context() as app_context:
    mlm_server ()
    devices_actor ()

@app.before_request
def mlm_connect ():
    print ("D: Python:mlm_client_name=rest.%d" % id (request))
    g.mlm_client = MlmClient ()
    zm_proto.lib.mlm_client_connect (g.mlm_client.ptr, app.config ["ENDPOINT"], 5000, b"rest.%d" % id (request))
    g.msg = ZmProto ()
    return None

@app.after_request
def mlm_disconnect (r):
    g.mlm_client.__del__()
    g.msg.__del__()
    del g.mlm_client
    del g.msg
    return r

@app.route ('/')
def slash ():
    return json.dumps (["/devices", ])

@app.route ('/devices')
def devices ():

    msg = g.msg.ptr
    mlm_client = g.mlm_client.ptr

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
