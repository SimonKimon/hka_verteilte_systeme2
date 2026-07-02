# Labor 6 - Einfache 3PC-Implementierung

Dieses Verzeichnis enthaelt eine **moeglichst einfache**, additive Umsetzung des
Three-Phase-Commit-Protokolls (3PC) auf Basis des vorhandenen 2PC-Stils.

Ziel dieser Loesung:
- den **grundlegenden 3PC-Zustandsautomaten** sauber abbilden
- dabei die Komplexitaet niedrig halten
- den vorhandenen 2PC-Code unangetastet lassen
- Koordinatorausfall mit **deterministischer Neuwahl** behandeln

## Enthaltene Dateien

- `3pc.py`
  - Startskript der Demo
  - startet `n` Teilnehmer + 1 Koordinator als Prozesse
- `coordinator.py`
  - zentraler 3PC-Koordinator
  - implementiert Phasen 1a, 2a, 3a
- `participant.py`
  - 3PC-Teilnehmer
  - implementiert Phasen 1b, 2b, 3b
- `const3PC.py`
  - alle Protokoll-Nachrichten und Konstanten
- `stablelog.py`
  - persistentes Zustands-Logging in Dateien
- `context.py`
  - importiert `lab_channel` und `lab_logging` aus `lib/`

## Protokollabbildung (wo ist was umgesetzt)

### Koordinator (`coordinator.py`)

1. **INIT -> WAIT**
   - in `run()` wird nach Start in `WAIT` gewechselt
   - `VOTE_REQUEST` wird an alle Teilnehmer gesendet

2. **WAIT (Votes sammeln)**
   - alle Antworten werden gelesen
   - bei Timeout oder `VOTE_ABORT` -> `ABORT` + `GLOBAL_ABORT`
   - nur wenn alle `VOTE_COMMIT` senden, geht es weiter

3. **WAIT -> PRECOMMIT**
   - Koordinator sendet `PREPARE_COMMIT` an alle Teilnehmer

4. **PRECOMMIT (READY_COMMIT sammeln)**
   - Antworten `READY_COMMIT` werden gesammelt
   - in dieser einfachen Variante fuehrt ein Timeout hier dennoch zum Commit
     (entspricht dem Gedanken, dass PRECOMMIT bereits nur noch in Commit fuehrt)

5. **PRECOMMIT -> COMMIT**
   - Koordinator sendet `GLOBAL_COMMIT`

### Teilnehmer (`participant.py`)

1. **INIT (auf Start warten)**
   - wartet auf `VOTE_REQUEST`
   - Timeout vor Protokollstart -> `ABORT`

2. **Lokale Transaktion**
   - `_do_work()` simuliert Erfolg/Misserfolg
   - bei Misserfolg: `VOTE_ABORT`, Zustand `ABORT`, Ende
   - bei Erfolg: Zustand `READY`, `VOTE_COMMIT`

3. **READY (Phase 2b)**
   - wartet auf Nachricht vom Koordinator
   - `GLOBAL_ABORT` oder Timeout -> `ABORT`
   - `PREPARE_COMMIT` -> `PRECOMMIT` + `READY_COMMIT`

4. **PRECOMMIT (Phase 3b)**
   - wartet auf `GLOBAL_COMMIT`
   - `GLOBAL_COMMIT` oder Koordinatorausfall -> Terminierungsprotokoll

### Terminierung bei Koordinatorausfall

Ist der Koordinator im Teilnehmer-Timeout nicht erreichbar, wird folgende
einfache Terminierung ausgefuehrt:

1. Alle Teilnehmer bestimmen **deterministisch** den neuen Koordinator:
   Teilnehmer mit kleinster numerischer ID.
2. Nicht-Leader senden ihren aktuellen Zustand an den Leader.
3. Leader sammelt Zustaende und entscheidet:
   - wenn mindestens ein `PRECOMMIT` oder `COMMIT` gesehen wird -> `GLOBAL_COMMIT`
   - sonst -> `GLOBAL_ABORT`
4. Leader sendet die globale Entscheidung an alle Teilnehmer.

Damit wird die in 2PC moegliche Blockade in der READY-Situation vermieden.

## Vereinfachungen (bewusst)

Diese Loesung ist absichtlich minimal gehalten:
- kein Wiederanlauf/Recovery abgestuerzter Prozesse
- kein Umgang mit Nachrichtenverlust
- kein komplexer verteilter Wahlalgorithmus (nur kleinste ID)

Damit entspricht die Loesung der Mindestanforderung (3PC-Zustandsautomat) mit
leichtem, timeout-basiertem Fehlverhalten, aber ohne zusaetzliche Komplexitaet.

## Ausfuehrung

Voraussetzung: Redis muss laufen.

```bash
cd lab6/3pc
pipenv run python 3pc.py
```

Die Zustandswechsel werden auf der Konsole und in `stablelogs/*.log` sichtbar.
