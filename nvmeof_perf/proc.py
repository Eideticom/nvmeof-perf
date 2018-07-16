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

import os
import pty
import re
import signal
import subprocess as sp
import sys
import threading
import time
import traceback

class ProcRunnerException(Exception):
    def __str__(self):
        pr, msg = self.args

        ret = "".join(pr.output_lines) + "\n\n"
        ret += msg + "\n"
        ret += "  " + " ".join(pr.exe + pr.args)
        return ret

class ProcRunner(threading.Thread):
    kill_sig = signal.SIGINT

    def __init__(self, log_file=None, print_output=False,
                 wait_for=False, *args, **kws):
        self.log_file = log_file
        self.print_output = print_output
        self.kill_me = not wait_for
        self.started = threading.Event()
        self.exception = None
        self.output_lines = []
        self.args = []
        super(ProcRunner, self).__init__(*args, **kws)

    def process_line(self, line):
        self.output_lines.append(line)

        if self.log_file:
            self.log_file.write(line)
        if self.print_output:
            sys.stdout.write(line)
            sys.stdout.flush()

    def setup(self):
        pass

    def finish(self):
        pass

    def run(self):
        try:
            master, slave = pty.openpty()
            self.slave = slave

            self.p = sp.Popen(self.exe + self.args,
                                  stdin=sp.PIPE,
                                  stdout=slave,
                                  stderr=slave,
                                  preexec_fn=os.setsid)

            mf = os.fdopen(master, "U")

            self.setup()

            while True:
                self.started.set()
                line = mf.readline()

                try:
                    self.process_line(line)
                except:
                    print("Exception occured while processing line:")
                    traceback.print_exc()

        except Exception as e:
            self.started.set()
            self.exception = sys.exc_info()

    def check_started(self):
        self.started.wait(2)
        if self.exception:
            self.join(5)
            raise self.exception[1]

    def start(self):
        super(ProcRunner, self).start()
        self.check_started()

    def wait(self):
        if self.started.wait(2):
            killed = False

            if self.p.poll() is None:
                #Delay a bit and see if the process finishes on its own
                time.sleep(0.1)

            if self.p.poll() is None and self.kill_me:
                killed = True
                os.killpg(self.p.pid, self.kill_sig)

            try:
                ret = self.p.wait()
            except KeyboardInterrupt:
                killed = True
                os.killpg(self.p.pid, self.kill_sig)
                ret = self.p.wait()

            os.close(self.slave)

        else:
            raise ProcRunnerException(self, "Timed out waiting for process "
                                      "to start")

        self.join(1)
        if ret and not killed:
            raise ProcRunnerException(self, "Error occured while running "
                                      "command")

        return ret

    def __enter__(self):
        try:
            self.start()
        except:
            try:
                self.wait()
            finally:
                raise

        return self

    def __exit__(self, type, value, traceback):
        self.wait()


class TimeProcessLineMixin(object):
    time_re = re.compile(r"^(?P<name>real|user|sys) (?P<value>[0-9\.]+)$")

    def __init__(self, *args, **kwargs):
        super(TimeProcessLineMixin, self).__init__(*args, **kwargs)
        self.time_stats = {}

    def process_line(self, line):
        super(TimeProcessLineMixin, self).process_line(line)

        m = self.time_re.match(line)
        if not m: return

        name = m.group('name')
        value = float(m.group('value'))
        self.time_stats[name] = value

        if 'user' in self.time_stats and 'sys' in self.time_stats:
            self.time_stats['total'] = (self.time_stats['user'] +
                                        self.time_stats['sys'])


    def calculate_results(self, duration=None, *args, **kwargs):
        if duration is not None:
            self.time_stats["duration"] = duration
            self.time_stats["cpu_percent_duration"] = \
                (100 * self.time_stats["total"] / duration)

        self.time_stats["cpu_percent_total"] = (self.time_stats["total"] /
                                                self.time_stats["real"]) * 100

class TimeMixin(TimeProcessLineMixin):
    def __init__(self, *args, **kwargs):
        super(TimeMixin, self).__init__(*args, **kwargs)
        self.exe = ["time", "-p"] + self.exe
