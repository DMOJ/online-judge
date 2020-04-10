import os
import socket
import struct
import time
import zlib

size_pack = struct.Struct('!I')


def open_connection():
    sock = socket.create_connection((host, port))
    return sock


def zlibify(data):
    data = zlib.compress(data.encode('utf-8'))
    return size_pack.pack(len(data)) + data


def dezlibify(data, skip_head=True):
    if skip_head:
        data = data[size_pack.size:]
    return zlib.decompress(data).decode('utf-8')


def main():
    global host, port
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--host', default='localhost')
    parser.add_argument('-p', '--port', default=9999, type=int)
    args = parser.parse_args()
    host, port = args.host, args.port

    print('Opening idle connection:', end=' ')
    s1 = open_connection()
    print('Success')
    print('Opening hello world connection:', end=' ')
    s2 = open_connection()
    print('Success')
    print('Sending Hello, World!', end=' ')
    s2.sendall(zlibify('Hello, World!'))
    print('Success')
    print('Testing blank connection:', end=' ')
    s3 = open_connection()
    s3.close()
    print('Success')
    result = dezlibify(s2.recv(1024))
    assert result == 'Hello, World!'
    print(result)
    s2.close()
    print('Large random data test:', end=' ')
    s4 = open_connection()
    data = os.urandom(1000000).decode('iso-8859-1')
    print('Generated', end=' ')
    s4.sendall(zlibify(data))
    print('Sent', end=' ')
    result = b''
    while len(result) < size_pack.size:
        result += s4.recv(1024)
    size = size_pack.unpack(result[:size_pack.size])[0]
    result = result[size_pack.size:]
    while len(result) < size:
        result += s4.recv(1024)
    print('Received', end=' ')
    assert dezlibify(result, False) == data
    print('Success')
    s4.close()
    print('Test malformed connection:', end=' ')
    s5 = open_connection()
    s5.sendall(data[:100000].encode('utf-8'))
    s5.close()
    print('Success')
    print('Waiting for timeout to close idle connection:', end=' ')
    time.sleep(6)
    print('Done')
    s1.close()


if __name__ == '__main__':
    main()
