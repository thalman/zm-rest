from setuptools import setup

setup(
    name='zm_rest',
    packages=['zm_rest'],
    include_package_data=True,
    install_requires=[
        'flask', 'cffi>=1.0.0'
    ],
    setup_requires=[
        'pytest-runner',
        "cffi>=1.0.0"
    ],
    tests_require=[
        'pytest',
        'pytest-flask'
    ],
    cffi_modules=["zm_rest/native.py:ffibuilder"],
)
