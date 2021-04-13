from comnetsemu.net import Containernet
from mininet.log import info
import os
import shutil
import pathlib


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
        print("Making a directory")
        os.mkdir(self.log_dir)


    def add_quantum_link(self, h1, h2, ip_address: str, bw=10, delay="100ms", simple=True):
        """
        Adds quantum link in the folloving way:

        q_container
            ┌┴┐
        h1 -┘ └- h2
        """
        q_link_dir = self.log_dir+"/bridge-"+str(self.quantum_bridge_counter)
        abs_dir = str(str(pathlib.Path().absolute()) + q_link_dir.replace("./","/"))

        print(abs_dir)
        os.mkdir(q_link_dir)

        bridge = self.addDockerHost(
            "bridge"+str(self.quantum_bridge_counter),
            dimage="quantum_bridge:latest",
            ip=ip_address,
            docker_args={
                "hostname": "quantum_bridge",
                "volumes": {f"{abs_dir}": {"bind": "/logs", "mode": "rw"}},
            },
        )

        self.addLink(h1, bridge, bw=bw, delay=delay, intfName1="h1-bridge", intfName2="bridge-h1")
        self.addLink(h2, bridge, bw=bw, delay=delay, intfName1="h1-bridge", intfName2="bridge-h2")
        self.quantum_bridge_counter = self.quantum_bridge_counter + 1 

        # SETTING KERNEL SETTINGS
        h1.cmd("sysctl -w  net.ipv4.conf.all.rp_filter=0")
        h2.cmd("sysctl -w  net.ipv4.conf.all.rp_filter=0")
        h1.cmd("sysctl -w  net.ipv4.conf.default.rp_filter=0")
        h2.cmd("sysctl -w  net.ipv4.conf.default.rp_filter=0")
        h2.cmd("sysctl -w  net.ipv4.conf.h1-bridge.rp_filter=0")

        bridge.cmd("ip addr flush dev bridge-h1")
        bridge.cmd("ip addr flush dev bridge-h2")
        bridge.cmd("brctl addbr bridge")
        bridge.cmd("brctl addif bridge bridge-h1")
        bridge.cmd("brctl addif bridge bridge-h2")
        bridge.cmd("ip link set dev bridge up")
        bridge.cmd("ip addr add 11.0.0.3/24 brd + dev bridge")
        bridge.cmd("route add default gw 11.0.0.1 dev bridge")

        # bridge.cmd("nft add filter input counter queue num 1")
        # bridge.cmd("nft add table bridge custom")
        # bridge.cmd("nft add chain bridge custom
        bridge.cmd("iptables -A FORWARD -i bridge -p all -j NFQUEUE --queue-num 1")

        bridge.cmd("echo '11.0.0.1 \n11.0.0.2' > /app/hosts.txt")
        self._start(simple, bridge)
        return bridge

    def _start(self, simple, bridge):
        """
        Initiate bridge.py and wait until it's up and running
        PRIVATE METHOD
        """
        if simple:
            bridge.cmd("tmux new-session -d -s bridge 'python simple_bridge.py' &")
        else:
            bridge.cmd("tmux new-session -d -s bridge 'python bridge.py' &")

        is_up = False

        info("\n*** Waiting for quantum bridge to initiate\n")
        while not is_up:
            if "log.txt" in bridge.cmd("ls /app/"):
                is_up = True

    def extract_data(self, bridge ,src:str, dest:str):
        """
        Extracting any files from the bridge container
        """
        dest_file = dest.split("/")[-1]

        print(f"cp {src} /logs/{dest_file}")
        bridge.cmd(f"cp {src} /logs/{dest_file}")
        q_link_file = self.log_dir+"/bridge-"+bridge.name.replace("bridge","") + "/" +dest_file
        q_link_file.replace("./","")

        shutil.copyfile(q_link_file, dest)

