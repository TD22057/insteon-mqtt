#!/usr/bin/env python

from setuptools import setup

readme = open('README.md').read()
requirements = open("requirements.txt").readlines()
test_requirements = open("requirements-test.txt").readlines()

setup(
    name='insteon-mqtt',
    version='0.4.0',
    description="Insteon <-> MQTT bridge server",
    long_description=readme,
    author="Ted Drain",
    author_email='',
    url='https://github.com/TD22057/insteon-mqtt',
    packages=['insteont_mqtt'],
    scripts=['scripts/insteon-mqtt'],
    include_package_data=True,
    install_requires=requirements,
    license="GNU General Public License v3",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    # avoid eggs
    zip_safe=False,
)
