import socket
import sys
import time
import pygame
import button_handler
import joystick
import pad_handler
import argparse
import signal
import statusdisplay
import pad_display

try:
    import touchphat
except (ImportError, OSError):
    print("Touch PHAT not supported")
    import touchphat_mock as touchphat

try:
    import ST7735
except (ImportError, OSError):
    print("no display support")


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
            results.append({'header': [msg[0], msg[1]], 'param': [panPos, tiltPos]})

            if args.debug:
                print("pos:", panPos, tiltPos)

            on_stored_position = None
            for key in stored_positions:
                if stored_positions[key] == [panPos, tiltPos]:
                    on_stored_position = key
                    break
            pad_handler.on_position(on_stored_position)

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


stored_positions = {}
bHandler = button_handler.ButtonHandler(['A', 'B', 'C', 'D', 'Back', 'Trigger1', 'Trigger2'])


@touchphat.on_touch(['Back', 'A', 'B', 'C', 'D'])
def handle_touch(event):
    pad_handler.set_pad(event.name, True)
    bHandler.on_pressed(event.name)


@touchphat.on_release(['Back', 'A', 'B', 'C', 'D'])
def handle_release(event):
    pad_handler.set_pad(event.name, False)
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
        pad_handler.set_selected(key)

@bHandler.on_press(['Trigger1', 'Trigger2'])
def handle_press(key):
    print("on_press", key)
    stop_all_axis(s)
    data = None
    if key == 'Trigger1':
        data = bytearray([0x02, 0x01, 0xFF])
    elif key == 'Trigger2':
        data = bytearray([0x02, 0x02, 0xFF])

    s.sendall(data)

@bHandler.on_long_press(['A', 'B', 'C', 'D'])
def handle_long_press(key):
    print("on_long_press", key)
    stop_all_axis(s)
    pad_handler.confirm(key)

    # poll the current axis position
    s.sendall(bytearray([0x01, 0x0A, 0xFF]))
    resp = wait_for_resp(s, [0x01, 0x0A])
    print("store", key, resp['param'][0], resp['param'][1])

    existing_key = None
    for k in stored_positions:
        if stored_positions[k] == resp['param']:
            existing_key = k
            break
    if existing_key is not None:
        del stored_positions[existing_key]
        pad_display.pad_stored(existing_key, False)
    stored_positions[key] = resp['param']
    pad_display.pad_stored(key, True)


@bHandler.on_long_press(['Back'])
def handle_restart(key):
    print("request restart")

    for i in range(0, 5):
        touchphat.set_led(key, True)
        time.sleep(0.1)
        touchphat.set_led(key, False)
        time.sleep(0.1)

    if s is not None:
        s.close()
    sys.exit()


def wait_for_server():
    while True:  # wait for server socket
        try:
            touchphat.all_on()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((args.server, args.port))
            s.setblocking(False)
            return s
        except socket.error:
            touchphat.all_off()
            time.sleep(1)


def shutdown_handler(signo, stack_frame):
    if s is not None:
        s.close()
    sys.exit()


def handle_joystick(joystick, sock):
    axis_speed = joystick.get_axis_speed()
    if axis_speed is not None:
        # 01 00 xx yy FF
        data = bytearray([0x01, 0x00])
        if axis_speed[0] < 0:
            data += 0x01.to_bytes(1, byteorder='little')
        else:
            data += 0x00.to_bytes(1, byteorder='little')
        data += abs(axis_speed[0]).to_bytes(1, byteorder='little')

        if axis_speed[1] < 0:
            data += 0x01.to_bytes(1, byteorder='little')
        else:
            data += 0x00.to_bytes(1, byteorder='little')
        data += abs(axis_speed[1]).to_bytes(1, byteorder='little')
        data += bytearray([0xFF])
        sock.sendall(data)


def poll_axis_state(sock):
    sock.sendall(bytearray([0x01, 0x0B, 0xFF]))
    try:
        data = sock.recv(128)
        resp = check_for_resp(data, [0x01, 0x0B])  # check axis state

        if resp is not None:
            if resp['param'][0] != 0 or resp['param'][1] != 0:
                sock.sendall(bytearray([0x01, 0x0A, 0xFF]))  # poll the current axis position
            if resp['param'][0] == 2 or resp['param'][1] == 2:  # axis started moving to position
                pad_handler.start_blink()
            if resp['param'][0] != 2 and resp['param'][1] != 2:  # all axis reached target
                pad_handler.stop_blink()
                sock.sendall(bytearray([0x01, 0x0A, 0xFF]))  # poll the current axis position
    except socket.error:
        pass  # no data yet


signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', '-s', help='set server address', required=True)
    parser.add_argument('--port', '-p', type=int, help='set the server port', default=80)
    parser.add_argument('--debug', '-d', action='store_true', help='run server in debug mode')
    args = parser.parse_args()

    if args.debug:
        print("debug mode")

    disp = ST7735.ST7735(
        port=0,
        cs=0,  # ST7735.BG_SPI_CS_FRONT,  # BG_SPI_CSB_BACK or BG_SPI_CS_FRONT
        rst=25,
        dc=24,
        rotation=180,
        width=128,
        height=160
    )
    disp.begin()

    pad_display = pad_display.PadDisplay(disp)
    pad_handler = pad_handler.PadHandler(display=pad_display)

    pygame.init()
    joystick = joystick.Joystick(bHandler, pad_handler)
    joystick.init()

    while True:
        s = wait_for_server()
        print("Connected to camera controller")
        stop_all_axis(s)

        # configure axis acceleration -> 0 - 100 per axis
        s.sendall(bytearray([0x01, 0xB0, 70, 40]))

        # TODO: add mechanism to support multiple cams
        cam = statusdisplay.CameraInfo(1)
        pad_display.update_status(cam, joystick.max_speed)
        pad_handler.startup()

        last_tick = 0

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            tick = time.time()

            bHandler.process()
            pad_handler.process()
            joystick.process()

            pad_display.update_status(cam, joystick.max_speed)
            pad_display.update()

            if tick - last_tick > 0.1:
                try:
                    handle_joystick(joystick, s)
                    poll_axis_state(s)
                except socket.error:
                    print("lost connection")
                    running = False
                    break
                last_tick = tick

            time.sleep(0.01)
