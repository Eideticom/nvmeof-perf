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

    def __init__(self, group="MEM", cpu="S0:0", *args, **kwargs):
        super(LikwidPerfMixin, self).__init__(*args, **kwargs)
        self.exe = ["likwid-perfctr", "-f", "-g", group, "-C", cpu] + self.exe
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

class LikwidTimeline(proc.ProcRunner):
    exe = ["likwid-perfctr"]
    col_re = re.compile(r"^(?P<name>[^\[\|]+)(\[(?P<units>.*?)\])?")
    kill_me = True

    def __init__(self, group="MEM", cpu=None, period=1.0, **kwargs):
        super().__init__(self, **kwargs)

        if cpu == None:
            cpu = likwid_all_sockets()

        self.args = ["-f", "-g", group, "-c", cpu, "-O"]
        data = sp.check_output(self.exe + self.args + ["-S", "10ms"])
        self.args += ["-t", "{}s".format(period)]
        cdata = csv.reader(StringIO(data.decode()), delimiter=",")

        for row in cdata:
            if row[0] == "TABLE" and row[1] == "Group 1 Metric":
                break

        self.cpus = [c for c in next(cdata)[1:] if c]
        self.cols = []
        self.units = []

        for row in cdata:
            if row[0] == "TABLE":
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

        self.queue = Queue()

    def wait_until_ready(self):
        while self.queue.empty():
            time.sleep(0.1)

    def __enter__(self):
        ret = super().__enter__()
        self.wait_until_ready()
        return ret

    def process_line(self, line):
        if line.startswith("1 "):
            cols = line.split()
        elif line.startswith("1,"):
            cols = line.split(",")
        else:
            return

        group_id = int(cols.pop(0))
        events = int(cols.pop(0))
        nthreads = int(cols.pop(0))
        timestamp = float(cols.pop(0))

        if events != len(self.cols):
            raise LikwidException("Unexpected number of events: {} != {}",
                                  events, len(self.cols))

        cpus = []
        for i in range(len(cols) // events):
            ncols = cols[i::(len(cols) // events)]
            ncols = [float(x) * m for x, m in zip(ncols, self.multiplier)]
            cpus.append(OrderedDict(zip(self.cols, ncols)))

        self.queue.put(cpus)

    def next(self):
        return self.queue.get()

    def print_next(self, indent=""):
        stats = self.next()

        print("{}{c.bold}Memory Bandwidth Stats:{c.rst}".
              format(indent, c=colours))
        indent += "  "

        for cname, c in zip(self.cpus, stats):
            read = Suffix(c["Memory read data volume"])
            write = Suffix(c["Memory write data volume"])
            read_bw = Suffix(c["Memory read bandwidth"], unit="B/s")
            write_bw = Suffix(c["Memory write bandwidth"], unit="B/s")

            print("{}{:<30} read:  {:>7.1f}  \t{:>7.1f}".
                  format(indent, cname, read, read_bw))
            print("{}{:<30} write: {:>7.1f}  \t{:>7.1f}".
                  format(indent, "", write, write_bw))

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
