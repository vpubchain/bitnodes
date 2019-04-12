tcpdump -i ens33 -w %s.ens33.pcap -v -n -G 2 -B 65536 -Z root > ens33 2>&1 &
tcpdump -i lo -w %s.lo.pcap -v -n -G 2 -B 65536 -Z root 'tcp and port 9050' > lo 2>&1 &
#tcpdump -i [ens33] -w %s.[ens33.pcap -v -n -G 2 -B 65536 -Z [root] 'tcp and not src host [IP_ADDRESS] and not src host [IPV6_ADDRESS]' > [ens33] 2>&1 &
#tcpdump -G 60 -Z root -w %Y_%m%d_%H%M_%S.pcap &
