"""
Client and server using classes
"""

import logging
import socket

import const_cs
from context import lab_logging

# init loging channels for the lab
lab_logging.setup(stream_level=logging.INFO)

# pylint: disable=logging-not-lazy, line-too-long


class Server:
    """ The server """
    _logger = logging.getLogger("vs2lab.lab1.clientserver.Server")
    _serving = True

    # In-Memory Telefon-Datenbank als Dictionary
    phonebook = {
        "Radek":    "0721-111111",
        "Pius":    "0721-222222",
        "Joel":     "0721-333333",
        "Philipp":  "0721-444444",
        "Simon":    "0721-555555"
    }

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # prevents errors due to "addresses in use"
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((const_cs.HOST, const_cs.PORT))
        self.sock.settimeout(3)  # time out in order not to block forever
        self._logger.info("Server bound to socket " + str(self.sock))

    def serve(self):
        """ Serve echo """
        self.sock.listen(1)
        # as long as _serving (checked after connections or socket timeouts)
        while self._serving:
            try:
                # pylint: disable=unused-variable
                # returns new socket and address of client
                (connection, address) = self.sock.accept()
                while True:  # forever
                    data = connection.recv(1024).decode(
                        'ascii')  # receive data from client
                    if not data:
                        break  # stop if client stopped

                    self._logger.info("Request: " + data)

                    # GET
                    if data.startswith("GET:"):
                        name = data[4:]  # take all after from 4
                        result = self.phonebook.get(name, "NOT FOUND")
                        connection.send(result.encode('ascii'))
                        self._logger.info("GET " + name + " = " + result)

                    # GETALL
                    elif data == "GETALL":
                        result = str(self.phonebook)
                        connection.send(result.encode('ascii'))
                        self._logger.info(
                            "GETALL = " + str(len(self.phonebook)) + " Einträge")

                connection.close()  # close the connection
            except socket.timeout:
                pass  # ignore timeouts
        self.sock.close()
        self._logger.info("Server down.")


class Client:
    """ The client """
    logger = logging.getLogger("vs2lab.a1_layers.clientserver.Client")

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((const_cs.HOST, const_cs.PORT))
        self.logger.info("Client connected to socket " + str(self.sock))

    def get(self, name):
        self.sock.send(("GET:" + name).encode('ascii'))
        result = self.sock.recv(1024).decode('ascii')
        self.logger.info("GET(" + name + ") = " + result)
        return result

    def getall(self):
        self.sock.send("GETALL".encode('ascii'))
        result = self.sock.recv(1024).decode('ascii')
        self.logger.info("GETALL result erhalen")
        return result

    def call(self, msg_in="Hello, world"):
        """ Call server """
        self.sock.send(msg_in.encode('ascii'))  # send encoded string as data
        data = self.sock.recv(1024)  # receive the response
        msg_out = data.decode('ascii')
        print(msg_out)  # print the result
        self.sock.close()  # close the connection
        self.logger.info("Client down.")
        return msg_out

    def close(self):
        """ Close socket """
        self.sock.close()
