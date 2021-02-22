from qunetsim.components import Host, Network
from qunetsim.objects import Qubit
from qunetsim.backends import ProjectQBackend
from threading import Thread, Event, Timer
import sys

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
        self.node_a.start()
        self.node_b.start()


    def transmit_packet(self, packet_bits:list, source_host):
        pass

class Node:
    def __init__(self, host:str, network, backend, queue_size=512, is_epr_initiator=False, frame_size=48, epr_transmission_time=1):
        self.host = Host(host, backend)
        self.host.start()
        self.network = network
        self.network.add_host(self.host)
        self.queue = []
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
        #if is_epr_initiator:
        #    self.epr_trigger.set()

    def connect(self, node):
        ''' Only one connection needs to be made '''
        print("Connecting hosts")
        self.host.add_connection(node.host.host_id)
        node.host.add_connection(self.host.host_id)
        self.peer = node
        node.peer = self


    def start(self):
        if self.is_epr_initiator:
            self.timer_thread = Timer(self.epr_transmission_time, self.epr_timer)
            self.timer_thread.start()
        self.received_thread = DaemonThread(self.receiver_protocol)
        self.sender_thread= DaemonThread(self.sender_protocol)
        print(self.host.host_id + " protocols initiated")

    def stop(self):
        print("Sending stop signal")
        self.stop_signal.set()
        self.received_thread.join()
        self.sender_thread.join()
    
    def wait_stop(self):
        self.received_thread.join()
        self.sender_thread.join()

    def runUntilFinished(self):
        self.received_thread.join()
        self.sender_thread.join()

    def epr_timer(self):
        if self.stop_signal.is_set():
            return
        print("EPR")
        self.epr_trigger.set()
        self.epr_lock.wait()
        self.epr_trigger.clear()
        self.epr_lock.clear()
        self.timer_thread = Timer(self.epr_transmission_timer, self.epr_timer)
        self.timer_thread.start()


    def receiver_protocol(self):
        print(self.host.host_id + " receiver protocol started")
        try:
            while True:
                if self.stop_signal.is_set():
                    return
                q = self.host.get_data_qubit(self.peer.host.host_id)
                if q == None:
                    continue
                m = q.measure()
                if m == 0:
                    self.receive_epr_frame()
                if m == 1:
                    self.receive_data_frame()
        except Exception as e:
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
        pass

    def transmit_epr_frame(self):
        print("Transmitting epr frame")
        q = Qubit(self.host)
        self.host.send_qubit(self.peer.host.host_id, q, await_ack=True)
        for i in range(self.frame_size):
            q1 = Qubit(self.host)
            q2 = Qubit(self.host)
            q1.cnot(q2)
            q1.H()
            self.queue.append(q1)
            self.host.send_qubit(self.peer.host.host_id, q, await_ack=False)
             


    def receive_data_frame(self):
        pass

    def transmit_packet(self):
        q = Qubit(self.host)
        q.X()
        self.host.send_qubit(self.peer.host.host_id, q, await_ack=True)

#RUN EPR GENERATION
if __name__=="__main__":
    channel = Channel(['a','b'])
    try:
        channel.node_a.wait_stop()
        channel.node_b.wait_stop()
    except KeyboardInterrupt:
        print("Keyboard Interrupt")
        channel.node_a.stop()
        channel.node_b.stop()
        sys.exit(0)

