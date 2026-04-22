import rpc
import logging
import time
import threading

from context import lab_logging

lab_logging.setup(stream_level=logging.INFO)

cl = rpc.Client()
cl.run()

base_list = rpc.DBList({'foo'})


callback_only_done = threading.Event()


def on_result_callback_only(result_list):
	print("[callback-only] Callback received: {}".format(result_list.value))
	callback_only_done.set()


def on_result_with_handle(result_list):
	print("[callback+handle] Callback received: {}".format(result_list.value))


print("\n--- Demo 1: Callback-only (kein AsyncResult im User-Code) ---")
cl.append_callback_only('bar', base_list, callback=on_result_callback_only)

for i in range(10):
	print("[callback-only] Client doing other work... {}".format(i + 1))
	time.sleep(1)

# Ensure the program doesn't exit before the callback arrives
callback_only_done.wait(timeout=30)

print("\n--- Demo 2: Callback + Handle (AsyncResult + optional wait) ---")
async_result = cl.append('baz', base_list, callback=on_result_with_handle)

for i in range(10):
	print("[callback+handle] Client doing other work... {}".format(i + 1))
	time.sleep(1)
	


result_list = async_result.wait()

print("[callback+handle] Result via wait(): {}".format(result_list.value))

cl.stop()
