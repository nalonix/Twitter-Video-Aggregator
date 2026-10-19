import glob
import os
import re


def find_latest_old_cleaned(directory: str = ".") -> str | None:
    """
    Return the "[N] Old Cleaned.csv" with the largest N in `directory` (the most
    recently archived batch), or None if there is none.
    """
    selected = None
    max_num = -1
    for path in glob.glob(os.path.join(directory, "* Old Cleaned.csv")):
        m = re.match(r"^\s*(\d+)\s+Old Cleaned\.csv$", os.path.basename(path))
        if m and int(m.group(1)) > max_num:
            max_num = int(m.group(1))
            selected = path
    return selected
