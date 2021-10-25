from typing_extensions import runtime
from xml.etree.ElementTree import SubElement
from player.parser import *
from r2a.ir2a import IR2A

import time

global kappa, omega, alpha, epsilon, e, grace_time, beta
kappa = 0.14
omega = 0.3
alpha = 0.2
epsilon = 0.15
beta = 0.2

class R2A_Panda(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []

        self.buffer_size = 26

        self.request_time = 0
        self.T = []
        self.T_estimado = [0]
        self.X_chapeu = []
        self.X_til = []
        self.Y = []
        self.r = []

        self.first_time_running = True

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()

        self.send_down(msg)

    def handle_xml_response(self, msg):
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()
        print(self.qi)

        t = time.perf_counter() - self.request_time
        self.T.append(t)

        throughput = msg.get_bit_length() / self.T[-1]
        self.X_til.append(throughput)
        self.X_chapeu.append(throughput)
        self.Y.append(throughput)
        self.r.append(self.get_quality_under(throughput))

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

        buffer_list = self.whiteboard.get_playback_buffer_size()

        if len(buffer_list) == 0:
            msg.add_quality_id(self.qi[0])
            self.r.append(self.qi[0])
            t = max(self.T[-1], self.T_estimado[-1])
            if self.Y[-1] < self.X_til[-1]:
                vazao = self.Y[-1] + (t * kappa * (omega + max(0, (self.X_til[-1] - self.X_chapeu[-1] + omega))))
            else:
                vazao = self.Y[-1] + (t * kappa * (omega - max(0, (self.Y[-1] - self.X_til[-1] + omega))))
            self.X_chapeu.append(max(vazao, self.qi[0]))
            vazao_suavizada = ((beta * (self.Y[-1] - self.X_chapeu[-1])) * t) + self.Y[-1]
            self.Y.append(vazao_suavizada)

        elif len(buffer_list) != 0:
            buffer_list = self.whiteboard.get_playback_buffer_size()
            if len(buffer_list) < 2:
                buffer = buffer_list[-1]
                buffer_antigo = buffer
            else:
                buffer = buffer_list[-1]
                buffer_antigo = buffer_list[-2]

            t = max(self.T[-1], self.T_estimado[-1])
            if self.Y[-1] < self.X_til[-1]:
                vazao = self.Y[-1] + (
                        t * kappa * (omega + max(0, (self.X_til[-1] - self.X_chapeu[-1] + omega))))
                self.X_chapeu.append(vazao)
            else:
                vazao = self.X_chapeu[-1] + (
                                (t) * kappa * (omega - max(0, (self.Y[-1] - self.X_til[-1] + omega))))
                self.X_chapeu.append(vazao)
            vazao_suavizada = ((-alpha * (self.Y[-1] - self.X_chapeu[-1])) * t) + self.Y[-1]
            self.Y.append(vazao_suavizada)

            delta_up = epsilon * vazao_suavizada
            delta_down = 0
            r_up = -1
            r_down = -1

            if (vazao_suavizada - delta_up) < self.qi[0] and buffer[1] < buffer_antigo[1]:
                r_up = 0
            elif (vazao_suavizada - delta_up) < self.qi[0] and buffer[1] >= buffer_antigo[1]:
                r_up = 1

            if (vazao_suavizada - delta_down) < self.qi[0] and buffer[1] < buffer_antigo[1]:
                r_down = 0
            elif (vazao_suavizada - delta_down) < self.qi[0] and buffer[1] >= buffer_antigo[1]:
                r_down = 1

            for i in range(19, -1, -1):
                if (vazao_suavizada - delta_up) >= self.qi[i] and r_up == -1:
                    r_up = i
                if (vazao_suavizada - delta_down) >= self.qi[i] and r_down == -1:
                    r_down = i

            r_1 = self.r[-1]

            if buffer[1] <= 1:
                r = 0
            elif r_1 < r_up:
                r = r_up
            elif r_up <= r_1 <= r_down:
                r = r_1
            else:
                r = r_down

            self.r.append(r)
            msg.add_quality_id(self.qi[r])

        if len(buffer_list) == 0:
            buffer = [0, 0]
        else:
            buffer = buffer_list[-1]
        tempo = (self.r[-1] / self.Y[-1]) + (beta * (buffer[1] - self.buffer_size))
        self.T_estimado.append(tempo)

        self.request_time = time.perf_counter()

        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.T.append(time.perf_counter() - self.request_time)

        throughput = msg.get_bit_length() / self.T[-1]

        self.X_til.append(throughput)

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
