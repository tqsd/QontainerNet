#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example to test quantum connection with Qontainernet
"""
from itertools import filterfalse
import random
import os
import csv
import numpy as np
import time
import subprocess
from scapy.all import *
from comnetsemu.cli import CLI
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

from qontainernet import Qontainernet


def test_topo(net,
              packet_generation_probability= 0.2,
              epr_buffer_size = 0.1,
              ea_rate=0.2,
              nea_rate=0.1,
              packet_size = 500,
              classical_buffer_size = 1, #in mbits
              test_length=100,
              ):
    """Run test topology: double hop"""
    if packet_size < 42:
        packet_size=0

    """2 second buffer"""
    #if classical_buffer_size is None:

    info(f"--> Running interface based GEWI simulation\n")
    info(f"---> PARAMS:\n")
    info(f"     - PACKET GENERATION PROBABILITY: {packet_generation_probability}\n")
    info(f"     - PACKET SIZE                  : {packet_size}bytes \n")
    info(f"     - ENTANGLEMENT BUFFER SIZE     : {epr_buffer_size}mbit\n")
    info(f"     - CLASSICAL BUFFER SIZE        : {classical_buffer_size}mbits\n")
    info(f"     - EA TRANSMISSION RATE         : {ea_rate} mbits/s\n")
    info(f"     - NEA TRANSMISSION RATE        : {nea_rate} mbits/s\n")
    info(f"     - TEST LENGTH                  : {test_length}s\n")


    info("*** Adding Controller \n")
    net.addController("c1", port=6644)

    info("*** Adding hosts\n")
    h1 = net.addDockerHost(
        "ih1",
        dimage="quantum_bridge:latest",
        ip="11.0.0.1/24",
        docker_args={"hostname":"ih1"}
    )
    h2 = net.addDockerHost(
        "ih2",
        dimage="quantum_bridge:latest",
        ip="11.0.0.2/24",
        docker_args={"hostname":"ih2"}
    )

    info("*** Adding switches\n")
    s1 = net.addSwitch("is1")
    s2 = net.addSwitch("is2")

    net.addLinkNamedIfce(h1,s1,bw=10, delay="0ms")
    net.addLinkNamedIfce(s2,s1,bw=10, delay="0ms")
    net.addLinkNamedIfce(h2,s2,bw=10, delay="0ms")



    print("Starting network")

    net.start()

    info("*** Configuring Quantum interfaces\n")
    bridge1 = net.quantum_interface("is1-is2",
                                    base_rate=nea_rate,
                                    peak_rate=ea_rate,
                                    e_buffer_size=epr_buffer_size,
                                    c_buffer_size=classical_buffer_size)

    ## TO SMOOTHEN THE TRAFFIC
    net.quantum_interface("ih1-is1", h1,base_rate=ea_rate, peak_rate=ea_rate,
                          e_buffer_size=0,
                          c_buffer_size=ea_rate)




    traffic_generation_command = f"python lt_traffic_generation.py 11.0.0.2 {packet_size} {packet_generation_probability} {int(ea_rate*1000*1000)}"
    wrapper_command = f"tmux new-session -d -s traffic '{traffic_generation_command}' &"
    print(traffic_generation_command)
    h1.cmd(wrapper_command)
    info("*** Started traffic generation\n")

    cmd1 = ["tshark","-i", "is1-ih1", "-w" , "if_traffic_in.pcap", "-a", f"duration:{test_length}", "-F", "pcap"]
    cmd2 = ["tshark","-i", "is2-is1", "-w" , "if_traffic_out.pcap", "-a", f"duration:{test_length}", "-F", "pcap"]
    subprocess.run(["pwd"])
    subprocess.run(["rm","if_traffic_in.pcap"])
    subprocess.run(["touch","if_traffic_in.pcap"])
    subprocess.Popen(["chmod", "a+rw", "if_traffic_in.pcap"])
    subprocess.run(["rm","if_traffic_out.pcap"])
    subprocess.run(["touch","if_traffic_out.pcap"])
    subprocess.Popen(["chmod", "a+rw", "if_traffic_out.pcap"])

    info(f"*** Capturing traffic for the next {test_length} seconds \n")
    h1.cmd(wrapper_command)
    subprocess.Popen(cmd2)
    subprocess.Popen(cmd1)
    time.sleep(test_length+2)

    info(f"*** Analyzing *.pcap fiels\n")
    in_count = 0
    out_count = 0
    for packet in rdpcap('if_traffic_in.pcap'):
        try:
            if IP in packet:
                if packet[IP].src == "11.0.0.1":
                    in_count = in_count+1
        except:
            pass

    transmission_rates = []
    segment_start_timestamp = 0
    segment_duration = 0.1
    segment_transmitted = 0
    for packet in rdpcap('if_traffic_out.pcap'):
        try:
            if IP in packet:
                if packet[IP].src == "11.0.0.1":
                    out_count = out_count+1

                if segment_start_timestamp == 0:
                    segment_start_timestamp = float(packet.time)
                    segment_transmitted = segment_transmitted + int(len(packet))
                elif (float(packet.time) - segment_start_timestamp)>segment_duration:
                    transmission_rates.append(segment_transmitted*8/segment_duration/1000/1000)
                    segment_transmitted = 0
                    segment_start_timestamp = segment_start_timestamp + segment_duration

                    empty_segments = 0
                    empty_segments = int((float(packet.time)-segment_start_timestamp) / segment_duration)
                    if empty_segments> 0:
                        for s in range(empty_segments):
                            transmission_rates.append(0)
                        segment_start_timestamp = segment_start_timestamp + empty_segments * segment_duration

                    segment_transmitted = segment_transmitted + int(len(packet))
                else:
                    segment_transmitted = segment_transmitted + int(len(packet))

        except Exception as e:
            print("exception", e)
            pass
    print("RESULTS: ")
    print(in_count)
    print(out_count)
    try:
        throughput = out_count/in_count
    except:
        throughput = 1
    if throughput > 1:
        throughput = 1

    rejection_rate = 1-throughput
    print(transmission_rates)
    average_transmission_rate = (out_count*packet_size*8/test_length)/10**6 # mbps
    average_active_transmission_rate = np.average([x for x in transmission_rates if x > ea_rate*0.1])
    print(packet_generation_probability, throughput, rejection_rate,
          average_transmission_rate, average_active_transmission_rate)

    return (packet_generation_probability, throughput, rejection_rate,
          average_transmission_rate, average_active_transmission_rate)

def continued_simulation(
                            epr_buffer_size = 0,
                            ea_rate=0.2,
                            nea_rate=0.1,
                            packet_size = 900,
                            classical_buffer_size = 1,
                            test_length=20,
                            rounds=None
                         ):

    #Kill previous docker containers and setup
    os.system("sudo ip link del is1-ih1")
    os.system("sudo ip link del is1-is2")
    containers = ["ih1","ih2"]
    for c in containers:
        try:
            os.system(f"docker kill $(docker ps -a -q --filter=name='{c}')")
        except:
            pass
    simulated_probabilities = []
    file_name = f"if_link_P={packet_size}_E={epr_buffer_size}_B={classical_buffer_size}_REA={ea_rate}_RNEA={nea_rate}_T={test_length}.csv"
    path = "if_temp"

    print(os.getcwd())
    print(file_name)
    if not os.path.exists(os.path.join(path)):
        print("Creating directory")
        os.mkdir(path)
    else:
        print("Directory exists")

    if not os.path.exists(os.path.join(path, file_name)):
        print("Creating a file")
        with open(os.path.join(path,file_name), "w") as file:
            print(os.path.abspath(file.name))

            print("Apparently file was opened")
            pass
        open((os.path.join(path,file_name)),'w+').close()
        print("Created a file")
        print(os.path.join(path,file_name))
    else:
        with open(os.path.join(path,file_name), "w") as file:
            print(os.path.abspath(file.name))
        print("File exists")

    i=1
    while True:
        probabilities = [x/(i*10) for x in range(0,i*10+1)]
        with open(os.path.join(path,file_name), newline="") as csvfile:
            reader = csv.reader(csvfile, delimiter='|')
            for row in reader:
                print(row)
                simulated_probabilities.append(float(row[0]))

        probabilities.pop(0)
        probabilities = list(filterfalse(set(simulated_probabilities).__contains__, probabilities))
        print(probabilities)

        #probabilities.reverse()

        print(probabilities)
        for p in probabilities:
            net = Qontainernet(controller=Controller, link=TCLink)
            results = test_topo(net,
                                packet_generation_probability= p,
                                epr_buffer_size = epr_buffer_size,
                                ea_rate=ea_rate,
                                nea_rate=nea_rate,
                                packet_size = packet_size,
                                classical_buffer_size = classical_buffer_size,
                                test_length=test_length,
                                )
            net.stop()
            print(f"Probability {p}")
            print(results)
            with open(os.path.join(path,file_name), 'a') as f:
                print(f.name)
                writer = csv.writer(f, delimiter="|")
                writer.writerow(results)
        i = i + 1
        if round is None:
            continue
        if i > rounds:
            break






if __name__ == "__main__":
    setLogLevel("info")

    continued_simulation(   epr_buffer_size =4,
                            ea_rate=4,
                            nea_rate=2,
                            packet_size = 500,
                            classical_buffer_size = 4,
                            test_length=50,
                            rounds = 2
                         )

    continued_simulation(   epr_buffer_size = 1,
                            ea_rate=0.4,
                            nea_rate=0.2,
                            packet_size = 750,
                            classical_buffer_size = 5,
                            test_length=10,
                            rounds = 2
                         )

