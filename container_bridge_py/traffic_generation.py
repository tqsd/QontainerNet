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
ROUNDS = int(sys.argv[2])
EPR_NUM = int(sys.argv[3])
PACKET_NUM = int(sys.argv[4])

def generate_packet(packet_size):
    packet = IP(dst=DESTINATION)
    return packet

def generate_epr_packet():
    #\x19 is first unused option
    packet = IP(dst=DESTINATION, options='\x19')
    return packet

def generate_traffic():
    if ROUNDS == -1:
        while True:
            generate_round()
    else:
        for r in range(ROUNDS):
            generate_round()

def generate_round():
    for i in range(EPR_NUM):
        packet = generate_epr_packet()
        send(packet)
    for i in range(PACKET_NUM):
        packet = generate_packet(0)
        send(packet)
if __name__=="__main__":
    generate_traffic()
