# -*- coding: utf-8 -*-

from xml.etree.ElementTree import SubElement
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
        self.last_throughtput = 0

        self.last_quality = 0

        self.DANGER_ZONE = 5
        self.INCREASE_ZONE = 10

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        # getting qi list
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        t = time.perf_counter() - self.request_time
        self.last_throughtput = msg.get_bit_length() / t
        self.throughputs.append(self.last_throughtput)

        self.send_up(msg)

    def get_quality_under(self, value):
        selected_qi = 0
        for i in range(len(self.qi)):
            if value > self.qi[i]:
                selected_qi = i
            else:
                return selected_qi

    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()

        buffer_size = self.whiteboard.get_amount_video_to_play()

        # selected_qi = self.get_quality_under(self.last_throughtput)

        selected_qi = self.last_quality

        if buffer_size <= self.DANGER_ZONE:
            selected_qi = int(selected_qi / 2)
        elif buffer_size > self.INCREASE_ZONE:
            selected_qi += 2 * self.get_quality_under(self.last_throughtput)
            selected_qi = int(selected_qi / 3)

        print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", buffer_size, selected_qi)

        msg.add_quality_id(self.qi[selected_qi])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        t = time.perf_counter() - self.request_time
        self.last_throughtput = msg.get_bit_length() / t
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
