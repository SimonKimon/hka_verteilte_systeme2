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
        self.event = threading.Event()

    def run(self):
        self.chan.bind(self.client)
        self.server = self.chan.subgroup('server')

    def stop(self):
        self.chan.leave('client')

    def append(self, data, db_list):
        assert isinstance(db_list, DBList)
        msglst = (constRPC.APPEND, data, db_list)  # message payload
        self.chan.send_to(self.server, msglst)  # send msg to server

        response = self.chan.receive_from(self.server)
        ack = response[1]
        print(f"ACK erhalten")

        thread = threading.Thread(
            target=self.wait_for_server_answer, #????????????
            args=(self.callback,) #????????????
        )
        thread.start()


    def wait_for_server_answer(self, callback):
        data = self.chan.receive_from(self.server) # Blockiert bis Ergebnis kommt 
        callback(data)
    
    def callback(self, data):
        db_list = data[1]
        print(f"Ergebnis erhalten:")
        for item in db_list.value:
            print(f"- {item}")
        self.event.set() 


class Server:
    def __init__(self):
        self.chan = lab_channel.Channel()
        self.server = self.chan.join('server')
        self.timeout = 3

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

                ack = {
                    "type": "ACK"
                }
                self.chan.send_to({client}, ack)
                time.sleep(1)
                msgrpc = msgreq[1]  # fetch call & parameters
                if constRPC.APPEND == msgrpc[0]:  # check what is being requested
                    result = self.append(msgrpc[1], msgrpc[2])  # do local call
                    self.chan.send_to({client}, result)  # return response
                else:
                    pass  # unsupported request, simply ignore
