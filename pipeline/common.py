import glob
import os
import re

import pandas as pd

# How the new likes are cut from the already-uploaded ones (used by Pipe 1 and
# fetch/fetch_likes.py). The newest ANCHOR_COUNT uploaded posts are the anchors;
# the cut is the first like where at least CLUSTER_MIN anchors appear within
# CLUSTER_WINDOW rows. Deleted or unliked anchors are simply skipped, and a single
# stray match (e.g. an old post you re-liked) can't cause a cut on its own.
ANCHOR_COUNT = 50
CLUSTER_WINDOW = 20
CLUSTER_MIN = 3

_OLD_CLEANED_RE = re.compile(r"^\s*(\d+)\s+Old Cleaned\.csv$")


def old_cleaned_files(directory: str = ".") -> list[str]:
    """All "[N] Old Cleaned.csv" files in `directory`, newest batch (largest N) first."""
    found = []
    for path in glob.glob(os.path.join(directory, "* Old Cleaned.csv")):
        m = _OLD_CLEANED_RE.match(os.path.basename(path))
        if m:
            found.append((int(m.group(1)), path))
    return [path for _, path in sorted(found, reverse=True)]


def find_latest_old_cleaned(directory: str = ".") -> str | None:
    """
    Return the "[N] Old Cleaned.csv" with the largest N in `directory` (the most
    recently archived batch), or None if there is none.
    """
    files = old_cleaned_files(directory)
    return files[0] if files else None


def _read_ids(path: str, nrows: int | None = None) -> list[str]:
    df = pd.read_csv(path, usecols=["id"], dtype={"id": str}, nrows=nrows)
    return df["id"].dropna().str.strip().tolist()


def recent_uploaded_ids(directory: str = ".", count: int = ANCHOR_COUNT) -> list[str]:
    """The ids of the `count` most recently uploaded posts, newest first, reading
    back through older batches if the latest one is smaller than `count`."""
    ids: list[str] = []
    for path in old_cleaned_files(directory):
        ids.extend(_read_ids(path, nrows=count - len(ids)))
        if len(ids) >= count:
            break
    return ids


def all_uploaded_ids(directory: str = ".") -> set[str]:
    """Every id in every "[N] Old Cleaned.csv"."""
    ids: set[str] = set()
    for path in old_cleaned_files(directory):
        ids.update(_read_ids(path))
    return ids


def find_cut_index(
    ids: list[str],
    anchors: set[str],
    window: int = CLUSTER_WINDOW,
    min_matches: int = CLUSTER_MIN,
) -> int | None:
    """Index of the first row of the already-uploaded block in `ids` (newest first),
    i.e. the first anchor that has at least `min_matches` anchors (itself included)
    within `window` rows starting at it. None if there is no such cluster."""
    positions = [i for i, x in enumerate(ids) if x in anchors]
    for start, p in enumerate(positions):
        nearby = sum(1 for q in positions[start:] if q < p + window)
        if nearby >= min_matches:
            return p
    return None
