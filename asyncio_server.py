# -*- coding: utf-8 -*-
"""
asyncio-server.py
~~~~~~~~~~~~~~~~

A fully-functional HTTP/2 server using asyncio. Requires Python 3.5+.

This example demonstrates handling requests with bodies, as well as handling
those without. In particular, it demonstrates the fact that DataReceived may
be called multiple times, and that applications must handle that possibility.

Please note that this example does not handle flow control, and so only works
properly for relatively small requests. Please see other examples to understand
how flow control should work.
"""
import sys
import asyncio
import io
import json
import collections
from typing import List, Tuple

from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import (
    ConnectionTerminated, DataReceived, RequestReceived, StreamEnded
)
from h2.errors import ErrorCodes
from h2.exceptions import ProtocolError


class H2Protocol(asyncio.Protocol):
    def __init__(self):
        config = H2Configuration(client_side=False, header_encoding='utf-8')
        self.conn = H2Connection(config=config)
        self.transport = None

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport
        self.conn.initiate_connection()
        self.transport.write(self.conn.data_to_send())

    def data_received(self, data: bytes):
        try:
            events = self.conn.receive_data(data)
        except ProtocolError as e:
            self.transport.write(self.conn.data_to_send())
            self.transport.close()
        else:
            self.transport.write(self.conn.data_to_send())
            for event in events:
                if isinstance(event, RequestReceived):
                    self.request_received(event.headers, event.stream_id)
                elif isinstance(event, ConnectionTerminated):
                    self.transport.write(self.conn.data_to_send())
                    self.transport.close()

            self.transport.write(self.conn.data_to_send())

    def request_received(self, headers: List[Tuple[str, str]], stream_id: int):
        data = b"Hello, world"

        response_headers = (
            (':status', '200'),
            ('content-length', str(len(data))),
        )
        self.conn.send_headers(stream_id, response_headers)
        self.conn.send_data(stream_id, data, end_stream=True)


port = int(sys.argv[1])
loop = asyncio.get_event_loop()
# Each client connection will create a new protocol instance
coro = loop.create_server(H2Protocol, '127.0.0.1', port)
server = loop.run_until_complete(coro)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
