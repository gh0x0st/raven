#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='raven',
    version='1.0.0',
    url='https://github.com/gh0x0st/raven',
    author='Tristram',
    author_email="discord:blueteamer",
    description='A lightweight file upload service used for penetration testing and incident response.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    license="MIT",
    keywords=['file upload', 'penetration testing', 'HTTP server', 'SimpleHTTPServer'],
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': ['raven = raven.__main__:main'],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Security",
        "Topic :: Utilities",
        "Topic :: Security",
        "Topic :: Security :: Penetration Testing",
        "Topic :: System :: Networking",
        "Topic :: System :: Systems Administration",
    ],
    python_requires='>=3.6',
)
