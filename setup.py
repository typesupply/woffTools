#!/usr/bin/env python

import sys
from distutils.core import setup

try:
    import fontTools
except:
    print "*** Warning: woffTools requires FontTools, see:"
    print "    fonttools.sf.net"


setup(
    name="woffTools",
    version="0.1beta",
    description="A set of tools for working with WOFF files.",
    author="Tal Leming",
    author_email="tal@typesupply.com",
    url="http://code.typesupply.com",
    license="MIT",
    packages=[
        "",
        "woffTools",
        "woffTools.tools",
        "woffTools.test"
    ],
    package_dir={"":"Lib"},
    scripts=[
        "woff-all",
        "woff-validate",
        "woff-info",
        "woff-proof",
        "woff-css",
    ]
)