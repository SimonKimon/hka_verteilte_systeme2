import rpc
import logging
import time

from context import lab_logging

lab_logging.setup(stream_level=logging.INFO)

cl = rpc.Client()
cl.run()

base_list = rpc.DBList({'foo'})
result_list = cl.append('bar', base_list)

i = 0
while not cl.event.is_set():
    print(f"Client arbeitet... {i}")
    time.sleep(1)
    i+=1

cl.stop()
