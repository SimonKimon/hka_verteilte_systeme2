import sys
import time
import zmq
import constPipe
import hashlib

# Mapper-ID als Kommandozeilenargument übergeben
me = str(sys.argv[1])

context = zmq.Context()

# PULL-Socket empfängt Sätze vom Splitter
pull = context.socket(zmq.PULL)
pull.connect("tcp://" + constPipe.SPLITTER_HOST + ":" + constPipe.SPLITTER_PORT)

# PUSH-Socket zu Reducer 1
push1 = context.socket(zmq.PUSH)
push1.connect("tcp://" + constPipe.REDUCER1_HOST + ":" + constPipe.REDUCER1_PORT)

# PUSH-Socket zu Reducer 2
push2 = context.socket(zmq.PUSH)
push2.connect("tcp://" + constPipe.REDUCER2_HOST + ":" + constPipe.REDUCER2_PORT)

time.sleep(1)
print(f"Mapper {me} started")

def stable_hash(word):
    return int(hashlib.md5(word.encode()).hexdigest(), 16)

while True:
    # Satz vom Splitter empfangen
    sentence = pull.recv_string()
    print(f"Mapper {me} received: {sentence}")

    words = sentence.split()
    for word in words:
        if stable_hash(word) % 2 == 0: # hash(word) % 2 bestimmt den Reducer
            push1.send_string(word)    # Wort an Reducer 1 schicken
        else:
            push2.send_string(word)    # Wort an Reducer 2 schicken