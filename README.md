# REST API layer of zmon.it project

This is work in progress REST API backend for zmon.it project

## License

Mozilla Public License 2,0

## Status

Proof of concept

## Install

    pip install Flask
    # add http://download.opensuse.org/repositories/network:/messaging:/zeromq:/git-draft/
    # add http://download.opensuse.org/repositories/home:/mvyskocil:/zmonit:/git-draft/
    # install python3-czmq-cffi python3-malamute-cffi python3-zm-proto-cffi python3-zm-proto

    python setup.py build #to build the native code

    PYTHONPATH=`pwd` FLASK_APP=zm_rest.py flask run
    curl http://localhost:5000/devices

## Test

    python setup.py test

## TODO
 * does NOT react on Ctrl+C
 * the the usage of cffi interface is ugly and unpythonic
   Partially solved by VoidWrapper, there are now classes for each basic types
 * more APIs
