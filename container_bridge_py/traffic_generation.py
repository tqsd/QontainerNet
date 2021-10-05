"""
Artificial simple traffic generation script
Script input variables:
- packet size
- time between packets
"""
from scapy.all import *
import random
import time
import sys

DESTINATION = str(sys.argv[1])
ROUNDS = int(sys.argv[2])
EPR_NUM = int(sys.argv[3])
PACKET_NUM = int(sys.argv[4])

PACKET_SIZE = 0
if len(sys.argv) > 5:
    PACKET_SIZE = int(sys.argv[5])

TYPE = "periodic"
if len(sys.argv) > 6:
    TYPE = sys.argv[6]

PROBABILITY = 0.5
if len(sys.argv) > 7:
    PROBABILITY = float(sys.argv[7])

def generate_packet(packet_size):
    packet = IP(dst=DESTINATION, src="11.0.0.1")
    packet_size = packet_size - 48
    if packet_size < 0:
        packet_size = 0
    load = bytearray([0]*packet_size)

    packet = packet/Raw(load=load)
    print(len(packet))
    return packet

def generate_epr_packet():
    #\x19 is first unused option
    packet = IP(dst=DESTINATION, options='\x19')
    return packet

def generate_traffic_periodic():
    if ROUNDS == -1:
        while True:
            generate_round()
    else:
        for r in range(ROUNDS):
            generate_round()

def generate_traffic_random():
    if ROUNDS == -1:
        while True:
            generate_random_round()
    else:
        for r in range(ROUNDS):
            generate_random_round()

def generate_random_round():
    packet = None
    if random.choices([True, False], [PROBABILITY, 1-PROBABILITY])[0]:
        packet = generate_packet(PACKET_SIZE)
    else:
        packet = generate_epr_packet()
    send(packet)
    time.sleep(2)

def generate_round():
    for i in range(EPR_NUM):
        packet = generate_epr_packet()
        send(packet)
        time.sleep(2)
    for i in range(PACKET_NUM):
        packet = generate_packet(PACKET_SIZE)
        send(packet)
        time.sleep(2)
if __name__=="__main__":
    if TYPE == "periodic":
        generate_traffic_periodic()
    else:
        generate_traffic_random()
