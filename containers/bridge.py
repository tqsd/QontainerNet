from netfilterqueue import NetfilterQueue
from qunetsim.components import Host
from qunetsim.backends import ProjectQBackend
from qunetsim.components import Network
from qunetsim.objects import Qubit
from scapy.all import *

from quantumBridge.Channel import SimpleBufferedQuantumChannel, DaemonThread, SimpleQuantumChannel

import time
import os

LOGFILE = "/app/log.txt"

def to_bit_array(pkt):
    byte_list = list(raw(pkt))
    bin_list = [format(x, "#010b") for x in byte_list]
    bin_list = [x[2:] for x in bin_list]
    return bin_list

def from_bit_array(bin_list):
    print(bin_list)
    byte_list = [hex(int(x,2)) for x in bin_list] 
    result = bytes([int(x,0) for x in byte_list])
    return result 
    

quantum_protocol = SimpleBufferedQuantumChannel()


def packet_processing(pkt):
    print("Packet has arrived")
    with open(LOGFILE, "a") as logfile:
        start = time.time()
        packet = IP(pkt.get_payload())
        packet_bits = to_bit_array(packet)

        #new_packet_bits = quantum_protocol.transmit_packet(packet_bits)
        new_packet_bits = packet_bits
        new_packet = IP(from_bit_array(new_packet_bits))

        #send(new_packet)
        end = time.time()
        logfile.write("PACKET TRANSMITTED_________________\n")
        logfile.write(hexdump(packet, dump=True) + "\n")
        logfile.write(hexdump(new_packet, dump=True)+ "\n")
        logfile.write("Transmission time:" + str(end-start) + "\n")
        packet.show()
        new_packet.show()

try:
    os.remove(LOGFILE)
except OSError:
    pass


nfqueue = NetfilterQueue()
nfqueue.bind(1, packet_processing)
print("Listening on a netfilter queue 1")
#print("Started with entanglement generation")
#t = DaemonThread(quantum_protocol.entanglement_generation)
#Create file to signal that bridge has started
open(LOGFILE, 'a').close()

try:
    nfqueue.run()
except KeyboardInterrupt:
    print('')

nfqueue.unbind()
