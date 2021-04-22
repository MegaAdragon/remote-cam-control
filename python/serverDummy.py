import socket

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)

panPos = 0
tiltPos = 0


def set_axis(pan, tilt):
    global panPos
    global tiltPos
    panPos += pan
    if panPos <= 0:
        panPos = 0
    if panPos >= 1023:
        panPos = 1023

    tiltPos += tilt
    if tiltPos <= 0:
        tiltPos = 0
    if tiltPos >= 1023:
        tiltPos = 1023


def get_pan():
    return panPos


def get_tilt():
    return tiltPos


def handle_command(data):
    if data[0] == 0x01: # move
        cmd = data[1]
        if cmd == 0x00: # speed
            set_axis(int.from_bytes(bytearray([data[2]]), byteorder='big', signed=True), int.from_bytes(bytearray([data[3]]), byteorder='big', signed=True))

        pan = get_pan().to_bytes(2, byteorder='big')
        tilt = get_tilt().to_bytes(2, byteorder='big')
        rsp = bytearray([0x01, cmd])
        rsp.append(pan[0] & 0xF0)
        rsp.append(pan[0] & 0x0F)
        rsp.append(pan[1] & 0xF0)
        rsp.append(pan[1] & 0x0F)
        rsp.append(tilt[0] & 0xF0)
        rsp.append(tilt[0] & 0x0F)
        rsp.append(tilt[1] & 0xF0)
        rsp.append(tilt[1] & 0x0F)
        rsp.append(0xFF)
        print(rsp)
        conn.sendall(rsp)


def comm_handler(conn):
    while True:
        data = conn.recv(16)  # receive 16 byte
        if not data:
            print("socket closed")
            return

        handle_command(data)


if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        print("server: ", HOST, PORT)
        s.listen()
        while True:
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
                comm_handler(conn)
