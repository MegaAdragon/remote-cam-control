import socket
import time
import pygame
import button_handler
import joystick

try:
    import touchphat
except ImportError:
    print("Touch PHAT not supported")
    import touchphat_mock as touchphat

HOST = '192.168.0.117'  # The server's hostname or IP address
PORT = 80  # The port used by the server


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


bHandler = button_handler.ButtonHandler(['A', 'B', 'C', 'D', 'Back'])

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
    pygame.init()
    joystick = joystick.Joystick(bHandler)
    joystick.init()

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

            joystick.process()
            bHandler.process()

            axis_speed = joystick.get_axis_speed()
            if axis_speed is not None:
                # 01 00 xx yy FF
                data = bytearray([0x01, 0x00])
                data += axis_speed[0].to_bytes(1, byteorder='little', signed=True)
                data += axis_speed[1].to_bytes(1, byteorder='little', signed=True)
                data += bytearray([0xFF])
                s.sendall(data)

            # poll the current axis position
            s.sendall(bytearray([0x01, 0x0A, 0xFF]))

            try:
                data = s.recv(32)
                handle_recv(data)
            except socket.error:
                '''no data yet..'''

            time.sleep(0.1)
