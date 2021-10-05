from threading import Event, Timer
import queue 

from qunetsim.components import Host
from qunetsim.objects import Logger

from .daemon_thread import DaemonThread
from .quantum_frame import QuantumFrame

Logger.DISABLED = False

class Node:
    """ Node class
    -> Runs protocols in threads
    -> Has three types of threads:
        -> Receiver protocol
        -> Sender protocol
        -> EPR initiator timer (Only one node can be epr initiator)
    """

    def __init__(self, host: str, network, backend, queue_size=512, is_epr_initiator=False, frame_size=48,
                 epr_transmission_time=20, epr_manual_mode=False,epr_frame_size=20):
        """
        Inits node
        """
        self.host = Host(host, backend)
        self.host.delay = 0
        self.network = network
        self.network.add_host(self.host)
        self.entanglement_buffer = queue.Queue()
        self.queue_size = queue_size
        self.frame_size = frame_size
        self.epr_frame_size = epr_frame_size
        #Packet management before/after channel transmission
        self.packet_in_queue_event = Event()
        self.packet_out_queue_event = Event()
        self.packet_in_queue = []
        self.packet_out_queue = []
        self.epr_trigger = Event()
        self.epr_lock = Event()
        self.stop_signal = Event()
        self.is_busy = Event()
        self.is_epr_initiator = is_epr_initiator
        self.timer_thread = None
        self.receiver_thread = None
        self.sender_thread = None
        self.peer = None
        self.max_queue_size = 8*1000
        self.epr_transmission_time = epr_transmission_time
        self.epr_manual_mode = epr_manual_mode

    def connect(self, node):
        """
        Connects node to another node,
        Only one node needs to connect, connection is made bi-directionally

        PUBLIC METHOD
        """
        self.host.add_connection(node.host.host_id)
        node.host.add_connection(self.host.host_id)
        self.peer = node
        node.peer = self
        self.network.update_host(self.host)
        self.network.update_host(self.peer.host)

    def start(self):
        """
        Starts host protocols

        PUBLIC METHOD
        """
        if self.is_epr_initiator:
            self.timer_thread = Timer(1, self.epr_timer)
            self.timer_thread.start()
        self.receiver_thread = DaemonThread(self.receiver_protocol)
        self.sender_thread = DaemonThread(self.sender_protocol)
        print(self.host.host_id + " protocols initiated")

    def stop(self):
        """
        Sends stop signal to threads.
        Used to stop protocol cleanly.

        PUBLIC METHOD
        """
        self.stop_signal.set()
        self.receiver_thread.join()
        self.sender_thread.join()

    def wait_stop(self):
        """
        Waits and joins the threads.
        Used to stop protocols cleanly.

        PULIC METHOD
        """
        self.receiver_thread.join()
        self.sender_thread.join()

    def run_until_finished(self):
        """
        Keep protocols running,
        doesn't return until protocols are finished

        PUBLIC METHOD
        """
        self.receiver_thread.join()
        self.sender_thread.join()

    def epr_timer(self):
        """
        Triggers epr frame transmission periodically,
        period is set with self.epr_transmission_time

        PUBLIC METHOD
        """
        if self.stop_signal.is_set():
            return
        if self.entanglement_buffer.qsize() > self.max_queue_size:
            return
        print(f"{self.host.host_id} initiated EPR Transmission")
        self.epr_trigger.set()
        self.epr_lock.wait()
        self.epr_trigger.clear()
        self.epr_lock.clear()
        self.timer_thread = Timer(self.epr_transmission_time, self.epr_timer)
        self.timer_thread.start()

    def receiver_protocol(self):
        """
        Listenes to incomming quantum frames.
        Is ran in thread.

        PUBLIC METHOD
        """
        print(self.host.host_id + " receiver protocol started")
        try:
            while True:
                if self.stop_signal.is_set():
                    return
                qf = QuantumFrame(node=self, mtu=self.epr_frame_size)
                print("WAITING TO RECEIVE")
                qf.receive(self.peer.host)
                print(f"NUMBER OF TRANSMISSIONS {qf.number_of_transmissions}")
                if qf.type == 'EPR':
                    for q in qf.extract_local_pairs():
                        #print(q.id)
                        self.entanglement_buffer.put(q)
                    #map(self.entanglement_buffer.put, qf.extract_local_pairs())
                    #self.entanglement_buffer.extend(qf.extract_local_pairs())
                    if self.epr_manual_mode:
                        self.packet_out_queue.append((qf.raw_qubits,
                                                        {"number_of_epr_pairs_consumed":qf.epr_consumed,
                                                        "number_of_transmissions":qf.number_of_transmissions,
                                                        "transmission_type":qf.type,
                                                        "measurment_time":"0"
                                                        }))
                        self.packet_out_queue_event.set()
                    print(str(self.entanglement_buffer.qsize()) + " available local pairs")
                else:
                    print("DATA FRAME RECEIVED -- " + qf.type)
                    self.packet_out_queue.append((qf.raw_bits,
                                                  {"number_of_epr_pairs_consumed":qf.epr_consumed,
                                                   "number_of_transmissions":qf.number_of_transmissions,
                                                   "transmission_type":qf.type,
                                                   "measurment_time":qf.measurement_time
                                                   }))
                    print(qf.epr_consumed)
                    print(qf.number_of_transmissions)
                    self.packet_out_queue_event.set()

        except Exception as e:
            print("Exception in receiver protocol")
            print(e)

    def sender_protocol(self):
        """
        Sends quantum frames if requested.
        Is ran in thread

        PUBLIC METHOD
        """
        print(self.host.host_id + " sender protocol started")
        try:
            while True:
                if self.stop_signal.is_set():
                    return
                if self.packet_in_queue_event.is_set():
                    packet = self.packet_in_queue.pop(0)
                    print("PACKET FLAG IS SET")
                    print(packet)
                    if packet == "EPR":
                        print("MANUAL EPR DATA FRAME TRANSMISSION")
                        self._transmit_epr_frame()
                    else:
                        self._transmit_data_frame(packet)
                    if len(self.packet_in_queue) == 0:
                        self.packet_in_queue_event.clear()
                elif self.epr_trigger.is_set() and not self.epr_manual_mode:
                    self._transmit_epr_frame()
                    self.epr_lock.set()
                    self.epr_trigger.clear()
        except Exception as e:
            print("Exception in sender protocol")
            print(e)

    def add_to_in_queue(self, data):
        """
        Adds packets to incomming queue.
        Used to interract with sender thread.

        PUBLIC METHOD
        """
        print("Adding packet to queue")
        self.packet_in_queue.append(data)
        self.packet_in_queue_event.set()

    def get_from_out_queue(self):
        """
        Waits and gets packet from outgoing queue.
        Used to interract with receiver thread.

        PUBLIC METHOD
        """
        self.packet_out_queue_event.wait()
        out_packet = self.packet_out_queue.pop(0)
        if len(self.packet_out_queue) == 0:
            self.packet_out_queue_event.clear()
        return out_packet

    def _transmit_epr_frame(self):
        """
        Sends epr quantum frame.
        Is triggered periodically by epr_timer() method.

        PRIVATE METHOD: called by sender_protocol()
        """
        qf = QuantumFrame(node=self, mtu=self.epr_frame_size)
        qf.send_epr_frame(self.peer)
        for q in qf.extract_local_pairs():
            self.entanglement_buffer.put(q)
        print("NUM OF QUBITS IN SENDER BUFFER", self.entanglement_buffer.qsize())

    def _transmit_data_frame(self, data):
        """
        Sends data frame.

        PRIVATE METHOD: called by sender_protocol()
        """
        qf = QuantumFrame(node=self,mtu=self.epr_frame_size)
        qf.send_data_frame(data, self.peer, self.entanglement_buffer)

