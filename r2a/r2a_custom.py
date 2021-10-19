# -*- coding: utf-8 -*-

from player.parser import *
from r2a.ir2a import IR2A

import time


class R2A_Custom(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []

        self.request_time = 0
        self.throughputs = []
        self.lastThroughtput = 0

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        # getting qi list
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        t = time.perf_counter() - self.request_time
        self.lastThroughtput = msg.get_bit_length() / t
        self.throughputs.append(self.lastThroughtput)

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        # time to define the segment quality choose to make the request
        t = time.perf_counter() - self.request_time
        self.lastThroughtput = msg.get_bit_length() / t

        selected_qi = 0
        for i in range(len(self.qi)):
            if self.lastThroughtput > self.qi[i]:
                selected_qi = i
            else:
                break

        print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", selected_qi)

        msg.add_quality_id(self.qi[selected_qi])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.request_time = time.perf_counter()
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
