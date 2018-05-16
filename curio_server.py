#!/usr/bin/env python3.5
# -*- coding: utf-8 -*-
"""
curio-server.py
~~~~~~~~~~~~~~

A fully-functional HTTP/2 server written for curio.

Requires Python 3.5+.
"""
import mimetypes
import os
import sys

from curio import Event, spawn, socket, ssl, run

import h2.config
import h2.connection
import h2.events


# The maximum amount of a file we'll send in a single DATA frame.
READ_CHUNK_SIZE = 8192


def create_listening_socket(address):
    """
    Create and return a listening TLS socket on a given address.
    """
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    sock.listen()

    return sock


async def h2_server(address):
    """
    Create an HTTP/2 server at the given address.
    """
    sock = create_listening_socket(address)
    print("Now listening on %s:%d" % address)

    async with sock:
        while True:
            client, _ = await sock.accept()
            server = H2Server(client)
            await spawn(server.run())


class H2Server:
    """
    A basic HTTP/2 file server. This is essentially very similar to
    SimpleHTTPServer from the standard library, but uses HTTP/2 instead of
    HTTP/1.1.
    """
    def __init__(self, sock):
        config = h2.config.H2Configuration(
            client_side=False, header_encoding='utf-8'
        )
        self.sock = sock
        self.conn = h2.connection.H2Connection(config=config)

    async def run(self):
        """
        Loop over the connection, managing it appropriately.
        """
        self.conn.initiate_connection()
        await self.sock.sendall(self.conn.data_to_send())

        while True:
            # 65535 is basically arbitrary here: this amounts to "give me
            # whatever data you have".
            data = await self.sock.recv(65535)
            if not data:
                break

            events = self.conn.receive_data(data)
            for event in events:
                if isinstance(event, h2.events.RequestReceived):
                    data = b"Hello, world"
                    response_headers = (
                        (':status', '200'),
                        ('content-length', str(len(data))),
                    )
                    self.conn.send_headers(event.stream_id, response_headers)
                    self.conn.send_data(event.stream_id, data, end_stream=True)
            await self.sock.sendall(self.conn.data_to_send())

if __name__ == '__main__':
    port = int(sys.argv[1])
    run(h2_server(("localhost", port)))

