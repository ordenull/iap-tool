#!/usr/bin/env python

import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()

requires = [
    'bottle',
    'requests',
    ]

setup(name='iap-tool',
      version='1.0',
      description='A helper tool to work with Apple''s App Store in-app-purchase receipts.',
      long_description=README,
      classifiers=[
        "Programming Language :: Python",
        "Intended Audience :: Developers",
        ],
      author='Stan Borbat',
      author_email='stan@borbat.com',
      url='https://stan.borbat.com',
      keywords='apple app purchase receipt verification subscription',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      entry_points={
        'console_scripts': [
            'iap-tool = iap_tool.iap_tool:main',
        ],
      },
)
