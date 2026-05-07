import time
import zmq
import constPipe

sentences = [
    "Die Katze frisst Pizza",
    "Bayern verliert aber die Pizza schmeckt",
    "Die Pizza schmeckt lecker",
    "Morgen spielt Bayern und PSG",
    "Bayern hat letzens 4:5 verloren",
    "Student empfindet die Pizza lecker",
    "Wir lieben verteilte Systeme"
]

context = zmq.Context()

# PUSH-Socket verteilt Sätze mit Round-Robinan an alle Mapper
push = context.socket(zmq.PUSH) 
push.bind("tcp://" + constPipe.SPLITTER_HOST + ":" + constPipe.SPLITTER_PORT) # how and where to connect

time.sleep(1)  # wait for mappers to connect
print("Splitter: sending sentences")

for sentence in sentences:
    push.send_string(sentence)
    print("Splitter sent:", sentence)