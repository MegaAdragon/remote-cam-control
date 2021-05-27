import socket
import time
import pygame
import button_handler

try:
    import touchphat
except ImportError:
    print("Touch PHAT not supported")

HOST = '192.168.0.117'  # The server's hostname or IP address
PORT = 80  # The port used by the server

pygame.init()
screen = pygame.display.set_mode((800, 600))


def handle_recv(data):
    data = data.split(b'\xFF')
    for msg in data:
        if len(msg) == 18 and msg[0] == 0x01 and msg[1] == 0x0A:
            panPos = int.from_bytes(bytearray([msg[2] + msg[3], msg[4] + msg[5], msg[6] + msg[7], msg[8] + msg[9]]),
                                    byteorder='little', signed=True)
            tiltPos = int.from_bytes(
                bytearray([msg[10] + msg[11], msg[12] + msg[13], msg[14] + msg[15], msg[16] + msg[17]]),
                byteorder='little', signed=True)
            print("pos:", panPos, tiltPos)
            return [0x01, 0x0A], panPos, tiltPos


def encode_stepper_pos(data, pos):
    posData = pos.to_bytes(4, byteorder='little', signed=True)
    for idx in range(0, 4 * 2):
        if idx % 2 == 0:
            data.append(posData[int(idx / 2)] & 0xF0)
        else:
            data.append(posData[int(idx / 2)] & 0x0F)


# FIXME: add a class to hide this
joystick = None
req_pan_speed = 0
req_tilt_speed = 0

bHandler = button_handler.ButtonHandler(['A', 'B', 'C', 'D', 'Back'])

joystick_key_map = {
    'A': 1,
    'B': 2,
    'C': 3,
    'D': 4,
}

joystick_button_state = {
    'A': False,
    'B': False,
    'C': False,
    'D': False
}


def handle_joystick():
    global joystick
    if joystick is None:
        return

    x_axis = joystick.get_axis(0)
    y_axis = -joystick.get_axis(1)

    if abs(x_axis) < 0.05:
        x_axis = 0
    if abs(y_axis) < 0.05:
        y_axis = 0

    pan_speed = round(0x7F * x_axis)
    tilt_speed = round(0x7F * y_axis)

    for key in joystick_key_map:
        if joystick.get_button(joystick_key_map[key]):
            touchphat.set_led(key, True)
            joystick_button_state[key] = True
            bHandler.on_pressed(key)
        elif joystick_button_state[key] == True:    # button was pressed
            touchphat.set_led(key, False)
            joystick_button_state[key] = False
            bHandler.on_released(key)

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


sock = None
storedPositions = {}


@touchphat.on_touch(['Back', 'A', 'B', 'C', 'D'])
def handle_touch(event):
    bHandler.on_pressed(event.name)


@touchphat.on_release(['Back', 'A', 'B', 'C', 'D'])
def handle_release(event):
    bHandler.on_released(event.name)


@bHandler.on_press(['A', 'B', 'C', 'D'])
def handle_press(key):
    print("on_press", key)
    if key in storedPositions:
        print("Go to stored position", key, storedPositions[key][0], storedPositions[key][1])
        data = bytearray([0x01, 0x01])
        encode_stepper_pos(data, storedPositions[key][0])
        encode_stepper_pos(data, storedPositions[key][1])
        data.append(0xFF)
        s.sendall(data)


@bHandler.on_long_press(['A', 'B', 'C', 'D'])
def handle_long_press(key):
    print("on_long_press", key)

    # fast blink
    for i in range(0, 5):
        touchphat.set_led(key, True)
        time.sleep(0.1)
        touchphat.set_led(key, False)
        time.sleep(0.1)

    # poll the current axis position
    s.sendall(bytearray([0x01, 0x0A, 0xFF]))

    # TODO: use timeout
    while True:
        try:
            data = s.recv(32)
            result = handle_recv(data)
            if result is not None and result[0][0] == 0x01 and result[0][1] == 0x0A:
                print("store", key, result[1], result[2])
                storedPositions[key] = [result[1], result[2]]
                break
        except socket.error:
            '''no data yet..'''


@bHandler.on_long_press(['Back'])
def handle_restart(key):
    print("request restart")
    # TODO: reset everything


if __name__ == '__main__':
    init_joystick()

    pads = ['Back', 'A', 'B', 'C', 'D', 'Enter']
    for pad in pads:
        touchphat.set_led(pad, True)
        time.sleep(0.1)
    time.sleep(0.2)
    for pad in pads[::-1]:
        touchphat.set_led(pad, False)
        time.sleep(0.1)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.setblocking(False)
        sock = s

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            screen.fill((0, 0, 0))
            pygame.draw.circle(screen, (255, 0, 0), (400, 300), 200, 1)

            handle_joystick()
            bHandler.process()

            # poll the current axis position
            s.sendall(bytearray([0x01, 0x0A, 0xFF]))

            try:
                data = s.recv(32)
                handle_recv(data)
            except socket.error:
                '''no data yet..'''

            time.sleep(0.1)
