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


def test_topo(net, epr_frame_size):
    """Run test topology: double hop"""

    info("*** Adding Controller \n")
    net.addController("c0")

    info("*** Adding hosts\n")
    h1 = net.addDockerHost(
        "h1_dh",
        dimage="quantum_bridge:latest",
        ip="11.0.0.2/24",
        docker_args={"hostname":"h1_dh"}
    )
    h2 = net.addDockerHost(
        "h2_dh",
        dimage="quantum_bridge:latest",
        ip="11.0.0.3/24",
        docker_args={"hostname":"h2_dh"}
    )
    info("*** Creating switch\n")

    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")


    #info("*** Creating quantum links")
    print("HMMMM")
    bridge1 = net.add_quantum_link(h1, s1,
                                   "11.0.0.10/24",
                                   node_1_ip="11.0.0.2/24",
                                   node_2_ip=None,
                                   simple=False,
                                   epr_frame_size=epr_frame_size,
                                   )
    """
    #h1.setIP("11.0.0.2/24", intf=f"{h1.name}-{bridge1.name}")
    print("Bridge")

    bridge2 = net.add_quantum_link(switch1, h2,
                                   "10.0.0.3/24",
                                   simple=False,
                                   epr_frame_size=epr_frame_size,
                                   name1="h2", name2="switch")
    """
    print("Switch")

    #h2.setIP("11.0.0.3/24", intf=f"h2-s1")
    #net.addLink(h2, switch1, bw=10, delay="100ms",
    #            intfName1="h2-s1", inftName2="s1-h2"
    #            )

    net.addLinkNamedIfce(s1, h2, bw=10, delay="50ms")
    #net.addLinkNamedIfce(s1, h2, bw=10, delay="50ms")
    print("Starting network")
    net.start()
    CLI(net)
    print("Stop?")
if __name__ == "__main__":
    setLogLevel("info")
    net = Qontainernet(controller=Controller, link=TCLink)
    try:
        test_topo(net, 10)
    except Exception as e:
        print(e)
        print("Some exception")
        info("*** Stopping network \n")
    finally:
        info("*** Stopping network \n")
        net.stop()
