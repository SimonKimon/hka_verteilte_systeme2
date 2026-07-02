import sys
import zmq
import constPipe

# Reducer-ID als Argument
me = str(sys.argv[1])

context = zmq.Context()

# PULL-Socket empfängt Wörter von allen Mappern
pull = context.socket(zmq.PULL)

# Jeder Reducer bindet seinen eigenen Port
if me == "1":
    pull.bind("tcp://" + constPipe.REDUCER1_HOST + ":" + constPipe.REDUCER1_PORT)
else:
    pull.bind("tcp://" + constPipe.REDUCER2_HOST + ":" + constPipe.REDUCER2_PORT)

print(f"Reducer {me} started")

# Dictionary zum Zählen der Wörter (Key: Wort, Value: Anzahl)
counts = {}

while True:
     # Wort von einem Mapper empfangen
    word = pull.recv_string()
    
    counts[word] = counts.get(word, 0) + 1
    print(f"{counts[word]}.mal '{word}'")