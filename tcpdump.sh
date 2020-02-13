tcpdump -i eth0 -w %s.eth0.pcap -v -n -G 2 -B 65536 -Z root > eth0 2>&1 &
