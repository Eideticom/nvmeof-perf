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

suffix_re = re.compile(r"^([0-9\.]+)([KMGTP]?)", re.IGNORECASE)

suffix_bin_values = [('' , 1),
                 ('K', 1 << 10),
                 ('M', 1 << 20),
                 ('G', 1 << 30),
                 ('T', 1 << 40),
                 ('P', 1 << 50)]
suffix_bin_dict = dict(suffix_bin_values)

suffix_dec_values = [('' , 1),
                 ('K', 1e3),
                 ('M', 1e6),
                 ('G', 1e9),
                 ('T', 1e12),
                 ('P', 1e15)]
suffix_dec_dict = dict(suffix_dec_values)

def parse_suffix(value):
    m = suffix_re.match(value)
    if not m:
        raise ValueError("Could not parse: '{}'".format(value))

    value = float(m.group(1))
    value *= suffix_bin_dict[m.group(2).upper()]
    return value

class Suffix(object):
    def __init__(self, value, unit="B", decimal=False):
        self.unit = unit

        suffix_values = suffix_dec_values if decimal else suffix_bin_values

        for s, v in suffix_values[::-1]:
            if value < v:
                continue
            if s and not decimal:
                s+= "i"

            self.div = v
            self.value = float(value) / v
            self.suffix = s
            break
        else:
            self.value = float(value)
            self.suffix = ""

    def __format__(self, format):
        return ("{:" + format + "} {}{}").format(self.value, self.suffix,
                                                 self.unit)
