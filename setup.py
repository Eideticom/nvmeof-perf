#!/usr/bin/env python3
########################################################################
##
## Copyright 2018 Eidetic Communications Inc.
##
## Licensed under the Apache License, Version 2.0 (the "License"); you
## may not use this file except in compliance with the License. You may
## obtain a copy of the License at
## http://www.apache.org/licenses/LICENSE-2.0 Unless required by
## applicable law or agreed to in writing, software distributed under the
## License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
## CONDITIONS OF ANY KIND, either express or implied. See the License for
## the specific language governing permissions and limitations under the
## License.
##
########################################################################

import subprocess as sp
from distutils.core import setup

try:
    version = sp.check_output(["git", "describe", "--always", "--tags",
                               "--match", "v[0-9]*"]).decode().strip()
except (sp.CalledProcessError, FileNotFoundError):
    version = "??"

setup(name='nvmeof_perf',
      version=version,
      description='Tools to help benchmark NVMe Open Fabrics Setups',
      author='Logan Gunthorpe',
      author_email='logang@deltatee.com',
      url='https://github.com/Eideticom/nvmeof-perf',
      packages=['nvmeof_perf'],
      scripts=['nvmeof-perf', 'rdma-perf'],
)
