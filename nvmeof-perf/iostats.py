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
import stat
import sys

from collections import namedtuple

IoStats = namedtuple("IoStats", ["reads", "reads_merged",  "read_sectors",
                                 "read_ms", "writes", "writes_merged",
                                 "write_sectors", "write_ms",
                                 "ios_in_progress", "io_ms",
                                 "ios_weighted_ms"])

def iostats_get_path(device):
    if os.path.exists(device):
        st = os.stat(device)
        if not stat.S_ISBLK(st.st_mode):
            raise IOError("{} is not a block device".format(device))

        major=os.major(st.st_rdev)
        minor=os.minor(st.st_rdev)
        return os.path.join("/sys", "dev", "block",
                            "{}:{}".format(major, minor), "stat")

    else:
        path = os.path.join("/sys", "class", "block", device, "stat")
        if not os.path.exists(path):
            raise IOError("Block device not found: {}".format(device))

        return path

def iostats_device_stats(device):
    data = open(iostats_get_path(device)).read().split()

    return IoStats._make(int(x) for x in data)

def iostats_stats(devices):
    ret = {}
    for d in devices:
        ret[d] = iostats_device_stats(d)
    return ret

if __name__ == "__main__":
    stats = iostats_stats(sys.argv[1:])

    for s, t in stats.items():
        print("{:<20}".format(s), t)
