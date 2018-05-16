#!/usr/bin/env python3
import sys
import json
import collections

import trio
import h2.config
import h2.connection
import h2.events


BUFFER_SIZE=65536


async def handle(stream):
    config = h2.config.H2Configuration(client_side=False, header_encoding="utf-8")
    conn = h2.connection.H2Connection(config=config)

    conn.initiate_connection()
    await stream.send_all(conn.data_to_send())

    while True:
        data = await stream.receive_some(BUFFER_SIZE)
        if not data:
            return
        events = conn.receive_data(data)
        for event in events:
            if isinstance(event, h2.events.RequestReceived):
                data = b"Hello, world"
                response_headers = (
                    (':status', '200'),
                    ('content-length', str(len(data))),
                )
                conn.send_headers(event.stream_id, response_headers)
                conn.send_data(event.stream_id, data, end_stream=True)
            elif isinstance(event, h2.events.ConnectionTerminated):
                await stream.send_all(conn.data_to_send())
                return
        await stream.send_all(conn.data_to_send())


async def main(port):
    await trio.serve_tcp(handle, port)

if __name__ == "__main__":
    port = int(sys.argv[1])
    print("Try: $ curl --tlsv1.2 --http2 -k https://localhost:{}/path -d'data'"
          .format(port))
    print("Or open a browser to https://localhost:{}/ and accept all the warnings"
          .format(port))
    trio.run(main, port)
