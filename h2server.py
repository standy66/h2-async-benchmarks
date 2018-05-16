import sys
import socket
import json
import h2.connection
import h2.events

def send_response(conn, event):
    data = b"Hello, world"
    response_headers = (
        (':status', '200'),
        ('content-length', str(len(data))),
    )
    conn.send_headers(event.stream_id, response_headers)
    conn.send_data(event.stream_id, data, end_stream=True)

def handle(sock):
    config = h2.config.H2Configuration(client_side=False, header_encoding="utf-8")
    conn = h2.connection.H2Connection(config=config)
    conn.initiate_connection()
    sock.sendall(conn.data_to_send())

    while True:
        data = sock.recv(65535)
        if not data:
            break
        events = conn.receive_data(data)
        for event in events:
            if isinstance(event, h2.events.RequestReceived):
                send_response(conn, event)
            elif isinstance(event, h2.events.ConnectionTerminated):
                sock.sendall(conn.data_to_send())
                sock.close()
                return
        sock.sendall(conn.data_to_send())


def main():
    port = int(sys.argv[1])
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', port))
    sock.listen()

    while True:
        handle(sock.accept()[0])
	

if __name__ == "__main__":
    main()
