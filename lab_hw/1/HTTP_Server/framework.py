import socket
import threading
import traceback
from collections import namedtuple
from typing import *

HTTPHeader = namedtuple('HTTPHeader', ['name', 'value'])


class HTTPRequest:
    def __init__(self, rsocket: socket.socket):
        """
            Read RFC7230: https://datatracker.ietf.org/doc/html/rfc7230#section-3

            3.  Message Format
            HTTP-message  = start-line
                              *( header-field CRLF )
                              CRLF
                              [ message-body ]

            start-line     = request-line / status-line

            3.1.1.  Request Line
                request-line   = method SP request-target SP HTTP-version CRLF
        """
        self.socket = rsocket
        # HTTP request fields
        self.headers: List[HTTPHeader] = list()
        self.method: str = ''
        self.request_target: str = ''  # We only need to handle absolute-path here.
        self.http_version: str = ''
        # HTTP request body info
        self.body_length = 0
        self.buffer = bytearray()

    def read_headers(self):
        """
        Read these structures from `self.socket`, format them and fill HTTPRequest object fields.

        HTTP-message   = method SP request-target SP HTTP-version CRLF
                         *( header-field CRLF )
                         CRLF

        :return:
        """
        # TODO: Task1, read from socket and fill HTTPRequest object fields
        flag = True # for too many headers
        while flag:
            data_in_bytes = self.socket.recv(1024)
            data = data_in_bytes.decode()
            datas = data.split('\r\n')
            request_line = datas[0].split(' ')

            self.method = request_line[0]
            self.request_target = request_line[1]
            self.http_version = request_line[2]

            idx = len(datas) # index of the \r\n separate head and body
            try:
                idx = datas.index('')
                flag = False
            except ValueError: # not found the index of '', i.e., no body in this stream
                flag = True
                
            for i in range(1, idx):
                name, value = datas[i].split(': ')
                name, value = name.strip(), value.strip()
                self.headers.append(HTTPHeader(name, value))

            if idx <= len(datas) - 2:
                mess_body = datas[idx+1]
                self.buffer = bytearray(mess_body, encoding='utf-8')
                self.body_length = len(self.buffer)

        # Debug: print http request
        # print(f"{self.method} {self.request_target} {self.http_version}")
        # for h in self.headers:
        #     print(f"{h.name}: {h.value}")
        # print()

    def read_message_body(self) -> bytes:
        # TODO: Task 3: complete read_message_body here
        content_length = self.get_header('Content-Length')
        if content_length is None:
            return bytes()
        if int(content_length) == self.body_length:
            return bytes(self.buffer)

        # left_length = int(content_length)
        # while left_length > 0:
        #     if left_length > 1024:
        #         data_in_bytes = self.socket.recv(1024)
        #         left_length -= 1024
        #     else:
        #         data_in_bytes = self.socket.recv(left_length)
        #         left_length = 0
        #     self.buffer.append(data_in_bytes)
        #     self.body_length += len(data_in_bytes)

        while data_in_bytes := self.socket.recv(1024):
            self.buffer.extend(data_in_bytes)
            self.body_length += len(data_in_bytes)
            content_length -= len(data_in_bytes)
            if content_length <= 0:
                break

        return bytes(self.buffer)

    def get_header(self, key: str) -> Union[str, None]:
        for h in self.headers:
            if h.name == key:
                return h[1]
        return None


class HTTPResponse:
    def __init__(self, wsocket: socket.socket):
        self.socket = wsocket
        """
        status-line = HTTP-version SP status-code SP reason-phrase CRLF
        """
        self.http_version = "HTTP/1.1"
        self.status_code: int = 400
        self.reason: str = 'Bad Request'
        self.headers: List[HTTPHeader] = list()
        # store Header in this format: "Host: 127.0.0.1:8080" -> ('Host', '127.0.0.1')
        self.body: bytes = b''

    def write_all(self):
        """
        set status_line, and write status_line, headers and message body (if exists) into self.socket
        :return:
        """
        # TODO: Task1, construct response from fields and write binary data to socket
        status_line: str = self.http_version + ' ' + str(self.status_code) + ' ' + self.reason + '\r\n'
        
        header_mess: str = ''
        for httpheader in self.headers:
            # print(httpheader.name)
            # print(type(httpheader.name))
            # print(httpheader.value)
            # print(type(httpheader.value))
            header_mess += httpheader.name + ': ' + httpheader.value + '\r\n'
        header_mess += '\r\n'

        http_response = (status_line + header_mess).encode() + self.body
        
        self.socket.sendall(http_response)

    def add_header(self, name: str, value: str):
        self.headers.append(HTTPHeader(name, value))


class HTTPServer:
    def __init__(self, listen_port: int):
        self.listen_addr = "127.0.0.1"
        self.listen_port = listen_port
        self.host = f'{self.listen_addr}:{self.listen_port}'
        self.server_path = "data/"
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.bind((self.listen_addr, self.listen_port))
        self.router: List[Route] = list()
        # Task 3: Store POST data in this bucket.
        self.task3_data: str = ""
        # Task 5: Session Bucket
        self.session: Dict[str, Any] = dict()

    def run(self):
        self.listen_socket.listen()
        print(f"Server start listening at http://{self.host}/")
        while True:
            client, src = self.listen_socket.accept()
            print(f"[Server] Server accept connection from {src[0]}:{src[1]}")
            threading.Thread(target=self.__client_run__, args=[client, src]).run()

    def register_handler(self, path: str, handler, allowed_methods=None):
        if allowed_methods is None:
            allowed_methods = ['GET', 'HEAD', 'POST']
        self.router.append(Route(path, allowed_methods, handler))

    def __client_run__(self, client_socket: socket.socket, source_address):
        try:
            request = HTTPRequest(client_socket)
            request.read_headers()
            host = request.get_header("Host")
            response = HTTPResponse(client_socket)
            # To simplify the implementation of the HTTP server, we require clients not to reuse TCP connections
            response.add_header("Connection", "close")
            if host == self.host:
                path = request.request_target.split('?', maxsplit=1)[0]
                route = self.__match_route__(path)
                if route:
                    if request.method in route.allowed_methods:
                        route.handler(self, request, response)
                    else:
                        (response.status_code, response.reason) = 405, "Method Not Allowed"
                else:
                    (response.status_code, response.reason) = 404, "Not Found"
            else:
                (response.status_code, response.reason) = 400, "Bad Request"
            response.write_all()
        except Exception:
            print(traceback.format_exc())
        finally:
            client_socket.close()
            print(f"[Server] Connection from {source_address} closed.")

    def __match_route__(self, path: str):
        """
        Match Route
        :param path: Request URL
        :return: matched Route instance
        """
        # match path
        ps = path.split('/')
        matched_len, matched_route = 0, None
        for route in self.router:
            rps = route.path.split('/')
            cnt = 0
            while cnt < min(len(rps), len(ps)):
                if rps[cnt] != ps[cnt]:
                    break
                cnt += 1
            if cnt > matched_len and cnt == len(rps):
                matched_len, matched_route = cnt, route
        return matched_route


class Route(NamedTuple):
    path: str
    allowed_methods: List[str]
    handler: Callable[[HTTPServer, HTTPRequest, HTTPResponse], None]
