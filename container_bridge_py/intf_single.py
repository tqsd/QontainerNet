import sys
from netfilterqueue import NetfilterQueue


QUEUE_NUM = int(sys.argv[1])

print(f"Listening on queue: {QUEUE_NUM}")

def print_and_accept(pkt):
    print(f"Packet received on in queue:{QUEUE_NUM}")
    print(pkt)
    pkt.accept()




nfqueue = NetfilterQueue()
nfqueue.bind(QUEUE_NUM, print_and_accept)


nfqueue.run()
