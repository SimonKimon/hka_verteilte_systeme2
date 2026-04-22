import constRPC

import threading
import time
from typing import Optional
import uuid

from context import lab_channel


class DBList:
    def __init__(self, basic_list):
        self.value = list(basic_list)

    def append(self, data):
        self.value = self.value + [data]
        return self


class AsyncResult:
    def __init__(self):
        self._done = threading.Event()
        self._lock = threading.Lock()
        self._value = None
        self._exception = None

    def set_result(self, value):
        with self._lock:
            if self._done.is_set():
                return
            self._value = value
            self._exception = None
            self._done.set()

    def set_exception(self, exc: Exception):
        with self._lock:
            if self._done.is_set():
                return
            self._exception = exc
            self._done.set()

    def done(self) -> bool:
        return self._done.is_set()

    def wait(self, timeout: Optional[float] = None):
        if not self._done.wait(timeout):
            raise TimeoutError('RPC result timeout')
        with self._lock:
            if self._exception is not None:
                raise self._exception
            return self._value


class Client:
    def __init__(self):
        self.chan = lab_channel.Channel()
        self.client = self.chan.join('client')
        self.server = None

        self._stop_event = threading.Event()
        self._recv_thread = None
        self._lock = threading.Lock()
        # call_id -> {'ack': Event, 'result': AsyncResult, 'callback': callable|None}
        self._pending = {}

    def run(self):
        self.chan.bind(self.client)
        self.server = self.chan.subgroup('server')

        # Dedicated receiver thread: waits for ACK/RESULT and triggers callbacks.
        self._recv_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self._recv_thread.start()

    def stop(self):
        self._stop_event.set()
        if self._recv_thread is not None:
            self._recv_thread.join(timeout=2)
        self.chan.leave('client')

    def _receiver_loop(self):
        while not self._stop_event.is_set():
            msg = self.chan.receive_from_any(timeout=1)
            if msg is None:
                continue

            sender, payload = msg
            if not isinstance(payload, tuple) or len(payload) < 2:
                continue

            msg_type = payload[0]
            call_id = payload[1]

            with self._lock:
                pending = self._pending.get(call_id)

            if pending is None:
                continue

            if msg_type == constRPC.ACK:
                pending['ack'].set()
            elif msg_type == constRPC.RESULT:
                result_value = None
                if len(payload) < 3:
                    pending['result'].set_exception(ValueError('Malformed RESULT message'))
                else:
                    result_value = payload[2]
                    pending['result'].set_result(result_value)

                cb = pending.get('callback')
                if cb is not None and result_value is not None:
                    try:
                        cb(result_value)
                    except Exception as exc:
                        pending['result'].set_exception(exc)

                with self._lock:
                    self._pending.pop(call_id, None)
            elif msg_type == constRPC.ERROR:
                if len(payload) >= 3 and isinstance(payload[2], Exception):
                    pending['result'].set_exception(payload[2])
                else:
                    pending['result'].set_exception(RuntimeError('RPC ERROR'))
                with self._lock:
                    self._pending.pop(call_id, None)
            else:
                # Unknown message type; ignore
                pass

    def append(self, data, db_list, callback=None):
        assert isinstance(db_list, DBList)

        call_id = uuid.uuid4().hex
        ack_event = threading.Event()
        async_result = AsyncResult()

        with self._lock:
            self._pending[call_id] = {'ack': ack_event, 'result': async_result, 'callback': callback}

        # message payload: (CALL, call_id, operation, args...)
        msglst = (constRPC.CALL, call_id, constRPC.APPEND, data, db_list)

        # Re-query server subgroup each call (start order / restarts)
        server_set = self.chan.subgroup('server')
        if not server_set:
            with self._lock:
                self._pending.pop(call_id, None)
            raise RuntimeError('No RPC server available (subgroup "server" is empty). Start runsrv.py first.')

        self.chan.send_to(server_set, msglst)

        # Wait for ACK (server accepted request) - should be quick.
        if not ack_event.wait(timeout=5):
            with self._lock:
                self._pending.pop(call_id, None)
            raise TimeoutError('RPC ACK timeout')

        # Compatibility: if no callback is provided, behave like synchronous call.
        if callback is None:
            return async_result.wait(timeout=None)

        return async_result

    def append_callback_only(self, data, db_list, callback):
        """Fire-and-forget API: result is delivered only via callback.

        Internally we still keep an AsyncResult to track completion, but callers
        don't need to store it.
        """
        self.append(data, db_list, callback=callback)


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
                msgrpc = msgreq[1]  # fetch call & parameters
                if isinstance(msgrpc, tuple) and len(msgrpc) >= 3 and msgrpc[0] == constRPC.CALL:
                    call_id = msgrpc[1]
                    operation = msgrpc[2]

                    # Immediately ACK the request
                    self.chan.send_to({client}, (constRPC.ACK, call_id))

                    # Simulate long execution time
                    time.sleep(10)

                    if operation == constRPC.APPEND and len(msgrpc) == 5:
                        result = self.append(msgrpc[3], msgrpc[4])
                        self.chan.send_to({client}, (constRPC.RESULT, call_id, result))
                    else:
                        self.chan.send_to({client}, (constRPC.ERROR, call_id, RuntimeError('Unsupported request')))
                else:
                    pass  # unsupported request, simply ignore
