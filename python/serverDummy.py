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
    if len(data) < 3:
        return
    if data[0] != 0xAA:
        return

    dataLength = data[1]
    if dataLength != len(data) - 1:
        return

    cmd = data[2]
    if cmd == 0x01:
        set_axis(int.from_bytes(bytearray([data[3]]), byteorder='big', signed=True), int.from_bytes(bytearray([data[4]]), byteorder='big', signed=True))


def comm_handler(conn):
    while True:
        data = conn.recv(16)  # receive 16 byte
        if not data:
            print("socket closed")
            return
        handle_command(data)
        pan = get_pan().to_bytes(2, byteorder='big')
        tilt = get_tilt().to_bytes(2, byteorder='big')
        resp = bytearray([0xAA, 0x00, 0x01])
        resp += pan
        resp += tilt
        resp[1] = len(resp) - 1
        print(resp)
        conn.sendall(resp)


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
