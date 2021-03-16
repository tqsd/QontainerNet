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

from comnetsemu_quantum.qlink import Qontainernet



net = Qontainernet(controller=Controller, link=TCLink)

def test_topo():
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

    info("*** Some small test \n")
    info("*** Creating quantum links\n")
    net.add_quantum_link(h_1, h_2, "10.0.0.3/24")
    h_1.setIP("11.0.0.1/24", intf="h1-bridge")

    info("*** Starting network\n")
    net.start()
    info("*** Setting the bridge\n")

    info("*** Setting host tmux and running iperf server daemon on both hosts\n")
    h_1.cmd("tmux new-session -d -s h 'tcpdump -i h_1-bridge icmp'")
    #h_1.cmd("iperf -s -D")
    h_2.cmd("tmux new-session -d -s h 'tcpdump -i h1-bridge icmp'")
    #h_2.cmd("iperf -s -D")

    info("*** Testing connections\n")
    CLI(net)


if __name__ == "__main__":
    setLogLevel("info")
    try:
        test_topo()
    finally:
        info("*** Stopping network")
        net.stop()
