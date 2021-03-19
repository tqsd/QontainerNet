import time

from qunetsim.objects import Logger
from qunetsim.objects import Qubit

def simple_logger(host, log_line):
    """Simple Logger function to test qubits"""
    with open(str(host)+".log", "a") as log_file:
        log_file.write(log_line+"\n")

EPR_DICT_FOR_LOGGING = {}
SENDER_EPR_QUBIT_IDS = []
RECEIVER_EPR_QUBIT_IDS = []

class QuantumFrame:
    """
    Quantum Frame class, handles actual transmition
    """
    epr_dict = {}

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
        self.deletion_time = None
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

    def send_data_frame(self, data, destination_node, entanglement_buffer=None):
        """Send data frame, sequential or superdense ecnoded"""
        self.creation_time = time.time()
        print("Sending data frame")
        self.raw_bits = data
        data.append(self.termination_byte)
        print(f"{self.node.host.host_id} is sending packet of lenght {len(data)}")
        if self.type is not None:
            raise Exception("Quantum Frame type already defined")

        send_sequentially = False
        print(entanglement_buffer, entanglement_buffer.qsize())
        if entanglement_buffer is not None:
            if entanglement_buffer.qsize() > 0:
                print("Sending superdense encoded")
                self.type = "DATA_SC"
                self._send_data_frame_header(destination_node.host)
                self._send_data_frame_sc(data, destination_node.host)
                return
            else:
                send_sequentially = True
        else:
            send_sequentially = True

        if send_sequentially:
            print("Sending sequentially")
            self.type = "DATA_SEQ"
            self._send_data_frame_header(destination_node.host)
            self._send_data_frame_seq(data, destination_node.host)

    def _send_data_frame_seq(self, data, destination):

        q_num = 0
        timestamp = str(time.time())
        for byte in data:
            qbyte_ids = []
            for iterat, bit in enumerate(byte):
                print(iterat)
                q = Qubit(self.host, q_id=str(q_num)+"-"+timestamp)
                q_num = q_num + 1
                if bit == '1':
                    q.X()
                self.host.send_qubit(destination.host_id, q, await_ack=self.await_ack,
                                            no_ack=True)
                qbyte_ids.append(q.id)

            print(f"{self.node.host.host_id} has sent {byte} sequentially")
            print(qbyte_ids)

    def _send_data_frame_sc(self, data, destination):
        buffer = self.node.entanglement_buffer
        # print(len(buffer))
        while len(data) > 0:
            if buffer.qsize() == 0:
                print("SENDING: No more local pairs available")
                break
            byte = data.pop(0)
            qbyte_ids = []
            for crumb in range(0, len(byte), 2):
                crumb = ''.join(byte[crumb:crumb + 2])
                print("Getting qubit from buffer")
                q = buffer.get(0)
                print(f"{q.id} recovered from buffer")
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
                print(f"{self.node.host.host_id}: SENDING DONE")
                qbyte_ids.append(q.id)
            print(f" {self.node.host.host_id}: AM I FINISHED with {byte}")
            print(f"{self.node.host.host_id}: {qbyte_ids}")
            #try:
            #    remote_q_ids = [EPR_DICT_FOR_LOGGING[x] for x in qbyte_ids]
            #except Exception as e:
            #    print(e)
            #finally:
            #    print("NO ERROR")
            print(f"{self.node.host.host_id}: Is adding something to some list")
            #log_list = []
            #for i, remote in enumerate(remote_q_ids):
            #    log_list.append(" , ".join([qbyte_ids[i], remote]))

            print(f"{self.node.host.host_id}: Is adding something to some list again")
            #log_list = "\n".join(log_list) + "-remote"


            #simple_logger(self.node.host.host_id,f"""SENT DATA SD: {byte}\n SENT_Q_IDS, REMOTE_Q_IDS: \n {log_list}""")
            print(f"{self.node.host.host_id} is sending {byte} super-dense")
            print(qbyte_ids)

        if len(data) > 0:
            print(f"{self.node.host.host_id} Continuing with sequential sending")
            print(data)
            self._send_data_frame_seq(data, destination)
        else:
            self.deletion_time = time.time()
            print("FRAME PROCESSING TIME:" + str(self.deletion_time-self.creation_time))

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
            print(f"HEADER SENDING: {h} with id {q.id}")
            self.host.send_qubit(destination.host_id, q, await_ack=self.await_ack,
                                        no_ack=True)

        print("Header sent")

    def send_epr_frame(self, destination_node):
        timestamp = str(time.time())
        q_f_num = 0
        
        if destination_node.is_busy.is_set() or self.node.is_busy.is_set():
            print(f"{self.node.host.host_id} is trying to transmit: Destination node is busy")
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
            #print("Sending " + str(x) + "/" + str(self.MTU) + " bytes")
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
                #print(q1.id, q2.id)
                EPR_DICT_FOR_LOGGING[q1.id]=q2.id
                simple_logger(self.node.host.host_id,
                            f"-EPR \n local: {q1.id} \n remote: {q2.id}")
        SENDER_EPR_QUBIT_IDS = [x.id for x in self.local_qubits]
        for q in self.local_qubits:
            q = q.id
            simple_logger(self.node.host.host_id+"-epr",
                          f"{q} - {EPR_DICT_FOR_LOGGING[q]}")

    def extract_local_pairs(self):
        return self.local_qubits

    def receive(self, source):
        print("Listening for quantum frame")
        header = ""
        while len(header) < 2:
            q = self.host.get_data_qubit(source.host_id, wait=-1)
            if q is not None:
                m = q.measure()
                print(f"HEADER RECEIVING {m} wiht id {q.id}")
                self.node.is_busy.set()
                simple_logger(self.node.host.host_id, f"Header qubit received: {q.id}")
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
        if header == '11':
            self.type = "UNDEFINED"
            print("ERROR, header:11 undefined")
        print(f"{self.node.host.host_id} received a packet of type {self.type}")
        self.node.is_busy.clear()

    def _receive_data_sc(self, source):
        print("Receiving data frame superdense encoded")
        #buffer = self.node.acquire_buffer()
        buffer = self.node.entanglement_buffer
        print(buffer.qsize())
        complete = False
        data = []
        rec_qbyte_ids = []
        buf_qbyte_ids = []
        while buffer.qsize() > 0 and not complete:
            print(f"{self.node.host.host_id} is receiving next superdense qubit")
            q1 = self.host.get_data_qubit(source.host_id, wait=-1)

            rec_qbyte_ids.append(q1.id)
            print(f"{self.node.host.host_id} received a qubit")
            q2 = buffer.get()
            print(f"{self.node.host.host_id} got a qubit from local queue")
            buf_qbyte_ids.append(q2.id)
            q1.cnot(q2)
            q1.H()
            crumb = ""
            crumb = crumb + str(q1.measure())
            crumb = crumb + str(q2.measure())
            if len(data) == 0:
                data.append(crumb)
                continue
            elif len(data[-1]) < 8:
                data[-1] = data[-1] + crumb
            else:
                data.append(crumb)

            if len(data[-1])==8:
                print(f"""{self.node.host.host_id} has received {data[-1]}
                superdense, current packet lenght: {len(data)}""")

                #rec_qbyte_ids = "\n".join(rec_qbyte_ids)
                #buf_qbyte_ids = "\n".join(buf_qbyte_ids)

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
        if data is None:
            data = []
        print("Receiving data frame sequentially")
        complete = False
        while not complete:
            q = self.host.get_data_qubit(source.host_id, wait=-1)
            print(q.id)
            bit = str(q.measure())
            if len(data) == 0:
                data.append(bit)
                continue
            elif len(data[-1]) < 8:
                data[-1] = data[-1] + bit
            else:
                print(data[-1], len(data))
                data.append(bit)
                continue

            if data[-1] == self.termination_byte:
                complete = True
        self.raw_bits = data

    def _receive_epr(self, source):
        self.type = 'EPR'
        for x in range(self.MTU):
            #print("Receiving " + str(x + 1) + "/" + str(self.MTU) + "bytes")
            for i in range(8):
                q = self.host.get_data_qubit(source.host_id, wait=-1)
                self.local_qubits.append(q)
        simple_logger(self.node.host.host_id, "---- EPR RECEIVED")
        for q in self.local_qubits:
            simple_logger(self.node.host.host_id+"-epr", str(q.id))
        RECEIVER_EPR_QUBIT_IDS = [x.id for x in self.local_qubits]
        order_flag = True
        for i, s_id in enumerate(SENDER_EPR_QUBIT_IDS):
            if RECEIVER_EPR_QUBIT_IDS[i] != EPR_DICT_FOR_LOGGING[s_id]:
                order_flag = False
        if order_flag:
            print("No errors in epr transmission -> order is ok")
        else:
            print("Errors in epr transmission -> order is not ok")
