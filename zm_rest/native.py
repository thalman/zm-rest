# native support code for zm_rest

import cffi

ffibuilder = cffi.FFI ()
ffibuilder.cdef ("""
typedef struct _zactor_t zactor_t;
zactor_t * start_malamute_server (const char* endpoint, bool verbose);
zactor_t * start_devices_server (const char *endpoint, bool verbose);
""")
ffibuilder.set_source ("_native", r"""
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

static void devices_server (zsock_t *pipe, void *args)
{
    zsys_debug ("devices_server: START");
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
        zsys_debug ("C:devices_server: got message");

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

static zactor_t *start_devices_server (const char *endpoint, bool verbose)
{
    zsys_debug ("C:start_devices_server: endpoint=%s, verbose=%s",
        endpoint,
        verbose ? "true" : "false");
    zactor_t *server = zactor_new (devices_server, (void*) endpoint);
    return server;
}
""", libraries=["czmq", "mlm", "zm_proto"], include_dirs = ["-I/usr/include/python3.6m"])

if __name__ == "__main__":
    ffibuilder.compile (verbose=True)
