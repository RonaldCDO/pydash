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

        self.alpha = 0.3
        self.exp_avg_throughput = 0

        self.last_quality = 0
        self.last_buffer_size = 0

        self.DANGER_ZONE = 5
        self.INCREASE_ZONE = 10

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        t = time.perf_counter() - self.request_time
        self.last_throughtput = msg.get_bit_length() / t
        self.throughputs.append(self.last_throughtput)

        self.exp_avg_throughput = self.alpha * self.last_throughtput

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
        buffer_size_variation = buffer_size - self.last_buffer_size

        # selected_qi = self.get_quality_under(self.last_throughtput)

        selected_qi = self.last_quality

        print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", self.exp_avg_throughput,
              buffer_size_variation, buffer_size, selected_qi)

        # avoid choosing higher qualities in the beginning
        if len(self.whiteboard.get_buffer()) < self.DANGER_ZONE:
            self.last_quality = 0
            self.last_buffer_size = buffer_size

            msg.add_quality_id(self.qi[0])
            self.send_down(msg)

            return

        selected_qi = self.get_quality_under(self.exp_avg_throughput)

        # if buffer_size <= self.DANGER_ZONE:
        #     selected_qi = int(selected_qi / 2)
        # elif buffer_size >= self.INCREASE_ZONE:
        #     selected_qi += 2
        #     selected_qi = min(
        #         selected_qi, self.get_quality_under(self.exp_avg_throughput))
        #     selected_qi = min(selected_qi, len(self.qi) - 1)
        # elif buffer_size_variation <= -2:
        #     selected_qi -= 5
        #     selected_qi = max(
        #         selected_qi, self.get_quality_under(self.exp_avg_throughput))
        #     selected_qi = max(0, selected_qi)

        print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
              buffer_size_variation, buffer_size, selected_qi)

        self.last_quality = selected_qi
        self.last_buffer_size = buffer_size

        msg.add_quality_id(self.qi[selected_qi])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        t = time.perf_counter() - self.request_time
        self.last_throughtput = msg.get_bit_length() / t

        self.exp_avg_throughput *= (1 - self.alpha)
        self.exp_avg_throughput = int(
            self.exp_avg_throughput + self.alpha * self.last_throughtput)

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
