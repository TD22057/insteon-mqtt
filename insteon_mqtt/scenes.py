#===========================================================================
#
# Scenes file utiltiies.
#
#===========================================================================

__doc__ = """Scenes file utilties
"""

#===========================================================================
import time
import difflib
import os
from datetime import datetime
from shutil import copy
from ruamel.yaml import YAML


def load_scenes(path):
    """Load and returns the scenes file.
    """
    with open(path, "r") as f:
        yaml = YAML()
        yaml.preserve_quotes = True
        return yaml.load(f)


#===========================================================================
def save_scenes(scenes, path):
    """Saves the scenes data to file.  Creates and keeps a backup
    file if diff produced is significant in size compared to original
    file size.  The diff process is a little intensive.  We could
    consider making this a user configurable option, but it seems prudent
    to have this given the amount of work a user may put into creating
    a scenes file.
    """
    # Create a backup file first`
    ts = time.time()
    timestamp = datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H-%M-%S')
    backup = path + "." + timestamp
    copy(path, backup)

    # Save the config file
    with open(path, "w") as f:
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.dump(scenes, f)

    # Check for diff
    orgCount = 0
    with open(backup, 'r') as old:
        for line in old:  # pylint: disable=W0612
            orgCount += 1
    with open(path, 'r') as new:
        with open(backup, 'r') as old:
            diff = difflib.unified_diff(
                old.readlines(),
                new.readlines(),
                fromfile='old',
                tofile='new',
            )
    # Count the number of deleted lines
    diffCount = len([l for l in diff if l.startswith('- ')])
    # Delete backup if # of lines deleted or altered from original file
    # is less than 5% of original file
    if diffCount / orgCount <= 0.05:
        os.remove(backup)
        backup = ''