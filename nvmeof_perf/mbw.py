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

from . import proc, likwid

import re
from itertools import repeat, chain

class MBWRunner(proc.ProcRunner):
    exe = ["mbw"]
    mbw_re = re.compile(r"(?P<N>[0-9]+)\s+" +
                        r"Method: (?P<method>[A-Z]+)\s+" +
                        r"Elapsed: (?P<elapsed>[0-9\.]+)\s+" +
                        r"MiB: (?P<mib>[0-9\.]+)\s+" +
                        r"Copy: (?P<rate>[0-9\.]+) MiB/s+")


    def __init__(self, loops=10000, array_size_mb=512, tests=[0],
                 *args, **kws):

        super(MBWRunner, self).__init__(*args, **kws)
        tests = [str(t) for t in tests]
        self.args = (["-n", str(loops)] +
                     list(chain(*zip(repeat('-t'), tests))) +
                     [str(array_size_mb)])
        self.rates = []
        self.volume = 0.

    def process_line(self, line):
        super(MBWRunner, self).process_line(line)

        m = self.mbw_re.match(line)
        if not m: return

        self.volume += float(m.group("mib")) * (1 << 20)
        rate = float(m.group("rate")) * (1 << 20)
        self.rates.append(rate)

    def clear(self):
        self.rates = []

    def stats(self):
        r = self.rates[1:-1]

        if not r: return {}
        return {"max": max(r),
                "min": min(r),
                "avg": sum(r) / len(r),
                "count": len(r),
                "volume": (self.volume * 2)} # multiply by 2 for read and write

class LikwidMBWRunner(likwid.LikwidPerfMixin, MBWRunner):
    pass
