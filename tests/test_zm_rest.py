# There will be the test of zm_rest

import pytest
from collections import namedtuple

import zm_rest

@pytest.fixture (scope="module")
def ctx ():
    zm_rest.app.testing = True
    Ctx = namedtuple ("Ctx", "app")
    ctx = Ctx (zm_rest.app.test_client ())
    with zm_rest.app.app_context ():
        zm_rest.zm_rest.mlm_server ()
        zm_rest.zm_rest.devices_actor ()
        zm_rest.zm_rest.mlm_connect ()
    yield ctx

def test_slash (ctx):
    rv = ctx.app.get (b"/")
    assert b'["/devices"]' == rv.data
