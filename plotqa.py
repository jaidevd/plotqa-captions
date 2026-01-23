import os
import re
import random
from pydoc import locate
from tornado.template import Template
import yaml
import pandas as pd
import warnings

op = os.path


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


if __name__ == "__main__":
    from joblib import Parallel, delayed
    from glob import glob
    from tqdm import tqdm

    with open("qa_templates.yaml", "r") as fin:
        tmpl_cfg = pd.DataFrame.from_records(yaml.safe_load(fin), index="id")

    for i, file in tqdm(enumerate(glob('data/parts/*_matched_qa.jsonl'))):
        outfile = f"data/parts/{i}_captions.jsonl"
        df = pd.read_json(file, lines=True)
        df.dropna(subset=['template_id', 'answer'], inplace=True)
        templates = tmpl_cfg.loc[df['template_id']]
        captions = Parallel(n_jobs=-1, verbose=2)(
            delayed(generate_caption)(qa, tmpl) for (_, qa), (_, tmpl) in zip(
                df.iterrows(), templates.iterrows()
            )
        )
        pd.DataFrame.from_records(captions).to_json(
            outfile, lines=True, orient="records"
        )
