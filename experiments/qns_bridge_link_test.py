#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example to test quantum connection with Qontainernet
"""
import time
import csv
import os
import numpy as np
from itertools import filterfalse

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller, OVSSwitch


from qontainernet import Qontainernet


epr_file = "qns_eval/epr_gen_times.csv"
nea_file = "qns_eval/nea_tr_times.csv"
ea_file = "qns_eval/ea_tr_times.csv"


def test_qns_link_epr_processing_times(epr_frame_size=20,
                                       classical_buffer_size = None):

    net = Qontainernet(controller=Controller, link=TCLink)
    info(f"--> Running QuNetSim GEWI simulation\n")
    info(f"--> EPR FRAME SIZE {epr_frame_size}\n")
    info(f"Killing previous containers is any are running \n")
    containers = ["qh1","qh2", "brqns0"]

    for c in containers:
        try:
            os.system(f"docker kill $(docker ps -a -q --filter=name='{c}')")
        except:
            pass

    info("*** Adding Controller \n")
    net.addController("c1", port=6655)

    info("*** Adding hosts\n")
    h1 = net.addDockerHost(
        "qh1",
        dimage="quantum_bridge:latest",
        ip="11.0.0.1/24",
        docker_args={"hostname":"qh1"}
    )
    h2 = net.addDockerHost(
        "qh2",
        dimage="quantum_bridge:latest",
        ip="11.0.0.2/24",
        docker_args={"hostname":"qh2"}
    )


    bridge1 = net.add_quantum_link(h1, h2,
                                   "11.0.0.100/24",
                                   node_1_ip="11.0.0.1",
                                   node_2_ip="11.0.0.2",
                                   epr_frame_size=epr_frame_size,
                                   classical_buffer_size=classical_buffer_size
                                   )

    net.start()
    ## START TEST

    info("*** START SIMULATION\n")
    h1.cmd(f"tmux new-session -d -s h1 'python traffic_generation.py 11.0.0.2 -1 10 0'")
    packet_num = 10
    net.wait_for_number_of_packets_transmitted(bridge1,packet_num)
    net.extract_data(bridge1, "/app/packet_logs.log", f"qns_eval/packet_log_epr_{epr_frame_size}-{packet_num}.csv")

    net.stop()

    epr_generation_times=[]
    with open(f"qns_eval/packet_log_epr_{epr_frame_size}-{packet_num}.csv") as f:
        reader = csv.reader(f,delimiter=",")
        next(reader)
        for row in reader:
            print(row)
            epr_generation_times.append(float(row[4]))

    average = np.average(epr_generation_times)
    deviation = np.std(epr_generation_times)
    epr_generation_times_per_qubit = [x/(8*epr_frame_size) for x in epr_generation_times]
    average_per_qubit = np.average(epr_generation_times_per_qubit)
    deviation_per_qubit = np.std(epr_generation_times_per_qubit)

    return average, deviation, average_per_qubit, deviation_per_qubit


def test_qns_link_nea_processing_times(epr_frame_size=0,
                                       packet_size=42,
                                       classical_buffer_size = None):

    packet_num = 10
    print(f"qns_eval/packet_log_nea_{packet_size}-{packet_num}.csv")
    if not os.path.isfile(f"qns_eval/packet_log_nea_{packet_size}-{packet_num}.csv"):
        net = Qontainernet(controller=Controller, link=TCLink)
        info(f"--> Running QuNetSim GEWI simulation for non assisted processing times\n")
        info(f"--> EPR FRAME SIZE {epr_frame_size}\n")
        info(f"--> PACKET SIZE {packet_size}\n")
        info(f"Killing previous containers is any are running \n")
        containers = ["qh1","qh2", "brqns0"]

        for c in containers:
            try:
                os.system(f"docker kill $(docker ps -a -q --filter=name='{c}')")
            except:
                pass

        info("*** Adding Controller \n")
        net.addController("c1", port=6655)

        info("*** Adding hosts\n")
        h1 = net.addDockerHost(
            "qh1",
            dimage="quantum_bridge:latest",
            ip="11.0.0.1/24",
            docker_args={"hostname":"qh1"}
        )
        h2 = net.addDockerHost(
            "qh2",
            dimage="quantum_bridge:latest",
            ip="11.0.0.2/24",
            docker_args={"hostname":"qh2"}
        )


        bridge1 = net.add_quantum_link(h1, h2,
                                    "11.0.0.100/24",
                                    node_1_ip="11.0.0.1",
                                    node_2_ip="11.0.0.2",
                                    epr_frame_size=epr_frame_size,
                                    classical_buffer_size=classical_buffer_size
                                    )

        net.start()
        ## START TEST

        info("*** START SIMULATION\n")
        h1.cmd(f"tmux new-session -d -s h1 'python traffic_generation.py 11.0.0.2 -1 0 1 {packet_size}'")
        print(packet_size)
        net.wait_for_number_of_packets_transmitted(bridge1,packet_num)
        net.extract_data(bridge1, "/app/packet_logs.log", f"qns_eval/packet_log_nea_{packet_size}-{packet_num}.csv")

        net.stop()

    packet_processing_times=[]
    actual_packet_size = []
    with open(f"qns_eval/packet_log_nea_{packet_size}-{packet_num}.csv") as f:
        reader = csv.reader(f,delimiter=",")
        next(reader)
        for row in reader:
            print(row)
            packet_processing_times.append(float(row[4]))
            actual_packet_size.append(int(row[-1])/8)

    if packet_size ==164:
        print(packet_processing_times)
    average = np.average(packet_processing_times)
    deviation = np.std(packet_processing_times)
    packet_processing_times_per_bit = []
    for i in range(len(packet_processing_times)):
        packet_processing_times_per_bit.append(packet_processing_times[i]/actual_packet_size[i])
    average_per_bit = np.average(packet_processing_times_per_bit)
    deviation_per_bit = np.std(packet_processing_times_per_bit)

    return average, deviation, average_per_bit, deviation_per_bit


def test_qns_link_ea_processing_times(epr_frame_size=0,
                                       packet_size=42,
                                       classical_buffer_size = None):


    epr_frame_size = packet_size * 2
    packet_num = 21
    if not os.path.isfile(f"qns_eval/packet_log_ea_{packet_size}-{packet_num}.csv"):
        print(f"qns_eval/packet_log_ea_{packet_size}-{packet_num}.csv")

        #To ensure enough entanglement for each packet
        net = Qontainernet(controller=Controller, link=TCLink)
        info(f"--> Running QuNetSim GEWI EA simulation\n")
        info(f"--> EPR FRAME SIZE {epr_frame_size}\n")
        info(f"Killing previous containers is any are running \n")
        containers = ["qh1","qh2", "brqns0"]

        for c in containers:
            try:
                os.system(f"docker kill $(docker ps -a -q --filter=name='{c}')")
            except:
                pass

        info("*** Adding Controller \n")
        net.addController("c1", port=6655)

        info("*** Adding hosts\n")
        h1 = net.addDockerHost(
            "qh1",
            dimage="quantum_bridge:latest",
            ip="11.0.0.1/24",
            docker_args={"hostname":"qh1"}
        )
        h2 = net.addDockerHost(
            "qh2",
            dimage="quantum_bridge:latest",
            ip="11.0.0.2/24",
            docker_args={"hostname":"qh2"}
        )


        bridge1 = net.add_quantum_link(h1, h2,
                                    "11.0.0.100/24",
                                    node_1_ip="11.0.0.1",
                                    node_2_ip="11.0.0.2",
                                    epr_frame_size=epr_frame_size,
                                    classical_buffer_size=classical_buffer_size
                                    )

        net.start()
        ## START TEST
        info("*** START SIMULATION\n")
        h1.cmd(f"mz -A 11.0.0.1 -B 11.0.0.2 -T udp -c -1 -p {packet_size}")
        packet_num = 10 * 2 + 1
        for i in range(packet_num):
            h1.cmd(f"tmux new-session -d -s h1 'python traffic_generation.py 11.0.0.2 -1 1 1 {packet_size}'")
        net.wait_for_number_of_packets_transmitted(bridge1,packet_num)
        net.extract_data(bridge1, "/app/packet_logs.log", f"qns_eval/packet_log_ea_{packet_size}-{packet_num}.csv")

        net.stop()

    packet_processing_times=[]
    actual_packet_size = []
    with open(f"qns_eval/packet_log_ea_{packet_size}-{packet_num}.csv") as f:
        reader = csv.reader(f,delimiter=",")
        next(reader)
        for row in reader:
            print(row)
            if row[-3] == "superdense":
                actual_packet_size.append(int(row[-1])*2/8)
                packet_processing_times.append(float(row[4]))

    average = np.average(packet_processing_times)
    deviation = np.std(packet_processing_times)
    packet_processing_times_per_bit = []
    for i in range(len(packet_processing_times)):
        packet_processing_times_per_bit.append(packet_processing_times[i]/actual_packet_size[i])
    average_per_bit = np.average(packet_processing_times_per_bit)
    deviation_per_bit = np.std(packet_processing_times_per_bit)

    return average, deviation, average_per_bit, deviation_per_bit


if __name__ == "__main__":
    setLogLevel("info")
    epr_gen_length = range(1,101)
    sim_epr = []
    with open(epr_file, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            sim_epr.append(int(row[0]))
    
    epr_gen_length = list(filterfalse(set(sim_epr).__contains__, epr_gen_length))


    for i in epr_gen_length:
        print("EVAL EPR TIMES")
        average, deviation, average_per_q, dev_q = test_qns_link_epr_processing_times(epr_frame_size=i)
        with open(epr_file, "a") as f:
            writer = csv.writer(f)
            writer.writerow([i,average, deviation, average_per_q, dev_q])

    packet_length = range(48, 200)
    sim_packet_length = []
    with open(nea_file, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            sim_packet_length.append(int(row[0]))

    packet_length = list(filterfalse(set(sim_packet_length).__contains__, packet_length))

    for i in packet_length:
        print("EVAL NEA TIMES")
        average, deviation, average_per_q, dev_q = test_qns_link_nea_processing_times(packet_size=i)
        with open(nea_file, "a") as f:
            writer = csv.writer(f)
            writer.writerow([i,average, deviation, average_per_q, dev_q])

    packet_length = range(48, 200)
    sim_packet_length = []
    with open(ea_file, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            sim_packet_length.append(int(row[0]))

    packet_length = list(filterfalse(set(sim_packet_length).__contains__, packet_length))

    for i in packet_length:
        print("EVAL EA TIMES")
        average, deviation, average_per_q, dev_q = test_qns_link_ea_processing_times(packet_size=i)
        with open(ea_file, "a") as f:
            writer = csv.writer(f)
            writer.writerow([i,average, deviation, average_per_q, dev_q])

