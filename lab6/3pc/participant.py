import logging
import random

import stablelog

from const3PC import VOTE_REQUEST, PREPARE_COMMIT, GLOBAL_COMMIT, GLOBAL_ABORT
from const3PC import VOTE_COMMIT, VOTE_ABORT, READY_COMMIT
from const3PC import STATE_REPORT
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

    # Progression of the 3PC participant states (higher == "later").
    # ABORT/COMMIT are terminal and never reach the termination protocol.
    _STATE_ORDER = {'NEW': 0, 'INIT': 0, 'READY': 1, 'PRECOMMIT': 2, 'COMMIT': 3}

    @classmethod
    def _is_earlier(cls, state, other):
        """True if `state` is strictly before `other` in the 3PC progression."""
        return cls._STATE_ORDER.get(state, 0) < cls._STATE_ORDER.get(other, 0)

    @staticmethod
    def _termination_decision(leader_state):
        """
        Final outcome, decided by the new coordinator P_k from ITS OWN state
        (README 3.2.2.b, cases 1-3). P_k is a participant here, so its 'READY'
        corresponds to the coordinator state 'WAIT' in the spec.

        - PRECOMMIT / COMMIT  -> GLOBAL_COMMIT  (cases 2 and 3-commit)
        - READY / ABORT / ... -> GLOBAL_ABORT   (cases 1 and 3-abort)
        """
        if leader_state in {'PRECOMMIT', 'COMMIT'}:
            return GLOBAL_COMMIT
        if leader_state in {'READY', 'WAIT', 'ABORT', 'INIT', 'NEW'}:
            return GLOBAL_ABORT
        raise AssertionError(f'Unexpected leader state {leader_state}')


    def _participant_termination_after_coordinator_failure(self):
        """
        Terminate the transaction after a coordinator crash (README 3.2.2.b).

        A new coordinator P_k is elected deterministically (smallest id). P_k
        announces its own state; the elected coordinator then decides purely
        from that state and broadcasts the global outcome.
        """
        all_participants = self.channel.subgroup('participant')
        leader = self._leader_of(all_participants)

        self.logger.info(
            'Coordinator failure detected by participant %s. Elected new coordinator: %s.',
            self.participant,
            leader,
        )

        if self.participant == leader:
            return self._terminate_as_new_coordinator(all_participants)
        return self._terminate_as_follower(leader, all_participants)

    def _terminate_as_new_coordinator(self, all_participants):
        """New coordinator P_k: announce state, then decide and broadcast."""
        others = set(all_participants) - {self.participant}

        # P_k sends its state to all P_i (README 3.2.2.b).
        self.channel.send_to(others, (STATE_REPORT, self.state))

        # Collect the acknowledgements ("senden entsprechende Nachrichten an
        # P_k"). Late/dead nodes are ignored (single-failure assumption).
        pending = set(others)
        while pending:
            msg = self.channel.receive_from(all_participants, TIMEOUT * 2)
            if not msg:
                break
            sender, payload = msg
            if isinstance(payload, tuple) and payload[0] == STATE_REPORT:
                pending.discard(sender)

        # Decision depends ONLY on P_k's own state (cases 1-3).
        decision = self._termination_decision(self.state)
        self.logger.info(
            'New coordinator %s (state %s) broadcasts %s.',
            self.participant,
            self.state,
            decision,
        )
        self.channel.send_to(others, decision)
        return decision

    def _terminate_as_follower(self, leader, all_participants):
        """Follower P_i: adopt P_k's state if earlier, then apply the outcome."""
        leader_state = None

        # Phase 1: receive P_k's announced state and synchronise.
        msg = self.channel.receive_from({leader}, TIMEOUT * 3)
        if msg and isinstance(msg[1], tuple) and msg[1][0] == STATE_REPORT:
            leader_state = msg[1][1]
            # Participants in an earlier state adopt P_k's state; participants
            # in a later state keep theirs (they only ever move to ABORT on a
            # GLOBAL_ABORT, README case 1).
            if self._is_earlier(self.state, leader_state):
                self._enter_state(leader_state)
            # Acknowledge our (possibly adopted) state to P_k.
            self.channel.send_to({leader}, (STATE_REPORT, self.state))

        # Phase 2: apply the global decision broadcast by P_k.
        msg = self.channel.receive_from(all_participants, TIMEOUT * 3)
        if msg and msg[1] in (GLOBAL_COMMIT, GLOBAL_ABORT):
            return msg[1]

        # Broadcast missed: derive the SAME outcome from P_k's announced state.
        # This is consistent by construction (identical to P_k's own decision),
        # unlike a rule based on our own local state.
        if leader_state is not None:
            return self._termination_decision(leader_state)

        # Neither state nor decision reached us: the new coordinator is also
        # unreachable, i.e. multiple failures, which are out of scope
        # (README 3.2 Abgrenzung). Abort as the safe default.
        self.logger.warning(
            'Participant %s could not reach new coordinator %s '
            '(out of scope: multiple failures). Defaulting to GLOBAL_ABORT.',
            self.participant,
            leader,
        )
        return GLOBAL_ABORT

    def run(self):
        # Phase 1b: wait for VOTE_REQUEST and do local work
        msg = self.channel.receive_from(self.coordinator, TIMEOUT)
        if not msg:
            self.logger.warning(
                'Participant %s assumes coordinator crashed in state INIT (before VOTE_REQUEST).',
                self.participant,
            )
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
            self.logger.warning(
                'Participant %s assumes coordinator crashed in state WAIT (before PREPARE_COMMIT/GLOBAL_ABORT).',
                self.participant,
            )
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
            self.logger.warning(
                'Participant %s assumes coordinator crashed in state PRECOMMIT (before GLOBAL_COMMIT).',
                self.participant,
            )
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
