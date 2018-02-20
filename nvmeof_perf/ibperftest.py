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

from . import likwid, proc

import re
import threading

class PerfTestOutputMixin(object):
    def __init__(self, mbw=None, *args, **kwargs):
        super(PerfTestOutputMixin, self).__init__(*args, **kwargs)
        self.mbw = mbw
        self.mbw_stats = None

        self.results_line = False

        self.units = {}
        self.values = {}

    def _process_field(self, f):
        f = f.strip().strip("# ")
        if "[" in f:
            name, unit = f.split("[")
            unit = unit.strip("[]")
            self.units[name] = unit
            return name
        else:
            return f.strip()

    def process_line(self, line):
        super(PerfTestOutputMixin, self).process_line(line)

        if self.results_line:
            self.results_line = False

            try:
                line = [float(x) for x in line.split()]
                self.values.update(zip(self.fields, line))
                if self.mbw is not None:
                    self.mbw_stats = self.mbw.stats()
            except ValueError:
                pass
        elif line.startswith(" #bytes"):
            self.fields = [self._process_field(f) for f in  re.split(" {2,}", line)]
            self.results_line = True

    def finish(self):
        if self.mbw_stats is None and self.mbw is not None:
            self.mbw_stats = self.mbw.stats()

        super(PerfTestOutputMixin, self).finish()

    def bandwidth(self):
        bw = self.values.get("BW average", None)
        if bw is None: return None

        return bw * 1000**2

    def volume(self):
        bytes = self.values.get("bytes", None)
        its = self.values.get("iterations", None)

        if bytes is None or its is None:
            return None

        return bytes * its

    def latency(self):
        avg = self.values.get("t_typical", self.values.get("t_avg", None))
        if avg is None: return None

        mn = self.values.get("t_min", 0)
        mx = self.values.get("t_max", 0)

        return {'avg': avg,
                'min': mn,
                'max': mx}

class PerfTestServer(PerfTestOutputMixin, proc.ProcRunner):
    def __init__(self, command="ib_write_bw", block_size=8388608, duration=5,
                 mmap=None, test_args=[], *args, **kwargs):
        super(PerfTestServer, self).__init__(*args, **kwargs)
        self.exe = [command]
        self.args = ["-R", "-s", str(block_size), "-D", str(duration)]
        self.args += test_args

        if mmap:
            self.args += ["--mmap", mmap]

        self.ready = threading.Event()

    def process_line(self, line):
        super(PerfTestServer, self).process_line(line)

        if "Waiting for client to connect" in line:
            self.ready.set()

        if self.mbw is not None and line.startswith(" #bytes"):
            self.mbw.clear()

    def start(self):
        super(PerfTestServer, self).start()
        if not self.ready.wait(2):
            raise proc.ProcRunnerException(self,
                "Timed out waiting for perftest server to start")

class LikwidPerfTestServer(likwid.LikwidPerfMixin, proc.TimeMixin,
                           PerfTestServer):
    pass

class PerfTestClient(PerfTestOutputMixin, proc.TimeProcessLineMixin,
                     proc.ProcRunner):
    def __init__(self, host, command="ib_write_bw", block_size=8388608,
                 duration=5, test_args=[], *args, **kwargs):
        super(PerfTestClient, self).__init__(*args, **kwargs)
        self.exe = ["ssh", host, "time", "-p", command]
        self.args = ["-R", "${SSH_CLIENT%% *}", "-s", str(block_size),
                     "-D", str(duration)]
        self.args += test_args
