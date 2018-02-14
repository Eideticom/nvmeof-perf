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

import os

def cpu_stats():
    ret = {}
    time_per_jiffie = 1 / os.sysconf(os.sysconf_names['SC_CLK_TCK'])

    ret = {}

    for l in open("/proc/stat").readlines():
        data = l.split()

        if data[0] == "cpu":
            ret["user"] = (int(data[1]) + int(data[2])) * time_per_jiffie
            ret["system"] = int(data[3]) * time_per_jiffie
            ret["idle"] = int(data[4]) * time_per_jiffie
            ret["iowait"] = int(data[4]) * time_per_jiffie
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

    return ret

if __name__ == "__main__":
    print(cpu_stats())
