#!/usr/bin/env python

import setuptools

readme = open('README.md').read()
requirements = open("requirements.txt").readlines()
test_requirements = open("requirements-test.txt").readlines()

setuptools.setup(
    name = 'insteon-mqtt',
    version = '0.6.9',
    description = "Insteon <-> MQTT bridge server",
    long_description = readme,
    author = "Ted Drain",
    author_email = '',
    url = 'https://github.com/TD22057/insteon-mqtt',
    packages = setuptools.find_packages(exclude=["tests*"]),
    scripts = ['scripts/insteon-mqtt'],
    include_package_data = True,
    install_requires = requirements,
    license = "GNU General Public License v3",
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
    ],
    test_suite = 'tests',
    tests_require = test_requirements,
    # avoid eggs
    zip_safe = False,
)
