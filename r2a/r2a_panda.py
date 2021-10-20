# -*- coding: utf-8 -*-

from typing_extensions import runtime
from xml.etree.ElementTree import SubElement
from player.parser import *
from r2a.ir2a import IR2A

import time
import sys
import math

global kappa, omega, alpha, epsilon, e, grace_time
kappa = 0.14
omega = 10000
alpha = 0.2
epsilon = 0.15
e = math.e
grace_time = 2.5


def mean(l):
    return sum(l) / len(l)


class R2A_Panda(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []

        self.request_time = 0

        self.T = []
        self.X_chapeu = []
        self.X_til = []

        self.Y = []

        self.r = []

        self.first_time_running = True

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.last_request_time = self.request_time

        self.send_down(msg)

    def handle_xml_response(self, msg):
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()
        print(self.qi)

        t = time.perf_counter() - self.request_time
        self.T.append(t)

        throughput = msg.get_bit_length() / t
        self.X_til.append(throughput)

        self.send_up(msg)

    def get_quality_under(self, value):
        selected_qi = 0
        for i in range(len(self.qi)):
            if self.qi[i] <= value:
                selected_qi = i
            else:
                break
        return selected_qi

    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()

        buffer_bias = math.log(
            max(1, self.whiteboard.get_amount_video_to_play()), e)

        t_chapeu = self.request_time - self.last_request_time

        self.T[-1] = max(t_chapeu, self.T[-1])

        if(self.first_time_running):
            self.first_time_running = False

            msg.add_quality_id(self.qi[0])
            self.X_chapeu.append(self.qi[0])
            self.Y.append(self.X_chapeu[-1])
            self.r.append(self.qi[0])
            self.send_down(msg)
            self.last_request_time = self.request_time
            return

        X_chapeu_atual_max = max(0, self.X_chapeu[-1] - self.X_til[-1] + omega)

        time_bias = (e ** ((self.T[-1] - grace_time) / 2.5))

        X_chapeu_atual = self.X_chapeu[-1] + \
            omega * buffer_bias -\
            kappa * X_chapeu_atual_max * time_bias

        print(
            f"{self.X_chapeu[-1]} + {omega} * {buffer_bias} - {kappa} * {X_chapeu_atual_max} * {time_bias}", X_chapeu_atual_max)
        print(
            f"{self.X_chapeu[-1]} + {omega * buffer_bias} - {kappa * X_chapeu_atual_max * time_bias}", X_chapeu_atual_max)

        X_chapeu_atual = max(0, X_chapeu_atual)

        self.X_chapeu.append(X_chapeu_atual)

        Y_atual = self.Y[-1] - alpha * self.T[-1] * (self.Y[-1]-X_chapeu_atual)

        self.Y.append(Y_atual)

        r_up = self.qi[self.get_quality_under(
            Y_atual - epsilon * mean(self.Y))]
        r_down = self.qi[self.get_quality_under(Y_atual)]

        if(r_up > self.r[-1]):
            r = r_up
        elif(self.r[-1] > r_down):
            r = r_down
        else:
            r = self.r[-1]

        self.r.append(r)

        print("X_chapeu ", self.X_chapeu[-5:])
        print("X_til ", self.X_til[-5:])
        print("Y ", self.Y[-5:])
        print("T ", self.T[-5:])
        print("r_up ", r_up)
        print("r_down ", r_down)
        print("r ", self.r[-5:])

        self.last_request_time = self.request_time

        msg.add_quality_id(int(r))
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        t_til = time.perf_counter() - self.request_time
        self.T.append(t_til)

        throughput = msg.get_bit_length() / t_til

        self.X_til.append(throughput)

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
