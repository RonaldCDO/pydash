# -*- coding: utf-8 -*-
"""
@author:    Gabriel Delano Erhardt;
            Guilherme Rodrigues Lodron Pire e;
            Ronald Cesar Dias de Oliveira.

@description: R2A Panda

Algoritmo ABR Panda implementado para o
trabalho final de Teleinformática e Redes 2.

"""
import time
from player.parser import *
from r2a.ir2a import IR2A

global kappa, omega, alpha, epsilon, e, grace_time, beta

#definição dos parâmetros do algoritmo
kappa = 0.14
omega = 0.3 * 1048576
alpha = 0.2
epsilon = 0.15
beta = 0.2


class R2A_Panda(IR2A):
    # Inicialização das váriavies da classe
    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []
        self.request_time = 0
        self.Y = []
        self.X_til = []
        self.X_chapeu = []
        self.T = []
        self.T_chapeu = []
        self.T_til = []
        self.r = []
        self.First_Run = True
        self.schedule = 0
        self.buffer_min = 26

    def handle_xml_request(self, msg):
        # Salva tempo inicial
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        # Salva a lista de qualidades
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        # Inserção do tempo medido na lista T
        self.T_til.append(time.perf_counter() - self.request_time)
        
        # Cálculo do throughput
        throughput = msg.get_bit_length() / self.T_til[-1]
        print(f'Throughput >>>>>>>>>>>>> {throughput}')

        if self.First_Run:
            # Limitação do throughput: evita qualidades iniciais muito altas
            throughput = min(throughput, self.qi[9])

            # Inserção do throughput medido nas listas de dados
            self.X_til.append(throughput)
            self.X_chapeu.append(throughput)
            self.Y.append(throughput)
            self.r.append(self.qi[0])

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        # Salva tempo inicial
        self.request_time = time.perf_counter()

        if self.First_Run:
            self.First_Run = False
        else:
            # Calculo da bandwidth alvo para o segmento requisitado agora
            X_chapeu_atual = self.X_chapeu[-1] + \
                            kappa * self.T[-1] * \
                            (omega - max(0, self.X_chapeu[-1] - self.X_til[-1] + omega))
            self.X_chapeu.append(X_chapeu_atual)

            # Calculo da média ponderada exponencial do alvo de bandwidth
            suavizado_atual = abs(-alpha * (self.Y[-1] - self.X_chapeu[-1]) * self.T[-1] + self.Y[-1])
            self.Y.append(suavizado_atual)

        delta_down = 0
        delta_up = epsilon * self.Y[-1]

        r_up = self.Y[-1] - delta_up
        r_down = self.Y[-1] - delta_down

        quantized_r_up = self.qi[0]
        quantized_r_down = self.qi[0]

        for i in self.qi:
            if i < r_up:
                quantized_r_up = i
            if i < r_down:
                quantized_r_down = i

        # Seleciona bitrate de acordo com o dead-zone quantizer do artigo
        if self.r[-1] < r_up:
            self.r.append(quantized_r_up)
        elif quantized_r_up <= self.r[-1] <= quantized_r_down:
            self.r.append(self.r[-1])
        else:
            self.r.append(quantized_r_down)

        print(f'Quantizado >>>>>>>>>>>>>> {self.r[-1]}')
        print(f'X_til >>>>>>>>>>>>>> {self.X_til[-1]}')
        print(f'X_chapeu>>>>>>>>>>>>>> {self.X_chapeu[-1]}')
        print(f'Y>>>>>>>>>>>>>> {self.Y[-1]}')

        msg.add_quality_id(self.r[-1])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        Buffer = self.whiteboard.get_amount_video_to_play()
        schedule = (self.r[-1] * 1
                    / self.Y[-1] + beta * (Buffer - self.buffer_min))


        # Inserção do tempo medido na lista T
        self.T.append(max(schedule, time.perf_counter() - self.request_time))

        # Cálculo do throughput
        throughput = msg.get_bit_length() / (time.perf_counter() - self.request_time)

        self.X_til.append(throughput)
        print(f'Throughput >>>>>>>>>>>>> {throughput}')

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
