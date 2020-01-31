import requests
import socket
import socketserver
import ssl
import logging
import io
import urllib.parse

class MyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # TODO: reconstruct these code, as it duplicates in intercept_headers
        # extracting headers from raw socket
        data = io.BytesIO()
        headers = b''
        while True:
            chunk = self.request.recv(1024)
            data.write(chunk)
            pos = chunk.find(b'\r\n\r\n')
            if pos != -1:
                data.flush()
                data.seek(0)
                headers = data.read(pos + 4)
                break

        headers = self.parse_headers(headers)
        print(headers)

        headers = self.intercept_headers('https://user.gamer.com.tw/login.php')
        print(headers)

        # exit() # TODO: figure out why shutdown doesn't work
        # self.server.shutdown()

    def parse_headers(self, raw_headers):
        headers = {}
        for line in raw_headers.decode().split('\r\n')[1:]:
            if line:
                p = line.find(':')
                headers[ line[:p] ] = line[p+1:].strip()
        return headers

    def intercept_headers(self, url):
        u = urllib.parse.urlsplit(url)
        with socket.create_connection((u.hostname, 443)) as s:
            context = ssl.create_default_context()
            s.settimeout(10)

            with context.wrap_socket(s, server_hostname=u.hostname) as ss:
                cmd = b'\r\n'.join(map(lambda x: x.encode(), [
                    f'GET {u.path} HTTP/1.1',
                    f'Host: {u.hostname}',
                    'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
                    'Accept: */*',
                    '', '',
                ]))
                ss.send(cmd)

                data = io.BytesIO()
                headers = b''
                while True:
                    chunk = ss.recv(1024)
                    self.request.sendall(chunk)

                    if not headers:
                        data.write(chunk)
                        pos = chunk.find(b'\r\n\r\n')
                        if pos != -1:
                            data.flush()
                            data.seek(0)
                            headers = data.read(pos + 4)

                    if len(chunk) <= 0 or chunk[-5:] == b'0\r\n\r\n':
                        break

                return self.parse_headers(headers)


def main():
    logging.basicConfig(level='DEBUG')

    with socketserver.TCPServer(('127.0.0.1', 8000), MyHandler) as ss:
        ss.serve_forever()

main()
