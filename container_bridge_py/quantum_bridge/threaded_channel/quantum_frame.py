import time
from datetime import timedelta, datetime

from qunetsim.objects import Logger
from qunetsim.objects import Qubit

def simple_logger(host, log_line):
    """
    Simple Logger function to test qubits, will be removed
    """
    with open(str(host)+".log", "a") as log_file:
        log_file.write(log_line+"\n")

EPR_DICT_FOR_LOGGING = {}
SENDER_EPR_QUBIT_IDS = []
RECEIVER_EPR_QUBIT_IDS = []


class QuantumFrame:
    """
    Quantum Frame class, handles actual transmition of data encoded into
    qubits. Quantum Frame is used for sending (Data frames and EPR frames)
    and receiving such frames
    """


    def __init__(self, node, mtu=20, await_ack=False):
        """
        Inits quantum frame
        """
        self.type = None
        self.node = node
        self.host = node.host
        self.MTU = mtu
        self.raw_bits = None
        self.raw_qubits = []
        self.qubit_array = []
        self.local_qubits = []
        # Performance statistics
        self.start_time = time.time()
        self.creation_time = None
        self.deletion_time = None
        self.received_time = None
        self.measurement_time = timedelta(seconds=0)
        self.await_ack = await_ack
        self.termination_byte = "01111110"
        self.epr_consumed = 0
        self.number_of_transmissions = 0
        self.total_measurement_time = timedelta(seconds=0)

    '''
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
    '''

    def send_data_frame(self, data, destination_node, entanglement_buffer=None):
        """
        Send data frame, sequential or superdense ecnoded
        """
        print("Send data frame")
        self.creation_time = time.time()
        self.raw_bits = data
        data.append(self.termination_byte)
        if self.type is not None:
            raise Exception("Quantum Frame type already defined")

        send_sequentially = False
        if entanglement_buffer is not None:
            if entanglement_buffer.qsize() > 0:
                self.type = "DATA_SC"
                self._send_data_frame_header(destination_node.host)
                print("Sending data frame superdense")
                self._send_data_frame_sc(data, destination_node.host)
                return
            send_sequentially = True
        else:
            send_sequentially = True

        if send_sequentially:
            self.type = "DATA_SEQ"
            self._send_data_frame_header(destination_node.host)
            print("Sending data frame without entanglement enhancment")
            self._send_data_frame_seq(data, destination_node.host)


    def _send_data_frame_seq(self, data, destination):
        """
        Sends data frame sequentially to destination.

        PRIVATE METHOD: called by send_data_frame() method
        """
        q_num = 0
        timestamp = str(time.time())
        for byte in data:
            qbyte_ids = []
            for iterat, bit in enumerate(byte):
                #print(f"sending {bit}")
                q = Qubit(self.host, q_id=str(q_num)+"-"+timestamp)
                q_num = q_num + 1
                if bit == '1':
                    q.X()
                self.host.send_qubit(destination.host_id, q, await_ack=self.await_ack,
                                            no_ack=True)
                qbyte_ids.append(q.id)
        print("DONE SENDING")

    def _send_data_frame_sc(self, data, destination):
        """
        Sends data frame superdensly, automatically switches to sequential sending
        if node runs out of entanglement.

        PRIVATE METHOD: called by send_data_frame()
        """
        buffer = self.node.entanglement_buffer
        while len(data) > 0:
            if buffer.qsize() == 0:
                break
            byte = data.pop(0)
            qbyte_ids = []
            for crumb in range(0, len(byte), 2):
                crumb = ''.join(byte[crumb:crumb + 2])
                q = buffer.get(0)
                if crumb == '00':
                    q.I()
                elif crumb == '10':
                    q.Z()
                elif crumb == '01':
                    q.X()
                elif crumb == '11':
                    q.X()
                    q.Z()
                self.host.send_qubit(destination.host_id, q, await_ack=self.await_ack,
                                     no_ack=True)
                qbyte_ids.append(q.id)

        if len(data) > 0:
            self._send_data_frame_seq(data, destination)
        else:
            self.deletion_time = time.time()

    def _send_data_frame_header(self, destination):
        """
        Creates and sends data frame header

        PRIVATE METHOD: called by send_data_frame()
        """
        header = None
        if self.type == "DATA_SEQ":
            header = "10"
        if self.type == "DATA_SC":
            header = "01"
        for h in header:
            q = Qubit(self.host)
            if h == '1':
                q.X()
            self.host.send_qubit(destination.host_id, q, await_ack=self.await_ack,
                                        no_ack=True)


    def send_epr_frame(self, destination_node):
        """
        Sends EPR frame to the destination

        PUBLIC METHOD
        """
        timestamp = str(time.time())
        q_f_num = 0

        if destination_node.is_busy.is_set() or self.node.is_busy.is_set():
            return
        header = '00'
        for h in header:
            q = Qubit(self.host, q_id=str(q_f_num) + "-" + timestamp + "-EPR-HEADER" )
            q_f_num = q_f_num + 1
            simple_logger(self.node.host.host_id,
                          f"Header: {h}\n {q.id}")
            if h == '1':
                q.X()
            self.host.send_qubit(destination_node.host.host_id, q, await_ack=self.await_ack,
                                 no_ack=False)
        for x in range(self.MTU):
            for i in range(8):
                q1 = Qubit(self.host, q_id=str(q_f_num) + "-" + timestamp + "-EPR-LOCAL" )
                #q_f_num = q_f_num + 1
                q2 = Qubit(self.host, q_id=str(q_f_num) + "-" + timestamp + "-EPR-REMOTE" )
                q_f_num = q_f_num + 1
                q1.H()
                q1.cnot(q2)
                self.local_qubits.append(q1)
                self.host.send_qubit(destination_node.host.host_id, q2, await_ack=self.await_ack,
                                     no_ack=True)
                EPR_DICT_FOR_LOGGING[q1.id]=q2.id
                simple_logger(self.node.host.host_id,
                            f"-EPR \n local: {q1.id} \n remote: {q2.id}")
        SENDER_EPR_QUBIT_IDS = [x.id for x in self.local_qubits]
        for q in self.local_qubits:
            q = q.id
            simple_logger(self.node.host.host_id+"-epr",
                          f"{q} - {EPR_DICT_FOR_LOGGING[q]}")

    def extract_local_pairs(self):
        """
        Returns qubits in a frame, used for storing EPR pairs

        PUBLIC METHOD
        """
        return self.local_qubits

    def receive(self, source):
        """
        Receives quantum frame from source
        doesn't finish until the whole frame was received (termination q_byte)

        PUBLIC METHOD
        """
        header = ""
        while len(header) < 2:
            #print("Listening for next header qubit")
            q = self.host.get_data_qubit(source.host_id, wait=-1)
            if q is not None:
                m = q.measure()
                self.node.is_busy.set()
                simple_logger(self.node.host.host_id, f"Header qubit received: {q.id}")
                if m:
                    header = header + '1'
                else:
                    header = header + '0'
        print(f"HEADER: {header}")
        if header == '00':
            self._receive_epr(source)
        if header == '01':
            self.type = "DATA_SC"
            self._receive_data_sc(source)
        if header == '10':
            self.type = "DATA_SEQ"
            self._receive_data_seq(source)
        if header == '11':
            self.type = "UNDEFINED"
            print("ERROR, header:11 undefined")
        self.node.is_busy.clear()

    def _receive_data_sc(self, source):
        """
        Receives data frame in a superdense fashion
        Automatically switches to receiving sequentially

        PRIVATE METHOD: Called by receive()
        """

        buffer = self.node.entanglement_buffer
        complete = False
        data = []
        rec_qbyte_ids = []
        buf_qbyte_ids = []
        while buffer.qsize() > 0 and not complete:
            q1 = self.host.get_data_qubit(source.host_id, wait=-1)
            rec_qbyte_ids.append(q1.id)
            q2 = buffer.get()
            buf_qbyte_ids.append(q2.id)
            q1.cnot(q2)
            q1.H()
            pre_measurement_time = datetime.now()
            crumb = ""
            crumb = crumb + str(q1.measure())
            crumb = crumb + str(q2.measure())
            self.measurement_time = self.measurement_time +(datetime.now()-pre_measurement_time)

            self.epr_consumed = self.epr_consumed + 1
            self.number_of_transmissions = self.number_of_transmissions + 1

            if len(data) == 0:
                data.append(crumb)
                continue
            if len(data[-1]) < 8:
                data[-1] = data[-1] + crumb
            else:
                data.append(crumb)

            if len(data[-1])==8:
                log_list = []
                for i, rec in enumerate(rec_qbyte_ids):
                    log_list.append(" , ".join([rec, buf_qbyte_ids[i]]))
                log_list = "\n".join(log_list)

                simple_logger(self.node.host.host_id,
                              f"""RECEIVED DATA SD: {data[-1]}\nRECEIVED_Q_IDS, BUFF_IDS:\n{log_list}
                              """)
                buf_qbyte_ids = []
                rec_qbyte_ids = []

            if data[-1] == self.termination_byte:
                complete = True

        if not complete:
            self._receive_data_seq(source, data)
        else:
            self.raw_bits = data

    def _receive_data_seq(self, source, data=None):
        """
        Receives data frame sequentially
        if data parameter is given received data is appended to it
        (used for switching from superdense to sequential fashion)

        PRIVATE METHOD: called by receive() or _receive_data_sc()
        """
        if data is None:
            data = []
        complete = False
        while not complete:
            #print("Waiting for next normal qubit")
            q = self.host.get_data_qubit(source.host_id, wait=-1)
            pre_measurement_time = datetime.now()
            bit = str(q.measure())
            self.measurement_time = self.measurement_time +(datetime.now()-pre_measurement_time)
            self.number_of_transmissions = self.number_of_transmissions + 1
            if len(data) == 0:
                data.append(bit)
                continue
            if len(data[-1]) < 8:
                data[-1] = data[-1] + bit
            else:
                data.append(bit)
                continue

            if data[-1] == self.termination_byte:
                complete = True
        self.raw_bits = data

    def _receive_epr(self, source):
        """
        Receive epr qubits from source

        PRIVATE METHOD: called by receive()
        """
        self.type = 'EPR'
        for x in range(self.MTU):
            for i in range(8):
                q = self.host.get_data_qubit(source.host_id, wait=-1)
                self.epr_consumed = self.epr_consumed - 1
                self.local_qubits.append(q)
            self.raw_qubits.append('eeeeeeee')
        simple_logger(self.node.host.host_id, "---- EPR RECEIVED")
        for q in self.local_qubits:
            simple_logger(self.node.host.host_id+"-epr", str(q.id))
