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


def test_qns_link_test(epr_frame_size=20,
                       classical_buffer_size = None,
                       packet_size=0,
                       traffic_type="periodic",
                       probability=0.5,
                       period_length=10,
                       period_generation_length=5):

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
    net.addController("c1", port=6666)

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
    print(traffic_type)
    if traffic_type == "periodic":
        epr_gen_len = period_length - period_generation_length

        print(f"tmux new-session -d -s h1 'python traffic_generation.py 11.0.0.2 -1 {epr_gen_len} {period_generation_length} {packet_size}'")
        h1.cmd(f"tmux new-session -d -s h1 'python traffic_generation.py 11.0.0.2 -1 {epr_gen_len} {period_generation_length} {packet_size}'")
    else:
        print(f"tmux new-session -d -s h1 'python traffic_generation.py 11.0.0.2 -1 0 0 {packet_size} random {probability}'")
        h1.cmd(f"tmux new-session -d -s h1 'python traffic_generation.py 11.0.0.2 -1 0 0 {packet_size} random {probability}'")
    packet_num = 100
    net.wait_for_number_of_packets_transmitted(bridge1,packet_num)
    net.extract_data(bridge1, "/app/packet_logs.log", f"qns_eval/{traffic_type}_packet_log_epr_{epr_frame_size}-{packet_num}.csv")

    net.stop()

    epr_generation_times=[]
    transmissions = []
    with open(f"qns_eval/{traffic_type}_packet_log_epr_{epr_frame_size}-{packet_num}.csv") as f:
        reader = csv.reader(f,delimiter=",")
        next(reader)
        for row in reader:
            print(row)
            epr_generation_times.append(float(row[4]))
            print(row[-3])
            if not row[-3] == "epr":
                transmissions.append(int(row[-1]))
    print(transmissions)
    bit_per_transmission = [(packet_size)*8/x for x in transmissions]
    tr_avg = np.average(transmissions)
    tr_std = np.std(transmissions)
    bpt_avg = np.average(bit_per_transmission)
    bpt_std = np.std(bit_per_transmission)

    print(tr_avg, tr_std, bpt_avg, bpt_std)
    return tr_avg, tr_std, bpt_avg, bpt_std

def periodic():
    print("TESTING ONLY INFINITELY LARGE BUFFERS")
    file_dir = "qns_eval"
    file_name = "qns_periodic.csv"
    gen_len = range(1,11)
    sim_gen_len = []
    with open(file_dir + "/" + file_name) as f:
        reader = csv.reader(f)
        for row in reader:
            sim_gen_len.append(int(row[0]))

    gen_len = list(filterfalse(set(sim_gen_len).__contains__, gen_len))
    packet_size = 48

    for gl in gen_len:
        print(f"GENERATION LENGTH -- {gl}")
        tr_avg, tr_std, bpt_avg, bpt_std = test_qns_link_test(
            epr_frame_size=int((packet_size+1)/2),
            packet_size=packet_size,
            traffic_type="periodic",
            period_length=10,
            period_generation_length=gl)

        with open(file_dir+"/"+file_name, "a") as f:
            writer = csv.writer(f)
            writer.writerow([gl,tr_avg,tr_std, bpt_avg, bpt_std])

def random():
    print("TESTING ONLY INFINITELY LARGE BUFFERS")
    file_dir = "qns_eval"
    file_name = "qns_random.csv"
    probabilities = range(1,11)
    probabilities = [x/10 for x in probabilities]
    sim_probabilities = []
    with open(file_dir + "/" + file_name) as f:
        reader = csv.reader(f)
        for row in reader:
            sim_probabilities.append(float(row[0]))

    probabilities = list(filterfalse(set(sim_probabilities).__contains__, probabilities))
    packet_size = 48

    for p in probabilities[::-1]:
        print(f"PROBABILITIES -- {p}")
        tr_avg, tr_std, bpt_avg, bpt_std= test_qns_link_test(
            epr_frame_size=int((packet_size+1)/2),
            packet_size=packet_size,
            traffic_type="random",
            period_length=10,
            period_generation_length=100,
            probability=p
        )

        with open(file_dir+"/"+file_name, "a") as f:
            writer = csv.writer(f)
            writer.writerow([p,tr_avg,tr_std,bpt_avg,bpt_std])
if __name__ == "__main__":
    setLogLevel("info")
    random()
    periodic()
