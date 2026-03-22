"""Update captions in MongoDB from a JSONL file.
Easier to use whent the file is manipulated with sed or vim."""

import sys
import pandas as pd
from pymongo import MongoClient, UpdateOne

path = sys.argv[1]
with MongoClient() as client:
    coll = client.plotqa.captions
    for chunk in pd.read_json(path, lines=True, chunksize=10_000):
        ops = [
            UpdateOne({"_id": row["_id"]}, {"$set": {"caption": row["caption"]}})
            for _, row in chunk.iterrows()
        ]
        coll.bulk_write(ops, ordered=False)
