#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example to test multiple switches in a single network
"""

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller

from comnetsemu_quantum.qlink import Qontainernet


def test_topo(net):
    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    h1 = net.addDockerHost(
        "h1",
        dimage="quantum_bridge:latest",
        ip="11.0.0.1/24",
        docker_args={"hostname": "h1"},
    )
    h2 = net.addDockerHost(
        "h2",
        dimage="quantum_bridge:latest",
        ip="11.0.0.2/24",
        docker_args={"hostname": "h2"},
    )

    info("*** Creating quantum links\n")
    net.add_quantum_link(h1, h2, "10.0.0.3/24")
    h1.setIP("11.0.0.1/24", intf="h1-bridge")

    info("*** Starting network\n")
    net.start()
    info("*** Setting the bridge\n")

    info("*** Setting host tmux\n")
    h1.cmd("tmux new-session -d -s h 'tcpdump -i h1-bridge icmp'")
    h2.cmd("tmux new-session -d -s h 'tcpdump -i h1-bridge icmp'")

    info("*** Testing connections\n")
    CLI(net)


if __name__ == "__main__":
    setLogLevel("info")
    net = Qontainernet(controller=Controller, link=TCLink)
    net.test_method()
    try:
        test_topo(net)
    finally:
        info("*** Stopping network")
        net.stop() 


