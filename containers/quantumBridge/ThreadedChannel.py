from qunetsim.components import Host, Network
from qunetsim.objects import Qubit
from qunetsim.backends import ProjectQBackend
from threading import Thread, Event, Timer
import sys, time

class DaemonThread(Thread):
    """ A Daemon thread that runs a task until completion and then exits. """

    def __init__(self, target, args=None):
        if args is not None:
            super().__init__(target=target, daemon=True, args=args)
        else:
            super().__init__(target=target, daemon=True)
        self.start() 

class Channel:
    def __init__(self, hosts):
        self.backend = ProjectQBackend()
        self.network = Network.get_instance()
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
        pass

class Node:
    def __init__(self, host:str, network, backend, queue_size=512, is_epr_initiator=False, frame_size=48, epr_transmission_time=1):
        self.host = Host(host, backend)
        self.network = network
        self.network.add_host(self.host)
        self.entanglement_buffer= []
        self.queue_size = queue_size
        self.frame_size = 48
        self.packet_in_queue = Event()
        self.epr_trigger = Event()
        self.epr_lock = Event()
        self.stop_signal = Event()
        self.is_epr_initiator = is_epr_initiator
        self.receiver_thread = None
        self.sender_thread = None
        self.epr_transmission_time = epr_transmission_time

    def connect(self, node):
        ''' Only one connection needs to be made '''
        self.host.add_connection(node.host.host_id)
        node.host.add_connection(self.host.host_id)
        self.peer = node
        node.peer = self
        self.network.update_host(self.host)
        self.network.update_host(self.peer.host)


    def start(self):
        if self.is_epr_initiator:
            self.timer_thread = Timer(self.epr_transmission_time, self.epr_timer)
            self.timer_thread.start()
        self.receiver_thread = DaemonThread(self.receiver_protocol)
        self.sender_thread= DaemonThread(self.sender_protocol)
        print(self.host.host_id + " protocols initiated")

    def stop(self):
        print("Sending stop signal")
        self.stop_signal.set()
        self.receiver_thread.join()
        self.sender_thread.join()
    
    def wait_stop(self):
        self.receiver_thread.join()
        self.sender_thread.join()

    def runUntilFinished(self):
        self.receiver_thread.join()
        self.sender_thread.join()

    def epr_timer(self):
        if self.stop_signal.is_set():
            return
        print("EPR")
        self.epr_trigger.set()
        self.epr_lock.wait()
        self.epr_trigger.clear()
        self.epr_lock.clear()
        self.timer_thread = Timer(self.epr_transmission_time, self.epr_timer)
        self.timer_thread.start()


    def receiver_protocol(self):
        print(self.host.host_id + " receiver protocol started")
        try:
            while True:
                print("Listening for quantum frames")
                print(self.stop_signal.is_set())
                if self.stop_signal.is_set():
                    return
                qf = QuantumFrame(self.host)
                qf.receive(self.peer.host)

                continue
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

    def receive_epr_frame(self):
        print("Receiving epr frame")
        pass

    def transmit_epr_frame(self):
        qf = QuantumFrame(host=self.host) 
        qf.create_epr_frame()
        self.entanglement_buffer.extend(qf.extract_local_pairs())
        qf.send(self.peer.host)

    def receive_data_frame(self):
        pass

    def transmit_packet(self):
        q = Qubit(self.host)
        q.X()
        self.host.send_qubit(self.peer.host.host_id, q, await_ack=True)

class QuantumFrame:
    def __init__(self, host, MTU=10):
        # MTU is in bytes
        self.type = None
        self.host = host
        self.MTU = MTU
        self.qubit_array = []
        self.local_qubits = []
        # Performance statistics
        self.start_time = time.time()
        self.creation_time = None
        self.received_time = None
        self.measurement_time = None

    def _create_header(self):
        q1 = Qubit(self.host)
        q2 = Qubit(self.host)

        if self.type == "EPR":
            #Do nothing
            pass
        elif self.type == "DATA_SC":
            q2.X()
        elif self.type == "DATA_SEQ":
            q1.X()
        return [q1, q2]

    def create_epr_frame(self):
        if not self.type == None:
            raise Exception("Quantum Frame type already defined")
        self.type = "EPR" 
        #Create header 00 -> EPR frame
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
        print("EPR FRAME CREATED")
        print("IT took: " + str( self.creation_time - self.start_time ))

    def extract_local_pairs(self):
        return self.local_qubits

    def send(self, destination):
        print("Sending quantum frame from " + self.host.host_id + " to " + destination.host_id) 
        for i, q in enumerate(self.qubit_array):
            #print("Sending "+str(i)+"/"+str(len(self.qubit_array))+": "+ str(q))
            self.host.send_qubit(destination.host_id, q, await_ack=False)

    def receive(self, source):
        print("Receiving quantum frame")
        received_qubits = []
        header = ""
        while len(header) < 2:
            q = self.host.get_data_qubit(source.host_id)
            print(q)
            if not q is None:
                m = q.measure()
                if m:
                    header = header + '1'
                else:
                    header = header + '0'
                print(len(header))

        print(header)
            
#RUN EPR GENERATION
if __name__=="__main__":
    channel = Channel(['Alice','Bob'])
    try:
        channel.node_a.wait_stop()
        channel.node_b.wait_stop()
    except KeyboardInterrupt:
        print("Keyboard Interrupt")
        channel.node_a.stop()
        channel.node_b.stop()
        sys.exit(0)

