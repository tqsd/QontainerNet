"""
Probability based traffic generator
"""
import os
import threading
import sched
import time
import sys
import random
import subprocess

DESTINATION = str(sys.argv[1])
PACKET_SIZE = int(sys.argv[2])
PROBABILITY = float(sys.argv[3])
RATE_IF_TRANS = int(sys.argv[4])

scheduler = sched.scheduler(time.time, time.sleep)
udp_packet_header_size = 42
packet_size = PACKET_SIZE - udp_packet_header_size
packet_count = int(RATE_IF_TRANS/(8*PACKET_SIZE))

delay = int(1/packet_count * 10**6)
delay_cmd = ""
if delay > 1:
    delay_cmd = f"-d {delay}"

command = f"mz -A 11.0.0.1 -B {DESTINATION} -T udp -c {packet_count} -p {packet_size}" 

def one_second_traffic():
    if random.choices([True,False],[PROBABILITY,1-PROBABILITY])[0]:
        print(f"packet size {PACKET_SIZE}")
        print(f"rate {RATE_IF_TRANS}")
        print(f"packet count {packet_count}")
        print(command)
        os.system(command)

def generate_tick():
    scheduler.enter(1,1,generate_tick)
    t = threading.Thread(target=one_second_traffic)
    t.start()


generate_tick()
scheduler.run()
