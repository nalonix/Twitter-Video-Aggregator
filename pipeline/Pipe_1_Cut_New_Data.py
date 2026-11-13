import os

import pandas as pd
from common import (
    ANCHOR_COUNT,
    CLUSTER_MIN,
    CLUSTER_WINDOW,
    all_uploaded_ids,
    find_cut_index,
    find_latest_old_cleaned,
    recent_uploaded_ids,
)

# File paths
file1_path = "New Data.csv"
output_path = "New Cleaned.csv"

latest = find_latest_old_cleaned()
if not latest:
    raise FileNotFoundError("No '* Old Cleaned.csv' files found in the scrapped directory.")
print(f"🔎 Latest uploaded batch: {os.path.basename(latest)}")

df1 = pd.read_csv(file1_path, dtype={"id": str})
ids = df1["id"].astype(str).str.strip().tolist()

# Anchors: the most recently uploaded posts (newest first). Some may be deleted or
# unliked on X; we only need a few of them close together to find the cut. 🤖
anchors = recent_uploaded_ids(".", ANCHOR_COUNT)
if len(anchors) < CLUSTER_MIN:
    raise ValueError(f"❌ Need at least {CLUSTER_MIN} previously uploaded posts to compare against.")
anchor_rank = {a: i + 1 for i, a in enumerate(anchors)}

cut_index = find_cut_index(ids, set(anchors))
if cut_index is None:
    present = [i for i, x in enumerate(ids) if x in anchor_rank]
    raise ValueError(
        f"❌ Couldn't find the last uploaded batch in {file1_path}: needed {CLUSTER_MIN} of the "
        f"{len(anchors)} most recently uploaded posts within {CLUSTER_WINDOW} rows, but only "
        f"{len(present)} appear at all (rows {present[:10]}). The export probably doesn't reach "
        "back far enough."
    )

nearby = [(i, anchor_rank[x]) for i, x in enumerate(ids[cut_index : cut_index + CLUSTER_WINDOW], cut_index) if x in anchor_rank]
print(
    f"⚓ Matched {len(nearby)} of the {len(anchors)} most recent uploads in rows "
    f"{cut_index}-{cut_index + CLUSTER_WINDOW - 1} (row → upload rank): {nearby}"
)
print(f"✂️ Cutting {file1_path} at row {cut_index}")

# Keep only the rows above the cut (the new likes)
df_cut = df1.iloc[:cut_index]

# Drop anything that was already uploaded in an earlier batch (e.g. an old post you
# unliked and liked again, which X moves back to the top of your likes). 🤖
uploaded = all_uploaded_ids(".")
already = df_cut["id"].astype(str).str.strip().isin(uploaded)
if already.any():
    print(f"♻️ Dropping {int(already.sum())} new likes that were already uploaded before: {df_cut.loc[already, 'id'].tolist()}")
    df_cut = df_cut[~already]

df_cut.to_csv(output_path, index=False)
print(f"📁 {len(df_cut)} new likes saved as: {output_path}")
