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

import likwid
import proc
import suffix

import re
import threading

class FioRunner(proc.ProcRunner):
    def __init__(self, test_args=[], **kwargs):
        self.exe = ["fio", "-"]

        self.extra_job_lines = "\n".join(test_args)
        super(FioRunner, self).__init__(**kwargs)

    def setup(self):
        opts = dict(self.__class__.__dict__)
        opts.update(self.__dict__)

        job = self.job.format(**opts)
        job = job + "\n" + self.extra_job_lines

        if self.log_file:
            print("\n", file=self.log_file)
            print("-"*40, file=self.log_file)
            print("Job File", file=self.log_file)
            print("-"*40, file=self.log_file)
            for l in job.split():
                print(l.strip(), file=self.log_file)
            print("-"*40, file=self.log_file)
            print("", file=self.log_file)

        self.p.stdin.write(job.encode())
        self.p.stdin.close()

class FioServer(FioRunner):
    job = """[rdma-server]
             rw=read
             ioengine=rdma
             port=11692
             bs={block_size}
             size={size}"""

    mbw_stats = {}

    def __init__(self, command=None, block_size=1<<20, size=100<<40,
                 duration=None,  mbw=None, mmap=None, **kwargs):
        self.block_size = block_size
        if self.block_size < 4096: self.block_size = 4096
        self.size = size
        self.mbw = mbw
        self.mbw_started = False
        self.mmap = mmap
        if self.mmap is not None:
            self.job += "\nmem=mmapshared:{mmap}"

        self.ready = threading.Event()

        super(FioServer, self).__init__(**kwargs)

    def process_line(self, line):
        super(FioServer, self).process_line(line)

        if "waiting for connection" in line:
            self.ready.set()
        elif (self.mbw is not None and not self.mbw_started and
              line.startswith("Jobs")):
            self.mbw.clear()
            self.mbw_started = True
        elif self.mbw_started and line.startswith("rdma-server"):
            self.mbw_stats = self.mbw.stats()
            self.mbw_started = False

    def start(self):
        super(FioServer, self).start()
        if not self.ready.wait(6):
            raise proc.ProcRunnerException(self,
            		"Timed out waiting for fio server to start")

    def bandwidth(self):
        return None

    def latency(self):
        return None

    def volume(self):
        return None

class LikwidFioServer(likwid.LikwidPerfMixin, proc.TimeMixin, FioServer):
    pass

class FioClient(proc.TimeProcessLineMixin, FioRunner):
    job = """[rdma-client]
             rw=write
             ioengine=rdma
             runtime={duration}
             hostname=${{SERVER}}
             port=11692
             verb={verb}
             bs={block_size}
             size={size}"""

    def __init__(self, host, command="fio:write", duration=10, block_size=512,
                 size=100<<40, **kwargs):
        self.block_size = block_size
        self.size = size
        if ":" in command:
            self.verb = command.split(":")[1]
        else:
            self.verb = "write"
        self.duration = duration
        self._volume = self._bandwidth = self._latency = None

        super(FioClient, self).__init__(**kwargs)

        self.args = ["SERVER=${SSH_CLIENT%% *}", "time", "-p"] + self.exe
        self.exe = ["ssh", host]

    lat_re = re.compile(r"^[^:]*: *min= *(?P<min>[0-9.e]+), *"
                        r"max= *(?P<max>[0-9.e]+), *"
                        r"avg= *(?P<avg>[0-9.e]+), *"
                        r"stdev= *(?P<stdev>[0-9.e]+)")

    def process_line(self, line):
        super(FioClient, self).process_line(line)

        line = line.strip()
        if line.startswith("write:"):
            line = line.split()
            self._volume = suffix.parse_suffix(line[1].split("=")[1])
            self._bandwidth = suffix.parse_suffix(line[2].split("=")[1])
        elif line.startswith("lat"):
            m = self.lat_re.match(line)
            if m:
                self._latency = {k: float(v) for k,v in m.groupdict().items()}

    def bandwidth(self):
        return self._bandwidth

    def latency(self):
        return self._latency

    def volume(self):
        return self._volume
