import socket
import time
import pygame
from pygame import K_DOWN, K_UP, K_LEFT, K_RIGHT

HOST = '192.168.0.117'  # The server's hostname or IP address
PORT = 80  # The port used by the server

pygame.init()
screen = pygame.display.set_mode((800, 600))


def handle_recv(data):
    data = data.split(b'\xFF')
    for msg in data:
        if len(msg) == 10 and msg[0] == 0x01 and msg[1] == 0x0A:
            panPos = int.from_bytes(bytearray([msg[2] + msg[3], msg[4] + msg[5]]), byteorder='big')
            tiltPos = int.from_bytes(bytearray([msg[6] + msg[7], msg[8] + msg[9]]), byteorder='big')
            print("pos:", panPos, tiltPos)


# FIXME: add a class to hide this
joystick = None
req_pan_speed = 0
req_tilt_speed = 0

def handle_joystick():
    pan_speed = 0
    tilt_speed = 0

    global joystick

    if joystick is not None:
        x_axis = joystick.get_axis(0)
        y_axis = -joystick.get_axis(1)

        if abs(x_axis) < 0.05:
            x_axis = 0
        if abs(y_axis) < 0.05:
            y_axis = 0

        pan_speed = round(0x7F * x_axis)
        tilt_speed = round(0x7F * y_axis)

    pressed_keys = pygame.key.get_pressed()
    if pressed_keys[K_UP]:
        tilt_speed = 0x7F
    elif pressed_keys[K_DOWN]:
        tilt_speed = -0x7F
    if pressed_keys[K_LEFT]:
        pan_speed = -0x7F
    elif pressed_keys[K_RIGHT]:
        pan_speed = 0x7F

    pygame.draw.circle(screen, (255, 0, 0), (400 + pan_speed * (200 / 0x7F) , 300 - tilt_speed * (200 / 0x7F)), 10)

    global req_pan_speed
    global req_tilt_speed

    if pan_speed != req_pan_speed or tilt_speed != req_tilt_speed:
        req_pan_speed = pan_speed
        req_tilt_speed = tilt_speed
        # 01 00 xx yy FF
        data = bytearray([0x01, 0x00])
        data += pan_speed.to_bytes(1, byteorder='big', signed=True)
        data += tilt_speed.to_bytes(1, byteorder='big', signed=True)
        data += bytearray([0xFF])
        s.sendall(data)


def init_joystick():
    if pygame.joystick.get_count() < 1:
        return

    global joystick
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print("Joystick: " + joystick.get_name())
    print("Number of axes: " + str(joystick.get_numaxes()))


if __name__ == '__main__':
    init_joystick()
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

            # poll the current axis position
            s.sendall(bytearray([0x01, 0x0A, 0xFF]))

            pygame.display.flip()

            try:
                data = s.recv(16)
                handle_recv(data)
            except socket.error:
                '''no data yet..'''

            time.sleep(0.1)
