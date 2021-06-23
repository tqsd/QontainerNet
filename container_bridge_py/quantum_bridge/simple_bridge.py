from threading import Timer
import time

class SimpleChannel():
    def __init__(self, entantlement_frame_length=80*8, epr_generation_time=5, epr_buffer_size=50000):
        self.entanglement_pairs = 0
        self.super_dense_time = 1
        self.sequential_time = 1
        self.int_to_sec = 0.001
        self.epr_generation_time = epr_generation_time
        self.timer_thread = Timer(epr_generation_time, self.create_entanglement)
        self.timer_thread.start()
        self.epr_buffer_size = epr_buffer_size

    def create_entanglement(self, entanglement_pairs=80*8):
        self.entanglement_pairs = self.entanglement_pairs + entanglement_pairs
        if self.entanglement_pairs > self.epr_buffer_size:
            self.entanglement_pairs = self.epr_buffer_size
        print(f"Available pairs: {self.entanglement_pairs}")
        self.timer_thread = Timer(self.epr_generation_time, self.create_entanglement)
        self.timer_thread.start()

    def transmit_packet(self, packet, address):
        #Wait time for headers
        print(f"from {address}")
        wait_time = 2*self.sequential_time
        packet_bit_length = len(packet)*8+8
        cost = 0
        if self.entanglement_pairs > packet_bit_length:
            print("SUPERDENSE")
            #Superdense
            wait_time = wait_time + (packet_bit_length/2)*self.super_dense_time  
            self.entanglement_pairs = self.entanglement_pairs - packet_bit_length
            cost = packet_bit_length
        elif self.entanglement_pairs == 0:
            print("SEQUENTIAL")
            #Fully sequential
            wait_time = wait_time + (packet_bit_length)*self.sequential_time  
            cost = 0
        else:
            #Superdense and Sequential
            print("SUPERDENSE AND SEQUENTIAL")
            available_entanglement_pairs = self.entanglement_pairs
            wait_time = wait_time + (available_entanglement_pairs/2)*self.super_dense_time
            packet_bit_length = packet_bit_length - available_entanglement_pairs
            self.entanglement_pairs = self.entanglement_pairs-available_entanglement_pairs 
            cost = available_entanglement_pairs
        print(f"---- DELAYING PACKET FOR  {wait_time*self.int_to_sec} \n ---- PACKET LENGTH:{packet_bit_length}")
        time.sleep(wait_time*self.int_to_sec)
        return packet, cost

if __name__ == "__main__":
    channel = SimpleChannel()
