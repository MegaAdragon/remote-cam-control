import socket
import time
import pygame
from pygame import K_DOWN, K_UP, K_LEFT, K_RIGHT

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 65432  # The port used by the server

pygame.init()
screen = pygame.display.set_mode((800, 600))

def handle_recv(data):
    if data[0] == 0x01 and len(data) == 11:
        panPos = int.from_bytes(bytearray([data[2] + data[3], data[4] + data[5]]), byteorder='big')
        tiltPos = int.from_bytes(bytearray([data[6] + data[7], data[8] + data[9]]), byteorder='big')
        print("pos:", panPos, tiltPos)


def handle_joystick():
    pressed_keys = pygame.key.get_pressed()
    pan_speed = 0
    tilt_speed = 0

    if pressed_keys[K_UP]:
        tilt_speed = 10
    elif pressed_keys[K_DOWN]:
        tilt_speed = -10
    if pressed_keys[K_LEFT]:
        pan_speed = -10
    elif pressed_keys[K_RIGHT]:
        pan_speed = 10

    pygame.draw.circle(screen, (255, 0, 0), (400 + pan_speed * 20, 300 - tilt_speed * 20), 10)

    if pan_speed != 0 or tilt_speed != 0:
        # 01 00 xx yy FF
        data = bytearray([0x01, 0x00])
        data += pan_speed.to_bytes(1, byteorder='big', signed=True)
        data += tilt_speed.to_bytes(1, byteorder='big', signed=True)
        data += bytearray([0xFF])
        s.sendall(data)


if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.setblocking(False)

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            screen.fill((0, 0, 0))
            pygame.draw.circle(screen, (255, 0, 0), (400, 300), 200, 1)

            handle_joystick()

            pygame.display.flip()

            try:
                data = s.recv(16)
                handle_recv(data)
            except socket.error:
                '''no data yet..'''

            time.sleep(0.1)
