import sys
import io
import json
import asyncio
import collections
import h2.connection
import h2.events
import h2.errors

BUF_SIZE = 2048

async def handle(reader, writer):
    config = h2.config.H2Configuration(client_side=False, header_encoding="utf-8")
    conn = h2.connection.H2Connection(config=config)
    print("initializing")
    conn.initiate_connection()
    writer.write(conn.data_to_send())
    await writer.drain()
    try:
        while True:
            data = await reader.read(BUFFER_SIZE)
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
                    return
                writer.write(conn.data_to_send())
                await writer.drain()
    finally:
        writer.write(conn.data_to_send())
        await writer.drain()
        writer.close()
 

def main():
    port = int(sys.argv[1])
    loop = asyncio.get_event_loop()
    task = asyncio.start_server(lambda r, w: handle(r, w), host="0.0.0.0", port=port, loop=loop, ssl=None)
    server = loop.run_until_complete(task)
    print(f"Listening on {server.sockets}")
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()

if __name__ == "__main__":
    main()
