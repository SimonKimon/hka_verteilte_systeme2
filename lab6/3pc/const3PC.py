# Coordinator -> Participant messages
VOTE_REQUEST = 'VOTE_REQUEST'
PREPARE_COMMIT = 'PREPARE_COMMIT'
GLOBAL_COMMIT = 'GLOBAL_COMMIT'
GLOBAL_ABORT = 'GLOBAL_ABORT'

# Participant -> Coordinator messages
VOTE_COMMIT = 'VOTE_COMMIT'
VOTE_ABORT = 'VOTE_ABORT'
READY_COMMIT = 'READY_COMMIT'

# Participant <-> Participant messages used during coordinator-failure handling
NEED_STATE = 'NEED_STATE'
STATE_REPORT = 'STATE_REPORT'

# Local participant outcomes (simulation of local transaction)
LOCAL_SUCCESS = 'LOCAL_SUCCESS'
LOCAL_ABORT = 'LOCAL_ABORT'

# Timeout used to model fail-noisy behavior.
TIMEOUT = 1
