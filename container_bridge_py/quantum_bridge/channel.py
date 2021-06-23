import sched
import time

from qunetsim.components import Host, Network
from qunetsim.objects import Qubit
from qunetsim.backends import ProjectQBackend
from threading import Thread, Event


class DaemonThread(Thread):
    """ A Daemon thread that runs a task until completion and then exits. """

    def __init__(self, target, args=None):
        if args is not None:
            super().__init__(target=target, daemon=True, args=args)
        else:
            super().__init__(target=target, daemon=True)
        self.start()


class Channel:
    """
    Basic channel, to force implementation of two methods
    """
    def __init__(self):
        raise NotImplementedError

    def transmit_packet(self, packet_bits: list):
        """
        Should transmit packet through channel
        """
        raise NotImplementedError


class SimpleBufferedQuantumChannel(Channel):
    """
    Simple buffered quantum link
    has two hosts direction of transmission is not important
    """

    def __init__(self, buffer_size=1000, epr_gen_time=5, epr_frame_length=48):
        """
        Inits Simple Buffered Quantum Channel
        """
        super().__init__()
        self.buffer_size = buffer_size
        self.buffer = []
        self.epr_gen_int = epr_gen_time
        self.epr_frame_length = epr_frame_length
        backend = ProjectQBackend()
        self.network = Network.get_instance()
        self.network.start(backend=backend)
        self.host = Host('A', backend)
        self.host.start()
        self.network.add_host(self.host)
        self.is_free = Event()
        self.is_free.set()
        self.epr_gen_schedule = None

    def entanglement_generation(self):
        """
        Generates entanglement
        """
        self.epr_gen_schedule = sched.scheduler(time.time, time.sleep)
        self.epr_gen_schedule.enter(self.epr_gen_int, 1, self._entanglement_generation_thread)
        self.epr_gen_schedule.run(blocking=True)

    def _entanglement_generation_thread(self):
        """
        Thread that generates epr periodically
        """
        if not self.is_free.is_set():
            print("Waiting for is_free flag")
        self.is_free.wait()
        self.is_free.clear()
        t = DaemonThread(self._entanglement_generation)
        t.join()
        self.is_free.set()
        self.epr_gen_schedule.enter(self.epr_gen_int, 1, self._entanglement_generation_thread)

    def _entanglement_generation(self):
        """
        Method that handles epr generation

        PRIVATE METHOD
        """
        print("--------EPR GENERATION--------")
        start = time.time()
        for i in range(self.epr_frame_length):
            if not len(self.buffer) >= self.buffer_size:
                self.buffer.append(self._generate_epr_tuple())
            else:
                break
        print("EPR GENERATION TIME: ", time.time() - start)
        print("EPR BUFFER: ", str(len(self.buffer)) + "/" + str(self.buffer_size))

    def _generate_epr_tuple(self):
        """
        Generate epr tuple

        PRIVATE METHOD
        """
        q1 = Qubit(self.host)
        q2 = Qubit(self.host)
        q1.H()
        q1.cnot(q2)
        return (q1, q2)

    def transmit_packet(self, packet_bits: list):
        """
        Handles data frame transmission

        PUBLIC METHOD
        """
        if not self.is_free.is_set():
            print("Waiting for is_free flag")
        self.is_free.wait()
        self.is_free.clear()
        bit_num = sum([len(i) for i in packet_bits])
        print(bit_num, len(self.buffer))
        if bit_num <= len(self.buffer):
            print("Superdense transmitting")
            new_packet_bits = self._transmit_packet_dens(packet_bits)
        else:
            print("Sequential transmitting")
            new_packet_bits = self._transmit_packet_seq(packet_bits)
        print("Packet transmitted")
        self.is_free.set()
        return new_packet_bits

    def _transmit_packet_dens(self, packet_bits: list):
        """
        Handles transmission of packet supredensly
        PRIVATE METHOD
        """
        received_packet = []
        for byte in packet_bits:
            print(byte)
            received_packet.append(self._transmit_byte_dens(byte))
        return received_packet

    def _transmit_byte_dens(self, byte):
        """
        Handles transmissoin od byte superdensly
        PRIVATE METHOD
        """
        received_byte = ""
        for i in range(len(byte), 2):
            print(byte[i:i + 1])
            received_byte = received_byte + self._transmit_crumb_dens(byte[i:i + 1])
        return received_byte

    def _transmit_crumb_dens(self, crumb):
        """
        Handles transmission of crumb
        PRIVATE METHOD
        """
        epr = self.buffer.pop(0)
        self._dens_encode(crumb, epr[0])
        self._transmit_qubit(epr[0])
        return self._dens_decode(epr)

    # Errors due to transmission
    def _transmit_qubit(self, qubit):
        pass

    @staticmethod
    def _dens_encode(crumbs, q):
        """
        Handles superdense encoding
        PRIVATE METHOD
        """
        if crumbs == '00':
            q.I()
        elif crumbs == '10':
            q.Z()
        elif crumbs == '01':
            q.X()
        elif crumbs == '11':
            q.X()
            q.Z()

    @staticmethod
    def _dens_decode(qubits):
        """
        Handles supredense decoding
        PRIVATE METHOD
        """
        qubits[0].cnot(qubits[1])
        qubits[0].H()
        meas = [None, None]
        meas[0] = qubits[0].measure()
        meas[1] = qubits[1].measure()
        print(meas)
        return str(meas[0]) + str(meas[1])

    def _transmit_packet_seq(self, packet_bits: list):
        """
        Handles transmission of packet in a sequential manner

        PRIVATE METHOD
        """
        received_packet = []
        print(packet_bits)
        for byte in packet_bits:
            received_byte = ""
            print(byte)
            for bit in byte:
                qubit = Qubit(self.host)
                if bit == '1':
                    qubit.X()
                self._transmit_qubit(qubit)
                received_byte = received_byte + bit
                qubit.measure()
                received_byte = received_byte + str(qubit.measure())
                print(received_byte)
            received_packet.append(received_byte)
        return received_packet


class SimpleQuantumChannel:
    """
    Simple Quantum Channel
    Just encodes bits in qubits and measures them
    """
    def __init__(self):
        """Init method"""
        backend = ProjectQBackend()
        self.network = Network.get_instance()
        self.nodes = ["A", "B"]
        self.network.start(backend=backend)
        self.hosts = []
        self.hosts.append(Host('A', backend))
        self.hosts.append(Host('B', backend))
        self.hosts[0].start()
        self.hosts[1].start()
        self.hosts[0].add_connection(self.hosts[1].host_id)
        self.hosts[1].add_connection(self.hosts[0].host_id)
        self.network.add_host(self.hosts[0])
        self.network.add_host(self.hosts[1])

    def transmit_packet(self, packet_bits):
        """
        Handles transmission of a packet
        PUBLIC METHOD
        """
        received_packet = []
        for byte in packet_bits:
            received_packet.append(self._transmit_byte(byte))
        return received_packet

    def _transmit_byte(self, byte):
        """
        Handles transmission of single byte
        PRIVATE METHOD
        """
        received_byte = ""
        q_byte = []
        for bit in byte:
            q = Qubit(self.hosts[0])
            if bit == '1':
                q.X()
            q_byte.append(q)
            q_id = self.hosts[0].send_qubit('B', q, await_ack=False)
            q_byte.append(q_id)
            print(str(len(received_byte)) + "/" + str(len(byte)))

        for q_id in q_byte:
            q_rec = self.hosts[1].get_data_qubit('A', q_id)
            print(q_id)
            while q_rec is None:
                q_rec = self.hosts[1].get_data_qubit('A', q_id)
            received_byte = received_byte + str(q_rec.measure())
        return received_byte

    def _transmit_bit(self, bit):
        """
        Transmits single bit

        PRIVATE METHOD
        """
        q = Qubit(self.hosts[0])
        if bit == '1':
            q.X()
        q_id = self.hosts[0].send_qubit('B', q, await_ack=False)
        q_rec = self.hosts[1].get_data_qubit('A', q_id, wait=2)
        while q_rec == None:
            print("Receiving")
            q_rec = self.hosts[1].get_data_qubit('A', q_id, wait=2)
        return str(q_rec.measure())
