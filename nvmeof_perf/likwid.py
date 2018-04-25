########################################################################
##
## Copyright 2015 PMC-Sierra, Inc.
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

from . import colours, proc
from .suffix import Suffix

import csv
import re
import subprocess as sp
import time

from queue import Queue
from io import StringIO
from collections import OrderedDict

class LikwidPerfMixin(object):
    likwid_re = re.compile(r"^\|\s+(?P<name>[^\[\|]+)" +
                           r"( \[(?P<units>.*?)\])?\s+" +
                           r"\|\s+(?P<value>[0-9\.e\+]+)\s+\|")

    def __init__(self, groups=["MEM"], cpu="S0:0", *args, **kwargs):
        super(LikwidPerfMixin, self).__init__(*args, **kwargs)
        groups = [y for x in zip(["-g"] * len(groups), groups) for y in x]
        self.exe = ["likwid-perfctr", "-f", "-C", cpu] + groups + self.exe
        self.likwid_stats = {}
        self.likwid_units = {}

    def process_line(self, line):
        super(LikwidPerfMixin, self).process_line(line)

        m = self.likwid_re.match(line)
        if not m: return
        self.likwid_stats[m.group("name")] = float(m.group("value"))
        self.likwid_units[m.group("name")] = m.group("units")

class LikwidException(Exception):
    pass

class _LikwidGroup(object):
    col_re = re.compile(r"^(?P<name>[^\[\|]+)(\[(?P<units>.*?)\])?")

    def __init__(self, name, group_id, cdata):
        self.cols = []
        self.units = []
        self.name = name
        self.group_id = group_id

        for row in cdata:
            if row[0] == "TABLE" and row[1] == "Group {} Metric".format(group_id):
                break

        self.cpus = [c for c in next(cdata)[1:] if c]

        for row in cdata:
            if row[0] == "TABLE" or row[0] == "STRUCT":
                break

            m = self.col_re.match(row[0])

            self.cols.append(m.group("name").strip())
            self.units.append(m.group("units"))

        self.cols = tuple(self.cols)
        self.units = self.units
        self.multiplier = [1] * len(self.units)

        for i in range(len(self.units)):
            if not self.units[i]:
                continue
            elif self.units[i].startswith("KByte"):
                self.multiplier[i] = 1 << 10
                self.units[i] = "B"
            elif self.units[i].startswith("MByte"):
                self.multiplier[i] = 1 << 20
                self.units[i] = "B"
            elif self.units[i].startswith("GByte"):
                self.multiplier[i] = 1 << 30
                self.units[i] = "B"
            elif self.units[i].startswith("TByte"):
                self.multiplier[i] = 1 << 40
                self.units[i] = "B"


class LikwidTimeline(proc.ProcRunner):
    exe = ["likwid-perfctr"]
    kill_me = True

    def __init__(self, groups=["L3", "MEM"], cpu=None, period=1.0, **kwargs):
        super().__init__(self, **kwargs)

        groups_args = [y for x in zip(["-g"] * len(groups), groups) for y in x]

        if cpu == None:
            cpu = likwid_all_sockets()

        period /= len(groups)

        self.args = ["-f", "-c", cpu, "-O"] + groups_args
        data = sp.check_output(self.exe + self.args + ["-S", "10ms"])
        self.args += ["-t", "{}s".format(period)]
        cdata = csv.reader(StringIO(data.decode()), delimiter=",")

        self.groups = OrderedDict()
        for i, name in enumerate(groups):
            grp_id = i + 1
            self.groups[grp_id] = _LikwidGroup(name, grp_id, cdata)

        self.queue = Queue()

    def wait_until_ready(self):
        while self.queue.qsize() < len(self.groups):
            time.sleep(0.1)

    def __enter__(self):
        ret = super().__enter__()
        self.wait_until_ready()
        return ret

    def process_line(self, line):
        if not line[0].isdigit():
            return

        if "," in line:
            cols = line.split(",")
        else:
            cols = line.split()

        group_id = int(cols.pop(0))
        events = int(cols.pop(0))
        nthreads = int(cols.pop(0))
        timestamp = float(cols.pop(0))

        grp = self.groups[group_id]

        if events != len(grp.cols):
            raise LikwidException("Unexpected number of events: {} != {}",
                                  events, len(grp.cols))

        cpus = []
        for i in range(len(cols) // events):
            ncols = cols[i::(len(cols) // events)]
            ncols = [float(x) * m for x, m in zip(ncols, grp.multiplier)]
            cpus.append(OrderedDict(zip(grp.cols, ncols)))

        self.queue.put((cpus, grp))

    def next(self):
        self.latest = OrderedDict()
        for g in self.groups.values():
            cpus, grp = self.queue.get()
            self.latest[grp.name] = cpus, grp
        return self.latest

    def print_MEM(self, grp, stats, indent=""):
        print("{}{c.bold}Memory Bandwidth Stats:{c.rst}".
              format(indent, c=colours))
        indent += "  "

        for cname, c in zip(grp.cpus, stats):
            read = Suffix(c["Memory read data volume"])
            write = Suffix(c["Memory write data volume"])
            read_bw = Suffix(c["Memory read bandwidth"], unit="B/s")
            write_bw = Suffix(c["Memory write bandwidth"], unit="B/s")

            print("{}{:<30} read:  {:>7.1f}  \t{:>7.1f}".
                  format(indent, cname, read, read_bw))
            print("{}{:<30} write: {:>7.1f}  \t{:>7.1f}".
                  format(indent, "", write, write_bw))

    def print_L3(self, grp, stats, indent=""):
        print("{}{c.bold}L3 Cache Stats:{c.rst}".
              format(indent, c=colours))
        indent += "  "

        for cname, c in zip(grp.cpus, stats):
            load = Suffix(c["L3 load data volume"])
            evict = Suffix(c["L3 evict data volume"])
            total = Suffix(c["L3 data volume"])

            load_bw = Suffix(c["L3 load bandwidth"], unit="B/s")
            evict_bw = Suffix(c["L3 evict bandwidth"], unit="B/s")
            total_bw = Suffix(c["L3 bandwidth"], unit="B/s")

            print("{}{:<30} load:  {:>7.1f}  \t{:>7.1f}".
                  format(indent, cname, load, load_bw))
            print("{}{:<30} evict: {:>7.1f}  \t{:>7.1f}".
                  format(indent, "", evict, evict_bw))
            print("{}{:<30} total: {:>7.1f}  \t{:>7.1f}".
                  format(indent, "", total, total_bw))

    def print_next(self, indent=""):
        for name, (stats, grp) in self.next().items():
            getattr(self, "print_" + name)(grp, stats, indent)

    def csv(self):
        return tuple(x for g in self.groups.values()
                     for y in self.latest[g.name][0]
                     for x in y.values())

    def csv_titles(self):
        return tuple("{}:{}".format(c, t) for g in self.groups.values()
                     for c in g.cpus for t in self.latest[g.name][0][0].keys())

def likwid_all_sockets():
    data = sp.check_output(["likwid-pin", "-p"]).decode()
    domain_re = re.compile(r"^Domain (S[0-9]+):$")

    sockets = []
    for l in data.split("\n"):
        m = domain_re.match(l)
        if m:
            sockets.append(m.group(1))

    return "@".join("{}:1".format(s) for s in sockets)

if __name__ == "__main__":
    tl = LikwidTimeline(cpu=likwid_all_sockets(), period=2.0)

    with tl:
        while True:
            print(time.asctime())
            tl.print_next();
            print()
            print()
