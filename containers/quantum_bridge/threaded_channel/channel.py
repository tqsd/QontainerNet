from qunetsim.backends.qutip_backend import QuTipBackend
from qunetsim.components import Network
from qunetsim.objects import Logger

Logger.DISABLED = False

from .node import Node


def routing_algorithm(di_graph, source, destination):
    """ Efficient routing algorithm for quantum network"""
    return [source, destination]


class Channel:
    """ Channel class
    -> Initiates network and nodes,
    -> Passes classical messages to the right node and retrievs them from other node
    """

    def __init__(self, hosts, backend=QuTipBackend()):
        """
        Inits Channel
        """
        self.backend = backend
        self.network = Network.get_instance()
        self.network.delay = 0
        self.network.quantum_routing_algo = routing_algorithm
        self.network.start(nodes=hosts, backend=self.backend)
        self.node_a = Node(hosts[0], self.network, self.backend, is_epr_initiator=True)
        self.node_b = Node(hosts[1], self.network, self.backend)
        self.node_a.connect(self.node_b)
        self.node_b.connect(self.node_a)
        self.node_a.start()
        self.node_a.host.start()
        self.node_b.start()
        self.node_b.host.start()

    def transmit_packet(self, packet_bits, source_host):
        """
        Passes packet to appropriate node to be sent through quantum link.
        Waits until packet was received, and then returns the bits that came out
        on the other side

        PUBLIC METHOD
        """
        source_node = [node for node in [self.node_a, self.node_b]
                       if node.host.host_id == source_host][0]
        destination_node = [node for node in [self.node_a, self.node_b]
                            if node.host.host_id != source_host][0]
        source_node.add_to_in_queue(packet_bits)
        out_bits = destination_node.get_from_out_queue()
        return out_bits
