#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example to test quantum connection with Qontainernet
"""

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

from qontainernet import Qontainernet




def test_topo(rounds, epr_num, packet_num, epr_frame_size,net):
    """Run test topology"""
    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    h_1 = net.addDockerHost(
        "h1",
        dimage="quantum_bridge:latest",
        ip="11.0.0.1/24",
        docker_args={"hostname": "h1"},
    )
    h_2 = net.addDockerHost(
        "h2",
        dimage="quantum_bridge:latest",
        ip="11.0.0.2/24",
        docker_args={"hostname": "h2"},
    )

    info("*** Creating quantum link\n")
    bridge = net.add_quantum_link(h_1, h_2, "10.0.0.3/24",
                                  node_1_ip="11.0.0.1",
                                  node_2_ip="11.0.0.2",
                                  simple=False,
                                  epr_frame_size=epr_frame_size)
    #h_1.setIP("11.0.0.1/24", intf="h1-bridge")

    info("*** Starting network\n")
    net.start()

    info("*** Setting host tmux and running server daemon on both hosts\n")
    h_1.cmd("tmux new-session -d -s h 'tcpdump -i h_1-bridge icmp'")
    h_2.cmd("tmux new-session -d -s h 'tcpdump -i h1-bridge icmp'")

    info("*** Starting simulation\n")
    h_1.cmd(f"tmux new-session -d -s h1 'python traffic_generation.py 11.0.0.2 {rounds} {epr_num} {packet_num}'")
    info("*** Waiting for enough packets to be transmitted\n")
    #info("*** Starting debug console")
    #CLI(net)
    net.wait_for_number_of_packets_transmitted(bridge, 100)# rounds*(packets_per_epr+1))
    info("*** Enough packets recorded\n")
    #Testing log extraction
    net.extract_data(bridge, "/app/packet_logs.log", f"simulation_results/packet_log_{epr_frame_size}B-{rounds}-{epr_num}-{packet_num}.csv")
    #net.extract_data(bridge, "/app/packet_logs.log", f"simulation_results/'EPR-B:{epr_frame_size} P/EPR:{packet_num}/{epr_num}.csv'")


if __name__ == "__main__":
    setLogLevel("info")

    settings = [
        {
            "rounds":100,
            "epr_per_round":10,
            "packets_per_round":1,
            "epr_frame_size":1
        },
        {
            "rounds":100,
            "epr_per_round":10,
            "packets_per_round":10,
            "epr_frame_size":10
        },
        {
            "rounds":100,
            "epr_per_round":10,
            "packets_per_round":10,
            "epr_frame_size":11
        },
     ]
    print(settings)
    for i in range(9, 12, 1):
        settings.append({
            "rounds":100,
            "epr_per_round":10,
            "packets_per_round":3,
            "epr_frame_size":i
        })
    for i in range(6, 12, 1):
        settings.append({
            "rounds":100,
            "epr_per_round":10,
            "packets_per_round":1,
            "epr_frame_size":i
        })
    for i in range(1, 12, 1):
        settings.append({
            "rounds":100,
            "epr_per_round":10,
            "packets_per_round":5,
            "epr_frame_size":i
        })
    print(settings)
    for setting in settings:
        net = Qontainernet(controller=Controller, link=TCLink)
        try:
            rounds =  setting["rounds"]
            rounds = -1
            epr_num = setting["epr_per_round"]
            packet_num = setting["packets_per_round"]
            epr_frame_size = setting["epr_frame_size"]
            info(f"*** Running simulation \nRounds:{rounds}\nEPR num:{epr_num}\nPacket num:{packet_num}\nEPR frame size:{epr_frame_size}\n")
            test_topo(rounds , epr_num, packet_num, epr_frame_size, net)
        except Exception as e:
            print(e)
            info("*** Stopping network\n")
            try:
                net.stop()
            except Exception as e:
                print(e)
        finally:
            info("*** Stopping network\n")
            net.stop()
