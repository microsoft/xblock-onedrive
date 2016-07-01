""" Copyright (c) Microsoft Corporation. All Rights Reserved. """
""" Licensed under the MIT license. See LICENSE file on the project webpage for details. """

"""Setup for onedrive XBlock."""

import os
from setuptools import setup


def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


setup(
    name='xblock-onedrive',
    version='0.6',
    description='OneDrive XBlock for adding documents from onedrive to courseware',
    packages=[
        'onedrive',
    ],
    install_requires=[
        'XBlock',
    ],
    entry_points={
        'xblock.v1': [
            'onedrive = onedrive:OneDriveXBlock',
        ]
    },
    package_data=package_data("onedrive", ["static", "public"]),
)
