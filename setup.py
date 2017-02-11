#!/usr/bin/env python3

from distutils.core import setup

setup(
    name='CT',
    version='0.1',
    description='Cube timer',
    author='Eivind Fonn',
    author_email='evfonn@gmail.com',
    license='GPL3',
    url='https://github.com/TheBB/butter',
    py_packages=['ct'],
    entry_points={
        'console_scripts': ['ct=ct.__main__:main'],
    },
    install_requires=[
        'pyqt5',
    ],
)
