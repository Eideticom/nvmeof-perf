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

import re

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
