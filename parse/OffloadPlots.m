## Copyright (C) 2018 Eideticom, Inc
## 
## This program is free software; you can redistribute it and/or modify it
## under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.

## Author: Stephen Bates <stephen@eideticom.com>
## Created: 2018-02-23

close all ; clear all ; clc

  # Some important columns

%1 timestamp
%2 idle
%3 idle_pct
%4 user
%5 user_pct
%6 system
%7 system_pct
%8 iowait
%9 iowait_pct
%10 mem_used
%11 mem_used_pct
%12 intr
%13 ctxt
%14 Core 1:Runtime (RDTSC)
%15 Core 1:Runtime unhalted
%16 Core 1:Clock
%17 Core 1:CPI
%18 Core 1:Memory read bandwidth
%19 Core 1:Memory read data volume
%20 Core 1:Memory write bandwidth
%21 Core 1:Memory write data volume
%22 Core 1:Memory bandwidth
%23 Core 1:Memory data volume
%24 /dev/nvme0n1:read
%25 /dev/nvme0n1:read_rate
%26 /dev/nvme0n1:write
%27 /dev/nvme0n1:write_rate
%28 /dev/nvme0n1:ios
%29 /dev/nvme0n1:io_rate
%30 mlx0p1:tx
%31 mlx0p1:rx
%32 mlx0p1:tx_rate
%33 mlx0p1:rx_rate
%34 switchtec0:upstream:ingress
%35 switchtec0:upstream:egress
%36 switchtec0:upstream:ingress_rate
%37 switchtec0:upstream:egress_rate
%38 switchtec0:p2pmem1:ingress
%39 switchtec0:p2pmem1:egress
%40 switchtec0:p2pmem1:ingress_rate
%41 switchtec0:p2pmem1:egress_rate
%42 "switchtec0:nvme0 p2pmem0:ingress"
%43 "switchtec0:nvme0 p2pmem0:egress"
%44 "switchtec0:nvme0 p2pmem0:ingress_rate"
%45 "switchtec0:nvme0 p2pmem0:egress_rate"
%46 "switchtec0:mlx5_0 mlx0p1:ingress"
%47 "switchtec0:mlx5_0 mlx0p1:egress"
%48 "switchtec0:mlx5_0 mlx0p1:ingress_rate"
%49 "switchtec0:mlx5_0 mlx0p1:egress_rate"


  # Load in all the interesting data.

matVanilla   = csvread('vanilla.csv');
matOffload   = csvread('offload.csv');
matP2pmem    = csvread('p2pmem.csv');
matOffP2pmem = csvread('offload+p2pmem.csv');

peTimeVanilla   = matVanilla(2:end,1) - matVanilla(2,1);
peTimeOffload   = matOffload(2:end,1) .- matOffload(2,1);
peTimeP2pmem    = matP2pmem(2:end,1) .- matP2pmem(2,1);
peTimeOffP2pmem = matOffP2pmem(2:end,1) .- matOffP2pmem(2,1);

figMem = figure();
hold on ; grid on ; zoom on
plot(peTimeVanilla, matVanilla(2:end, 22))
plot(peTimeOffload, matOffload(2:end, 22),'r')
plot(peTimeP2pmem, matP2pmem(2:end, 22),'g')
plot(peTimeOffP2pmem, matOffP2pmem(2:end, 22),'m')
xlabel('Time, seconds')
ylabel('CPU Memory BW (GB/s)')
legend('Vanilla','Offload', 'p2pmem', 'Offload+p2pmem')
title('CPU Memory Bandwidth vs Time')
axis([0 80 0 4e9]);

figCpu = figure();
hold on ; grid on ; zoom on
plot(peTimeVanilla, 100*matVanilla(2:end, 7))
plot(peTimeOffload, 100*matOffload(2:end, 7),'r')
plot(peTimeP2pmem, 100*matP2pmem(2:end, 7),'g')
plot(peTimeOffP2pmem, 100*matOffP2pmem(2:end, 7),'m')
xlabel('Time, seconds')
ylabel('CPU Utilization')
legend('Vanilla','Offload', 'p2pmem', 'Offload+p2pmem')
title('CPU Utilization vs Time')
axis([0 80 0 10]);

figPciCpu = figure();
hold on ; grid on ; zoom on
plot(peTimeVanilla, matVanilla(2:end, 36) + matVanilla(2:end, 37))
plot(peTimeOffload, matOffload(2:end, 36) + matOffload(2:end, 37),'r')
plot(peTimeP2pmem, matP2pmem(2:end, 36) + matP2pmem(2:end, 37),'g')
plot(peTimeOffP2pmem, matOffP2pmem(2:end, 36) + matOffP2pmem(2:end, 37),'m')
xlabel('Time, seconds')
ylabel('CPU PCIe Bandwidth')
legend('Vanilla','Offload', 'p2pmem', 'Offload+p2pmem')
title('CPU PCIe Bandwidth vs Time')
axis([0 80 0 8e9]);

figPciNvme = figure();
hold on ; grid on ; zoom on
plot(peTimeVanilla, matVanilla(2:end, 44) + matVanilla(2:end, 45))
plot(peTimeOffload, matOffload(2:end, 44) + matOffload(2:end, 45),'r')
plot(peTimeP2pmem, matP2pmem(2:end, 44) + matP2pmem(2:end, 45),'g')
plot(peTimeOffP2pmem, matOffP2pmem(2:end, 44) + matOffP2pmem(2:end, 45),'m')
xlabel('Time, seconds')
ylabel('NVMe PCIe Bandwidth')
legend('Vanilla','Offload', 'p2pmem', 'Offload+p2pmem')
title('NVMe PCIe Bandwidth vs Time')
axis([0 80 0 4e9]);

figCx5Eth = figure();
hold on ; grid on ; zoom on
plot(peTimeVanilla, matVanilla(2:end, 32) + matVanilla(2:end, 33))
plot(peTimeOffload, matOffload(2:end, 32) + matOffload(2:end, 33),'r')
plot(peTimeP2pmem, matP2pmem(2:end, 32) + matP2pmem(2:end, 33),'g')
plot(peTimeOffP2pmem, matOffP2pmem(2:end, 32) + matOffP2pmem(2:end, 33),'m')
xlabel('Time, seconds')
ylabel('ConnectX-5 RDMA Bandwidth')
legend('Vanilla','Offload', 'p2pmem', 'Offload+p2pmem')
title('ConnectX-5 RDMA Bandwidth vs Time')
axis([0 80 0 4e9]);

print(figMem, "figMem.png",'-dpng');
print(figCpu, "figCpu.png",'-dpng');
print(figPciCpu, "figPciCpu.png",'-dpng');
print(figPciNvme, "figPciNvme.png",'-dpng');
print(figCx5Eth, "figCx5Eth.png",'-dpng');
