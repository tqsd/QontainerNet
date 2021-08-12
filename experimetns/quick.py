from pprint import pprint
from scapy.all import * 
from scapy.layers.inet import _IPOption_HDR
"""
class _IPOption_HDR(Packet):
    fields_desc = [BitField("copy_flag", 0, 1),
                   BitEnumField("optclass", 0, 2, {0: "control", 2: "debug"}),
                   BitEnumField("option", 0, 5, _ip_options_names)]
"""

class IPOption_ERP(IPOption):
    name = "IP option epr generation"
    option = 25
    fields_desc = [_IPOption_HDR]

packet = IP(dst='11.0.0.1', options='\x19')
options = packet.getfieldval('options')
print(ls(packet))
pprint(packet)
pprint(packet.flags)

packet2 = sr1(IP(dst='127.0.0.1', options=b'\x19'))
pprint(packet2)
print(list(raw(packet2)))
print(len(list(raw(packet2))))
print(list(raw(packet2))[-4])
