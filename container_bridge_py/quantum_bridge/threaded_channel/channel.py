from qunetsim.backends.qutip_backend import QuTipBackend
from qunetsim.components import Network
from qunetsim.objects import Logger
from datetime import timedelta, datetime
from .simple_stabilizer_backend import SimpleStabilizerBackend

Logger.DISABLED = True

from .node import Node


def routing_algorithm(di_graph, source, destination):
    """ Efficient routing algorithm for quantum network"""
    return [source, destination]


class Channel:
    """ Channel class
    -> Initiates network and nodes,
    -> Passes classical messages to the right node and retrievs them from other node
    """

    def __init__(self, hosts, epr_frame_size, backend=SimpleStabilizerBackend()):
        """
        Inits Channel
        """
        self.backend = backend
        self.network = Network.get_instance()
        self.epr_frame_size = epr_frame_size
        self.network.delay = 0
        self.network.quantum_routing_algo = routing_algorithm
        self.network.classical_routing_algo = routing_algorithm
        self.network.start(nodes=hosts, backend=self.backend)
        self.node_a = Node(hosts[0], self.network, self.backend, is_epr_initiator=False,
                           epr_manual_mode=True, epr_frame_size=self.epr_frame_size)
        self.node_b = Node(hosts[1], self.network, self.backend, is_epr_initiator=False,
                           epr_manual_mode=True, epr_frame_size=self.epr_frame_size)
        self.node_a.connect(self.node_b)
        self.node_b.connect(self.node_a)
        self.node_a.start()
        self.node_a.host.start()
        self.node_b.start()
        self.node_b.host.start()

        self.packet_logger = _Packet_logger(datetime.now(), "packet_logs.log")

    def transmit_packet(self, packet_bits, source_host, packet_type):
        """
        Passes packet to appropriate node to be sent through quantum link.
        Waits until packet was received, and then returns the bits that came out
        on the other side

        PUBLIC METHOD
        packet_type = [EPR, NORMAL]
        """
        print(f"Packet_type: {packet_type}")
        start_time = datetime.now()
        source_node = [node for node in [self.node_a, self.node_b]
                    if node.host.host_id == source_host][0]
        destination_node = [node for node in [self.node_a, self.node_b]
                                if node.host.host_id != source_host][0]
        if packet_type == "normal":
            source_node.add_to_in_queue(packet_bits)
            out_packet = destination_node.get_from_out_queue()
            out_bits = out_packet[0]
            epr_consumed = out_packet[1]["number_of_epr_pairs_consumed"]
            number_of_transmissions = out_packet[1]["number_of_transmissions"]
            transmission_type = out_packet[1]["transmission_type"]
            measurement_time = out_packet[1]["measurment_time"]

            end_time = datetime.now()
            self.packet_logger.log_packet(source_node.host.host_id, destination_node.host.host_id,
                                        start_time, end_time, measurement_time,
                                        out_bits, int(epr_consumed), int(number_of_transmissions), transmission_type)
            return out_bits
        elif packet_type == "epr":
            print("SENDING EPR??")
            source_node.add_to_in_queue("EPR")
            out_packet = destination_node.get_from_out_queue()
            out_bits = out_packet[0]
            epr_consumed = out_packet[1]["number_of_epr_pairs_consumed"]
            number_of_transmissions = out_packet[1]["number_of_transmissions"]
            transmission_type = out_packet[1]["transmission_type"]
            end_time = datetime.now()
            measurement_time = timedelta(seconds=0)
            print(f"{type(epr_consumed)}, epr consumed, {epr_consumed}")
            print(f"{type(number_of_transmissions)}, number_of_transmissions, {number_of_transmissions}")
            self.packet_logger.log_packet(source_node.host.host_id, destination_node.host.host_id,
                                        start_time, end_time, measurement_time,
                                        out_bits, int(epr_consumed), int(number_of_transmissions), transmission_type)


class _Packet_logger:
    """ _Packet_logger
    private class
    logs packet information into a file

    """
    def __init__(self, channel_start_time, log_file):
        self.channel_start_time = channel_start_time
        self.log_file = log_file
        log_line = ["sender", "receiver", "start_time", "end_time", "transmission_time",
                    "measurement_time", "transmission_time_no_measurement", "packet bit length",
                    "packet transmission rate (w m)", "packet transmission rate (w/o measurement)"]
        log_line.extend(["transmission type", "number of epr consumed", "number of transmissions"])
        self._write_log_line(log_line)

    def log_packet(self, sender, receiver, start_time, end_time, measurement_time, packet_bits,
                   epr_used, number_of_transmissions, transmission_type):
        print(f"Logging: {transmission_type}")
        transmission_time = end_time - start_time
        transmission_time_no_measurement = transmission_time - measurement_time
        #transmission_time = str(transmission_time.seconds) + '.' + str(transmission_time.microseconds/1000)
        start_time =  start_time - self.channel_start_time
        #start_time = str(start_time.seconds) + '.' + str(start_time.microseconds/1000)
        bit_len = len(packet_bits)*8
        end_time =  end_time - self.channel_start_time
        #end_time = str(end_time.seconds) + '.' + str(end_time.microseconds/1000)

        bandwidth = bit_len/(float(transmission_time.total_seconds()))
        bandwidth_n_m = bit_len/(float(transmission_time_no_measurement.total_seconds()))

        if transmission_type == "DATA_SEQ":
            transmission_type = "normal"
        elif epr_used < 0:
            transmission_type = "epr"
        elif epr_used != number_of_transmissions:
            transmission_type = "mixed"
        else:
            transmission_type = "superdense"



        log_line = [sender, receiver, format(float(start_time.total_seconds()),".2f"),
                    format(float(end_time.total_seconds()),".2f"), format(float(transmission_time.total_seconds()),".2f")]
        log_line.extend([format(float(measurement_time.total_seconds()), ".2f"),
                         format(float(transmission_time_no_measurement.total_seconds()),".2f")])
        log_line.extend([str(bit_len), format(bandwidth,".2f"),format(bandwidth_n_m,".2f")])
        log_line.extend([transmission_type, str(epr_used), str(number_of_transmissions)])
        log_line = [str(x) for x in log_line]
        self._write_log_line(log_line)

    def _write_log_line(self, log_line):
        with open(self.log_file, "a") as f:
            log_line = ",".join(log_line)
            f.write(log_line+"\n")





