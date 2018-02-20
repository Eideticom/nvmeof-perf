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

from . import colours, utils
from .suffix import Suffix

import os
import copy
import ctypes as c

from collections import OrderedDict

class SwitchtecPortId(c.Structure):
    _fields_ = [("partition", c.c_ubyte),
                ("stack", c.c_ubyte),
                ("upstream", c.c_ubyte),
                ("stk_id", c.c_ubyte),
                ("phys_id", c.c_ubyte),
                ("log_id", c.c_ubyte)]

class SwitchtecStatus(c.Structure):
    _fields_ = [("port", SwitchtecPortId),
                ("cfg_link_width", c.c_ubyte),
                ("neg_link_width", c.c_ubyte),
                ("link_up", c.c_ubyte),
                ("link_rate", c.c_ubyte),
                ("ltssm", c.c_ubyte),
                ("ltssm_str", c.c_char_p),
                ("pci_dev", c.c_char_p),
                ("vendor_id", c.c_int),
                ("device_id", c.c_int),
                ("class_devices", c.c_char_p)]

    @staticmethod
    def deepcopy(other):
        ret = SwitchtecStatus.from_buffer_copy(other)
        if other.pci_dev:
            ret.pci_dev = c.c_char_p(other.pci_dev)

        if ret.class_devices:
            ret.class_devices = c.c_char_p(other.class_devices)

        return ret

class SwitchtecBwCntrDir(c.Structure):
    _fields_ = [("posted", c.c_uint64),
                ("comp", c.c_uint64),
                ("nonposted", c.c_uint64)]

    def total(self):
        return self.posted + self.comp + self.nonposted

    def __sub__(a, b):
        ret = SwitchtecBwCntrDir()

        ret.posted = a.posted - b.posted
        ret.comp = a.comp - b.comp
        ret.nonposted = a.nonposted - b.nonposted

        return ret

class SwitchtecBwCntrRes(c.Structure):
    _fields_ = [("time_us", c.c_uint64),
                ("egress", SwitchtecBwCntrDir),
                ("ingress", SwitchtecBwCntrDir)]

    def __sub__(a, b):
        ret = SwitchtecBwCntrRes()

        ret.time_us = a.time_us - b.time_us
        ret.egress = a.egress - b.egress
        ret.ingress = a.ingress - b.ingress

        return ret

    def time(self):
        return self.time_us * 1e-6

SwitchtecStatusPtr = c.POINTER(SwitchtecStatus)

try:
    swlib = c.cdll.LoadLibrary("libswitchtec.so")
    swlib.switchtec_open.argtypes = [c.c_char_p]
    swlib.switchtec_open.restype = c.c_void_p
    swlib.switchtec_close.argtypes = [c.c_void_p]
    swlib.switchtec_strerror.restype = c.c_char_p
    swlib.switchtec_status.argtypes = [c.c_void_p,
                                       c.POINTER(SwitchtecStatusPtr)]
    swlib.switchtec_status.restype = c.c_int
    swlib.switchtec_status_free.argtypes = [SwitchtecStatusPtr, c.c_int]
    swlib.switchtec_get_devices.argtypes = [c.c_void_p, SwitchtecStatusPtr,
                                            c.c_int]
    swlib.switchtec_bwcntr_many.argtypes = [c.c_void_p, c.c_int,
                                            c.POINTER(c.c_int), c.c_int,
                                            c.POINTER(SwitchtecBwCntrRes)]
except OSError:
    swlib = None

class SwitchtecError(Exception):
    def __init__(self, msg):
        err_msg = swlib.switchtec_strerror().decode()
        super().__init__("{}: {}".format(msg, err_msg))

class Switchtec(object):
    def __init__(self, devpath="/dev/switchtec0", *args, **kwargs):
        super().__init__(*args, **kwargs)

        if swlib is None:
            raise OSError("Unable to load libswitchtec.so")

        self.devpath = devpath

        self.dev = swlib.switchtec_open(devpath.encode())
        if not self.dev:
            raise SwitchtecError(devpath)

    def __del__(self):
        swlib.switchtec_close(self.dev)

    def status(self):
        st = SwitchtecStatusPtr()
        nr_ports = swlib.switchtec_status(self.dev, c.pointer(st))
        if nr_ports < 0:
            raise SwitchtecError()

        ret = swlib.switchtec_get_devices(self.dev, st, nr_ports)
        if ret:
            raise SwitchtecError()

        ret = [SwitchtecStatus.deepcopy(st[i]) for i in range(nr_ports)]

        swlib.switchtec_status_free(st, nr_ports)

        return ret

    def bwcntr_many(self, port_ids, reset=False):
        bwdata = (SwitchtecBwCntrRes * len(port_ids))()
        ids = (c.c_int * len(port_ids))(*port_ids)

        ret = swlib.switchtec_bwcntr_many(self.dev, len(port_ids), ids, 0,
                                          bwdata)
        if ret < 0:
            raise SwitchtecError()

        return [SwitchtecBwCntrRes.from_buffer_copy(bwdata[i])
                for i in range(len(port_ids))]

class SwitchtecTimeline(Switchtec, utils.Timeline):
    ignore_classes = [b"ucm", b"issm", b"umad", b"uverbs", b"ptp"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        st = self.status()
        self.port_ids = [s.port.phys_id for s in st]

        self.names = [self.get_name(s) for s in st]

        self.last = None

    def get_name(self, st):
        if st.port.upstream:
            return "upstream"

        if st.class_devices:
            classes = [c.strip() for c in st.class_devices.split(b",")]
            classes = [c.decode() for c in classes
                       if not any(c.startswith(x) for x in self.ignore_classes)]

            return ", ".join(classes)

        if st.pci_dev:
            return st.pci_dev

        return "Port {}".format(st.port.log_id)

    def next(self):
        super().next()

        bwdata_new = self.bwcntr_many(self.port_ids)

        if self.last:
            bwdata = [bw - l for bw, l in zip(bwdata_new, self.last)]
        else:
            bwdata = bwdata_new

        self.last = bwdata_new

        byte_counts = OrderedDict()
        for n, bw in zip(self.names, bwdata):
            byte_counts[n] = (bw.ingress.total(), bw.egress.total())

        rates = OrderedDict()
        for n, bw in zip(self.names, bwdata):
            rates[n] = (bw.ingress.total() / bw.time(),
                        bw.egress.total() / bw.time())


        return byte_counts, rates

    def print_next(self, indent=""):
        bytes, rates = self.next()

        print("{}{c.bold}Switchtec PCI Stats for {}{c.rst}:".
              format(indent, os.path.basename(self.devpath), c=colours))
        indent += "  "

        for (n, (ing, eg)), (_, (ing_rate, eg_rate)) in zip(bytes.items(),
                                                            rates.items()):
            ing = Suffix(ing)
            eg = Suffix(eg)
            ing_rate = Suffix(ing_rate, "B/s")
            eg_rate = Suffix(eg_rate, "B/s")

            n += ":"

            print("{}{:<30} in:    {:>7.1f}  \t{:>7.1f}".
                  format(indent, n, ing, ing_rate))
            print("{}{:<30} out:   {:>7.1f}  \t{:>7.1f}".
                  format(indent, "",  eg, eg_rate))

if __name__ == "__main__":
    import time

    sw = SwitchtecTimeline(period=2.0)

    while True:
        print(time.asctime())
        sw.print_next();
        print()
        print()
