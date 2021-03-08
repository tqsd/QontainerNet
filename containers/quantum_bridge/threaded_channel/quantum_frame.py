import time

from qunetsim.objects import Logger
from qunetsim.objects import Qubit


class QuantumFrame:
    def __init__(self, node, mtu=80, await_ack=False):
        # MTU is in bytes
        self.type = None
        self.node = node
        self.host = node.host
        self.MTU = mtu
        self.raw_bits = None
        self.qubit_array = []
        self.local_qubits = []
        # Performance statistics
        self.start_time = time.time()
        self.creation_time = None
        self.received_time = None
        self.measurement_time = None
        self.await_ack = await_ack
        self.termination_byte = "01111110"

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

    def send_data_frame(self, data, destination_node, entanglement_buffer=[]):
        """Send data frame, sequential or superdense ecnoded"""
        print("Sending data frame")
        self.raw_bits = data
        data.append(self.termination_byte)
        if self.type is not None:
            raise Exception("Quantum Frame type already defined")

        if len(entanglement_buffer) == 0:
            print("Sending sequentially")
            self.type = "DATA_SEQ"
            self._send_data_frame_header(destination_node.host)
            self._send_data_frame_seq(data, destination_node.host)
        else:
            print("Sending superdense encoded")
            self.type = "DATA_SC"
            self._send_data_frame_header(destination_node.host)
            self._send_data_frame_sc(data, destination_node.host)
        print("Data frame transmitted")

    def _send_data_frame_seq(self, data, destination):
        for byte in data:
            for bit in byte:
                q = Qubit(self.host)
                if bit == '1':
                    q.X()
                q_id = self.host.send_qubit(destination.host_id, q, await_ack=self.await_ack,
                                            no_ack=True)

    def _send_data_frame_sc(self, data, destination):
        buffer = self.node.acquire_buffer()
        # print(len(buffer))
        while len(data) > 0:
            if len(buffer) < 8:
                print("SENDING: No more local pairs available")
                break
            byte = data.pop(0)
            for crumb in range(0, len(byte), 2):
                crumb = ''.join(byte[crumb:crumb + 2])
                q = buffer.pop(0)
                # print("sending crumb " + crumb)
                if crumb == '00':
                    q.I()
                elif crumb == '10':
                    q.Z()
                elif crumb == '01':
                    q.X()
                elif crumb == '11':
                    q.X()
                    q.Z()
                q_id = self.host.send_qubit(destination.host_id, q, await_ack=self.await_ack,
                                            no_ack=True)
        if len(data) > 0:
            print("Continuing with sequential sending")
            print(data)
            self._send_data_frame_seq(data, destination)
        self.node.release_buffer(buffer)

    def _send_data_frame_header(self, destination):
        print("Sending header")
        header = None
        if self.type == "DATA_SEQ":
            header = "10"
        if self.type == "DATA_SC":
            header = "01"
        for h in header:
            q = Qubit(self.host)
            if h == '1':
                q.X()
            q_id = self.host.send_qubit(destination.host_id, q, await_ack=self.await_ack,
                                        no_ack=True)

        print("Header sent")

    def send_epr_frame(self, destination_node):
        if destination_node.is_busy.is_set():
            print("Destination node is busy")
            return
        header = '00'
        for h in header:
            q = Qubit(self.host)
            if h == '1':
                q.X()
            self.host.send_qubit(destination_node.host.host_id, q, await_ack=self.await_ack,
                                 no_ack=True)
        for x in range(self.MTU):
            print("Sending " + str(x) + "/" + str(self.MTU) + " bytes")
            for i in range(8):
                q1 = Qubit(self.host)
                q2 = Qubit(self.host)
                q1.H()
                q1.cnot(q2)
                self.local_qubits.append(q1)
                self.host.send_qubit(destination_node.host.host_id, q2, await_ack=self.await_ack,
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
                self.node.is_busy.set()
                if m:
                    header = header + '1'
                else:
                    header = header + '0'
        print("Header received: " + header)
        if header == '00':
            self._receive_epr(source)
        if header == '01':
            self.type = "DATA_SC"
            self._receive_data_sc(source)
        if header == '10':
            self.type = "DATA_SEQ"
            self._receive_data_seq(source)
        self.node.is_busy.clear()

    def _receive_data_sc(self, source):
        print("Receiving data frame superdense encoded")
        buffer = self.node.acquire_buffer()
        print(len(buffer))
        complete = False
        data = []
        while len(buffer) > 7 and not complete:
            q1 = self.host.get_data_qubit(source.host_id)
            if q1 is None:
                continue
            q2 = buffer.pop(0)
            q1.cnot(q2)
            q1.H()
            crumb = ""
            crumb = crumb + str(q1.measure())
            crumb = crumb + str(q2.measure())
            # print("received " + crumb)
            if len(data) == 0:
                data.append(crumb)
                continue
            elif len(data[-1]) < 8:
                data[-1] = data[-1] + crumb
            else:
                print(data[-1])
                data.append(crumb)
                continue

            if data[-1] == self.termination_byte:
                complete = True
        self.node.release_buffer(buffer)

        if not complete:
            self._receive_data_seq(source, data)
        else:
            self.raw_bits = data

    def _receive_data_seq(self, source, data=[]):
        print("Receiving data frame sequentially")
        complete = False
        while not complete:
            q = self.host.get_data_qubit(source.host_id)
            if q is None:
                continue
            bit = str(q.measure())
            if len(data) == 0:
                data.append(bit)
                continue
            elif len(data[-1]) < 8:
                data[-1] = data[-1] + bit
            else:
                data.append(bit)
                print(data)
                continue

            if data[-1] == self.termination_byte:
                complete = True
        self.raw_bits = data

    def _receive_epr(self, source):
        self.type = 'EPR'
        for x in range(self.MTU):
            print("Receiving " + str(x + 1) + " byte of " + str(self.MTU))
            for i in range(8):
                q = self.host.get_data_qubit(source.host_id)
                while q is None:
                    q = self.host.get_data_qubit(source.host_id)
                self.local_qubits.append(q)
        Logger.get_instance().log(str(self.host.host_id) + "received EPR frame")
