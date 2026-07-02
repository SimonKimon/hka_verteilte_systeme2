import logging
import random

import stablelog

from const3PC import VOTE_REQUEST, PREPARE_COMMIT, GLOBAL_COMMIT, GLOBAL_ABORT
from const3PC import VOTE_COMMIT, VOTE_ABORT, READY_COMMIT
from const3PC import TIMEOUT


class Coordinator:

    def __init__(self, chan):
        self.channel = chan
        self.coordinator = self.channel.join('coordinator')
        self.participants = []
        self.logger = logging.getLogger('vs2lab.lab6.3pc.Coordinator')
        self.stable_log = stablelog.create_log('coordinator-' + self.coordinator)
        self.state = 'NEW'

    def _enter_state(self, state):
        self.stable_log.info(state)
        self.logger.info('Coordinator %s entered state %s.', self.coordinator, state)
        self.state = state

    def _crash(self):
        self.logger.warning(
            'Coordinator %s crashed in state %s.',
            self.coordinator,
            self.state,
        )
        return 'Coordinator {} crashed in state {}.'.format(self.coordinator, self.state)

    def init(self):
        self.channel.bind(self.coordinator)
        self.participants = self.channel.subgroup('participant')
        self._enter_state('INIT')

    def run(self):
        # Optional crash simulation before protocol start.
        if random.random() > 9 / 10:
            return self._crash()

        # Phase 1a: ask all participants for vote
        self._enter_state('WAIT')
        self.channel.send_to(self.participants, VOTE_REQUEST)

        # Crash in WAIT is the interesting case for leader-based termination.
        if random.random() > 3 / 4:
            return self._crash()

        yet_to_receive = set(self.participants)
        while len(yet_to_receive) > 0:
            msg = self.channel.receive_from(self.participants, TIMEOUT)

            # In WAIT: timeout or any VOTE_ABORT forces GLOBAL_ABORT.
            if (not msg) or msg[1] == VOTE_ABORT:
                reason = 'timeout' if not msg else 'VOTE_ABORT from ' + msg[0]
                self._enter_state('ABORT')
                self.channel.send_to(self.participants, GLOBAL_ABORT)
                return (
                    'Coordinator {} terminated in state ABORT. Reason: {}.'
                    .format(self.coordinator, reason)
                )

            assert msg[1] == VOTE_COMMIT
            yet_to_receive.discard(msg[0])

        # Phase 2a: all voted commit -> PRECOMMIT
        self._enter_state('PRECOMMIT')
        self.channel.send_to(self.participants, PREPARE_COMMIT)

        # Crash in PRECOMMIT should be resolved to COMMIT by participants.
        if random.random() > 2 / 3:
            return self._crash()

        yet_to_receive = set(self.participants)
        while len(yet_to_receive) > 0:
            msg = self.channel.receive_from(self.participants, TIMEOUT)

            # If a participant does not answer READY_COMMIT in PRECOMMIT phase,
            # we still commit in this simplified model (participant failure case).
            if not msg:
                break

            if msg[1] == READY_COMMIT:
                yet_to_receive.discard(msg[0])

        # Phase 3a: finish protocol with global commit
        self._enter_state('COMMIT')
        self.channel.send_to(self.participants, GLOBAL_COMMIT)
        return 'Coordinator {} terminated in state COMMIT.'.format(self.coordinator)
