from comnetsemu.net import Containernet
from mininet.log import info
import os
import shutil
import pathlib
import time
import datetime


class Qontainernet(Containernet):
    """
    Qontainernet is extension of Containernet
    It adds quantum links; Currently supports only one link
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.quantum_bridge_counter = 0
        self.log_dir = "./tmp"
        try:
            shutil.rmtree(self.log_dir)
        except OSError as e:
            print("Error: %s - %s." % (e.filename, e.strerror))
        os.mkdir(self.log_dir)

    def classical_interface(self, ifce, node=None):
        """
        Makes existing interface behave like quantum link.
        Buffers can only work one way and can not be shared between connected interfaces.
        """


        base_rate = 0.4
        peak_rate = 2
        buffer_size = 1024


        if node is not None:
            node.cmd(f"tc qdisc del root dev {ifce}")
            #node.cmd(f"tc qdisc add dev {ifce} root tbf rate {2*base_rate}mbit latency {latency}ms")
            node.cmd(f"tc qdisc add dev {ifce} root handle 1: htb default 2")
            node.cmd(f"tc class add dev {ifce} parent 1:1 classid 1:6 htb rate 0.5mbit ceil 1.5mbit burst 5mbit")

        else:
            os.system(f"tc qdisc del root dev {ifce}")
            os.system(f"tc qdisc add dev {ifce} root tbf rate {base_rate}mbit burst {buffer_size}kb latency 10ms")

    def quantum_interface(self, ifce, node=None, base_rate=1, peak_rate=2, buffer_size=10):
        """
        Makes existing interface behave like quantum link.
        Buffers can only work one way and can not be shared between connected interfaces.
        """


        latency = 200


        if node is not None:
            node.cmd(f"tc qdisc del root dev {ifce}")
            #node.cmd(f"tc qdisc add dev {ifce} root tbf rate {base_rate}mbit burst {buffer_size}kb latency {latency}ms peakrate {peak_rate}mbit mtu 1540")
            node.cmd(f"tc qdisc add dev {ifce} root handle 1: htb default 6")
            node.cmd(f"tc class add dev {ifce} parent 1:1 classid 1:6 htb rate {base_rate}mbit ceil {peak_rate}mbit burst {buffer_size}mbit")
        else:
            os.system(f"tc qdisc del root dev {ifce}")
            os.system(f"tc qdisc add dev {ifce} root handle 1: htb default 6")
            os.system(f"tc class add dev {ifce} parent 1:1 classid 1:6 htb rate {base_rate}mbit ceil {peak_rate}mbit burst {buffer_size}mbit")

    def add_quantum_link(self, node_1, node_2,
                         link_ip_address: str,
                         node_1_ip: str=None,
                         node_2_ip: str=None,
                         bw=100,
                         delay="10ms",
                         simple=False,
                         docker_bridge="quantum_bridge",
                         epr_frame_size=20):
        """
        Adds quantum link in the folloving way:
        if node_2_ip == NONE -> switch

        Since quantum link is actually a container, it needs IP address
        q_container
            ┌┴┐
        h1 -┘ └- h2
        """
        q_link_dir = self.log_dir+"/bridge-"+str(self.quantum_bridge_counter)
        abs_dir = str(str(pathlib.Path().absolute()) + q_link_dir.replace("./","/"))
        os.mkdir(q_link_dir)

        bridge = self.addDockerHost(
            "bridge"+str(self.quantum_bridge_counter),
            dimage=f"{docker_bridge}:latest",
            ip=link_ip_address,
            docker_args={
                "hostname": "quantum_bridge",
                "volumes": {f"{abs_dir}": {"bind": "/logs", "mode": "rw"}},
            },
        )
        self.quantum_bridge_counter = self.quantum_bridge_counter + 1

        bridgeName = bridge.name
        name1 = node_1.name
        name2 = node_2.name
        self.addLink(node_1, bridge, bw=bw, delay=delay,
                     intfName1=f"{name1}-{bridgeName}",
                     intfName2=f"{bridgeName}-{name1}")
        self.addLink(node_2, bridge, bw=bw, delay=delay,
                     intfName1=f"{name2}-{bridgeName}",
                     intfName2=f"{bridgeName}-{name2}")


        # SETTING KERNEL SETTINGS
        #h1.cmd("sysctl -w  net.ipv4.conf.all.rp_filter=0")
        #h2.cmd("sysctl -w  net.ipv4.conf.all.rp_filter=0")
        #h1.cmd("sysctl -w  net.ipv4.conf.default.rp_filter=0")
        #h2.cmd("sysctl -w  net.ipv4.conf.default.rp_filter=0")
        #h2.cmd("sysctl -w  net.ipv4.conf.h1-bridge.rp_filter=0")


        gw = link_ip_address.split('/')[0].split('.')
        gw[-1]='1'
        gw = '.'.join(gw)

        bridge.cmd(f"ip addr flush dev {bridgeName}-{name1}")
        bridge.cmd(f"ip addr flush dev {bridgeName}-{name2}")
        bridge.cmd("brctl addbr bridge")
        bridge.cmd(f"brctl addif bridge {bridgeName}-{name1}")
        bridge.cmd(f"brctl addif bridge {bridgeName}-{name2}")
        bridge.cmd("ip link set dev bridge up")
        bridge.cmd(f"ip addr add {link_ip_address} brd + dev bridge")
        bridge.cmd(f"route add default gw {gw} dev bridge")


        if node_1_ip is not None:
            node_1.setIP(node_1_ip, intf=f"{node_1.name}-{bridge.name}")

        if node_2_ip is not None:
            node_2.setIP(node_2_ip, intf=f"{node_2.name}-{bridge.name}")

        # bridge.cmd("nft add filter input counter queue num 1")
        # bridge.cmd("nft add table bridge custom")
        # bridge.cmd("nft add chain bridge custom
        #bridge.cmd("iptables -A FORWARD -i bridge -p all -j NFQUEUE --queue-num 1")
        #bridge.cmd(f"iptables -A FORWARD -i {bridgeName}-{name1} -p all -j NFQUEUE --queue-num 1")
        #bridge.cmd(f"iptables -A FORWARD -i {bridgeName}-{name2} -p all -j NFQUEUE --queue-num 2")
        n = 0
        er = bridge.cmd(f"iptables -I FORWARD -m physdev --physdev-is-bridged --physdev-in {bridgeName}-{name1} -j NFQUEUE --queue-num {n} --queue-bypass")
        bridge.cmd(f"iptables -I FORWARD -m physdev --physdev-is-bridged --physdev-in {bridgeName}-{name2} -j NFQUEUE --queue-num {n+1} --queue-bypass")

        bridge.cmd(f"echo '{node_1_ip}\n{node_2_ip}' > /app/hosts.txt")
        self._start(docker_bridge ,bridge , epr_frame_size=epr_frame_size, simple=simple)
        return bridge

    def _start(self, docker_bridge, bridge, epr_frame_size=100, epr_buffer_size=1000, sleep_time=5, single_transmission_delay=1, simple=False):
        """
        Initiate bridge.py and wait until it's up and running
        PRIVATE METHOD
        """
        if docker_bridge is "quantum_bridge_c":
            bridge.cmd(f"tmux new-session -d -s bridge './bridge {epr_frame_size} {epr_buffer_size} {sleep_time} {single_transmission_delay}' &")
        elif simple:
            bridge.cmd("tmux new-session -d -s bridge 'python simple_bridge.py' &")
        else:
            bridge.cmd(f"tmux new-session -d -s bridge 'python bridge.py {epr_frame_size}' &")

        is_up = False

        info("\n*** Waiting for quantum bridge to initiate\n")
        if docker_bridge is "quantum_bridge_c":
            is_up = True
        while not is_up :
            if "log.txt" in bridge.cmd("ls /app/"):
                is_up = True
        info("*** Bridge initiated\n")

    def wait_for_number_of_packets_transmitted(self, bridge, target_count):
        """
        Waiting for enough packets to be transmitted through a bridge
        """
        count = int(bridge.cmd("wc -l packet_logs.log").split(" ")[0])
        time.sleep(1)
        next_print = 0
        while count < target_count:
            #print(bridge.cmd("tail packet_logs.log"))
            count = int(bridge.cmd("wc -l packet_logs.log").split(" ")[0])
            #if (count-1) > next_print:
            c_string = '{:4d}'.format(count-1)
            print(f"{c_string} packets have been processed at {datetime.datetime.now()}")
            #    next_print = next_print + 10
            time.sleep(10)

    def extract_data(self, bridge ,src:str, dest:str):
        """
        Extracting any files from the bridge container
        """
        dest_file = dest.split("/")[-1]


        #print(f"cp {src} /logs/{dest_file}")
        bridge.cmd(f"cp {src} /logs/{dest_file}")
        q_link_file = self.log_dir+"/bridge-"+bridge.name.replace("bridge","") + "/" +dest_file
        q_link_file.replace("./","")
        dest_dirs = dest.split("/")[:-1]

        pathlib.Path("/".join(dest_dirs)).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(q_link_file, dest)
