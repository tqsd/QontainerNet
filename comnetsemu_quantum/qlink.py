from comnetsemu.net import Containernet
from mininet.log import info


class Qontainernet(Containernet):
    """
    Qontainernet is extension of Containernet
    It adds quantum links; Currently supports only one link
    """

    def add_quantum_link(self, h1, h2, ip_address: str, bw=10, delay="100ms"):
        """
        Adds quantum link in the folloving way:

        q_container
            ┌┴┐
        h1 -┘ └- h2
        """

        self.bridge = self.addDockerHost(
            "bridge",
            dimage="quantum_bridge:latest",
            ip=ip_address,
            docker_args={"hostname": "quantum_bridge"},
        )
        self.addLink(h1, self.bridge, bw=bw, delay=delay, intfName1="h1-bridge", intfName2="bridge-h1")
        self.addLink(h2, self.bridge, bw=bw, delay=delay, intfName1="h1-bridge", intfName2="bridge-h2")

        # SETTING KERNEL SETTINGS
        h1.cmd("sysctl -w  net.ipv4.conf.all.rp_filter=0")
        h2.cmd("sysctl -w  net.ipv4.conf.all.rp_filter=0")
        h1.cmd("sysctl -w  net.ipv4.conf.default.rp_filter=0")
        h2.cmd("sysctl -w  net.ipv4.conf.default.rp_filter=0")
        h2.cmd("sysctl -w  net.ipv4.conf.h1-bridge.rp_filter=0")

        self.bridge.cmd("ip addr flush dev bridge-h1")
        self.bridge.cmd("ip addr flush dev bridge-h2")
        self.bridge.cmd("brctl addbr bridge")
        self.bridge.cmd("brctl addif bridge bridge-h1")
        self.bridge.cmd("brctl addif bridge bridge-h2")
        self.bridge.cmd("ip link set dev bridge up")
        self.bridge.cmd("ip addr add 11.0.0.3/24 brd + dev bridge")
        self.bridge.cmd("route add default gw 11.0.0.1 dev bridge")

        # bridge.cmd("nft add filter input counter queue num 1")
        # bridge.cmd("nft add table bridge custom")
        # bridge.cmd("nft add chain bridge custom
        self.bridge.cmd("iptables -A FORWARD -i bridge -p all -j NFQUEUE --queue-num 1")

        self.bridge.cmd("echo '11.0.0.1 \n11.0.0.2' > /app/hosts.txt")
        self._start()
        return self.bridge

    def _start(self):
        """
        Initiate bridge.py and wait until it's up and running
        PRIVATE METHOD
        """
        self.bridge.cmd("tmux new-session -d -s bridge 'python bridge.py' &")

        is_up = False

        info("\n*** Waiting for quantum bridge to initiate\n")
        while not is_up:
            if "log.txt" in self.bridge.cmd("ls /app/"):
                is_up = True
