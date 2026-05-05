import constRPC
import threading
import time


from context import lab_channel


class DBList:
    def __init__(self, basic_list):
        self.value = list(basic_list)

    def append(self, data):
        self.value = self.value + [data]
        return self


class Client:
    def __init__(self):
        self.chan = lab_channel.Channel()
        self.client = self.chan.join('client')
        self.server = None

    def run(self):
        self.chan.bind(self.client)
        self.server = self.chan.subgroup('server')

    def stop(self):
        self.chan.leave('client')

    def wait_for_result(self, callback):
        # wait for response: [0] Absender, [1] Payload
        result = self.chan.receive_from(self.server)
        callback(result[1]) # handle_result Aufruf

    def append(self, data, db_list, callback):
        assert isinstance(db_list, DBList)
        msglst = (constRPC.APPEND, data, db_list)  # message payload
        self.chan.send_to(self.server, msglst)  # send msg to server

        # Auf ACK warten
        ack = self.chan.receive_from(self.server)
        assert ack[1] == constRPC.OK, "Kein ACK vom Server erhalten" # AssertionError
        print("Client: ACK erhalten. Server verarbeitet den Request.")

        t = threading.Thread(target=self.wait_for_result, args=(callback, ))
        t.daemon = True  # Thread beendet automatisch, wenn das Hauptprogramm endet
        t.start()       # Startet den Thread, wait_for_result läuft parallel zum Hauptprogramç



class Server:
    def __init__(self):
        self.chan = lab_channel.Channel()
        self.server = self.chan.join('server')
        self.timeout = 3 # wartet max 3 Sekunden, sonst return None

    @staticmethod
    def append(data, db_list):
        assert isinstance(db_list, DBList)  # - Make sure we have a list
        return db_list.append(data)

    def run(self):
        self.chan.bind(self.server)
        while True:
            msgreq = self.chan.receive_from_any(self.timeout)  # wait for any request
            if msgreq is not None:
                client = msgreq[0]  # see who is the caller
                msgrpc = msgreq[1]  # fetch call & parameters
                # check what is being requested
                if constRPC.APPEND == msgrpc[0]:
                    # Set mit Empfängern und Payload
                    self.chan.send_to({client}, constRPC.OK)
                    print("Server: ACK gesendet. Simuliere 10s.")
                    time.sleep(10)
                    result = self.append(msgrpc[1], msgrpc[2])  # do local call
                    self.chan.send_to({client}, result)  # return response
                    print("Server: Ergebnis gesendet.")
                else:
                    pass  # unsupported request, simply ignore
