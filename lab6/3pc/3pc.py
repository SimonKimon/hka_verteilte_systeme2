import logging
import multiprocessing as mp

import coordinator
import participant
from context import lab_channel, lab_logging

lab_logging.setup(stream_level=logging.INFO, file_level=logging.DEBUG)
logger = logging.getLogger('vs2lab.lab6.3pc.3pc')


def create_and_run(num_bits, proc_class, enter_bar, run_bar):
    """Create one node process, initialize it, then run protocol logic."""
    chan = lab_channel.Channel(n_bits=num_bits)
    proc = proc_class(chan)

    # Barrier 1: ensure all processes joined before anybody binds/initializes.
    enter_bar.wait()
    proc.init()

    # Barrier 2: ensure all nodes initialized before protocol starts.
    run_bar.wait()
    result = proc.run()

    # Avoid duplicate crash output: coordinator already logs its crash as WARNING.
    if (
        proc_class.__name__ == 'Coordinator'
        and isinstance(result, str)
        and 'crashed in state' in result
    ):
        return

    logger.info(result)


if __name__ == '__main__':
    m = 8  # address space size in bits for random channel ids
    n = 3  # number of participants

    # Clean communication state in Redis before each demo run.
    chan = lab_channel.Channel()
    chan.channel.flushall()

    mp.set_start_method('spawn')

    bar1 = mp.Barrier(n + 1)
    bar2 = mp.Barrier(n + 1)

    participants = []
    for i in range(n):
        p = mp.Process(
            target=create_and_run,
            name='Participant-' + str(i),
            args=(m, participant.Participant, bar1, bar2)
        )
        participants.append(p)
        p.start()

    c = mp.Process(
        target=create_and_run,
        name='Coordinator',
        args=(m, coordinator.Coordinator, bar1, bar2)
    )
    c.start()

    c.join()

    for p in participants:
        p.join()
