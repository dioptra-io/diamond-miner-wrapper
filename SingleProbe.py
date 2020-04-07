from scapy.all import sr1, IP, TCP
from ipaddress import IPv4Address

if __name__ == "__main__":

    destinations = []
    with open("resources/traceroute_list.txt") as f:
        for line in f:
            line = line.strip("\n")
            destinations.append(line)

    for i in range(1, len(destinations), 255):
        destination = destinations[i]
        print(destination)
        s_port = 24000
        d_port = 33434
        ttl = 30
        probe = IP(dst=destination, ttl=ttl, id=ttl) / TCP(
            sport=s_port, dport=d_port, seq=20000
        )
        # print(probe.show())
        p = sr1(probe, timeout=0.5, verbose=False)
        if p:
            p.show()
            print(IPv4Address(p[IP].src))
