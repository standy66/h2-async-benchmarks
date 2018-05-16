import io
import sys
import json
import asyncio
import collections
import h2.connection
import h2.events
import h2.errors

ReceivedData = collections.namedtuple("ReceivedData", ("headers", "data"))

class Server:
    BUF_SIZE = 1024

    def __init__(self, loop):
        config = h2.config.H2Configuration(client_side=False, header_encoding="utf-8")
        self.connection = h2.connection.H2Connection(config=config)
        self.loop = loop
        self.received_data = {}

    def request_received(self, event):
        headers = collections.OrderedDict(event.headers)
        self.received_data[event.stream_id] = ReceivedData(headers, io.BytesIO())

    def data_received(self, event):
        try:
            self.received_data[event.stream_id].data.write(event.data)
        except KeyError:
            self.connection.reset_stream(event.stream_id, h2.errors.ErrorCodes.PROTOCOL_ERROR)
        else:
            self.connection.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
 
    def stream_ended(self, event):
        stream_id = event.stream_id
        response_body = json.dumps({
            "headers": self.received_data[stream_id].headers,
            "body": self.received_data[stream_id].data.getvalue().decode("utf-8")
        }, indent=4).encode("utf-8")

        response_headers = [
            (":status", "200"),
            ("content-type", "application/json"),
            ("content-length", str(len(response_body))),
            ("server", "python-asyncio-h2"),
        ]

        self.connection.send_headers(stream_id=stream_id, headers=response_headers)
        self.connection.send_data(stream_id=stream_id, data=response_body, end_stream=True)

    async def __call__(self, reader, writer):
        try:
            self.connection.initiate_connection()
            writer.write(self.connection.data_to_send())
            await writer.drain()
            
            while True:
                data = await reader.read(Server.BUF_SIZE)
                if not data:
                    break
                try:
                    events = self.connection.receive_data(data)
                except h2.exceptions.ProtocolError as e:
                    return
                else:
                    writer.write(self.connection.data_to_send())
                    await writer.drain()
                    for event in events:
                        # print(event)
                        if isinstance(event, h2.events.RemoteSettingsChanged):
                            pass
                        elif isinstance(event, h2.events.SettingsAcknowledged):
                            pass
                        elif isinstance(event, h2.events.RequestReceived):
                            self.request_received(event)
                        elif isinstance(event, h2.events.DataReceived):
                            self.data_received(event)
                        elif isinstance(event, h2.events.StreamEnded):
                            self.stream_ended(event)
                        elif isinstance(event, h2.events.ConnectionTerminated):
                            return
                        else:
                            self.connection.close_connection(h2.errors.ErrorCodes.PROTOCOL_ERROR)
                            return
                        writer.write(self.connection.data_to_send())
                        await writer.drain()
        except:
            print("{!r}".format(sys.exc_info()))
        finally:
            writer.write(self.connection.data_to_send())
            await writer.drain()
            writer.close()


def main():
    port = int(sys.argv[1])
    loop = asyncio.get_event_loop()
    task = asyncio.start_server(lambda r, w: Server(loop)(r, w), host="0.0.0.0", port=port, loop=loop, ssl=None)
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
