# History

## Pipeline Restructuring

- Replaced all intermediate file-based storage with MongoDB. The pipeline now goes:
  source JSONL -> `match_and_store` -> `generate_and_store` -> `fix_captions_in_mongo` -> `check_and_store`
- `plotqa.py`: Added `match_and_store` (reads source JSONL, filters structural questions, matches templates, inserts into MongoDB) and `generate_and_store` (reads unprocessed docs from MongoDB, generates captions, updates in place)
- Added `_load_templates()` helper and `TEMPLATES_PATH` constant to `plotqa.py` to avoid duplicating template loading logic
- `grammar.py`: Rewrote `check_and_store` to read from MongoDB instead of files. Initially used `InsertOne` for fresh collection population, later changed to `UpdateOne` when the pipeline was restructured to update documents in place
- Added batched concatenation to `check_and_store` (1000 captions per LT request, n_jobs=4) for ~2x throughput over per-caption requests. Benchmarked at 14 mins per million captions. The old per-caption `_check_batch` function was replaced by `_check_chunk` (splits into sub-batches) + `_check_concatenated` (concatenates, sends, maps offsets back via `bisect_right`)
- `fixes.py`: New module consolidating all 5 sed files (`remove_structural_qs.sed`, `lt-config/fixes.sed`, `data/typos.sed`, `data/abbreviations.sed`, `data/determiner_gpes.sed`) into Python. Structural patterns compiled into a single regex via `_STRUCTURAL_RE`. Substitution order matters: HTML entities first, then typos, abbreviations, currency, diacritics, country aliases, determiners, hyphenated, one-word, repeated words, gender/possessive, misc, whitespace, punctuation, and dedup determiners last
- Added `is_structural()` filter to `match_and_store` to replace `remove_structural_qs.sed`
- `template_coverage.py` and `remove_structural_val.py` are now obsolete (superseded by MongoDB functions)
- All sed files are now superseded by `fixes.py`
- Unmatched questions (template_id = null) are now inserted into MongoDB instead of silently skipped — removed the `if result["template_id"] is None: continue` guard
- `__main__` block in `grammar.py` rewritten to call `check_and_store` with `sys.argv` for db/collection
- Each MongoDB document has an `n_errors` field (length of `lt_matches`) for convenient querying (e.g. `{"n_errors": {"$gt": 0}}`)

## Grammar Module Cleanup

- Removed 19 unused functions from `grammar.py`: `process_from_mongo`, `fix_spaces`, `fix_tokens`, `space_before_bracket`, `missing_determiner`, `determiner_suffix_nnp`, `unpaired_symbol`, `trim_leading_symbols`, `fix`, `repeated_words`, `fix_is_subject`, `fix_determiner_superlative`, `fix_one_plural`, `check`, `draw_sample`, `get_typos`, `remove_error` — verified against notebook invocations before removal
- Removed unused imports: `gc`, `re`, `tqdm`, `MongoClient`, `UpdateOne`, `InvalidOperation`, `bson`

## Infrastructure Setup

- Docker MongoDB with persistent volume: `docker run -d --name mongodb -p 27017:27017 -v mongodb_data:/data/db mongo`
- No authentication required — plain `MongoClient()` connects by default. Auth available via `MONGO_INITDB_ROOT_USERNAME`/`MONGO_INITDB_ROOT_PASSWORD` env vars if needed
- `mongodump`/`mongorestore` documented for moving data between machines; also `--archive` form for single-file transfers with Docker
- `PIPELINE.md` created: step-by-step guide covering prerequisites, all 4 pipeline stages, MongoDB queries for analysis, module reference
- `patch.py` added: reads a JSONL file with `_id` and `caption` fields via `sys.argv[1]`, bulk-updates MongoDB in chunks of 10,000
- `tmp.py`: one-off script used to re-match 5990 broken template 44 docs to template 37 after the negative lookahead fix
- `burndown.csv` created with timestamps and error totals for visualization

## Grammar Checking Infrastructure

- `check_and_store` accepts an optional `query` parameter to re-check specific subsets of documents
- Default query changed from `{"caption": {"$exists": True}, "lt_matches": {"$exists": False}}` to `{"caption": {"$exists": True}}` to support re-checking
- `disabledRules` field added to MongoDB documents; the cursor projection in `check_and_store` updated to fetch it alongside `_id` and `caption`
- `_check_concatenated` collects the union of all `disabledRules` across a batch and passes them to the LT API via the `disabledRules` parameter. `check_grammar` already had an `ignore` parameter, but `_check_concatenated` didn't support it until this was added
- `lt-config/lt_config.ini` updated to globally disable `ENGLISH_WORD_REPEAT_BEGINNING_RULE` (batching false positive) via `disabledRuleIds`
- `lt-config/ignore.txt` restored from git history (was deleted in the mongo-ize commit) with 27 words: IBRD, Kyrgyz, nonconcessional, etc. Appended to LT's `spelling.txt` during setup. Both `README.md` and `PIPELINE.md` updated with the `cat` command
- `inflect` library added as a dependency for proper noun pluralization in `fix_top_two_plural_in_mongo`

## Template Fixes

- Template 40: Added missing `randomize_40` to `captions.py` and `template_header` to `qa_templates.yaml`. Was generating broken captions with literal string `captions.randomize_40`
- Template 45: Added missing `randomize_45` to `captions.py` and `template_header` to `qa_templates.yaml`. Same issue as template 40
- Template 44: Added `(?!that in)` negative lookahead to regex to prevent it from stealing "and that in" questions from template 37. Template 44 has more regex groups (7 vs 5), so it always won in `search_templates` despite matching incorrectly. This caused ~6000 captions with broken parentheses. The 5990 affected docs were re-matched to template 37 via `tmp.py` and regenerated

## Grammar Error Reduction (15.9M -> ~0)

### Automated fixes in `fixes.py`

Each fix has a standalone function and a corresponding `*_in_mongo` function that targets specific LT rule IDs. `fix_captions_in_mongo` applies all fixes at once and sets `caption_fixed: true` as an idempotency flag.

- `fix_whitespace` / `fix_whitespace_in_mongo`: Collapse consecutive spaces, add space before brackets, trim. Accepts `rule_id` parameter (CONSECUTIVE_SPACES, SPACE_BEFORE_PARENTHESIS, WHITESPACE_RULE)
- `fix_punctuation` / `fix_punctuation_in_mongo`: No space before periods/commas/closing parens, space after commas, remove escaped quotes (`\\\"\s*`), remove leading empty quotes (`^""+\s*`). Targeted COMMA_PARENTHESIS_WHITESPACE
- `fix_determiners` / `fix_determiners_in_mongo`: Add "the" before GPE names (Bahamas, Netherlands, etc.) with negative lookbehind `(?<!\bthe )(?<!\bThe )` to avoid "the the". Targeted DETERMINER_GEOGRAPHICAL_WORD
- `fix_spelling` / `fix_spelling_in_mongo`: Typos, abbreviations (gdp->GDP, ppp->PPP), HTML entities, currency (us$->USD). Accepts `rule_id` param. Used for MORFOLOGIK_RULE_EN_US and EN_SPECIFIC_CASE
- `fix_diacritics` / `fix_diacritics_in_mongo`: Sao Tome -> São Tomé, Cote d'Ivoire -> Côte d'Ivoire, Curacao -> Curaçao. Targeted EN_DIACRITICS_REPLACE_* (matched via `$regex: "^EN_DIACRITICS_REPLACE_"`)
- `fix_compounds` / `fix_compounds_in_mongo`: Hyphenated words (self employed -> self-employed, second highest -> second-highest) and joined words (tax payers -> taxpayers, Wage workers -> wageworkers). Originally named `fix_hyphens` / `fix_hyphens_in_mongo` with `_COMPILED_HYPHEN`, renamed when `_ONE_WORD` was merged in to `_COMPILED_COMPOUNDS`. Targeted EN_COMPOUNDS_*, WORKER_COMPOUNDS, KEEPER_COMPOUNDS, SECOND_LARGEST_HYPHEN, NON_ANTI_JJ (matched via `$regex`)
- `fix_possessive` / `fix_possessive_in_mongo`: females population -> female population, Benefits incidence -> benefit incidence, Armed forces personnel -> armed forces. `_GENDER` list renamed to `_POSSESSIVE_APOSTROPHE`. Targeted POSSESSIVE_APOSTROPHE
- `fix_misc` / `fix_misc_in_mongo`: "in/as thousand metric tons" -> "in/as one thousand metric tons", litre -> liter, Twenty-foot Equivalent Units(TEU) -> twenty-foot equivalent units (TEU). Accepts `rule_id` param. Targeted NODT_DOZEN, EN_SPLIT_WORDS_HYPHEN
- `fix_country_aliases` / `fix_country_aliases_in_mongo`: "Yemen, Rep." -> "Yemen", "Egypt, Arab Rep." -> "Egypt", "Gambia, The" -> "the Gambia" (with "The Gambia" at sentence start, and "the Gambia, The" -> "the Gambia"). Original regex used `\bYemen, Rep\..*?\b` which failed — the `.*?\b` after `Rep.` never matched. Fixed by removing the trailing `.*?\b`. Query matches against `Rep\.`, `Arab Rep\.`, and `Gambia, The`. Targeted DOUBLE_PUNCTUATION, THE_CC
- `fix_repeated_words` / `fix_repeated_words_in_mongo`: General regex `\b(\w+)\s+(\1)\b` (case insensitive) removes any consecutive duplicate word. Replaced the old enumerated `_REPEATED_WORDS` list (which only covered specific pairs like "total total", "in in"). Targeted ENGLISH_WORD_REPEAT_RULE. Also integrated into `fix_caption`
- `fix_one_plural` / `fix_one_plural_in_mongo`: "in 1 years" -> "in one year", "than 1 countries" -> "than one country". Uses `_ONE_PLURAL_MAP` + `_one_plural_repl` callback for correct singular forms. Initially tried pattern `as thousand metric tons` which didn't match — actual text was `in thousand metric tons`. Fixed to `(as|in) thousand metric tons`. Targeted ONE_PLURAL
- `fix_superlatives` / `fix_superlatives_in_mongo`: Add missing determiners before superlatives ("in Least developed" -> "in the least developed", "in poorest quintile" -> "in the poorest quintile"). Fixed typo in original pattern: `qunitile` -> `qu[in]+tile`. Also added `In` to the `(in|of)` group for sentence-initial case. Removed duplicate Isle of Man / Turks and Caicos entries from `_OTHER_DETERMINERS` since `_DETERMINERS_GPES` already handles them. Targeted THE_SUPERLATIVE
- `fix_caption`: Master function applying all compiled substitutions (`_COMPILED_SUBS`) plus `fix_repeated_words`

### spaCy-based fixes in `grammar.py`

- `fix_agreement_in_mongo`: Uses spaCy to find root verb and nsubj, fixes verb number (is->are, does->do) when they disagree. Accepts `rule_id` param. Used for SUBJECT_VERB_AGREEMENT_PLURAL, AGREEMENT_SENT_START
- `disable_false_nns_in_nnp`: Uses spaCy to validate verb-subject agreement; if they agree, adds NNS_IN_NNP_VBZ to `disabledRules` via `$addToSet` (false positive from LT misidentifying subject in prepositional chains like "disbursements from IMF is")
- `fix_top_two_plural_in_mongo`: Pluralizes the nsubj of "differ" in "The top two {metric} differ" captions. Initially used naive `lemma_ + "s"` which produced "expectancys", "densitys", "indexs". Replaced with `inflect.engine().plural()` for correct forms (expectancies, densities, indices). Cleanup substitutions added to `_TYPOS` for the broken forms

### Rules disabled per-document via `disabledRules` (`$addToSet`)

- ENGLISH_WORD_REPEAT_BEGINNING_RULE (batching false positive — now also globally disabled in LT config)
- NNS_IN_NNP_VBZ (false positive: LT misidentifies plural nouns in prepositional phrases as the subject)
- HE_VERB_AGR (false positive: "Czech Republic differ" — LT thinks "Republic" is subject)
- HYPHEN_TO_EN (irrelevant style rule)
- THE_SENT_END (false positive: "the Gambia." at end of sentence)
- TO_TWO (false positive)
- LC_AFTER_PERIOD (false positive)
- AGREEMENT_SENT_START (false positive for "arms imports/exports" and "forest land in Vietnam")
- TWELFTH_OF_NEVER (false positive)

### Documents deleted

- Captions starting with "The title of the graph" or ending with "is the title of the graph."
- Captions containing NaN values (various patterns: "is nan.", "is nan times", "by nan", "^nan is the", etc.)
- Captions with genuinely unpaired brackets (from bad regex matches in templates 2 and 44) — identified via `[(][^)]*$|^[^(]*[)]`. Cross-tabulation showed 5990 from template 44 and the rest from template 2. Total: 7544 genuinely broken captions
- Broken "and that is/are" captions from template mismatching — matched via `caption: { $regex: "and that (is|are)" }`
- ADJECTIVE_IN_ATTRIBUTE matches (37 docs)
- Final cleanup: all remaining docs with `n_errors > 0` (359 docs, mostly COMMA_PERIOD bug + 2 EN_UNPAIRED_BRACKETS)
- Various small batches during manual patching

### Specific substitutions added during long-tail work

- `\bFemal\b` -> Female, `\bfemal\b` -> female
- `\bEntrace\b` -> Entrance
- `\blabor\b` -> labour (British spelling per LT dictionary setup)
- `(?i)\brdb\b` -> "" (removed, data artifact of unknown meaning)
- `\br&d\b` -> R&D, `\bs&p\b` -> S&P (plain text, in addition to HTML-encoded forms `r&;d`, `s&;p`)
- `\batms\b` -> ATMs
- `(?i)\bvitamin a\b` -> vitamin A (replaced case-sensitive `\bVitamin A\b`)
- `\bexpectancys\b` -> expectancies, `\bdensitys\b` -> densities, `\bindexs\b` -> indices (cleanup from naive pluralization)
- `\bczech republic\b` -> Czech Republic, `\bnetherlands\b` -> Netherlands, `\bkorea\b` -> Korea, `\bslovak republic\b` -> Slovak Republic
- `\bWage workers\b` -> wageworkers (case variant of existing `\bwage workers\b` rule)
- Determiner lookbehinds: all GPE patterns updated with `(?<!\bthe )(?<!\bThe )` to avoid "the the"
- `\bin poorest qunitile\b` fixed to `\bin poorest qu[in]+tile\b` -> "in the poorest quintile" (typo in both original pattern and replacement)
- `(In|in|of) Least developed` — added `In` to capture sentence-initial case

## MongoDB Techniques Used

Throughout the project, various mongosh patterns were used:

- **Sampling**: `$sample` in aggregation pipelines for random document inspection
- **Aggregation**: `$unwind` + `$group` + `$sort` for error frequency analysis; cross-tabulation of rules against template IDs
- **Export**: `forEach(doc => print(JSON.stringify(doc)))` for JSONL export; `JSON.stringify(...toArray())` piped through `jq` for formatted JSON
- **Bulk updates**: `updateMany` with `$addToSet` for per-document rule disabling; `$unset` for clearing fields before regeneration
- **Bulk deletes**: `deleteMany` with `$regex`, `$in`, and compound conditions
- **Array queries**: `$size` for exact length, `"field.N": {$exists: true}` for length >= N, `$expr` with `$size` for arbitrary comparisons
- **Regex in queries**: `$regex` with `$options: "i"` for case-insensitive matching
- **Note**: `$replaceAll` in aggregation pipeline updates did not work (likely MongoDB version limitation) — Python-based fixes used instead

## Notes

- EN_UNPAIRED_BRACKETS count is non-deterministic across full sweeps due to batched concatenation changing how LT parses sentence boundaries. The genuinely broken captions (with actual unpaired brackets) were identified separately via regex and deleted
- ENGLISH_WORD_REPEAT_BEGINNING_RULE is always a false positive when batching unrelated captions — three adjacent captions starting with "The" triggers it
- Full re-checks after LT server restarts can cause MORFOLOGIK regressions if `ignore.txt` is not re-appended to `spelling.txt` before restart
- The `search_templates` function picks the template with the most matched regex groups (`max(..., key=lambda x: len(x[1]))`), which means templates with more groups can incorrectly steal matches from more specific templates with fewer groups — this is what caused the template 44/37 conflict
- The `check_grammar` function has a `template_id` parameter that is accepted but not used in the return value — it was intended for associating errors with templates but the association is done at the MongoDB level instead
- When querying for unchecked docs after regeneration, use `n_errors: {$exists: false}` rather than `lt_matches: {$exists: false}` — the latter may not work if the field was previously set and then unset

## Burndown Summary

| Errors | Milestone |
|---|---|
| 15,924,664 | Baseline |
| 8,155,498 | CONSECUTIVE_SPACES eliminated |
| 3,507,867 | Whitespace + determiners + punctuation |
| 1,494,577 | Spelling + hyphens |
| 1,046,313 | NODT_DOZEN + WHITESPACE_RULE |
| 538,769 | Repeated words + diacritics + superlatives |
| 345,067 | Compounds + ONE_PLURAL |
| 255,340 | Country aliases + agreement fixes |
| 199,804 | Top-two pluralization + misc |
| 5,846 | Full re-check after LT restart with ignore.txt |
| 1,583 | Manual patching |
| 359 | Near-zero |
| ~0 | Final state (pending confirmation) |
