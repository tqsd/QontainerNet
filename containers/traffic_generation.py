"""
Artificial simple traffic generation script
Script input variables:
- packet size
- time between packets
"""
from scapy.all import *
import time
import sys

DESTINATION = str(sys.argv[1])
SLEEP_TIME  = int(sys.argv[2])
NUMBER_OF_PACKETS = int(sys.argv[3])

def generate_packet(packet_size):
    packet = IP(dst=DESTINATION)
    return packet

def generate_traffic():
    for i in range(NUMBER_OF_PACKETS):
        packet = generate_packet(0)
        send(packet)
        time.sleep(SLEEP_TIME)

if __name__=="__main__":
    generate_traffic()
