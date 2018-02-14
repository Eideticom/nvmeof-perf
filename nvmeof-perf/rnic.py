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

import os
import sys
from collections import OrderedDict

class RNICException(Exception):
    pass

def _readfile(fname):
    return open(fname).read(4096)

def rnic_port_dir_stats(device, ports_dir):
    ports = {}
    for p in sorted(os.listdir(ports_dir)):
        tx = os.path.join(ports_dir, p, "hw_counters", "tx_bytes")
        rx = os.path.join(ports_dir, p, "hw_counters", "tx_bytes")

        if not os.path.exists(tx) or not os.path.exists(rx):
            tx = os.path.join(ports_dir, p, "counters", "port_xmit_data")
            rx = os.path.join(ports_dir, p, "counters", "port_rcv_data")

        if not os.path.exists(tx) or not os.path.exists(rx):
            raise RNICException("Stats files not found for device '{}'".
                                format(device))

        ports[p] = (int(_readfile(tx)), int(_readfile(rx)))

    return ports

def rnic_device_stats(device):
    ports_dir = os.path.join("/sys", "class", "infiniband", device, "ports")

    if os.path.isdir(ports_dir):
        return rnic_port_dir_stats(device, ports_dir)

    ib_dir = os.path.join("/sys", "class", "net", device, "device", "infiniband")
    if os.path.isdir(ib_dir) and len(os.listdir(ib_dir)) == 1:
        ib_dev = os.listdir(ib_dir)[0]
        return rnic_device_stats(ib_dev)

    raise RNICException("Device not found: {}".format(device))

def rnic_stats(devices):
    ret = OrderedDict()
    for d in devices:
        ret[d] = rnic_device_stats(d)
    return ret

if __name__ == "__main__":

    try:
        stats = rnic_stats(sys.argv[1:])
        for dev, ports in stats.items():
            print("{:<20}".format(dev))
            for p, (tx, rx) in ports.items():
                print("   port {:<5} tx: {:>10} rx: {:>10}".format(p, tx, rx))
    except RNICException as e:
        print(e)
