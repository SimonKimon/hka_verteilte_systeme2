import rpc
import logging
import time

from context import lab_logging

lab_logging.setup(stream_level=logging.INFO)

cl = rpc.Client()
cl.run()

base_list = rpc.DBList({'foo'})

# Callback-Funktion zur Verarbeitung des Ergebnisses


def handle_result(result):  # Wird aufgerufen, erst wenn das Ergebnis vom Server kommt
    print("\nClient: Callback aufgerufen. Ergebnis vom Server erhalten.")
    print("Result: {}".format(result.value))


# Asynchronen RPC-Aufruf starten
cl.append('bar', base_list, callback=handle_result)

# Client ist aktiv während er wartet
print("Client: Request gesendet. Client macht weiter.")
for i in range(1, 12):
    time.sleep(1)
    print("Client: Noch aktiv... ({}/11s)".format(i))

# result_list = cl.append('bar', base_list)
# print("Result: {}".format(result_list.value))

cl.stop()
