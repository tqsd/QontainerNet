#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Basic example to test quantum connection with Qontainernet
"""
import time

from comnetsemu.cli import CLI
from comnetsemu.net import Containernet
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller, OVSSwitch


from comnetsemu_quantum.qlink import Qontainernet


def test_topo(net, epr_frame_size):
    """Run test topology: double hop"""

    info("*** Adding Controller \n")
    net.addController("c0")

    info("*** Adding hosts\n")
    h1 = net.addDockerHost(
        "h1",
        dimage="quantum_bridge:latest",
        ip="11.0.0.1/24",
        docker_args={"hostname":"h1_dh"}
    )
    h2 = net.addDockerHost(
        "h2",
        dimage="quantum_bridge:latest",
        ip="11.0.0.2/24",
        docker_args={"hostname":"h2_dh"}
    )
    info("*** Creating switch\n")

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")
    #s1.cmd('ovs-vsctl set bridge s1 stp-enable=true')
    s2 = net.addSwitch("s2")

    info("*** Creating quantum links\n")
    bridge1 = net.add_quantum_link(s2 , s1,
                                   "11.0.0.100/24",
                                   node_1_ip=None,
                                   node_2_ip=None,
                                   docker_bridge="quantum_bridge_c",
                                   epr_frame_size=epr_frame_size,
                                   )
    bridge2 = net.add_quantum_link(s2, s1,
                                   "11.0.0.101/24",
                                   node_1_ip=None,
                                   node_2_ip=None,
                                   docker_bridge="quantum_bridge_c",
                                   epr_frame_size=epr_frame_size,
                                   )
    '''
    bridge2 = net.add_quantum_link(s2, s1,
                                   "11.0.0.102/24",
                                   node_1_ip=None,
                                   node_2_ip=None,
                                   docker_bridge="quantum_bridge_c",
                                   epr_frame_size=epr_frame_size,
                                   )
    '''

    net.addLinkNamedIfce(s1, h1, bw=10, delay="0ms")
    net.addLinkNamedIfce(s2, h2, bw=10, delay="0ms")
    print("Starting network")
    net.start()

    info("*** Enabling STP to prevent routing loops\n")
    s1.cmd("ovs-vsctl set-fail-mode s1 standalone")
    s1.cmd("ovs-vsctl set bridge s1 stp_enable=true")
    #s2.cmd("ovs-vsctl set-fail-mode s2 standalone")
    #s2.cmd("ovs-vsctl set bridge s2 stp_enable=true")


    info("*** Waiting for STP to finish\n")
    while(s1.cmd('ovs-ofctl show s1 | grep -o FORWARD | head -n1') != "FORWARD\r\n"):
        time.sleep(2)

    info("*** Adding switch port routing rules\n")
    #s1.cmd("ovs-ofctl add-flow s1 priority=500,in_port=3,actions=output:1")
    #s1.cmd("ovs-ofctl add-flow s1 priority=500,in_port=2,actions=output:3")

    #s2.cmd("ovs-ofctl add-flow s2 priority=500,in_port=3,actions=output:2")
    #s2.cmd("ovs-ofctl add-flow s2 priority=500,in_port=1,actions=output:3")

    CLI(net)

if __name__ == "__main__":
    setLogLevel("info")
    net = Qontainernet(controller=Controller, link=TCLink)
    try:
        test_topo(net, 100)
    except Exception as e:
        print(e)
        print("Some exception")
        info("*** Stopping network \n")
    finally:
        info("*** Stopping network \n")
        net.stop()
