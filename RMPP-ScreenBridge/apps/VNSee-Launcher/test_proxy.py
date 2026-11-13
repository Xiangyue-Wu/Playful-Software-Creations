"""Local relay test using memory streams; never contacts RMPP or VNC."""
import queue
import socket
import threading
import time

import portable_gui


class Stream:
    def __init__(self):
        self.inbox = queue.Queue()
        self.peer = None
        self.timeout = None

    def settimeout(self, value):
        self.timeout = value

    def recv(self, size):
        try:
            return self.inbox.get(timeout=self.timeout)
        except queue.Empty:
            raise socket.timeout()

    def sendall(self, data):
        self.peer.inbox.put(data)

    def shutdown_write(self):
        self.peer.inbox.put(b'')

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def pair():
    a, b = Stream(), Stream()
    a.peer, b.peer = b, a
    return a, b


def test_delayed_banner_after_half_close():
    channel, requester = pair()
    local, server = pair()
    original_connect = socket.create_connection
    errors = []

    def serve():
        try:
            server.settimeout(3)
            assert server.recv(1) == b''
            time.sleep(1.2)  # Forces relay.recv to time out once.
            server.sendall(b'RFB 003.008\n')
            server.shutdown_write()
        except Exception as exc:
            errors.append(exc)

    socket.create_connection = lambda *_args, **_kwargs: local
    try:
        server_thread = threading.Thread(target=serve, daemon=True)
        relay_thread = threading.Thread(target=portable_gui.pipe, args=(channel,), daemon=True)
        server_thread.start()
        relay_thread.start()
        requester.settimeout(3)
        requester.shutdown_write()
        assert requester.recv(12) == b'RFB 003.008\n'
        server_thread.join(2)
        relay_thread.join(2)
        assert not errors, errors
        assert not relay_thread.is_alive()
    finally:
        socket.create_connection = original_connect


if __name__ == '__main__':
    test_delayed_banner_after_half_close()
    print('relay test OK')
