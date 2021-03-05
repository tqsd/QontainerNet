from threading import Event, Timer

from qunetsim.components import Host
from qunetsim.objects import Logger

Logger.DISABLED = True


class Node:
    """ Node class
    -> Runs protocols in threads
    -> Has three types of threads:
        -> Receiver protocol
        -> Sender protocol
        -> EPR initiator timer (Only one node can be epr initiator)
    """

    def __init__(self, host: str, network, backend, queue_size=512, is_epr_initiator=False, frame_size=48,
                 epr_transmission_time=100):
        self.host = Host(host, backend)
        self.host.delay = 0
        self.network = network
        self.network.add_host(self.host)
        self.entanglement_buffer = []
        self.queue_size = queue_size
        self.frame_size = 48
        self.packet_in_queue_event = Event()
        self.packet_out_queue_event = Event()
        self.packet_in_queue = []
        self.packet_out_queue = []
        self.epr_trigger = Event()
        self.epr_lock = Event()
        self.stop_signal = Event()
        self.is_epr_initiator = is_epr_initiator
        self.timer_thread = None
        self.receiver_thread = None
        self.sender_thread = None
        self.peer = None
        self.epr_transmission_time = epr_transmission_time

    def connect(self, node):
        """ Only one connection needs to be made """
        self.host.add_connection(node.host.host_id)
        node.host.add_connection(self.host.host_id)
        self.peer = node
        node.peer = self
        self.network.update_host(self.host)
        self.network.update_host(self.peer.host)

    def start(self):
        """ Starts host protocols """
        if self.is_epr_initiator:
            self.timer_thread = Timer(1, self.epr_timer)
            self.timer_thread.start()
        self.receiver_thread = DaemonThread(self.receiver_protocol)
        self.sender_thread = DaemonThread(self.sender_protocol)
        print(self.host.host_id + " protocols initiated")

    def stop(self):
        """ Sends stop signal to threads """
        self.stop_signal.set()
        self.receiver_thread.join()
        self.sender_thread.join()

    def wait_stop(self):
        """ Waits and joins the threads """
        self.receiver_thread.join()
        self.sender_thread.join()

    def run_until_finished(self):
        """ Protocols don't actually ever finish """
        self.receiver_thread.join()
        self.sender_thread.join()

    def epr_timer(self):
        """ Triggers epr frame transmission periodically """
        if self.stop_signal.is_set():
            return
        print("Initiating EPR Transmission")
        self.epr_trigger.set()
        self.epr_lock.wait()
        self.epr_trigger.clear()
        self.epr_lock.clear()
        self.timer_thread = Timer(self.epr_transmission_time, self.epr_timer)
        self.timer_thread.start()

    def receiver_protocol(self):
        """ Receiver protocol """
        print(self.host.host_id + " receiver protocol started")
        try:
            while True:
                if self.stop_signal.is_set():
                    return
                qf = QuantumFrame(node=self)
                qf.receive(self.peer.host)
                if qf.type == 'EPR':
                    self.entanglement_buffer.extend(qf.extract_local_pairs())
                    print(str(len(self.entanglement_buffer)) + " available local pairs")
                else:
                    print("DATA FRAME RECEIVED -- " + qf.type)
                    self.packet_out_queue.append(qf.raw_bits)
                    self.packet_out_queue_event.set()

        except Exception as e:
            print("Exception in receiver protocol")
            print(e)

    def sender_protocol(self):
        print(self.host.host_id + " sender protocol started")
        try:
            while True:
                if self.stop_signal.is_set():
                    return
                if self.packet_in_queue_event.isSet():
                    self.transmit_data_frame(self.packet_in_queue.pop(0))
                    if len(self.packet_in_queue) == 0:
                        self.packet_in_queue_event.clear()
                elif self.epr_trigger.isSet():
                    self.transmit_epr_frame()
                    self.epr_lock.set()
                    self.epr_trigger.clear()
        except Exception as e:
            print(e)

    def add_to_in_queue(self, data):
        self.packet_in_queue.append(data)
        self.packet_in_queue_event.set()

    def get_from_out_queue(self):
        self.packet_out_queue_event.wait()
        out_packet = self.packet_out_queue.pop(0)
        if len(self.packet_out_queue) == 0:
            self.packet_out_queue_event.clear()
        return out_packet

    def transmit_epr_frame(self):
        qf = QuantumFrame(node=self)
        qf.send_epr_frame(self.peer.host)
        print("Transmitted")
        self.entanglement_buffer.extend(qf.extract_local_pairs())

    def transmit_data_frame(self, data):
        qf = QuantumFrame(node=self)
        qf.send_data_frame(data, self.peer.host, self.entanglement_buffer)
        print("Transmitted data")

    def ackquire_buffer(self):
        buffer = self.entanglement_buffer
        self.entanglement_buffer = []
        return buffer

    def release_buffer(self, buffer):
        self.entanglement_buffer = buffer + self.entanglement_buffer
