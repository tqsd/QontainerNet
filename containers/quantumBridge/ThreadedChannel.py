from qunetsim.components import Host, Network
from qunetsim.objects import Qubit
from qunetsim.backends import ProjectQBackend 
from qunetsim.backends.qutip_backend import QuTipBackend
from threading import Thread, Event, Timer
import sys
import time
from qunetsim.objects import Logger

Logger.DISABLED = True


class DaemonThread(Thread):
    """ A Daemon thread that runs a task until completion and then exits. """

    def __init__(self, target, args=None):
        if args is not None:
            super().__init__(target=target, daemon=True, args=args)
        else:
            super().__init__(target=target, daemon=True)
        self.start() 


def routing_algorithm(di_graph, source, destination):
    """ Efficient routing algorithm for quantum network"""
    return [source, destination]


class Channel:
    """ Channel class
    -> Initiates network and nodes,
    -> Passes classical messages to the right node and retrievs them from other node
    """
    def __init__(self, hosts, backend=QuTipBackend()):
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
        """ Passes classical packet through quantum channel"""
        pass


class Node:
    """ Node class
    -> Runs protocols in threads
    -> Has three types of threads:
        -> Receiver protocol
        -> Sender protocol
        -> EPR initiator timer (Only one node can be epr initiator)
    """
    def __init__(self, host:str, network, backend, queue_size=512, is_epr_initiator=False, frame_size=48, epr_transmission_time=100):
        self.host = Host(host, backend)
        self.host.delay = 0
        self.network = network
        self.network.add_host(self.host)
        self.entanglement_buffer = []
        self.queue_size = queue_size
        self.frame_size = 48
        self.packet_in_queue = Event()
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
        self.sender_thread= DaemonThread(self.sender_protocol)
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
                qf = QuantumFrame(self.host)
                qf.receive(self.peer.host)
                if qf.type == 'EPR':
                    self.entanglement_buffer.extend(qf.extract_local_pairs())
                    print(str(len(self.entanglement_buffer)) + " available local pairs")
                elif qf.type == 'DATA_SC':
                    pass
                elif qf.type == 'DATA_SEQ':
                    pass

        except Exception as e:
            print("Exception in receiver protocol")
            print(e)

    def sender_protocol(self):
        print(self.host.host_id + " sender protocol started")
        try:
            while True: 
                if self.stop_signal.is_set():
                    return
                if self.packet_in_queue.isSet():
                    self.transmit_packet()
                elif self.epr_trigger.isSet():
                    self.transmit_epr_frame()
                    self.epr_lock.set()
                    self.epr_trigger.clear()
        except Exception as e:
            print(e)

    def transmit_epr_frame(self):
        qf = QuantumFrame(host=self.host) 
        qf.send_epr_frame(self.peer.host)
        print("Transmitted")
        self.entanglement_buffer.extend(qf.extract_local_pairs())

    def receive_data_frame(self):
        pass

    def transmit_packet(self):
        q = Qubit(self.host)
        q.X()
        self.host.send_qubit(self.peer.host.host_id, q, await_ack=True)


class QuantumFrame:
    def __init__(self, host, mtu=10, await_ack=False):
        # MTU is in bytes
        self.type = None
        self.host = host
        self.MTU = mtu
        self.qubit_array = []
        self.local_qubits = []
        # Performance statistics
        self.start_time = time.time()
        self.creation_time = None
        self.received_time = None
        self.measurement_time = None
        self.await_ack = await_ack

    def _create_header(self):
        """ For ahead of time qubit preparation, not used currently"""
        q1 = Qubit(self.host)
        q2 = Qubit(self.host)

        if self.type == "EPR":
            pass
        elif self.type == "DATA_SC":
            q2.X()
        elif self.type == "DATA_SEQ":
            q1.X()
        return [q1, q2]

    def create_epr_frame(self):
        """ Creating epr ahead of time, not used currently"""
        if self.type is not None:
            raise Exception("Quantum Frame type already defined")
        self.type = "EPR" 
        self.qubit_array.extend(self._create_header())
        print("Header created")
        for x in range(self.MTU):
            for i in range(8):
                q1 = Qubit(self.host)
                q2 = Qubit(self.host)
                q1.H()
                q1.cnot(q2)
                self.local_qubits.append(q1)
                self.qubit_array.append(q2)

        self.creation_time = time.time()

    def send_epr_frame(self, destination):
        header = '00'
        for h in header:
            q = Qubit(self.host)
            if h == '1':
                q.X()
            q_id = self.host.send_qubit(destination.host_id, q, await_ack=self.await_ack,
                                        no_ack=True)
        for x in range(self.MTU):
            print("Sending " + str(x)+"/"+str(self.MTU)+" bytes")
            for i in range(8):
                q1 = Qubit(self.host)
                q2 = Qubit(self.host)
                q1.H()
                q1.cnot(q2)
                self.local_qubits.append(q1)
                q_id = self.host.send_qubit(destination.host_id, q2, await_ack=self.await_ack,
                                            no_ack=True)
                
    def extract_local_pairs(self):
        return self.local_qubits

    def receive(self, source):
        print("Listening for quantum frame")
        header = ""
        while len(header) < 2:
            q = self.host.get_data_qubit(source.host_id)
            if q is not None:
                m = q.measure()
                if m:
                    header = header + '1'
                else:
                    header = header + '0'

        if header == '00':
            self._receive_epr(source)

    def _receive_epr(self, source):
        self.type = 'EPR'
        for x in range(self.MTU):
            print("Receiving " + str(x+1) + " byte of " + str(self.MTU))
            for i in range(8):
                q = self.host.get_data_qubit(source.host_id)
                while q is None:
                    q = self.host.get_data_qubit(source.host_id)
                self.local_qubits.append(q)
        Logger.get_instance().log(str(self.host.host_id) + "received EPR frame")


if __name__ == "__main__":
    channel = Channel(['Alice', 'Bob'])
    try:
        channel.node_a.wait_stop()
        channel.node_b.wait_stop()
    except KeyboardInterrupt:
        print("Keyboard Interrupt")
        channel.node_a.stop()
        channel.node_b.stop()
        sys.exit(0)

