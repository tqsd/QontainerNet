from scapy.all import *
import matplotlib.pyplot as plt
from binascii import hexlify
from threading import Thread
from datetime import datetime
import time


class Network_Analyzer:
    def __init__(self, time, segment_len):
        self.time = time
        self.segment_len = segment_len
        self.bws = []
        self.ts  = [0]
        self.capture_thread= None
        for i in range(0,int(time/self.segment_len)-1):
            if len(self.ts) == 0:
                continue
            self.ts.append(self.ts[-1] + self.segment_len)

    def capture(self, iface):
        bw = []
        print(f"Capturing traffic for {self.time}s")
        f_time = datetime.now().timestamp()
        packets = sniff(iface=iface, timeout=self.time)
        f_time = 0 ## Timestamp of first packet
        current_segment = 1
        segment_load = 0
        for packet in packets:
            if f_time == 0:
                f_time = packet.time
            try:
                packet[IP].src
            except:
                continue

            if packet.time > f_time + current_segment*self.segment_len:
                #New segment
                segment_bw = ((segment_load*8)/self.segment_len)/1024
                bw.append(segment_bw)
                segment_load = 0
                current_segment = current_segment + 1

                #Calculate pauses if no packet was transmitted
                if (packet.time - (f_time+current_segment*self.segment_len)) > (2* self.segment_len):
                    pause =int((packet.time - f_time-current_segment*self.segment_len)/self.segment_len)
                    print(pause)
                    for i in range(pause):
                        current_segment = current_segment + 1
                        bw.append(0)
            segment_load = segment_load + len(packet)
        self.bws.append(bw)

    def run_capture_thread(self, ifce):
        print("Running a capture thread")
        self.capture_thread = threading.Thread(target=self.capture, args=(ifce,))
        self.capture_thread.start()
        pass

    def join_capture_thread(self):
        self.capture_thread.join()
        #print(self.bws[0])
        #print(self.ts)
        print(f"{len(self.bws[0])} - {len(self.ts)}")

    def plot(self, file_name=None):
        plt.clf()
        average = [0] * int((self.time/self.segment_len))
        average_div = [0] * int((self.time/self.segment_len))
        for bw in self.bws:

            for i in range(0,len(self.ts)-len(bw)):
                bw.append(0)

            plt.plot(self.ts , bw, alpha=0.1)
            for i in range(len(bw)):
                average[i] = average[i] + bw[i]
                average_div[i] = average_div[i] + 1
        for i in range(len(average)):
            try:
                average[i] = average[i]/average_div[i]
            except:
                average[i] = 0
        x = 0
        for i in range(len(average)):
            x = i
            if average_div[i] == 0:
                break

        plt.plot(self.ts, average, "black")
        print("Updating plots")
        if file_name is None:
            plt.title("Bandwidth")
            plt.xlabel("time[s]")
            plt.ylabel("bandwidth[Kbits/s]")
            plt.ion()
            plt.show()
            plt.draw()
            plt.pause(0.001)
        else:
            pass #Save figure


if __name__ == "__main__":
    na = Network_Analyzer(30, 0.5)
    try:
        while True:
            print("New sequence")
            na.run_capture_thread("sw2-h2")
            na.join_capture_thread()
            na.plot()
            time.sleep(20)
    except KeyboardInterrupt:
        print("Exiting")

'''
#packets = sniff(iface="s1-s2", timeout=100)

# Time length of segment
#segment_length = 1
#Bandwidth Array
bw = [0]
#Time array
ts = []

f_time = 0
segment_load = 0
segment_start_time = 10
for packet in packets:
    if f_time == 0:
        f_time = packet.time
        segment_start_time = f_time

    if packet.time > segment_start_time + segment_length:
        #New segment

        segment_bw = ((segment_load*8)/segment_length)/1024
        print(segment_load*8)
        print(segment_length)
        print(segment_bw)
        bw.append(segment_bw)

        if (packet.time - segment_start_time) > (2* segment_length):
            print(packet.time)
            print(segment_start_time)
            pause =int((packet.time - segment_start_time)/segment_length)
            #pause = int(() / segment_length)
            print(pause)
            for i in range(pause):
                bw.append(0)

        segment_load = 0
        segment_start_time = packet.time
    segment_load = segment_load + len(packet)

ts = []
x = 0
for i in range(0,len(bw)):
    ts.append(x)
    x = x + segment_length
print(ts)
print(bw)
plt.plot(ts,bw)
plt.savefig('test.png')
'''





