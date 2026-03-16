"""Utilities to fix grammatical errors in captions. Grammar checks are done with LanguageTool."""

import json
from collections import Counter
from requests import post, get
from joblib import Parallel, delayed
from spacy.tokens import Doc
import pandas as pd

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


if __name__ == "__main__":
    df = pd.read_json("captions.jsonl", lines=True)
    df['question_id'] = df.pop('qid')

    def _chunked(df, size=1000):
        total = len(df) // size + 1
        for i in range(total):
            chunk = df.iloc[i * size : (i + 1) * size]
            caption = "\n".join(chunk['caption'].drop_duplicates().tolist())
            yield i, {"language": "en-US", "text": caption}


    def req(i, params):
        resp = post(URL, params=params)
        resp.raise_for_status()
        with open(f'data/parts/err_{i}.json', 'w') as fout:
            json.dump(resp.json(), fout, indent=2)


    errors = Parallel(n_jobs=4, verbose=2)(
        delayed(req)(i, params) for i, params in _chunked(df)
    )
