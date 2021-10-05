"""
Bridge script catches packages from netfilterqueue
and adds puts them through custom channels
"""
import os
import time
import sys

from netfilterqueue import NetfilterQueue
from qunetsim.components import Host
from qunetsim.backends import ProjectQBackend
from qunetsim.components import Network
from qunetsim.objects import Qubit
from scapy.all import *

from quantum_bridge.threaded_channel.channel import Channel
from quantum_bridge.simple_bridge import SimpleChannel


LOGFILE = "/app/log.txt"


def to_bit_array(pkt):
    """
    Takes packet netfilterqueue packet and returns list
    bytes as list of integers representing bits
    """
    byte_list = list(raw(pkt))
    bin_list = [format(x, "#010b") for x in byte_list]
    bin_list = [x[2:] for x in bin_list]
    return bin_list


def from_bit_array(bin_list):
    """
    Takes list of bytes as list of integers representing bits
    and returns raw bytes that can be used to reconstruct a packet
    """
    print(bin_list)
    byte_list = [hex(int(x,2)) for x in bin_list]
    result = bytes([int(x,0) for x in byte_list])
    return result

hosts = []
with open("/app/hosts.txt", "r") as host_file:
    for line in host_file.readlines():
        hosts.append(line.rstrip())

epr_frame_size = 40
if len(sys.argv) > 1:
    epr_frame_size = int(sys.argv[1])
buffer_size = None
if len(sys.argv) > 2:
    buffer_size = int(sys.argv[2])

quantum_protocol = Channel(hosts, epr_frame_size)

def packet_diff(in_bits:list, out_bits:list):
    """
    Compares in_bits and out_bits to see what errors
    occured during transmission
    NEEDS TO BE IMPLEMENTED
    """
    print("PACKET DIFF")
    print(in_bits)
    print(out_bits)
    for i, i_bits in enumerate(in_bits):
        try:
            if i_bits != out_bits[i]:
                print(i_bits, out_bits[i])
        except e:
            print(e)
            print("Exception in packet_diff")
            break



def packet_processing(pkt):
    """
    Gets called for every packet in the netfilter queue
    """
    with open("/proc/net/netfilter/nfnetlink_queue", "r") as proc_file:
        proc_line = [x for x in proc_file.readline().split(" ") if x]
        print(f"Packets in queue:  {proc_line[2]}")
        #print(f"Packets processed: {proc_line[7]}")

    with open(LOGFILE, "a") as logfile:
        pkt.drop()
        start = time.time()
        print(pkt.get_payload())
        print(pkt.get_payload_len())
        packet = IP(pkt.get_payload())
        packet_bits = to_bit_array(packet)

        source_address = packet[IP].src
        print(f"Packet received from {source_address}")

        raw_bytes_list = list(raw(packet))
        print(raw_bytes_list)
        if len(raw_bytes_list) == 52 and raw_bytes_list[-4] == 25:
            print("EPR SIGNAL RECEIVED")
            epr_packet_bits = quantum_protocol.transmit_packet('epr', source_address, "epr")
            return


        new_packet_bits = quantum_protocol.transmit_packet(packet_bits, source_address, "normal")
        print("SENDING ONWARDS")
        new_packet = IP(from_bit_array(new_packet_bits))
        send(new_packet)
        end = time.time()
        logfile.write("PACKET TRANSMITTED_________________\n")
        logfile.write(hexdump(packet, dump=True) + "\n")
        logfile.write(hexdump(new_packet, dump=True) + "\n")
        logfile.write("Transmission time:" + str(end-start) + "\n")
        #packet.show()
        #new_packet.show()


try:
    os.remove(LOGFILE)
except OSError:
    pass


nfqueue = NetfilterQueue()
if buffer_size == None:
    nfqueue.bind(1, packet_processing)
else:
    nfqueue.bind(1, packet_processing, buffer_size)


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
