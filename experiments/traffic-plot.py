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
import math
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


def deviations(array):
    average = np.average(array)
    negative = []
    positive = []
    for point in array:
        if point >= average:
            positive.append(point-average)
            negative.append(0)
        if point <= average:
            negative.append(average-point)
            positive.append(0)

    p = 0
    n = 0
    for x in positive:
        p = p + x**2
    for x in negative:
        n = n + x**2

    try:
        p = math.sqrt(p/len(positive))
        n = math.sqrt(n/len(negative))
    except:
        print("Division by 0")

    return p,n


def traffic(traffic="random",
            packet_generation_probability=0.5,
            period_length = 10,
            generation_period_length=5,
            test_length=100
            ):

    os.system("sudo ip link del ts1-th1")
    os.system("sudo ip link del ts1-ts2")
    containers = ["th1","th2"]
    for c in containers:
        try:
            os.system(f"docker kill $(docker ps -a -q --filter=name='{c}')")
        except:
            pass
    ea_rate=0.2
    nea_rate=0.1
    packet_size = 900
    classical_buffer_size = 1
    net = Qontainernet(controller=Controller, link=TCLink)

    info("--> CREATING TRAFFIC PLOTS\n")
    net.addController("c1", port=6677)
    info("---> Adding hosts\n")

    h1 = net.addDockerHost(
        "th1",
        dimage="quantum_bridge:latest",
        ip="11.0.0.1/24",
        docker_args={"hostname":"th1"}
    )
    h2 = net.addDockerHost(
        "th2",
        dimage="quantum_bridge:latest",
        ip="11.0.0.2/24",
        docker_args={"hostname":"th2"}
    )
    info("*** Creating switch\n")

    info("*** Adding switch\n")
    s1 = net.addSwitch("ts1")
    s2 = net.addSwitch("ts2")

    net.addLinkNamedIfce(h1,s1,bw=10, delay="0ms")
    net.addLinkNamedIfce(s1,s2,bw=10, delay="0ms")
    net.addLinkNamedIfce(h2,s2,bw=10, delay="0ms")
    net.start()
    print(ea_rate)

    net.quantum_interface("th1-ts1", h1,base_rate=ea_rate, peak_rate=ea_rate,
                          e_buffer_size=0,
                          c_buffer_size=ea_rate)


    traffic_generation_command_random = f"python lt_traffic_generation.py 11.0.0.2 {packet_size} {packet_generation_probability} {int(ea_rate*1024*1024)}"
    traffic_generation_command_periodic = f"python periodic_traffic_generation.py 11.0.0.2 {packet_size} {period_length} {generation_period_length} {int(ea_rate*1000*1000)}"
    wrapper_command = None
    if traffic == "random":
        wrapper_command = f"tmux new-session -d -s traffic '{traffic_generation_command_random}' &"
    else:
        wrapper_command = f"tmux new-session -d -s traffic '{traffic_generation_command_periodic}' &"


    cmd1 = ["tshark","-i", "ts1-ts2", "-w" , "t_traffic_in.pcap", "-a", f"duration:{test_length}", "-F", "pcap"]
    cmd2 = ["tshark","-i", "ts2-ts1", "-w" , "t_traffic_out.pcap", "-a", f"duration:{test_length}", "-F", "pcap"]
    subprocess.run(["pwd"])
    subprocess.run(["rm","t_traffic_in.pcap"])
    subprocess.run(["touch","t_traffic_in.pcap"])
    subprocess.Popen(["chmod", "a+rw", "t_traffic_in.pcap"])
    subprocess.run(["rm","t_traffic_out.pcap"])
    subprocess.run(["touch","t_traffic_out.pcap"])
    subprocess.Popen(["chmod", "a+rw", "t_traffic_out.pcap"])

    info(f"*** Capturing traffic for the next {test_length} seconds \n")
    subprocess.Popen(cmd2)
    subprocess.Popen(cmd1)
    h1.cmd(wrapper_command)
    time.sleep(test_length+2)
    print(wrapper_command)
    info("*** Started traffic generation\n")


    info(f"*** Analyzing *.pcap fiels\n")
    in_count = 0
    out_count = 0
    for packet in rdpcap('t_traffic_in.pcap'):
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
    for packet in rdpcap('t_traffic_out.pcap'):
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

    incoming_rates = []
    segment_start_timestamp = 0
    segment_duration = 0.1
    segment_transmitted = 0
    f_ts = 0
    l_ts = 0
    for packet in rdpcap('t_traffic_in.pcap'):
        try:
            if IP in packet:
                if f_ts == 0:
                    f_ts = packet.time
                if segment_start_timestamp == 0:
                    segment_start_timestamp = float(packet.time)
                    segment_transmitted = segment_transmitted + int(len(packet))
                elif (float(packet.time) - segment_start_timestamp)>segment_duration:
                    incoming_rates.append(segment_transmitted*8/segment_duration/1000/1000)
                    segment_transmitted = 0
                    segment_start_timestamp = segment_start_timestamp + segment_duration

                    empty_segments = 0
                    empty_segments = int((float(packet.time)-segment_start_timestamp) / segment_duration)
                    if empty_segments> 0:
                        for s in range(empty_segments):
                            incoming_rates.append(0)
                        segment_start_timestamp = segment_start_timestamp + empty_segments * segment_duration

                    segment_transmitted = segment_transmitted + int(len(packet))
                else:
                    segment_transmitted = segment_transmitted + int(len(packet))
                l_ts = packet.time

        except Exception as e:
            print("exception", e)
            pass
    try:
        throughput = out_count/in_count
    except:
        throughput = 1
    if throughput > 1:
        throughput = 1

    rejection_rate = 1-throughput
    average_transmission_rate = (out_count*packet_size*8/test_length)/10**6 # mbps
    average_active_transmission_rate = np.average([x for x in transmission_rates if x > ea_rate*0.1])
    ur_err_pos, ur_err_neg = deviations([x for x in transmission_rates if x > ea_rate*0.1])
    aar_dev = np.std([x for x in transmission_rates if x > ea_rate*0.1])


    print(incoming_rates)
    return(incoming_rates)

if __name__=="__main__":
    setLogLevel("info")
    test_length = 200
    setups =[
        #{
            #"traffic":"random",
            #"probability":0.25,
            #"period_length":20,
            #"generation_period_length":20,
            #},
        #{
        #    "traffic":"random",
        #    "probability":0.5,
        #    "period_length":20,
        #    "generation_period_length":20,
        #},
        #{
        #    "traffic":"random",
        #    "probability":0.75,
        #    "period_length":20,
        #    "generation_period_length":20,
        #},
        #{
        #    "traffic":"periodic",
        #    "period_length":20,
        #    "generation_period_length":5,
        #    "probability":0.75,
        #},
        #{
        ##    "traffic":"periodic",
        #   "period_length":20,
        #    "generation_period_length":10,
        #    "probability":0.75,
        #},
        {
            "traffic":"periodic",
            "period_length":20,
            "generation_period_length":15,
            "probability":0.75,
        },
    ]
    for s in setups:
        with open("traffic.csv","a") as file:
            writer = csv.writer(file, delimiter=",")
            print(s)
            traffic = traffic(test_length=test_length,
                              traffic=s["traffic"],
                              packet_generation_probability=s["probability"],
                              period_length=s["period_length"],
                              generation_period_length=s["generation_period_length"]
                              )
            writer.writerow(traffic)



