import logging
import random

import stablelog

from const3PC import VOTE_REQUEST, PREPARE_COMMIT, GLOBAL_COMMIT, GLOBAL_ABORT
from const3PC import VOTE_COMMIT, VOTE_ABORT, READY_COMMIT
from const3PC import NEED_STATE, STATE_REPORT
from const3PC import LOCAL_SUCCESS, LOCAL_ABORT
from const3PC import TIMEOUT


class Participant:
    def __init__(self, chan):
        self.channel = chan
        self.participant = self.channel.join('participant')
        self.coordinator = set()
        self.logger = logging.getLogger('vs2lab.lab6.3pc.Participant')
        self.stable_log = stablelog.create_log('participant-' + self.participant)
        self.state = 'NEW'

    @staticmethod
    def _do_work():
        # Simulate local transaction success/failure.
        return LOCAL_ABORT if random.random() > 2 / 3 else LOCAL_SUCCESS

    def _enter_state(self, state):
        self.stable_log.info(state)
        self.logger.info('Participant %s entered state %s.', self.participant, state)
        self.state = state

    def init(self):
        self.channel.bind(self.participant)
        self.coordinator = self.channel.subgroup('coordinator')
        self._enter_state('INIT')

    @staticmethod
    def _leader_of(participants):
        """Deterministic leader election: participant with smallest numeric id."""
        return min(participants, key=lambda p: int(p))

    @staticmethod
    def _termination_decision(self_state):
        if self_state in {'PRECOMMIT', 'COMMIT'}:
            return GLOBAL_COMMIT

        if self_state in {'WAIT', 'READY', 'ABORT', 'INIT', 'NEW'}:
            return GLOBAL_ABORT

        raise AssertionError(f'Unexpected leader state {self_state}')
    


    def _participant_termination_after_coordinator_failure(self):
        """
        Handle coordinator crash by deterministic leader election.

        All active participants compute the same leader (smallest id).
        The leader collects state reports and broadcasts the final decision.
        """
        all_participants = self.channel.subgroup('participant')
        leader = self._leader_of(all_participants)

        self.logger.info(
            'Coordinator failure detected by participant %s. Elected new coordinator: %s.',
            self.participant,
            leader,
        )

        # I am not leader: report my local state and wait for final decision.
        if self.participant != leader:
            self.channel.send_to({leader}, (STATE_REPORT, self.state))

            while True:
                msg = self.channel.receive_from(all_participants, TIMEOUT * 3)

                if not msg:
                    # Fallback under partial synchrony: PRECOMMIT implies commit,
                    # all earlier states abort.
                    return GLOBAL_COMMIT if self.state == 'PRECOMMIT' else GLOBAL_ABORT

                payload = msg[1]
                if payload in [GLOBAL_COMMIT, GLOBAL_ABORT]:
                    return payload

                if isinstance(payload, tuple) and payload[0] == NEED_STATE:
                    self.channel.send_to({msg[0]}, (STATE_REPORT, self.state))

        # I am leader: request reports, decide, broadcast outcome.
        others = set(all_participants) - {self.participant}
        self.channel.send_to(others, (NEED_STATE, self.state))

        observed_states = {self.state}
        yet_to_receive = set(others)

        while len(yet_to_receive) > 0:
            msg = self.channel.receive_from(all_participants, TIMEOUT * 2)
            if not msg:
                break

            sender, payload = msg
            if isinstance(payload, tuple) and payload[0] == STATE_REPORT:
                observed_states.add(payload[1])
                yet_to_receive.discard(sender)
            elif isinstance(payload, tuple) and payload[0] == NEED_STATE:
                # Concurrent requests are possible; answer with own state.
                self.channel.send_to({sender}, (STATE_REPORT, self.state))

        decision = self._termination_decision(self.state)
        self.logger.info(
            'New coordinator %s collected states %s and broadcasts %s.',
            self.participant,
            sorted(observed_states),
            decision,
        )
        self.channel.send_to(all_participants, decision)
        return decision

    def run(self):
        # Phase 1b: wait for VOTE_REQUEST and do local work
        msg = self.channel.receive_from(self.coordinator, TIMEOUT)
        if not msg:
            self._enter_state('ABORT')
            return (
                'Participant {} terminated in state ABORT. '
                'Reason: coordinator timeout before VOTE_REQUEST.'
                .format(self.participant)
            )

        assert msg[1] == VOTE_REQUEST

        local_decision = self._do_work()
        if local_decision == LOCAL_ABORT:
            self.channel.send_to(self.coordinator, VOTE_ABORT)
            self._enter_state('ABORT')
            return (
                'Participant {} terminated in state ABORT. '
                'Reason: local transaction failed.'
                .format(self.participant)
            )

        self._enter_state('READY')
        self.channel.send_to(self.coordinator, VOTE_COMMIT)

        # Phase 2b: expect PREPARE_COMMIT or GLOBAL_ABORT
        msg = self.channel.receive_from(self.coordinator, TIMEOUT)
        if not msg:
            # Coordinator failed while participant is READY.
            decision = self._participant_termination_after_coordinator_failure()
            if decision == GLOBAL_COMMIT:
                self._enter_state('COMMIT')
                return (
                    'Participant {} terminated in state COMMIT. '
                    'Reason: coordinator crash resolved by new coordinator.'
                    .format(self.participant)
                )

            self._enter_state('ABORT')
            return (
                'Participant {} terminated in state ABORT. '
                'Reason: coordinator crash resolved by new coordinator.'
                .format(self.participant)
            )

        if msg[1] == GLOBAL_ABORT:
            self._enter_state('ABORT')
            return (
                'Participant {} terminated in state ABORT. Reason: GLOBAL_ABORT.'
                .format(self.participant)
            )

        assert msg[1] == PREPARE_COMMIT

        self._enter_state('PRECOMMIT')
        self.channel.send_to(self.coordinator, READY_COMMIT)

        # Phase 3b: expect GLOBAL_COMMIT
        msg = self.channel.receive_from(self.coordinator, TIMEOUT)

        if not msg:
            # Coordinator failed while participant is PRECOMMIT.
            decision = self._participant_termination_after_coordinator_failure()
            if decision == GLOBAL_ABORT:
                self._enter_state('ABORT')
                return (
                    'Participant {} terminated in state ABORT. '
                    'Reason: coordinator crash resolved by new coordinator.'
                    .format(self.participant)
                )

            self._enter_state('COMMIT')
            return (
                'Participant {} terminated in state COMMIT. '
                'Reason: coordinator crash resolved by new coordinator.'
                .format(self.participant)
            )

        if msg[1] == GLOBAL_COMMIT:
            self._enter_state('COMMIT')
            return (
                'Participant {} terminated in state COMMIT. Reason: GLOBAL_COMMIT.'
                .format(self.participant)
            )

        # Defensive fallback: any unexpected message is treated as abort.
        self._enter_state('ABORT')
        return (
            'Participant {} terminated in state ABORT. '
            'Reason: unexpected message {}.'
            .format(self.participant, msg[1])
        )
