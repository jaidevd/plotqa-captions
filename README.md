# PlotCaptions

The task proposed by the [PlotQA paper](https://arxiv.org/pdf/1909.00997.pdf)
was that of training a machine to answer questions based on a scientific plot.
The proposed 'sentencification' of QA pairs allows us to train machines to
generate captions for plots.

This repository contains code to generate a variant of the [PlotQA](https://github.com/NiteshMethani/PlotQA/blob/master/PlotQA_Dataset.md) dataset, which converts the QA pairs in the
original dataset to sentences. Here is a sample QA pair from the original
dataset:

Question: Across all years, what is the maximum percentage of male population who survived till age of 65?
Answer: 82.0172

This QA pair can be presented as a sentence, as follows:

Across years, the maximum percentage of male population who survived till the
age of 65  is 82.0172.

# Preparing the dataset

**Note**: We use json-lines almost exclusively. It's easier to use tools like
grep and sed that way.

## Generating Captions

* Preprocessing
  - Start with PlotQA, which contains three splits - train, validation and test. Each split has three files - a tarball of pngs, an annotations file, and another JSON containing QA pairs.
  - Read the JSON file into a pandas dataframe, it should have these columns: `['image_index', 'qid', 'question_string', 'answer_bbox', 'template', 'answer', 'answer_id', 'type', 'question_id']`
  - Remove the QA pairs corresponding to the "structural" template, i.e. `df = df[df['template'] != "structural"]`
  - Some structural questions are not marked as such. Use `remove_structural_qs.sed` to remove them

* Finding templates for each question string
  - Load the question templates from `qa_templates.yaml`. Each template has an
    ID.
  - Use `plotqa.search_templates` to match a question string to a template.
    Thus, map a question ID to a template ID. In addition, extract the name
    regular expression groups from the question string.

* Generating captions
  - Use `plotqa.generate_caption` to generate a caption for each QA pair, using the
    matched template and the extracted regex groups. Refer to the docstring of
    that function for more.


## Question templates

The original paper helpfully provides a collection of templates that were used
to generate questions which were eventually included in the original dataset. A
generalization of these templates is included [here](./qa_templates.yaml).

Such templates can then be used to convert the question answer pair into a
sentence.

Consider the following question:

```
What is the percentage of female population who survived till age of 65 in 1993?
```

This string is matched by the second template in our list:

```
"What is the (?P<yvalue>.*?) (?P<preposition>of|in) (?P<xvalue>.*?)\\s?\\?$"
```

This can be done in Python as follows:

```python
>>> import re
>>> question = "What is the percentage of female population who survived till age of 65 in 1993?"
>>> pattern = "What is the (?P<yvalue>.*?) (?P<preposition>of|in) (?P<xvalue>.*?)\\s?\\?$"
>>> matches = re.search(pattern, question).groupdict()
>>> print(matches)
{'yvalue': 'percentage',
 'preposition': 'of',
 'xvalue': 'female population who survived till age of 65 in 1993'}
```

## Caption Generation

From the training data, we know the answer to be 87.4244. So, this can then be templatized into an answer as follows:

```python
>>> answer_template = "The {yvalue} {preposition} {xvalue} is {answer}."
>>> print(answer_template.format(answer=87.4244, **matches))
The percentage of female population who survived till age of 65 in 1993 is 87.4244.
```

The QA templates have been written so as to randomize the answer templates, i.e.
for all question matching this pattern, the caption template will not
necessarily be the same as `answer_template` above.

## Usage

Suppose you have a QA pair from the original data as follows:

```python
>>> qa_sample = {
...     "question_string": "What is the percentage of female population who survived till age of 65 in 1993 ?",
...     "answer": 87.4244,
...     "question_id": 2
... }
```

Then, the right template can be found as follows:
```python
>>> # Read the templates into memory
>>> import yaml
>>> from plotqa import search_templates
>>> with open("qa_templates.yaml", "r") as fin:
...     tmpl_cfg = pd.DataFrame.from_records(yaml.safe_load(fin), index="id")
...     templates = tmpl_cfg['regex'].reset_index().to_dict(orient='records')
>>> matched_template = search_templates(templates, **qa_sample)
>>> print(matched_template)
{'question_id': 2,
 'template_id': 2,
 'matches': {'yvalue': 'percentage',
             'preposition': 'of',
	     'xvalue': 'female population who survived till age of 65 in 1993'}}
>>> # This means that the given QA pair matched template ID 2
```

The caption can then be generated as:
```python
>>> from plotqa import caption_qa
>>> caption = caption_qa(answer=qa_sample['answer'], **matched_template)
>>> print(caption)
{'question_id': 2,
 'template_id': 2,
 'caption': ' The percentage of female population who survived till age of 65 in 1993 is 87.4244. '}
 ```

## Grammatical Checks on Generated Captions

Download [LanguageTool](https://languagetool.org/download/LanguageTool-stable.zip) as follows:

```bash
$ wget https://languagetool.org/download/LanguageTool-6.3.zip
$ unzip LanguageTool-6.3.zip -d .
$ mv ./LanguageTool-6.3 ./LanguageTool
```

Run the following commands to make changes in LanguageTool's configuration:
```bash
$ ln -s ./lt-config/lt_config.ini ./LanguageTool/config.ini
$ echo >> ./LanguageTool/org/languagetool/resource/en/hunspell/spelling.txt
$ cat ./lt-config/british_spelling.txt >> ./LanguageTool/org/languagetool/resource/en/hunspell/spelling.txt
$ cat ./lt-config/ignore.txt >> ./LanguageTool/org/languagetool/resource/en/hunspell/spelling.txt
```

**Note on types of questions:** The original dataset contains questions
classified into three categories:
  1. _Structural understanding_: questions pertaining to the appearance and
     graphical elements of the plot, like how many legend labels it has, or what
     the title of the graph is.
  2. _Data Retrieval_: questions pertaining to information contained in a single
     element of the plot, like the value of a metric.
  3. _Reasoning_:  Questions that need either numeric or visual _reasoning_ to
     answer.

In our dataset, we are concerned only with the _captions_ that would be written
for plots. So we filter out all questions in the structural understanding
category, and some from the data retrieval category.

Suppose the captions are in a file named `captions.json`, then first remove some unwanted captions with:
```bash
$ sed -i -f ./remove_structural_qs.sed captions.json
```


Run the initial set of fixes on the remaining captions:
```bash
$ sed -i -f ./lt-config/fixes.sed captions.json
```

Start the LanguageTool server as follows:

```bash
$ cd LanguageTool
$ java -cp languagetool-server.jar org.languagetool.server.HTTPServer --port 8081 --allow-origin --config config.ini
```

Then run the captions through the LanguageTool API as follows:

```python
>>> import pandas as pd
>>> from grammar import check_grammar
>>> df = pd.read_json('captions.json', lines=True)
>>> for _, row in df.iterrows():
... 	errors = check_grammar(**row)
```
