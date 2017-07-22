from flask import url_for

def test_app (client):
    assert client.get (url_for ("devices")).status_code == 200
