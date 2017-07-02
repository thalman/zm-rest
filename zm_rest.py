#
# PoC of REST API layer for zmon.it project
#
#

from flask import Flask, url_for
import json
app = Flask ("zm_rest")

import cffi
import malamute_cffi as mlm
import czmq_cffi as czmq
import zm_proto_cffi as zm_proto

ffi = cffi.FFI ()
ffi.cdef ("""
typedef void zm_proto_t;
typedef void mlm_client_t;
typedef void zactor_t;
zactor_t * start_malamute_server (const char* endpoint, bool verbose);
zactor_t * start_devices_server (const char *endpoint, bool verbose);
int zm_proto_sendto (zm_proto_t *self, mlm_client_t *client, const char *address, const char *subject);
int zm_proto_recv_mlm (zm_proto_t *self, mlm_client_t *client);
    """)
ffi.set_source ("_zm_rest", r"""
#include <malamute.h>
#include <zmproto.h>

static zactor_t * start_malamute_server (const char* endpoint, bool verbose)
{
    zactor_t *server = zactor_new (mlm_server, "Malamute");
    zstr_sendx (server, "BIND", endpoint, NULL);
    if (verbose)
        zstr_sendx (server, "VERBOSE", NULL);
    return server;
}

//  Send MAILBOX DELIVER zm_proto_t message via mlm_client
int
    zm_proto_sendto (zm_proto_t *self, mlm_client_t *client, const char *address, const char *subject)
{
    assert (self);
    assert (client);
    assert (address);
    assert (subject);

    zmsg_t *msg = zmsg_new ();
    assert (msg);
    int r = zm_proto_send (self, msg);
    if (r == -1) {
        zmsg_destroy (&msg);
        return -1;
    }

    return mlm_client_sendto (client, address, subject, NULL, 5000, &msg);
}

static void devices_server (zsock_t *pipe, void *args)
{
    char *endpoint = strdup ((char*) args);
    mlm_client_t *client = mlm_client_new ();
    mlm_client_connect (client, endpoint, 5000, "devices");

    zpoller_t *poller = zpoller_new (pipe, mlm_client_msgpipe (client), NULL);

    zm_proto_t *reply = zm_proto_new ();
    zm_proto_set_id (reply, ZM_PROTO_DEVICE);
    zsock_signal (pipe, 0);

    while (!zsys_interrupted)
    {
        void *which = zpoller_wait (poller, -1);

        if (which == pipe)
            break;

        zmsg_t *msg = mlm_client_recv (client);
        zmsg_destroy (&msg);

        for (int i = 0; i != 2; i++) {
            char *device = zsys_sprintf ("device.%d", i);
            zm_proto_set_device (reply, device);
            zm_proto_sendto (reply, client, mlm_client_sender (client), "DEVICES-ALL");
            zstr_free (&device);
        }
    }

    zm_proto_destroy (&reply);
    mlm_client_destroy (&client);
    zstr_free (&endpoint);
}

//  Receive zm_proto_t from mlm_client, return -1 and do not touch zm_proto_t
//  if zm_proto_t was NOT delivered
int
zm_proto_recv_mlm (zm_proto_t *self, mlm_client_t *client)
{
    assert (self);
    assert (client);

    zmsg_t *msg = mlm_client_recv (client);
    if (!msg)
        return -1;

    int r = zm_proto_recv (self, msg);
    zmsg_destroy (&msg);
    return r;
}

static zactor_t *start_devices_server (const char *endpoint, bool verbose)
{
    zactor_t *server = zactor_new (devices_server, (void*) endpoint);
    return server;
}

""", libraries=["czmq", "mlm", "zm_proto" ], include_dirs = ["-I/usr/include/python3.6m", ])

ffi.compile (verbose=True)

from _zm_rest.lib import start_malamute_server, start_devices_server, zm_proto_sendto, zm_proto_recv_mlm

ENDPOINT = b"inproc://malamute"
mlm_server = start_malamute_server (ENDPOINT, False)

devices_server = start_devices_server (ENDPOINT, False)

rest = mlm.lib.mlm_client_new ()
mlm.lib.mlm_client_connect (rest, ENDPOINT, 5000, b"rest")

msg = zm_proto.lib.zm_proto_new ()
zm_proto.lib.zm_proto_set_id (msg, 3) # ZM_PROTO_DEVICE

@app.route ("/")
def do_root ():
    return json.dumps (
        [url_for ("GET_devices"),
         url_for ("GET_devices_device", device="device")
        ]
    )

@app.route ("/devices/", methods = ["GET", ])
def GET_devices ():
    zm_proto_sendto (msg, rest, b"devices", b"DEVICES-ALL");

    ret = list ()
    zm_proto_recv_mlm (msg, rest)
    ret.append (ffi.string (zm_proto.lib.zm_proto_device (msg)))
    zm_proto_recv_mlm (msg, rest)
    ret.append (ffi.string (zm_proto.lib.zm_proto_device (msg)))

    return json.dumps ([x.decode ("utf-7") for x in ret])
    

@app.route ("/devices/<device>", methods = ["GET", ])
def GET_devices_device (device):
    return json.dumps (
        {"device" : device,
         "uri" : url_for ("GET_devices_device", device=device),
         "ext" : {"foo" : "bar"}
        }
    )
