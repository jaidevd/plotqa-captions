import os
import re
import random
from pydoc import locate
from tornado.template import Template
import yaml
import pandas as pd
import warnings
from joblib import Parallel, delayed
from pymongo import MongoClient, InsertOne, UpdateOne
from tqdm import tqdm
from fixes import is_structural

op = os.path

TEMPLATES_PATH = op.join(op.dirname(__file__), "qa_templates.yaml")


def _load_templates():
    """Load qa_templates.yaml and return (tmpl_list, tmpl_cfg DataFrame)."""
    with open(TEMPLATES_PATH, "r") as fin:
        raw = yaml.safe_load(fin)
    tmpl_list = [{"id": t["id"], "regex": t["regex"]} for t in raw]
    tmpl_cfg = pd.DataFrame.from_records(raw, index="id")
    return tmpl_list, tmpl_cfg


def search_templates(tmpls, question_id, question_string, **kwargs):
    """Search for which template best matches the question string.

    The quality of the search depends on how many regex groups exist in the match.
    More matching groups imply a better match.

    Parameters
    ----------
    tmpls : list
        List of records which represent a template. Essentially the
        contents of `qa_templates.yaml`.
    question_id : int
        question_id of the question string - for backreference.
    question_string : str
        The string to match with the templates.
    """
    matches = [
        (tmpl["id"], re.search(tmpl["regex"], question_string)) for tmpl in tmpls
    ]
    matches = [(t, m.groupdict()) if m else (t, {}) for t, m in matches]
    match = max(matches, key=lambda x: len(x[1]))
    if len(match[1]) == 0:
        warnings.warn(f"Question ID {question_id} didn't match any template.")
        matched_template, matches = None, []
    else:
        matched_template, matches = match[:2]
    return {
        "question_id": question_id,
        "template_id": matched_template,
        "matches": matches,
    }


def generate_caption(qa, template):
    """Generate a caption given a template and a QA object.

    Parameters
    ----------
    qa : dict
        A dictionary containing the question id, the question string, the
        answer, the template ID and the regex matches.
    template : dict
        A dictionary containing the template information, including the header,
        the caption f-strings and the original regex. This is one of the records
        from `qa_templates.yaml`; and should have the same ID as that matched in `qa`.
    """
    tmpl = template['template_header']
    caption = template['caption_templates']
    if isinstance(caption, list):
        tmpl += random.choice(caption)
    elif isinstance(caption, str):
        func = locate(caption)
        if callable(func):
            tmpl += func(qa['answer'])
        else:
            tmpl += caption
    else:
        raise ValueError(f"Invalid caption template {caption}.")
    generated = Template(
        tmpl, autoescape=None
    ).generate(answer=qa['answer'], **qa['matches']).decode()

    return {'qid': qa['question_id'], 'caption': generated}


def match_and_store(path, db="plotqa", collection="captions", chunksize=10_000):
    """Read a source JSONL file, match each question to a template, and insert into MongoDB.

    The source file is expected to have at least: `question_id`, `question_string`, `answer`.

    Each inserted document has the schema::

        {
            "_id": <question_id>,
            "question_string": <str>,
            "answer": <str or number>,
            "template_id": <int or None>,
            "regex_matches": <dict>,   # named groups extracted by the matched regex
        }

    Parameters
    ----------
    path : str
        Path to the source JSONL file.
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of rows to process per batch.
    """
    tmpl_list, _ = _load_templates()
    with MongoClient() as client:
        coll = client[db][collection]
        for chunk in tqdm(pd.read_json(path, lines=True, chunksize=chunksize)):
            chunk = chunk[~chunk["question_string"].map(is_structural)]
            if chunk.empty:
                continue
            results = Parallel(n_jobs=6, verbose=2)(
                delayed(search_templates)(
                    tmpl_list, row["question_id"], row["question_string"]
                )
                for _, row in chunk.iterrows()
            )
            ops = []
            for (_, row), result in zip(chunk.iterrows(), results):
                doc = {
                    "_id": row["question_id"],
                    "question_string": row["question_string"],
                    "answer": row["answer"],
                    "template_id": result["template_id"],
                    "regex_matches": result["matches"] or None,
                }
                ops.append(InsertOne(doc))
            if ops:
                coll.bulk_write(ops, ordered=False)


def generate_and_store(db="plotqa", collection="captions", chunksize=10_000):
    """Generate captions for all matched documents in MongoDB and update them in place.

    Reads documents that have a `template_id` but no `caption` yet,
    generates a caption for each, and sets the `caption` field.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    """
    _, tmpl_cfg = _load_templates()
    query = {"template_id": {"$ne": None}, "caption": {"$exists": False}}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _generate_batch(batch, tmpl_cfg, coll)
            batch = []
        if batch:
            _generate_batch(batch, tmpl_cfg, coll)


def _generate_batch(batch, tmpl_cfg, coll):
    """Generate captions for a batch of MongoDB documents and write updates."""
    qa_rows = []
    tmpl_rows = []
    for doc in batch:
        tid = doc["template_id"]
        if tid not in tmpl_cfg.index:
            continue
        qa_rows.append({
            "question_id": doc["_id"],
            "answer": doc["answer"],
            "matches": doc["regex_matches"],
        })
        tmpl_rows.append(tmpl_cfg.loc[tid].to_dict())
    if not qa_rows:
        return
    results = Parallel(n_jobs=6, verbose=2)(
        delayed(generate_caption)(qa, tmpl)
        for qa, tmpl in zip(qa_rows, tmpl_rows)
    )
    ops = [
        UpdateOne({"_id": r["qid"]}, {"$set": {"caption": r["caption"]}})
        for r in results
    ]
    coll.bulk_write(ops, ordered=False)
