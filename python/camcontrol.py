import socket
import time

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 65432  # The port used by the server


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
        pass


if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        while True:
            data = [0xAA, 0x01, 0x03, 0x00, 0x00]
            s.sendall(bytearray(data))
            data = s.recv(16)
            handle_recv(data)
            time.sleep(0.1)
