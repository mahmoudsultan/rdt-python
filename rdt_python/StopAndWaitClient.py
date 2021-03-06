import socket
import time
import logging
from threading import Timer

from config import client_config
from Packet import Packet
from helpers.Simulators import get_corrupt_simulator

CONFIG_FILE = "inputs/client.in"
PACKET_LEN = 50
TIMEOUT = 3

# Logger configs
logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

FILE_HANDLER = logging.FileHandler('logs/{}.txt'.format(__name__))
FILE_HANDLER.setLevel(logging.DEBUG)
LOGGER.addHandler(FILE_HANDLER)

TERIMAL_HANDLER = logging.StreamHandler()
TERIMAL_HANDLER.setFormatter(logging.Formatter(">> %(asctime)s:%(threadName)s:%(levelname)s:%(module)s:%(message)s"))
TERIMAL_HANDLER.setLevel(logging.DEBUG)
LOGGER.addHandler(TERIMAL_HANDLER)

SERVER_IP, SERVER_PORT, CLIENT_PORT, FILE, RCV_WINDOW_SIZE = client_config(
    CONFIG_FILE)

# TODO: Multiple clients on different ports
# Creating client socket
S_CLIENT = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
S_CLIENT.bind(('localhost', 9222))

timer = None

def main_receive_loop(file_name, probability, seed_num):
    seq_number = 0
    buffer = []
    corrupt_or_not = get_corrupt_simulator(probability, seed_num)

    LOGGER.info("Starting Stop and Wait Client..")

    pkt = Packet(seq_num=seq_number, data=file_name)
    send_packet_and_set_timer(pkt.bytes(), S_CLIENT)
    # S_CLIENT.sendto(pkt.bytes(), (SERVER_IP, SERVER_PORT))
    LOGGER.info("File Request Sent.")

    recieved_pkt = None
    while True:
        # FIXME: 512 should be el buffer size exactly
        packet, address = S_CLIENT.recvfrom(512)
        timer.cancel()
        # Simulates network layer delay
        # time.sleep(0.5)
        LOGGER.info("RECEIVED PACKET: {}".format(packet))
        print("RECEIVED PACKET: {}".format(packet))

        try:
            recieved_pkt = Packet(packet_bytes=corrupt_or_not(packet))
        except ValueError:
            # Packet is corrupted resend last packet
            LOGGER.info("Packet {} is corrupted".format(packet))
            S_CLIENT.sendto(ack_pkt.bytes(), (SERVER_IP, SERVER_PORT))
            continue
        
        if recieved_pkt.seq_num is not seq_number:
            # Last packet is not received
            print("OUT OF SEQ PACKET RECIEVED")
            S_CLIENT.sendto(ack_pkt.bytes(), (SERVER_IP, SERVER_PORT))
            continue
        # Acknowledge received packet
        buffer.append(recieved_pkt.data)
        seq_number = (seq_number + 1) % 2
        ack_pkt = Packet(seq_num=seq_number, data='')

        S_CLIENT.sendto(ack_pkt.bytes(), (SERVER_IP, SERVER_PORT))
        LOGGER.info("PACKET SEQ {} SENT...".format(seq_number))
        
        if recieved_pkt.is_last_pkt:
            with open("recieved/{}".format(file_name.split('/')[-1]), 'w') as f:
                f.write(''.join(buffer))
            LOGGER.info("FILE RECEIVED AND SAVED...")
            break
    
def send_packet_and_set_timer(pkt, server_socket):
    global timer
    server_socket.sendto(pkt, (SERVER_IP, SERVER_PORT))
    timer = Timer(TIMEOUT, send_packet_and_set_timer, args=[pkt, server_socket])
    timer.start()
    LOGGER.info("Packet {} Sent and Timer is set.".format(pkt))

if __name__ == '__main__':
    file_name = 'public/small_file.txt'
    main_receive_loop(file_name, 0.3, 1000)