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


def testTopo(net):

    # xterms=True, spawn xterms for all nodes after net.start()
    # net = Containernet(controller=Controller, link=TCLink)

    info("*** Adding controller\n")
    net.addController("c0")

    info("*** Adding hosts\n")
    h1 = net.addDockerHost(
        "h1",
        dimage="quantum_bridge:latest",
        ip="10.0.0.1/24",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8), "hostname": "h1"},
    )
    h2 = net.addDockerHost(
        "h2",
        dimage="quantum_bridge:latest",
        ip="10.0.0.2/24",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8), "hostname": "h2"},
    )

    bridge = net.addDockerHost(
        "bridge",
        dimage="quantum_bridge:latest",
        ip="10.0.0.3/24",
        docker_args={"cpuset_cpus": "0", "nano_cpus": int(1e8), "hostname": "h2"},
        )

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")
    s2 = net.addSwitch("s2")

    info("*** Creating links\n")
    #net.addLink(h1,bridge, bw=10, delay="100ms")
    net.addLink(h1, bridge, bw=10, delay="100ms", intfName1="h1-bridge", intfName2="bridge-h1")
    h1.setIP("10.0.0.1/24", intf="h1-bridge")
    bridge.setIP("10.0.0.3/24", intf="bridge-h1")
    net.addLink(h2, bridge, bw=10, delay="100ms", intfName1="h1-bridge", intfName2="bridge-h2")
    



    info("*** Starting network\n")
    net.start()
    info("*** Setting the bridge\n")
    bridge.cmd("ip addr flush dev bridge-h1")
    bridge.cmd("ip addr flush dev bridge-h2")
    bridge.cmd("brctl addbr bridge")
    bridge.cmd("brctl addif bridge bridge-h1")
    bridge.cmd("brctl addif bridge bridge-h2")
    bridge.cmd("ip link set dev bridge up")
    bridge.cmd("ip addr add 10.0.0.3/24 brd + dev bridge")
    bridge.cmd("route add default gw 10.0.0.1 dev bridge")
    
    #bridge.cmd("nft add filter input counter queue num 1")
    #bridge.cmd("nft add table bridge custom")
    #bridge.cmd("nft add chain bridge custom 
    bridge.cmd("iptables -A FORWARD -i bridge -p all -j NFQUEUE --queue-num 1")

    bridge.cmd("echo '10.0.0.1 \n10.0.0.2' > /app/hosts.txt")

    info("*** Running bridge.py in tmux session \n")
    bridge.cmd("tmux new-session -d -s bridge 'python bridge.py' &")
    #bridge.cmd("python /app/bridge.py &")

    is_up = False

    info("*** Waiting for quantum bridge to initiate\n")
    while not is_up:
        if "log.txt" in bridge.cmd("ls /app/"):
            is_up = True

    info("*** Testing connections\n")
    CLI(net)



if __name__ == "__main__":
    setLogLevel("info")
    net = Containernet(controller=Controller, link=TCLink)
    try:
        testTopo(net)
    finally:
        info("*** Stopping network")
        net.stop() 


