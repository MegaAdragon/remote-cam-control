import socket
import time
import pygame
from pygame import K_DOWN, K_UP, K_LEFT, K_RIGHT

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 65432  # The port used by the server

pygame.init()
pygame.display.set_mode((800, 600))


def handle_recv(data):
    if len(data) < 3:
        return
    if data[0] != 0xAA:
        return

    dataLength = data[1]
    if dataLength != len(data) - 1:
        return

    cmd = data[2]
    if cmd == 0x01:
        panPos = int.from_bytes(bytearray([data[3], data[4]]), byteorder='big')
        tiltPos = int.from_bytes(bytearray([data[5], data[6]]), byteorder='big')
        print("pos:", panPos, tiltPos)


if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            pressed_keys = pygame.key.get_pressed()

            pan = 0
            tilt = 0

            if pressed_keys[K_UP]:
                tilt = 10
            elif pressed_keys[K_DOWN]:
                tilt = -10
            if pressed_keys[K_LEFT]:
                pan = -10
            elif pressed_keys[K_RIGHT]:
                pan = 10

            data = bytearray([0xAA, 0x00, 0x01])
            data += pan.to_bytes(1, byteorder='big', signed=True)
            data += tilt.to_bytes(1, byteorder='big', signed=True)
            data[1] = len(data) - 1
            s.sendall(data)
            data = s.recv(16)
            handle_recv(data)
            time.sleep(0.1)
