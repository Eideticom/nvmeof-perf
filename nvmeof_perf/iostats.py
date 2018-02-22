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
import stat
import sys

from collections import namedtuple, OrderedDict

class IoStats(namedtuple("IoStats", ["reads", "reads_merged",  "read_sectors",
                                     "read_ms", "writes", "writes_merged",
                                     "write_sectors", "write_ms",
                                     "ios_in_progress", "io_ms",
                                     "ios_weighted_ms"])):
    def __sub__(a, b):
        return IoStats(reads = a.reads - b.reads,
                       reads_merged = a.reads_merged - b.reads_merged,
                       read_sectors = a.read_sectors - b.read_sectors,
                       read_ms = a.read_ms - b.read_ms,
                       writes = a.writes - b.writes,
                       writes_merged = a.writes_merged - b.writes_merged,
                       write_sectors = a.write_sectors - b.write_sectors,
                       write_ms = a.write_ms - b.write_ms,
                       ios_in_progress = a.ios_in_progress - b.ios_in_progress,
                       io_ms = a.io_ms - b.io_ms,
                       ios_weighted_ms = a.ios_weighted_ms - b.ios_weighted_ms)

def iostats_get_path(device):
    if os.path.exists(device):
        st = os.stat(device)
        if not stat.S_ISBLK(st.st_mode):
            raise IOError("{} is not a block device".format(device))

        major=os.major(st.st_rdev)
        minor=os.minor(st.st_rdev)
        return os.path.join("/sys", "dev", "block",
                            "{}:{}".format(major, minor), "stat")

    else:
        path = os.path.join("/sys", "class", "block", device, "stat")
        if not os.path.exists(path):
            raise IOError("Block device not found: {}".format(device))

        return path

def iostats_device_stats(device):
    data = open(iostats_get_path(device)).read().split()

    return IoStats._make(int(x) for x in data)

def iostats_stats(devices):
    ret = OrderedDict()
    for d in devices:
        ret[d] = iostats_device_stats(d)
    return ret

class IoStatsTimeline(utils.Timeline):
    def __init__(self, devices=[], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.devices = devices
        self.last = None

    def next(self):
        super().next()

        stats_new = iostats_stats(self.devices)

        if self.last:
            stats = OrderedDict((d, a - self.last[d])
                                for d, a in stats_new.items())
        else:
            stats = stats_new

        self.last = stats_new

        ret = OrderedDict()
        for d, s in stats.items():
            read = s.read_sectors * 512
            write = s.write_sectors * 512
            ios = s.reads + s.writes

            read_rate = read / self.duration if self.duration else 0
            write_rate = write / self.duration if self.duration else 0
            io_rate = (ios / self.duration) if self.duration else 0

            ret[d] = (read, read_rate, write, write_rate, ios, io_rate)

        self.latest = ret
        self.latest_titles = ("read", "read_rate", "write", "write_rate",
                              "ios", "io_rate")

        return ret

    def print_next(self, indent=""):
        stats = self.next()

        print("{}{c.bold}IO Stats:{c.rst}".format(indent, c=colours))
        indent += "  "

        for d, (rd, rd_rate, wr, wr_rate, io, io_rate) in stats.items():
            d = os.path.basename(d)

            rd = Suffix(rd)
            wr = Suffix(wr)
            io = Suffix(io, unit="IOPS", decimal=True)

            rd_rate = Suffix(rd_rate, unit="B/s")
            wr_rate = Suffix(wr_rate, unit="B/s")
            io_rate = Suffix(io_rate, unit="IOPS/s", decimal=True)

            print("{}{:<30} read:  {:>7.1f}  \t{:>7.1f}".
                  format(indent, d, rd, rd_rate))
            print("{}{:<30} wrote: {:>7.1f}  \t{:>7.1f}".
                  format(indent, "", wr, wr_rate))
            print("{}{:<30} ios:   {:>7.1f}  \t{:>7.1f}".
                  format(indent, "", io, io_rate))

    def csv(self):
        return tuple(x for y in self.latest.values() for x in y)

    def csv_titles(self):
        return tuple("{}:{}".format(n, x) for n in self.latest.keys() for x in
                     self.latest_titles)

if __name__ == "__main__":
    import time

    tl = IoStatsTimeline(period=2.0, devices=["/dev/nvme0n1", "/dev/sda"])

    while True:
        print(time.asctime())
        tl.print_next();
        print()
        print()
