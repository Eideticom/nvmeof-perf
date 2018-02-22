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

from. import colours, utils
from .suffix import Suffix

import os
import sys
import time
from collections import OrderedDict

class RNICException(Exception):
    pass

def _readfile(fname):
    return open(fname).read(4096)

class RnicStats(object):
    def __init__(self):
        self.ports = {}

    def add_port(self, pid, tx, rx):
        self.ports[pid] = tx, rx

    def __sub__(a, b):
        ret = RnicStats()

        for port, (tx, rx) in a.ports.items():
            btx, brx = b.ports[port]
            ret.add_port(port, tx - btx, rx - brx)

        return ret

    def total(self):
        tx_tot = rx_tot = 0
        for p, (tx, rx) in self.ports.items():
            tx_tot += tx
            rx_tot += rx

        return tx_tot, rx_tot

def rnic_port_dir_stats(device, ports_dir):
    ret = RnicStats()

    for p in sorted(os.listdir(ports_dir)):
        tx = os.path.join(ports_dir, p, "hw_counters", "tx_bytes")
        rx = os.path.join(ports_dir, p, "hw_counters", "tx_bytes")
        mult = 1

        if not os.path.exists(tx) or not os.path.exists(rx):
            tx = os.path.join(ports_dir, p, "counters", "port_xmit_data")
            rx = os.path.join(ports_dir, p, "counters", "port_rcv_data")
            mult = 4

        if not os.path.exists(tx) or not os.path.exists(rx):
            raise RNICException("Stats files not found for device '{}'".
                                format(device))

        ret.add_port(p, int(_readfile(tx)) * mult, int(_readfile(rx)) * mult)

    return ret

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

class RnicTimeline(utils.Timeline):
    def __init__(self, devices=[], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.devices = devices
        self.last = None
        self.last_read = None

    def next(self):
        super().next()

        stats_new = rnic_stats(self.devices)

        if self.last:
            stats = {d: a - self.last[d] for d, a in stats_new.items()}
            duration = time.time() - self.last_read
        else:
            stats = stats_new
            duration = None

        self.last = stats_new
        self.last_read = time.time()

        ret = OrderedDict()
        for d, s in stats.items():
            tx, rx = s.total()

            tx_rate = tx / duration if duration else 0
            rx_rate = rx / duration if duration else 0

            ret[d] = tx, rx, tx_rate, rx_rate

        self.latest = ret
        self.latest_titles = ["tx", "rx", "tx_rate", "rx_rate"]

        return ret

    def print_next(self, indent=""):
        stats = self.next()

        print("{}{c.bold}RNIC Stats:{c.rst}".format(indent, c=colours))
        indent += "  "

        for d, (tx, rx, tx_rate, rx_rate) in stats.items():
            tx = Suffix(tx)
            rx = Suffix(rx)
            tx_rate = Suffix(tx_rate, unit="B/s")
            rx_rate = Suffix(rx_rate, unit="B/s")

            print("{}{:<30} tx:    {:>7.1f}  \t{:>7.1f}".
                  format(indent, d, tx, tx_rate))
            print("{}{:<30} rx:    {:>7.1f}  \t{:>7.1f}".
                  format(indent, "", rx, rx_rate))

    def csv(self):
        return tuple(x for y in self.latest.values() for x in y)

    def csv_titles(self):
        return tuple("{}:{}".format(n, x) for n in self.latest.keys() for x in
                     self.latest_titles)


if __name__ == "__main__":
    import time

    tl = RnicTimeline(period=2.0, devices=["mlx5_0"])

    while True:
        print(time.asctime())
        tl.print_next();
        print()
        print()
