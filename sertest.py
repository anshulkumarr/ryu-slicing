from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import udp
from ryu.lib.packet import tcp
from ryu.lib.packet import icmp
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp


class TrafficSlicing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TrafficSlicing, self).__init__(*args, **kwargs)

        # outport = self.mac_to_port[dpid][mac_address]
        self.mac_to_port = {
            "5e:2c:7f:21:59:a1": 1,
            "fa:80:e6:7d:6e:3b": 2,
            "22:07:0d:1d:d2:e5": 3}
            
        self.initial_dst_mac = {}
        self.initial_dst_ip = {} 
        
       

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority, match=match, instructions=inst
        )
        self.logger.info("add_flow.datapath.send_msg(%s)", vars(mod))
        datapath.send_msg(mod)

    def _send_package(self, msg, datapath, in_port, actions):
        data = None
        ofproto = datapath.ofproto
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        self.logger.info("_send_package.datapath.send_msg(%s)", vars(out))
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src
        

        dpid = datapath.id
        print("reached here!!!")

        if (pkt.get_protocol(tcp.tcp) and pkt.get_protocol(tcp.tcp).dst_port == 9999):
            print("tcp")
            out_port = self.mac_to_port[dst]
            dst_ip=tcp.dst
            src_ip=tcp.src
            port = pkt.get_protocol(tcp.tcp).dst_port
            print("***********")
            print(port)
            print("**********")
            self.initial_dst_mac[src_mac] = dst
            self.initial_dst_ip[src_ip] = dst_ip
            match = datapath.ofproto_parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst,
                eth_src=src,
                eth_type=ether_types.ETH_TYPE_IP,
                ip_proto=0x06, 
                )

            actions = [
                parser.OFPActionSetField(ipv4_src="10.0.0.2"),
                parser.OFPActionSetField(eth_src='5e:2c:7f:21:59:a1'),
                parser.OFPActionOutput(1)
            ]
            self.add_flow(datapath, 2, match, actions)
            self._send_package(msg, datapath, in_port, actions)
            
        elif (pkt.get_protocol(tcp.tcp) and pkt.get_protocol(tcp.tcp).dst_port == 9988):
            print("tcp")
            out_port = self.mac_to_port[dst]
            port = pkt.get_protocol(tcp.tcp).dst_port
            print("***********")
            print(port)
            print("**********")
            dst_ip=tcp.dst
            src_ip=tcp.src
            self.initial_dst_mac[src] = dst_mac
            self.initial_dst_ip[src_ip] = dst_ip
            match = datapath.ofproto_parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst,
                eth_src=src,
                eth_type=ether_types.ETH_TYPE_IP,
                ip_proto=0x06, 
                )

            actions = [
                parser.OFPActionSetField(ipv4_src="10.0.0.3"),
                parser.OFPActionSetField(eth_src='22:07:0d:1d:d2:e5'),
                parser.OFPActionOutput(3)
            ]
            self.add_flow(datapath, 2, match, actions)
            self._send_package(msg, datapath, in_port, actions)
            
            
            
        elif (pkt.get_protocol(tcp.tcp) and pkt.get_protocol(tcp.tcp).dst_port != 9999 and pkt.get_protocol(tcp.tcp).dst_port != 9988):
            print("tcp")
            new_src_mac= self.initial_dst_mac[dst]
            new_src_ip= self.initial_dst_ip[dst_ip]
            out_port = self.mac_to_port[dst]
            port = pkt.get_protocol(tcp.tcp).dst_port
            print("***********")
            print(port)
            print("**********")
            match = datapath.ofproto_parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst,
                eth_src=src,
                eth_type=ether_types.ETH_TYPE_IP,
                ip_proto=0x06, 
                )

            actions = [
                parser.OFPActionSetField(ipv4_src=new_src_ip),
                parser.OFPActionSetField(eth_src=new_src_mac),
                parser.OFPActionOutput(out_port)
                ]
            self.add_flow(datapath, 2, match, actions)
            self._send_package(msg, datapath, in_port, actions)
            
            
        elif (pkt.get_protocol(arp.arp)):
            print("arp")
            out_port = ofproto.OFPP_FLOOD
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            match = datapath.ofproto_parser.OFPMatch(in_port=in_port)
            self.add_flow(datapath, 1, match, actions)
            self._send_package(msg, datapath, in_port, actions)
            
            
            

        elif pkt.get_protocol(icmp.icmp):
            out_port = self.mac_to_port[dst]
            match = datapath.ofproto_parser.OFPMatch(
                in_port=in_port,
                eth_dst=dst,
                eth_src=src,
                eth_type=ether_types.ETH_TYPE_IP,
                ip_proto=0x01,  # ICMP
                )
            actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
            self.add_flow(datapath, 1, match, actions)
            self._send_package(msg, datapath, in_port, actions)
	else :
	    print("reached end")

