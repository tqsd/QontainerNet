import random
import time
import math
import threading

from qunetsim.components import Host, Network
from qunetsim.backends import ProjectQBackend
#from qunetsim.objects import Logger, Qubit
#from messages import messages
Logger.DISABLED = True
# Time Multiplex
DISCRETE_TIME_STEP = 0.1
PROB = 0.98
EPR_FRAME_LENGTH = 48
DATA_FRAME_LENGTH = 96

# Threading variables
packet_in_buffer = threading.Event()
packet_in_channel = threading.Event()
packet = None
received_packet = None

def transmit_packet(packet):
    packet = packet
    packet_in_buffer.set()

    print("Waiting for packet to come through")
    packet_in_channel.wait()
    return received_packet
    



def string_to_binary(st):
    binary_chars = ''.join("0" + format(ord(i), 'b') for i in st)
    if len(binary_chars) != 96:
        raise Exception("binary string of length ",len(binary_chars), " detected. String reads as", st)
    return binary_chars

def binary_to_string(st):
    return ''.join(chr(int(''.join(x), 2)) for x in zip(*[iter(st)] * 8))

def dens_encode(q: Qubit, bits: str):
    # assumption: qubit q is entangled with another qubit q' which resides at receiver
    # bits is a two-bit string
    # think of dense_encode as an optical device at the sender side, where each qubit has to pass through the optical device
    # I, X, Y, Z are another way of writing the Pauli matrices
    if bits == '00':
        q.I()
    elif bits == '10':
        q.Z()
    elif bits == '01':
        q.X()
    elif bits == '11':
        q.X()
        q.Z()
    else:
        raise Exception('Bad input')
    return q


def dense_decode(stored_epr_half: Qubit, received_qubit: Qubit):
    received_qubit.cnot(stored_epr_half)
    received_qubit.H()
    meas = [None, None]
    meas[0] = received_qubit.measure()
    meas[1] = stored_epr_half.measure()
    return str(meas[0]) + str(meas[1])


def encode(q: Qubit, bit: str):
    if bit == "0":
        q.I()
    elif bit == "1":
        q.X()
    else:
        raise Exception("Bad input")
    return q

def decode( q: Qubit):
    meas = None
    meas = q.measure()
    return str(meas)

def parse_message_dense(bits: str):
    # check whether string is of even length ... omitted here
    out = []
    for i in range(int(len(bits)/2)):
        out.append(bits[ 2*i : 2*i+2 ])
    return out

def parse_message(bits: str):
    # check whether string is of even length ... omitted here
    out = []
    for i in range(int(len(bits))):
        out.append(bits[ i : i + 1 ])
    return out

def transmit_bit_frame(bit_frame:str, sender_host, receiver_host_id):
    # the sender needs to check whether it has enough entanglement shared with the receiver to handle the entire frame using dense coding
    eb = len(sender_host.get_epr_pairs(receiver_host_id))
    #print("entanglement buffer has",eb,"EPR pairs")
    # we need a header to inform the receiver what's coming - qubits for data transmission or qubits to be stored into entanglement buffer
    number_of_transmitted_qubits = 0
    headerQubit = Qubit(sender_host)
    #print("SENDER: generated headerQubit with id",headerQubit._id)
    sender_host.send_qubit( receiver_host_id, headerQubit)
    #print("header was sent")
    time.sleep(DISCRETE_TIME_STEP)
    number_of_transmitted_qubits += 1
    protocol_type = 0
    if eb > len(bit_frame)/2:
        protocol_type = 1
        msgs = parse_message_dense(bit_frame)
        for i in range(len(msgs)):
            q = sender_host.get_epr(receiver_host_id)
            # here we apply the envisioned optical device to the 2-bit piece of the message
            qout = dens_encode( q, str(msgs[i]) )
            sender_host.send_qubit( receiver_host_id, qout )
            number_of_transmitted_qubits += 1
            time.sleep(DISCRETE_TIME_STEP)
    else:
        protocol_type = 2
        msgs = parse_message(bit_frame)
        for i in range(len(msgs)):
            q = Qubit(sender_host)
            # here we apply the envisioned optical device to the 2-bit piece of the message
            qout = encode( q, str(msgs[i]) )
            sender_host.send_qubit( receiver_host_id, qout )
            number_of_transmitted_qubits += 1
            time.sleep(DISCRETE_TIME_STEP)
    print("SENDER: transmitted data frame with",number_of_transmitted_qubits,"qubits")
    return protocol_type

def transmit_epr_frame(sender_host, receiver_host_id):
    # count the total number of transmitted qubits for logging purpose
    number_of_transmitted_qubits = 0
    # we need a header to inform the receiver what's coming - qubits for data transmission or qubits to be stored into entanglement buffer
    headerQubit = Qubit(sender_host)
    # put header qubit into state "e_1"
    headerQubit.X()
    sender_host.send_qubit( receiver_host_id, headerQubit )
    time.sleep(DISCRETE_TIME_STEP)

    for i in range(EPR_FRAME_LENGTH):
        # generate two qubits
        q_sender = Qubit(sender_host)
        q_receiver = Qubit(sender_host)
        # entangle both qubits so that they are in EPR state
        q_sender.H()
        q_sender.cnot(q_receiver)
        # now store one half of the entangled state at the sender
        sender_host.add_epr(receiver_host_id,q_sender)
        # send the other half to the receicer
        sender_host.send_qubit( receiver_host_id, q_receiver )
        number_of_transmitted_qubits += 1
        time.sleep(DISCRETE_TIME_STEP)
        #print("sharing ",i," epr pairs now!")
    # now sender has transmitted an entire EPR frame to the receiver
    print("SENDER: transmitted EPR frame with",number_of_transmitted_qubits,"qubits")
    return 0

def pause():
    duration = 0
    while True:
        incoming = random.random()
        if incoming < PROB:
            duration += DISCRETE_TIME_STEP
        else:
            break
    return duration

def protocol_sender(host: Host, receiver: str):
    current_index = 0
    while True:
    #while current_index < len(messages):
        # don't ever set PROB to 1 ...
        #print(current_index)
        current_pause = pause()
        print("SENDER: time until next message is",current_pause)
        if current_pause > EPR_FRAME_LENGTH * DISCRETE_TIME_STEP:
            # generate entanglement if pause is long enough
            # assuming here the sender knows the duration of the pause in advance!
            #no_frames = math.ceil( ( current_pause - EPR_FRAME_LENGTH )/( EPR_FRAME_LENGTH + 1 ) ) - 1
            print("SENDER: transmit 1 EPR frame")
            #for i in range(no_frames):
            #    transmit_epr_frame(host, receiver)
            # wait the remaining discrete time steps until the end of the pause
            done = transmit_epr_frame(host, receiver)
            #time.sleep(current_pause - EPR_FRAME_LENGTH)
            #time.sleep( ( current_pause - no_frames * (EPR_FRAME_LENGTH - 1 ) ) * DISCRETE_TIME_STEP )
        if packet_in_buffer.isSet():
            # have to transmit right away
            print("SENDER: sending data")
            #string_to_send = messages[current_index]
            string to send = "".join(packet)
            binary_string = string_to_binary(string_to_send)
            protocol_type = transmit_bit_frame(binary_string, host, receiver)
            print("SENDER: message with index",current_index, "was transmited")
            current_index += 1
            packet_in_buffer.clear()
    print("SENDER: finished")

def protocol_receiver(host: Host, sender: str):
    current_index = 0
    dense_counter = 0
    data_frame_counter = 0
    epr_frame_counter = 0
    received_messages = []
    while data_frame_counter < len(messages):
    #while True:
        number_of_received_qubits = 0
        q = host.get_data_qubit(sender, wait = 10)
        #If nothing was received try again
        if q == None:
            continue
        number_of_received_qubits += 1
        #print("RECEIVER: got header qubit with id",q._id)
        bitstring = ""
        switch = None
        switch = q.measure()
        #print("RECEIVER: switch received command", switch)
        if switch == 0:
            data_frame_counter += 1
            # here the sender intends to transmit data
            # receiver has to check its EPR buffer to decide how to decode
            epr_buffer = host.get_epr_pairs(sender)
            if len(epr_buffer) > math.ceil(DATA_FRAME_LENGTH/2) -1:
                # here we have enough stored EPR halfes, so we decode using dense coding
                print("RECEIVER: ", len(epr_buffer),"stored EPR halfes, using dense decoder")
                counter = 0
                while counter < math.ceil(DATA_FRAME_LENGTH/2):
                    stored_half = host.get_epr(sender)
                    arriving_half = host.get_data_qubit(sender, wait = 10)
                    if arriving_half == None:
                        arriving_half = host.get_data_qubit(sender, wait = 10)

                    number_of_received_qubits += 1
                    decoded_bits = dense_decode(arriving_half, stored_half)
                    bitstring += decoded_bits
                    counter += 1
                dense_counter += 1
            else:
                # here we decode one bit per qubit
                print("RECEIVER: ", len(epr_buffer),"stored epr halfes, using ordinary decoder")
                counter = 0
                while counter < DATA_FRAME_LENGTH:
                    arriving_qubit = host.get_data_qubit(sender, wait = 10)
                    number_of_received_qubits += 1
                    decoded_bit = decode(arriving_qubit)
                    bitstring += decoded_bit
                    counter += 1
            #print("RECEIVER: received",number_of_received_qubits,"qubits")
            print("RECEIVER: length of received bit string is",len(bitstring))
            print("RECEIVER:", binary_to_string(bitstring))
            received_messages.append(binary_to_string(bitstring))
        elif switch == 1:
            # here we store all incoming qubits as EPR halfes
            print("RECEIVER: receiving frame for EPR buffer")
            epr_frame_counter += 1
            counter = 0
            while counter < EPR_FRAME_LENGTH:
                arriving_half = host.get_data_qubit(sender, wait = 10)
                host.add_epr( sender, arriving_half)
                counter += 1
            print("RECEIVER: stored EPR frame")
        else:
            print(switch)
            raise Exception("receiver was not able to decode header")
        current_index += 1
    print("RECEIVER received ",data_frame_counter," data frames, out of which ",dense_counter," frames were transmitted using dense coding. In addition, ",epr_frame_counter,"epr frames were received.")
    print("RECEIVER received the following messages:",received_messages)
    # expected stats:
    # @ PROB = 0.99 : data_frames: 47, dense_frames  45,  epr_frames: 55
    # @ PROB = 0.98 : data_frames: 47, dense_frames  16,  epr_frames: 16
    # @ PROB = 0.95 : data_frames: 47, dense_frames: 1, epr_frames: 2
    # @ PROB = 0.9 : data_frames: 47, dende_frames: 0, epr_frames: 0
    # @ PROB = 0.8 : data_frames: 47, dende_frames: 0, epr_frames: 0

def main():
    for i in range(len(messages)):
        #print(len(messages[i]))
        if len(string_to_binary(messages[i])) != 96:
            print(i)
    #print(pause())
    #print(messages[0])
    #bits = string_to_binary(messages[0])
    #print(parse_message(bits))
    #print(len(parse_message_dense(bits)))
    network = Network.get_instance()
    network.start()

    host_A = Host('A')
    host_A.add_connection('B')
    host_A.start()
    host_B = Host('B')
    host_B.add_connection('A')
    host_B.start()

    network.add_hosts([host_A, host_B])

    t1 = host_A.run_protocol(protocol_sender, (host_B.host_id,))
    t2 = host_B.run_protocol(protocol_receiver, (host_A.host_id,))
    t1.join()
    t2.join()
    network.stop(True)

if __name__ == '__main__':
    main()
