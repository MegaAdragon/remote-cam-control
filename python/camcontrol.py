import socket
import time
import pygame
import button_handler
import joystick
import led_handler

try:
    import touchphat
except ImportError:
    print("Touch PHAT not supported")
    import touchphat_mock as touchphat

HOST = '192.168.0.117'  # The server's hostname or IP address
PORT = 80  # The port used by the server

def handle_recv(data):
    data = data.split(b'\xFF')
    results = []
    for msg in data:
        if len(msg) == 18 and msg[0] == 0x01 and msg[1] == 0x0A:
            panPos = int.from_bytes(bytearray([msg[2] + msg[3], msg[4] + msg[5], msg[6] + msg[7], msg[8] + msg[9]]),
                                    byteorder='little', signed=True)
            tiltPos = int.from_bytes(
                bytearray([msg[10] + msg[11], msg[12] + msg[13], msg[14] + msg[15], msg[16] + msg[17]]),
                byteorder='little', signed=True)
            print("pos:", panPos, tiltPos)
            results.append({'header': [msg[0], msg[1]], 'param': [panPos, tiltPos]})
        if len(msg) == 4 and msg[0] == 0x01 and msg[1] == 0x0B:
            results.append({'header': [msg[0], msg[1]], 'param': [msg[2], msg[3]]})
    return results


def check_for_resp(data, header):
    results = handle_recv(data)
    if results is None or len(results) == 0:
        return
    for r in results:
        if r['header'] == header:
            return r


def wait_for_resp(sock, header):
    # TODO: use timeout
    while True:
        try:
            data = sock.recv(32)
            resp = check_for_resp(data, header)
            if resp is not None:
                return resp
        except socket.error:
            pass  # no data yet


def encode_stepper_pos(data, pos):
    posData = pos.to_bytes(4, byteorder='little', signed=True)
    for idx in range(0, 4 * 2):
        if idx % 2 == 0:
            data.append(posData[int(idx / 2)] & 0xF0)
        else:
            data.append(posData[int(idx / 2)] & 0x0F)


def stop_all_axis(sock):
    sock.sendall(bytearray([0x01, 0x02, 0xFF]))
    joystick.lock()


bHandler = button_handler.ButtonHandler(['A', 'B', 'C', 'D', 'Back'])
led_handler = led_handler.LedHandler()

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
    if key in stored_positions:
        stop_all_axis(s)
        print("Go to stored position", key, stored_positions[key][0], stored_positions[key][1])
        data = bytearray([0x01, 0x01])
        encode_stepper_pos(data, stored_positions[key][0])
        encode_stepper_pos(data, stored_positions[key][1])
        data.append(0xFF)
        s.sendall(data)
        led_handler.set_selected(key)


@bHandler.on_long_press(['A', 'B', 'C', 'D'])
def handle_long_press(key):
    print("on_long_press", key)
    stop_all_axis(s)
    led_handler.confirm(key)

    # poll the current axis position
    s.sendall(bytearray([0x01, 0x0A, 0xFF]))
    resp = wait_for_resp(s, [0x01, 0x0A])
    print("store", key, resp['param'][0], resp['param'][1])
    stored_positions[key] = resp['param']


@bHandler.on_long_press(['Back'])
def handle_restart(key):
    print("request restart")
    # TODO: reset everything


if __name__ == '__main__':
    pygame.init()
    joystick = joystick.Joystick(bHandler)
    joystick.init()

    while True:
        while True:  # wait for server socket
            try:
                touchphat.all_on()
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect((HOST, PORT))
                s.setblocking(False)
                break
            except socket.error:
                touchphat.all_off()
                time.sleep(1)

        print("Connected to camera controller")
        led_handler.startup()

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            joystick.process()
            bHandler.process()
            led_handler.process()

            axis_speed = joystick.get_axis_speed()
            if axis_speed is not None:
                # 01 00 xx yy FF
                data = bytearray([0x01, 0x00])
                data += axis_speed[0].to_bytes(1, byteorder='little', signed=True)
                data += axis_speed[1].to_bytes(1, byteorder='little', signed=True)
                data += bytearray([0xFF])
                s.sendall(data)

            try:
                # poll the current axis state
                s.sendall(bytearray([0x01, 0x0B, 0xFF]))
            except socket.error:
                print("lost connection")
                running = False

            try:
                data = s.recv(128)
                resp = check_for_resp(data, [0x01, 0x0B])

                if resp is not None:
                    if resp['param'][0] != 0 or resp['param'][1] != 0:
                        s.sendall(bytearray([0x01, 0x0A, 0xFF]))  # poll the current axis position
                    if resp['param'][0] == 2 or resp['param'][1] == 2:  # axis started moving to position
                        led_handler.start_blink()
                    if resp['param'][0] != 2 and resp['param'][1] != 2:  # all axis reached target
                        led_handler.stop_blink()
            except socket.error:
                pass  # no data yet

            time.sleep(0.1)
