import os
import sys


def add_parent_path(steps_up=2):
    # Build repository root path by stepping up from this file location.
    path = os.path.dirname(__file__)
    for _ in range(steps_up):
        path = os.path.join(path, '..')

    # Make shared modules from lib/ importable for this lab folder.
    sys.path.insert(0, path)


# Add repository root to import path (same pattern as other labs).
add_parent_path()

# Re-export shared modules used by the lab files.
from lib import lab_logging, lab_channel
