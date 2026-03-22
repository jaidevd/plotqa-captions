"""Backfill MongoDB captions collection with metadata from qa.jsonl.

For each line in the JSONL, if the corresponding document exists in MongoDB
(matched by question_id -> _id), set the following fields:
    image_index, qid, answer_bbox, question_category (from 'template'),
    answer_id, type.
"""

import os
import pandas as pd
from pymongo import MongoClient, UpdateOne
from tqdm import tqdm

op = os.path

JSONL_PATH = op.join(op.dirname(__file__), "data", "qa.jsonl")

FIELD_MAP = {
    "image_index": "image_index",
    "qid": "qid",
    "answer_bbox": "answer_bbox",
    "template": "question_category",
    "answer_id": "answer_id",
    "type": "type",
}


def backfill(path=JSONL_PATH, db="plotqa", collection="captions", chunksize=10_000):
    with MongoClient() as client:
        coll = client[db][collection]
        for chunk in tqdm(pd.read_json(path, lines=True, chunksize=chunksize)):
            ids = chunk["question_id"].tolist()
            existing = set(
                doc["_id"] for doc in coll.find({"_id": {"$in": ids}}, {"_id": 1})
            )
            ops = []
            for _, row in chunk.iterrows():
                qid = row["question_id"]
                if qid not in existing:
                    continue
                update = {v: row[k] for k, v in FIELD_MAP.items()}
                ops.append(UpdateOne({"_id": qid}, {"$set": update}))
            if ops:
                coll.bulk_write(ops, ordered=False)


if __name__ == "__main__":
    backfill()
