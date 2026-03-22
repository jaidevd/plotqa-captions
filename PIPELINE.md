# PlotCaptions Pipeline

End-to-end guide for generating and grammar-checking captions from the PlotQA dataset.
All intermediate data lives in MongoDB -- the only file input is the source JSONL.

## Prerequisites

### Python dependencies

```bash
pip install pymongo pandas pyyaml tornado joblib tqdm requests spacy
python -m spacy download en_core_web_sm
```

### MongoDB

Start a persistent MongoDB instance with Docker:

```bash
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -v mongodb_data:/data/db \
  mongo
```

No authentication is required. The code connects to `localhost:27017` by default.

### LanguageTool

Download and set up LanguageTool (needed for Step 4):

```bash
wget https://languagetool.org/download/LanguageTool-6.3.zip
unzip LanguageTool-6.3.zip -d .
mv ./LanguageTool-6.3 ./LanguageTool
ln -s ./lt-config/lt_config.ini ./LanguageTool/config.ini
echo >> ./LanguageTool/org/languagetool/resource/en/hunspell/spelling.txt
cat ./lt-config/british_spelling.txt >> ./LanguageTool/org/languagetool/resource/en/hunspell/spelling.txt
cat ./lt-config/ignore.txt >> ./LanguageTool/org/languagetool/resource/en/hunspell/spelling.txt
```

Start the server before running Step 4:

```bash
cd LanguageTool
java -cp languagetool-server.jar org.languagetool.server.HTTPServer \
  --port 8081 --allow-origin --config config.ini
```

### Source data

You need a JSONL file with PlotQA question-answer pairs. Each line must have at
least these fields:

```json
{"question_id": 2, "question_string": "What is the percentage of ...?", "answer": 87.4244}
```

The original PlotQA dataset has additional columns (`image_index`, `template`,
`type`, etc.) which are ignored by the pipeline.

## Pipeline

All steps are idempotent -- each one queries MongoDB for documents that haven't
been processed yet, so you can safely re-run any step after an interruption.

### Step 1: Match questions to templates

Reads the source JSONL, filters out structural questions (about graph
appearance, legend labels, axis titles, etc.), matches each remaining question
to one of the 49 regex templates in `qa_templates.yaml`, and inserts the
results into MongoDB.

```python
from plotqa import match_and_store

match_and_store("path/to/source.jsonl")
```

After this step, each document in MongoDB looks like:

```json
{
  "_id": 2,
  "question_string": "What is the percentage of female population who survived till age of 65 in 1993?",
  "answer": 87.4244,
  "template_id": 2,
  "regex_matches": {
    "yvalue": "percentage",
    "preposition": "of",
    "xvalue": "female population who survived till age of 65 in 1993"
  }
}
```

Questions that don't match any template are skipped (not inserted).

### Step 2: Generate captions

Reads all documents that have a `template_id` but no `caption`, generates a
caption for each using the matched template and the answer, and updates the
document.

```python
from plotqa import generate_and_store

generate_and_store()
```

After this step, each document gains a `caption` field:

```json
{
  "_id": 2,
  "caption": " The percentage of female population who survived till age of 65 in 1993 is 87.4244. ",
  ...
}
```

Caption phrasing is randomized -- templates with multiple variants (defined in
`captions.py`) will produce different sentence structures across runs.

### Step 3: Apply text fixes

Applies spelling corrections, abbreviation normalization, determiner insertion
for geographic proper nouns, whitespace cleanup, and other fixes to every
caption that hasn't been fixed yet.

```python
from fixes import fix_captions_in_mongo

fix_captions_in_mongo()
```

This sets `caption_fixed: true` on each processed document so it won't be
re-processed on subsequent runs.

The fixes include:
- **Typos**: `resorces` -> `resources`, `emissisons` -> `emissions`, etc.
- **Abbreviations**: `gdp` -> `GDP`, `ppp` -> `PPP`, `imf` -> `IMF`, etc.
- **GPE determiners**: `Bahamas` -> `the Bahamas`, `United States` -> `the United States`, etc.
- **Diacritics**: `Sao Tome` -> `São Tomé`, `Curacao` -> `Curaçao`, etc.
- **Hyphenation**: `self employed` -> `self-employed`, `non concessional` -> `non-concessional`, etc.
- **Repeated words**: `total total` -> `total`, `in in` -> `in`, etc.
- **HTML entities**: `&amp;` -> `&`, `&#39;` -> `'`, etc.
- **Whitespace**: collapse multiple spaces, add space before brackets, trim.

### Step 4: Grammar check with LanguageTool

Captions are concatenated into batches of 1000 (newline-separated) and sent
as single requests to the LanguageTool HTTP API. Four such requests are
processed in parallel via joblib. This is roughly 2x faster than sending one
request per caption. Requires the LanguageTool server to be running
(see Prerequisites).

```python
from grammar import check_and_store

check_and_store()
# Or with custom batch size:
# check_and_store(batch_size=500)
```

Or from the command line:

```bash
python grammar.py            # defaults: db=plotqa, collection=captions
python grammar.py mydb mycol # custom db and collection
```

After this step, each document gains `lt_matches` and `n_errors`:

```json
{
  "_id": 2,
  "lt_matches": [
    {
      "message": "Possible spelling mistake found.",
      "shortMessage": "Spelling mistake",
      "replacements": [{"value": "PPP"}, ...],
      "offset": 4,
      "length": 3,
      "context": {"text": "The ppp conversion factor...", "offset": 4, "length": 3},
      "sentence": "The ppp conversion factor for gdp in 2002 is 0.90497.",
      "type": {"typeName": "Other"},
      "rule": {
        "id": "MORFOLOGIK_RULE_EN_US",
        "description": "Possible spelling mistake",
        "issueType": "misspelling",
        "category": {"id": "TYPOS", "name": "Possible Typo"}
      },
      "ignoreForIncompleteSentence": false,
      "contextForSureMatch": 0
    }
  ],
  "n_errors": 1,
  ...
}
```

## Quick start

Run the full pipeline in a Python session:

```python
from plotqa import match_and_store, generate_and_store
from fixes import fix_captions_in_mongo
from grammar import check_and_store

# Step 1: Source file -> MongoDB (template matching)
match_and_store("path/to/source.jsonl")

# Step 2: Generate captions
generate_and_store()

# Step 3: Apply text fixes
fix_captions_in_mongo()

# Step 4: Grammar check (LanguageTool server must be running)
check_and_store()
```

## Querying results

```python
from pymongo import MongoClient

with MongoClient() as client:
    coll = client.plotqa.captions

    # Count documents with grammar errors
    coll.count_documents({"n_errors": {"$gt": 0}})

    # Find all errors for a specific template
    list(coll.find({"template_id": 2, "n_errors": {"$gt": 0}}))

    # Aggregate error counts by template
    list(coll.aggregate([
        {"$match": {"n_errors": {"$gt": 0}}},
        {"$group": {"_id": "$template_id", "total_errors": {"$sum": "$n_errors"}}},
        {"$sort": {"total_errors": -1}},
    ]))

    # Find captions with a specific error type
    list(coll.find({"lt_matches.rule.id": "SUBJECT_VERB_AGREEMENT_PLURAL"}))
```

## Configuration

All pipeline functions accept `db` and `collection` keyword arguments
(defaults: `db="plotqa"`, `collection="captions"`). Batch sizes can be
tuned with the `chunksize` parameter. Steps 1-3 use `n_jobs=6` for
parallel processing with joblib. Step 4 uses `n_jobs=4` with batched
concatenation (`batch_size=1000` captions per LT request) for optimal
throughput.

## Module reference

| Module | Purpose |
|---|---|
| `plotqa.py` | Template matching (`match_and_store`) and caption generation (`generate_and_store`) |
| `captions.py` | Randomized caption templates for each of the 49 question types |
| `fixes.py` | Structural question filter (`is_structural`) and text fixes (`fix_captions_in_mongo`) |
| `grammar.py` | LanguageTool grammar checking (`check_and_store`) and NLP-based fixes |
| `qa_templates.yaml` | The 49 regex templates used to match questions |
