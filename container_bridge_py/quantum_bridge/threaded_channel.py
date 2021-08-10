import sys

from threaded_channel.channel import Channel

if __name__ == "__main__":
    channel = Channel(['Alice', 'Bob'])
    try:
        channel.node_a.wait_stop()
        channel.node_b.wait_stop()
    except KeyboardInterrupt:
        print("Keyboard Interrupt")
        channel.node_a.stop()
        channel.node_b.stop()
        sys.exit(0)
