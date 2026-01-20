import os
import re
import random
from pydoc import locate
from tornado.template import Template
import yaml
import pandas as pd
import warnings

op = os.path

with open("qa_templates.yaml", "r") as fin:
    tmpl_cfg = pd.DataFrame.from_records(yaml.safe_load(fin), index="id")


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


def generate_caption(header, caption, answer, **kwargs):
    tmpl = header
    if isinstance(caption, list):
        tmpl += random.choice(caption)
    elif isinstance(caption, str):
        func = locate(caption)
        if callable(func):
            tmpl += func(answer)
        else:
            tmpl += caption
    else:
        raise ValueError(f"Invalid caption template {caption}.")

    return Template(tmpl, autoescape=None).generate(answer=answer, **kwargs).decode()


def caption_qa(question_id, template_id, answer, matches, **kwargs):
    """Generate a caption given a QA pair and regex matches.

    Parameters
    ----------
    question_id : int
        question_id of the question string - for backreference.
    template_id : int
        ID of the template that matches the question string.
    answer : any
        answer to the question string
    matches : dict
        Regex groupdict containing the matches.
    """
    if answer is None:
        return {"question_id": question_id, "template_id": template_id, "caption": ""}
    tmpl = tmpl_cfg.loc[template_id]
    header = tmpl["template_header"]
    caption = tmpl["caption_templates"]
    try:
        if len(matches):
            out = generate_caption(header, caption, answer, **matches)
        else:
            out = ""
    except Exception as exc:
        print(f"Failed for tid: {template_id} qid: {question_id}")
        print(caption)
        print(matches)
        raise exc
    return {"question_id": question_id, "template_id": template_id, "caption": out}


def match_and_generate(qs, answer, pattern, header, tmpl_opts):
    matches = re.search(pattern, qs)
    if matches:
        matches = matches.groupdict()
    else:
        return ""
    tmpl = header
    if isinstance(tmpl_opts, list):
        tmpl += random.choice(tmpl_opts)
    elif isinstance(tmpl_opts, str):
        func = locate(tmpl_opts)
        if callable(func):
            tmpl += func(answer)
        else:
            tmpl += tmpl_opts
    else:
        raise ValueError(f"Invalid caption template {tmpl_opts}.")
    return Template(tmpl).generate(answer=answer, **matches).decode()


if __name__ == "__main__":
    import json
    from joblib import Parallel, delayed

    FILE = "/media/jaidevd/motherbox/archive/plotqa/qa_pairs_V2.json"
    with open(FILE, "r") as fin:
        df = pd.DataFrame.from_records(json.load(fin)["qa_pairs"])
        df = df[["question_id", "question_string"]].to_dict(orient="records")
    tmpls = tmpl_cfg[["regex"]].reset_index().to_dict(orient="records")
    matches = Parallel(n_jobs=-1, verbose=2)(
        delayed(lambda x: search_templates(tmpls, **x))(x) for x in df
    )
