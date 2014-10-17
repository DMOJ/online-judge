import ctypes
import socket
import struct
import time

__author__ = 'Quantum'
size_pack = struct.Struct('!I')
try:
    RtlGenRandom = ctypes.windll.advapi32.SystemFunction036
except AttributeError:
    RtlGenRandom = None


def open_connection():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    return sock


def zlibify(data):
    data = data.encode('zlib')
    return size_pack.pack(len(data)) + data


def dezlibify(data, skip_head=True):
    if skip_head:
        data = data[size_pack.size:]
    return data.decode('zlib')


def random(length):
    if RtlGenRandom is None:
        with open('/dev/urandom') as f:
            return f.read(length)
    buf = ctypes.create_string_buffer(length)
    RtlGenRandom(buf, length)
    return buf.raw


def main():
    global host, port
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--host', default='localhost')
    parser.add_argument('-p', '--port', default=9999, type=int)
    args = parser.parse_args()
    host, port = args.host, args.port

    print 'Opening idle connection:',
    s1 = open_connection()
    print 'Success'
    print 'Opening hello world connection:',
    s2 = open_connection()
    print 'Success'
    print 'Sending Hello, World!',
    s2.sendall(zlibify('Hello, World!'))
    print 'Success'
    print 'Testing blank connection:',
    s3 = open_connection()
    s3.close()
    print 'Success'
    result = dezlibify(s2.recv(1024))
    assert result == 'Hello, World!'
    print result
    s2.close()
    print 'Large random data test:',
    s4 = open_connection()
    data = random(1000000)
    print 'Generated',
    s4.sendall(zlibify(data))
    print 'Sent',
    result = ''
    while len(result) < size_pack.size:
        result += s4.recv(1024)
    size = size_pack.unpack(result[:size_pack.size])[0]
    result = result[size_pack.size:]
    while len(result) < size:
        result += s4.recv(1024)
    print 'Received',
    assert dezlibify(result, False) == data
    print 'Success'
    s4.close()
    print 'Test malformed connection:',
    s5 = open_connection()
    s5.sendall(data[:100000])
    s5.close()
    print 'Success'
    print 'Waiting for timeout to close idle connection:',
    time.sleep(6)
    print 'Done'
    s1.close()

if __name__ == '__main__':
    main()