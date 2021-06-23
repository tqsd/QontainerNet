"""
Bridge script catches packages from netfilterqueue
and adds puts them through custom channels
"""
import os
import time
from datetime import datetime
from threading import Thread

from netfilterqueue import NetfilterQueue
from qunetsim.components import Host
from qunetsim.backends import ProjectQBackend
from qunetsim.components import Network
from qunetsim.objects import Qubit
from scapy.all import *

from quantum_bridge.threaded_channel.channel import Channel
from quantum_bridge.simple_bridge import SimpleChannel


LOGFILE = "/app/log.txt"

BRIDGE_START_TIME = datetime.now()

def bw_calc(start_time, end_time, packet_bit_len):
    """
    Returns bandwidth in bits/seconds
    """
    delta_time = end_time - start_time
    delta_time = delta_time.seconds + delta_time.microseconds/1E6
    #Bandwidth b/s
    bw = packet_bit_len/delta_time
    return 





def log_info(LOGFILE, start_time, end_time, packet, C):
    packet_bit_len = len(packet)*8
    bw = bw_calc(start_time, end_time, packet_bit_len)
    # start_time, end_time, bit_len, bandwidth
    start_time = start_time - BRIDGE_START_TIME
    start_time = start_time.seconds()
    end_time = end_time - BRIDGE_START_TIME
    end_time = end_time.seconds()
    G = packet_bit_len
    line = [str(start_time), str(end_time), str(packet_bit_len), str(bw), str(C), str(G), f"{G/C:.3f}"]
    line = "|".join(line)
    print(f"Logging the following line \n{line}")





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

print(hosts)

quantum_protocol = SimpleChannel()

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

def packet_processing_thread(pkt):
    print("TEST")
    t = Thread(target=packet_processing, args=(pkt, ))
    t.start()

def packet_processing(pkt):
    """
    Gets called for every packet in the netfilter queue
    """
    with open("/proc/net/netfilter/nfnetlink_queue", "r") as proc_file:
        proc_line = [x for x in proc_file.readline().split(" ") if x]
        print(f"Packets in queue:  {proc_line[2]}")
        #print(f"Packets processed: {proc_line[7]}")
        #TEMP
        packet = IP(pkt.get_payload())
        pkt.drop()
        return

    with open(LOGFILE, "a") as logfile:
        pkt.drop()
        start = datetime.now()
        packet = IP(pkt.get_payload())
        packet_bits = to_bit_array(packet)

        source_address = packet[IP].src
        print(f"Packet received from {source_address}")

        new_packet_bits, cost = quantum_protocol.transmit_packet(packet_bits, source_address)

        new_packet = IP(from_bit_array(new_packet_bits))
        send(new_packet)
        end = datetime.now()
        log_info("badnwidt.log", start, end, new_packet_bits, cost)
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
nfqueue.bind(1, packet_processing_thread)
print("Listening on a netfilter queue 1")
#print("Started with entanglement generation")
#t = DaemonThread(quantu, costm_protocol.entanglement_generation)
#Create file to signal that bridge has started
open(LOGFILE, 'a').close()

try:
    nfqueue.run()
except KeyboardInterrupt:
    print('')

nfqueue.unbind()
