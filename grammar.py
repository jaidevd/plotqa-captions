"""Utilities to fix grammatical errors in captions. Grammar checks are done with LanguageTool."""

from bisect import bisect_right
from collections import Counter
from requests import get
from joblib import Parallel, delayed
from spacy.tokens import Doc
from pymongo import MongoClient, UpdateOne
from tqdm import tqdm

URL = "http://localhost:8081/v2/check"
AUX_VERB_PLURALIZE = {
    "was": "were",
    "is": "are",
    "does": "do",
    "has": "have",
    "differs": "differ",
}
AUX_VERB_SINGULARIZE = {v: k for k, v in AUX_VERB_PLURALIZE.items()}
is_noun_singular = lambda x: x.tag_ in ("NN", "NNP")  # NOQA: E731
is_noun_plural = lambda x: x.tag_ in ("NNS", "NNPS")  # NOQA: E731


def check_grammar(question_id, caption, ignore=None, template_id=None):
    """Process a single caption with LanguageTool.

    Parameters:
    -----------
    question_id: int
    caption: str
    ignore: list
        List of LT rules to ignore.
    template_id: int
        So that a set of errors can be associated with a template.

    """
    params = {"language": "en-US", "text": caption}
    if ignore is not None:
        params.update({"disabledRules": ",".join(ignore)})
    resp = get(URL, params=params)
    if resp.ok:
        return {"question_id": question_id, "matches": resp.json()["matches"]}
    print(resp.text)  # NOQA: T201
    raise ValueError(f"LT Request failed with status {resp.status_code}")


def has_match(matches, key, value):
    for match in matches:
        if value.lower() in match[key].lower():
            return True
    return False


def err_counter(messages, top=5):
    """Find the most common LT errors in a list of error messages."""
    msgs = []
    for m in messages:
        for match in m["matches"]:
            msgs.append(match["message"])
    ctr = Counter(msgs)
    if top:
        print(ctr.most_common(top))  # NOQA: T201
    return ctr


def filter_lt_messages(messages, reverse=False, **kwargs):
    """Filter a list of LT messages to find those that match a given pattern.

    Or, do a reverse match: find those that _don't_ match a given pattern.
    """
    if all([k is None for k in kwargs.values()]):
        raise ValueError("At least one kwarg must be ~None.")
    for k, v in kwargs.items():
        if reverse:
            messages = filter(lambda x: not has_match(x["matches"], k, v), messages)
        else:
            messages = filter(lambda x: has_match(x["matches"], k, v), messages)
    return [m for m in messages if len(m["matches"]) > 0]


# Fixes


def find_root_nsubj(doc):
    """Find the root and the nominal subject of a sentence."""
    root = None
    for token in doc:
        if token.dep_ == "ROOT":
            root = token
            break
    if root is None:
        raise ValueError("Cannot find root!")
    if len(list(root.ancestors)) > 0:
        candidates = []
        for token in doc:
            if len(list(token.ancestors)) == 0:
                candidates.append(token)
        if len(candidates) > 1:
            raise ValueError("Found more than one token that has no ancestors.")
        root = candidates[0]
    aux_verb = None
    for child in root.children:
        if child.dep_ == "aux":
            aux_verb = child
    nsubj = None
    for noun in root.children:
        if noun.dep_ == "nsubj":
            nsubj = noun
            if nsubj.pos_ == "ADJ":
                nsubj = nsubj.conjuncts[0]
            break
    if (aux_verb is not None) and (nsubj in aux_verb.children):
        root = aux_verb
    return root, nsubj


def has_agreement(verb, subject):
    """Check if a verb agrees with its subject."""
    if (subject is None) or (subject.tag_ == "CD"):
        return True, verb

    if verb.tag_ == "VBP":
        return is_noun_plural(subject), verb
    if verb.tag_ == "VBZ":
        return is_noun_singular(subject), verb
    if verb.tag_ == "VBD":
        is_singular = verb.morph.get("Number") == ["Sing"]
        if is_singular:
            return is_noun_singular(subject), verb
        return is_noun_plural(subject), verb
    if verb.tag_ == "VB":
        # Find the auxiliary child and that becomes the new verb
        for child in verb.children:
            if child.dep_ == "aux":
                break
        return has_agreement(child, subject)
    raise ValueError(f"Tag for verb {verb} not valid.")


def fix_verb_subject_agreement(doc):
    """Fix verb agreement by changing the number (singular / plural)."""
    verb, subject = find_root_nsubj(doc)
    agrees, verb = has_agreement(verb, subject)
    verbix = verb.i
    if agrees:
        return doc.text
    if subject.tag_ in ("NN", "NNP"):  # subject is singular
        verb = AUX_VERB_SINGULARIZE.get(verb.text, verb.text)
    elif subject.tag_ in ("NNS", "NNPS"):  # subject is plural
        verb = AUX_VERB_PLURALIZE.get(verb.text, verb.lemma_)
    elif subject.tag_ in ("NFP",):
        return doc.text
    else:
        raise ValueError(f"Tag {subject.tag_} of noun {subject.text} not recognized.")
    words = [t.text for t in doc]
    words[verbix] = verb
    spaces = [bool(t.whitespace_) for t in doc]
    return Doc(doc.vocab, words, spaces).text


def get_repl_values(data):
    values = []
    for err in data:
        for match in err["matches"]:
            values.extend([k["value"] for k in match["replacements"]])
    return set(values)


def _check_concatenated(docs):
    """Concatenate captions, send as one LT request, and map matches back.

    Parameters
    ----------
    docs : list[dict]
        Each dict must have ``_id`` and ``caption``.

    Returns
    -------
    dict
        Mapping of ``_id`` to list of LT match objects (with offsets adjusted
        to be relative to the individual caption).
    """
    # Build the concatenated text and an offset map.
    # offsets[i] is the start position of docs[i] in the blob.
    offsets = []
    pos = 0
    for doc in docs:
        offsets.append(pos)
        pos += len(doc["caption"]) + 1  # +1 for the newline separator

    text = "\n".join(doc["caption"] for doc in docs)
    resp = get(URL, params={"language": "en-US", "text": text})
    if not resp.ok:
        print(resp.text)  # NOQA: T201
        raise ValueError(f"LT request failed with status {resp.status_code}")

    # Assign each match to its caption using the global offset.
    # bisect_right gives the index of the first offset > match_offset,
    # so the caption index is one less.
    result = {doc["_id"]: [] for doc in docs}
    for match in resp.json()["matches"]:
        global_offset = match["offset"]
        idx = bisect_right(offsets, global_offset) - 1
        doc_id = docs[idx]["_id"]
        # Adjust offset to be relative to this caption
        match["offset"] = global_offset - offsets[idx]
        result[doc_id].append(match)

    return result


def check_and_store(db="plotqa", collection="captions", batch_size=1000, chunksize=10_000):
    """Grammar-check captions in MongoDB and update each document with results.

    Captions are concatenated into batches (newline-separated) before being
    sent to the LanguageTool API. This is substantially faster than one
    request per caption. Four batches are processed in parallel.

    Finds documents that have a ``caption`` but no ``lt_matches`` yet,
    and sets the following fields on each document::

        {
            "lt_matches": [            # list of LanguageTool match objects
                {
                    "message": <str>,
                    "shortMessage": <str>,
                    "replacements": [{"value": <str>, ...}, ...],
                    "offset": <int>,       # relative to this caption
                    "length": <int>,
                    "context": {"text": <str>, "offset": <int>, "length": <int>},
                    "sentence": <str>,
                    "type": {"typeName": <str>},
                    "rule": {
                        "id": <str>,
                        "description": <str>,
                        "issueType": <str>,
                        "category": {"id": <str>, "name": <str>},
                    },
                    "ignoreForIncompleteSentence": <bool>,
                    "contextForSureMatch": <int>,
                },
                ...
            ],
            "n_errors": <int>,         # len(lt_matches), for convenient querying
        }

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    batch_size : int
        Number of captions to concatenate per LT request.
    chunksize : int
        Number of documents to read from MongoDB per cursor batch.
    """
    query = {"caption": {"$exists": True}, "lt_matches": {"$exists": False}}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        chunk = []
        for doc in tqdm(cursor, total=total):
            chunk.append(doc)
            if len(chunk) < chunksize:
                continue
            _check_chunk(chunk, coll, batch_size)
            chunk = []
        if chunk:
            _check_chunk(chunk, coll, batch_size)


def _check_chunk(chunk, coll, batch_size):
    """Split a chunk into sub-batches, check in parallel, and write updates."""
    # Split into sub-batches of batch_size
    sub_batches = [
        chunk[i : i + batch_size] for i in range(0, len(chunk), batch_size)
    ]
    # Process sub-batches in parallel (4 concurrent LT requests)
    batch_results = Parallel(n_jobs=4, verbose=2)(
        delayed(_check_concatenated)(sub) for sub in sub_batches
    )
    # Merge results and write to MongoDB
    ops = []
    for result in batch_results:
        for doc_id, matches in result.items():
            ops.append(
                UpdateOne(
                    {"_id": doc_id},
                    {"$set": {"lt_matches": matches, "n_errors": len(matches)}},
                )
            )
    coll.bulk_write(ops, ordered=False)


if __name__ == "__main__":
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else "plotqa"
    collection = sys.argv[2] if len(sys.argv) > 2 else "captions"
    check_and_store(db=db, collection=collection)
