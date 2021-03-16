from comnetsemu.net import Containernet
from mininet.log import info


class Qontainernet(Containernet):

    def add_quantum_link(self, h1, h2, ip_address: str, bw=10, delay="100ms"):
        bridge = self.addDockerHost(
            "bridge",
            dimage="quantum_bridge:latest",
            ip=ip_address,
            docker_args={"hostname": "quantum_bridge"},
        )
        self.addLink(h1, bridge, bw=10, delay="100ms", intfName1="h1-bridge", intfName2="bridge-h1")
        self.addLink(h2, bridge, bw=10, delay="100ms", intfName1="h1-bridge", intfName2="bridge-h2")

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

        bridge.cmd("tmux new-session -d -s bridge 'python bridge.py' &")

        is_up = False

        info("\n*** Waiting for quantum bridge to initiate\n")
        while not is_up:
            if "log.txt" in bridge.cmd("ls /app/"):
                is_up = True
        return bridge

    def test_method(self):
        print("Qontainernet")