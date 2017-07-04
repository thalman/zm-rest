from setuptools import setup

setup(
    name='zm_rest',
    packages=['zm_rest'],
    include_package_data=True,
    install_requires=[
        'flask', 'cffi'
    ],
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
    ],
)
