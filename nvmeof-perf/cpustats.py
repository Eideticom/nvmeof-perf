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

import utils
from suffix import Suffix

import os

from collections import namedtuple

class CpuStats(namedtuple("CpuStats", ["user", "system", "idle",
                                       "iowait", "total", "intr",
                                       "mem_total", "mem_avail",
                                       "mem_used"])):
    def __sub__(a, b):
        return CpuStats(user=a.user - b.user,
                        system=a.system - b.system,
                        idle=a.idle - b.idle,
                        iowait=a.iowait - b.iowait,
                        total=a.total - b.total,
                        intr=a.intr - b.intr,
                        mem_total=a.mem_total,
                        mem_avail=a.mem_avail,
                        mem_used=a.mem_used)

def cpu_stats():
    ret = {}
    time_per_jiffie = 1 / os.sysconf(os.sysconf_names['SC_CLK_TCK'])

    ret = {}

    for l in open("/proc/stat").readlines():
        data = l.split()

        if data[0] == "cpu":
            ret["user"] = (int(data[1]) + int(data[2])) * time_per_jiffie
            ret["system"] = ((int(data[3]) + int(data[6]) + int(data[7])) *
                              time_per_jiffie)
            ret["idle"] = int(data[4]) * time_per_jiffie
            ret["iowait"] = int(data[5]) * time_per_jiffie
            ret["total"] = (ret["user"] + ret["system"] + ret["idle"] +
                            ret["iowait"])

        elif data[0] == "intr":
            ret["intr"] = int(data[1])

    for l in open("/proc/meminfo").readlines():
        name, value = l.split(":")

        try:
            value, unit = value.strip().split()
        except ValueError:
            pass

        value = int(value)

        if name == "MemTotal":
            ret["mem_total"] = value * 1024
        elif name == "MemAvailable":
            ret["mem_avail"] = value * 1024

    ret["mem_used"] = ret["mem_total"] - ret["mem_avail"]

    return CpuStats(**ret)

class CpuTimeline(utils.Timeline):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last = None

    def next(self):
        super().next()

        stats_new = cpu_stats()

        if self.last:
            stats = stats_new - self.last
        else:
            stats = stats_new

        self.last = stats_new

        return stats

    def print_next(self, indent=""):
        stats = self.next()

        print("{}CPU Stats:".format(indent))
        indent += "  "

        def print_line(typ):
            print("{}{:<39} {:>7.1f}  \t{:>7.1%}".
                  format(indent, typ.title() + ":", getattr(stats, typ),
                         getattr(stats, typ) / stats.total))

        print_line("idle")
        print_line("user")
        print_line("system")
        print_line("iowait")

        mem_used = Suffix(stats.mem_used)

        print("{}{:<39} {:>7.1f}  \t{:>7.1%}".
              format(indent, "Memory Used:", mem_used,
                     stats.mem_used / stats.mem_total))

if __name__ == "__main__":
    import time

    tl = CpuTimeline()
    while True:
        print(time.asctime())
        tl.print_next();
        print()
        print()
