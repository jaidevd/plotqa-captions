"""Text fixes for captions and structural question filters.

Replaces the sed files:
  - remove_structural_qs.sed  (STRUCTURAL_PATTERNS)
  - lt-config/fixes.sed       (merged into SUBSTITUTIONS)
  - data/typos.sed            (merged into SUBSTITUTIONS)
  - data/abbreviations.sed    (merged into SUBSTITUTIONS)
  - data/determiner_gpes.sed  (merged into SUBSTITUTIONS)
"""

import re
from pymongo import MongoClient, UpdateOne
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Structural question patterns (from remove_structural_qs.sed)
# Questions matching any of these are removed before template matching.
# ---------------------------------------------------------------------------

STRUCTURAL_PATTERNS = [
    r"Are all the bars in the graph horizontal \?",
    r"Are the number of bars on each tick of the (X|Y)-axis equal \?",
    r"Are the number of bars per tick equal to the number of legend labels \?",
    r'Does ".*" appear as one of the legend labels in the graph \?',
    r"Does the graph contain any zero values \?",
    r"Does the graph contain grids \?",
    r"Does the line corresponding to .* intersect with the line corresponding to .* \?",
    r"How are the legend labels stacked \?",
    r"How many .* bars are there \?",
    r"How many bars are there \?",
    r"How many different coloured (dot)?lines are there \?",
    r"How many different coloured lines are there \?",
    r"How many dotlines are there \?",
    r"How many legend labels are there \?",
    r"How many lines are there \?",
    r"How many years are there in the graph \?",
    r"In how many cases, is the number of bars for a given .* not equal to the number of legend labels \?",
    r"Is the number of dotlines queal to the number of legend labels \?",
    r"Is the number of lines equal to the number of legend labels \?",
    r"What does the .* represents \?",
    r"Where does the legend appear in the graph \?",
    r"appear as one of the legend labels in the graph \?",
    r"bars? from the (left|right|top|bottom)",
    r"difference between two consecutive major ticks",
    r"major ticks on the Y-axis",
    r"number of bars.*number of legend labels",
    r"scientific E-notation",
    r"label or title of the (X|Y)-axis",
    r"The title of the graph is",
    r"is the title of the graph\.",
    r"The label or title of the (X|Y)-axis is",
    r"The label of the [0-9]+(st|nd|rd|th) group of bars",
]

_STRUCTURAL_RE = re.compile("|".join(f"(?:{p})" for p in STRUCTURAL_PATTERNS))


def is_structural(question_string):
    """Return True if the question is structural and should be filtered out."""
    return bool(_STRUCTURAL_RE.search(question_string))


# ---------------------------------------------------------------------------
# Caption substitutions
# Consolidated from: fixes.sed, typos.sed, abbreviations.sed, determiner_gpes.sed
# Order matters: typos/abbreviations first, then determiners, then cleanup.
# ---------------------------------------------------------------------------

# (pattern, replacement) — applied with re.sub(pattern, replacement, caption)
# All patterns use Python regex syntax.

_TYPOS = [
    # Misspellings
    (r"resorces", "resources"),
    (r"emissisons", "emissions"),
    (r"enforece", "enforce"),
    (r"centeral", "central"),
    (r"conusmption", "consumption"),
    (r"recevied", "received"),
    (r"commerical", "commercial"),
    (r"commercal", "commercial"),
    (r"servies", "services"),
    (r"Maunufacturing", "Manufacturing"),
    (r"Periodicty", "Periodicity"),
    (r"hospiatls", "hospitals"),
    (r"sanitaion", "sanitation"),
    (r"curriences", "currencies"),
    (r"Inverstment", "Investment"),
    (r"Techinal", "Technical"),
    (r"donars", "donors"),
    (r"subsciptions", "subscriptions"),
    (r"chiildren", "children"),
    (r"\bdalay\b", "delay"),
    (r"\bdisimbursed\b", "disbursed"),
    (r"\bmoney investmented\b", "money invested"),
    (r"\blargent city\b", "largest city"),
    (r"\bmatural\b", "natural"),
    (r"\bunderweighted\b", "underweight"),
    (r"\bexpectancys\b", "expectancies"),
    (r"\bdensitys\b", "densities"),
    (r"\bindexs\b", "indices"),
    (r"\bbranche\b", "branches"),
    (r"\bEntrace\b", "Entrance"),
    (r"\bFemal\b", "Female"),
    (r"\bfemal\b", "female"),
    (r"\blabor\b", "labour"),
    (r"(?i)\brdb\b", ""),
    # Casing of country names
    (r"\bbelgium\b", "Belgium"),
    (r"\bsweden\b", "Sweden"),
    (r"\biceland\b", "Iceland"),
    (r"\bitaly\b", "Italy"),
    (r"\bireland\b", "Ireland"),
    (r"\bspain\b", "Spain"),
    (r"\baustralia\b", "Australia"),
    (r"\bfrance\b", "France"),
    (r"\bfinland\b", "Finland"),
    (r"\bswitzerland\b", "Switzerland"),
    (r"\bcanada\b", "Canada"),
    (r"\baustria\b", "Austria"),
    (r"\bpoland\b", "Poland"),
    (r"\bluxembourg\b", "Luxembourg"),
    (r"\bdenmark\b", "Denmark"),
    (r"\bgreece\b", "Greece"),
    (r"\bportugal\b", "Portugal"),
    (r"\bnorway\b", "Norway"),
    (r"\bgermany\b", "Germany"),
    (r"\bnew zealand\b", "New Zealand"),
    (r"\bnetherlands\b", "Netherlands"),
    (r"\bkorea\b", "Korea"),
    (r"\bczech republic\b", "Czech Republic"),
    (r"\bslovak republic\b", "Slovak Republic"),
    # Casing of organization names
    (r"\binternational monetary fund\b", "International Monetary Fund"),
    (r"\bworld bank\b", "World Bank"),
    # Specific product/context fixes
    (r"\bPrive\b", "Price"),
    (r"\bprive\b", "price"),
    (r"\bari treatment\b", "ARI treatment"),
    (r"\bcpia rating\b", "CPIA rating"),
    (r"\bdac donors\b", "DAC donors"),
    (r"\batms\b", "ATMs"),
    (r"Mauriti the US", "Mauritius"),
    (r"\bUSable\b", "usable"),
    (r"\bUSed\b", "used"),
    (r"\bUSers\b", "users"),
    (r"\bUSe\b", "use"),
    (r"\bUSing\b", "Using"),
    (r"(?i)\bvitamin a\b", "vitamin A"),
    (r"\bNumber of enrolments of both sexes\b", "number of enrolments of both sexes"),
]

_ABBREVIATIONS = [
    (r"\bdod\b", "DoD"),
    (r"\bgdp\b", "GDP"),
    (r"\bghg\b", "GHG"),
    (r"\bgni\b", "GNI"),
    (r"\bhfc\b", "HFC"),
    (r"\bibrd\b", "IBRD"),
    (r"\bict\b", "ICT"),
    (r"\bida\b", "IDA"),
    (r"\blpi\b", "LPI"),
    (r"\bnonOECD\b", "non-OECD"),
    (r"\boda\b", "ODA"),
    (r"\bpfc\b", "PFC"),
    (r"\bppg\b", "PPG"),
    (r"\bppp\b", "PPP"),
    (r"\bundp\b", "UNDP"),
    (r"\bunhcr\b", "UNHCR"),
    (r"\bunpbf\b", "UNPBF"),
    (r"\bunrwa\b", "UNRWA"),
    (r"\bwfp\b", "WFP"),
    (r"\bunta\b", "UNTA"),
    (r"\bunaids\b", "UNAIDS"),
    (r"\bimf\b", "IMF"),
    (r"\bhiv\b", "HIV"),
    (r"\buk\b", "UK"),
    (r"\beu\b", "EU"),
]

_HTML_ENTITIES = [
    (r"&amp;", "&"),
    (r"&#39;", "'"),
    (r"r&;d", "R&D"),
    (r"R&;D", "R&D"),
    (r"\br&d\b", "R&D"),
    (r"s&;p", "S&P"),
    (r"\bs&p\b", "S&P"),
    (r"R&amp", "R&"),
    (r"r&amp", "r&"),
]

_DETERMINERS_GPES = [
    (r"(?<!\bthe )(?<!\bThe )\bMiddle East\b", "the Middle East"),
    (r"(?<!\bthe )(?<!\bThe )\bBahamas\b", "the Bahamas"),
    (r"(?<!\bthe )(?<!\bThe )\bCayman Islands\b", "the Cayman Islands"),
    (r"(?<!\bthe )(?<!\bThe )\bCentral African Republic\b", "the Central African Republic"),
    (r"(?<!\bthe )(?<!\bThe )\bChannel Islands\b", "the Channel Islands"),
    (r"(?<!\bthe )(?<!\bThe )\bComoros\b", "the Comoros"),
    (r"(?<!\bthe )(?<!\bThe )\bCongo\b", "the Congo"),
    (r"(?<!\bthe )(?<!\bThe )\bCzech Republic\b", "the Czech Republic"),
    (r"(?<!\bthe )(?<!\bThe )\bDominican Republic\b", "the Dominican Republic"),
    (r"(?<!\bthe )(?<!\bThe )\bGambia\b", "the Gambia"),
    (r"(?<!\bthe )(?<!\bThe )\bIsle of Man\b", "the Isle of Man"),
    (r"(?<!\bthe )(?<!\bThe )\bMaldives\b", "the Maldives"),
    (r"(?<!\bthe )(?<!\bThe )\bMarshall Islands\b", "the Marshall Islands"),
    (r"(?<!\bthe )(?<!\bThe )\bNetherlands\b", "the Netherlands"),
    (r"(?<!\bthe )(?<!\bThe )\bPhilippines\b", "the Philippines"),
    (r"(?<!\bthe )(?<!\bThe )\bSlovak Republic\b", "the Slovak Republic"),
    (r"(?<!\bthe )(?<!\bThe )\bSolomon Islands\b", "the Solomon Islands"),
    (r"(?<!\bthe )(?<!\bThe )\bTurks and Caicos Islands\b", "the Turks and Caicos Islands"),
    (r"(?<!\bthe )(?<!\bThe )\bUnited Arab Emirates\b", "the United Arab Emirates"),
    (r"(?<!\bthe )(?<!\bThe )\bUnited Kingdom\b", "the United Kingdom"),
    (r"(?<!\bthe )(?<!\bThe )\bUnited States\b", "the United States"),
    (r"(?<!\bthe )(?<!\bThe )\bVirgin Islands\b", "the Virgin Islands"),
    (r"(?<!\bthe )(?<!\bThe )\bWest Bank\b", "the West Bank"),
    (r"(?<!\bthe )(?<!\bThe )\bCaribbean\b", "the Caribbean"),
]

_OTHER_DETERMINERS = [
    (r"\b(In|in|of) Least developed\b", r"\1 the least developed"),
    (r"\bin largest city\b", "in the largest city"),
    (r"\b(in|of) Labor Market\b", r"\1 the labor market"),
    (r"\bin poorest qu[in]+tile\b", "in the poorest quintile"),
    (r"(?<!\bthe )(?<!\bThe )\bIsle of Man\b", "the Isle of Man"),
    (r"(?<!\bthe )(?<!\bThe )\bTurks and Caicos Islands\b", "the Turks and Caicos Islands"),
    (r"(?<!\bthe )(?<!\bThe )\bpoorest\b", "the poorest"),
    (r"(?<!\bthe )(?<!\bThe )\blargest\b", "the largest"),
]

_CURRENCY = [
    (r"\bus\$", "USD"),
    (r"\bUS\$", "USD"),
]

_DIACRITICS = [
    ("Sao Tome and Principe", "São Tomé and Príncipe"),
    ("Sao Tome", "São Tomé"),
    ("Cote d'Ivoire", "Côte d'Ivoire"),
    ("Curacao", "Curaçao"),
]

_COUNTRY_ALIASES = [
    (r"\bYemen, Rep\.", "Yemen"),
    (r"\bEgypt, Arab Rep\.", "Egypt"),
    (r"\bthe Gambia, The\b", "the Gambia"),
    (r"(?<=^)Gambia, The\b", "The Gambia"),
    (r"\bGambia, The\b", "the Gambia"),
]

_HYPHENATED = [
    (r"\bsecond highest\b", "second-highest"),
    (r"\bself employed\b", "self-employed"),
    (r"\bwell developed\b", "well-developed"),
    (r"\bNon renewable\b", "Non-renewable"),
    (r"\bnon concessional\b", "non-concessional"),
    (r"\bnonconcessional\b", "non-concessional"),
    (r"\bnon residents\b", "non-residents"),
    (r"\bonduty\b", "on-duty"),
]

_ONE_WORD = [
    (r"\bmoney lenders\b", "moneylenders"),
    (r"\btax payers\b", "taxpayers"),
    (r"\bpeace keepers\b", "peacekeepers"),
    (r"\bwage workers\b", "wageworkers"),
    (r"\bWage workers\b", "wageworkers"),
]

_REPEATED_WORDS_RE = re.compile(r"\b(\w+)\s+(\1)\b", re.IGNORECASE)


def _dedup_word(match):
    """Keep the first occurrence of a repeated word.

    If the repeat is at the start of a sentence (first word is capitalized,
    second is lowercase), keep the capitalized form.
    """
    first, second = match.group(1), match.group(2)
    return first


# Placeholder so SUBSTITUTIONS list still works — the general regex is applied
# separately via _REPEATED_WORDS_RE in fix_repeated_words().
_REPEATED_WORDS = []

_POSSESSIVE_APOSTROPHE = [
    (r"\bunemployed females population\b", "unemployed female population"),
    (r"\bunemployed males population\b", "unemployed male population"),
    (r"\bfemales population\b", "female population"),
    (r"\bmales population\b", "male population"),
    (r"\bBenefits incidence\b", "benefit incidence"),
    (r"\bArmed forces personnel\b", "armed forces"),
]

_ONE_PLURAL_MAP = {
    "years": "year", "countries": "country", "days": "day", "hours": "hour",
}
_ONE_PLURAL_RE = re.compile(
    r"(?i)\b(in|than) 1 (years|countries|days|hours)\b"
)


def _one_plural_repl(match):
    prep = match.group(1)
    noun = _ONE_PLURAL_MAP[match.group(2).lower()]
    return f"{prep} one {noun}"

_MISC = [
    (r"\b(as|in) thousand metric tons\b", r"\1 one thousand metric tons"),
    (r"\blitre\b", "liter"),
    (r"\baverage per year\b", "average annual"),
    (r"\bTwenty-\s*foot Equivalent Units?\s*\(TEU\)", "twenty-foot equivalent units (TEU)"),
    (r"\( 0 = weak", "(0 = weak"),
    (r"mm \)", "mm)"),
]

_WHITESPACE = [
    (r"(\S)\(", r"\1 ("),  # space before bracket
    (r"\s+\(", " ("),      # collapse multiple spaces before bracket
    (r"\s+", " "),         # collapse repeated whitespace
]

_PUNCTUATION = [
    (r'\\\"\s*', ""),        # remove escaped quotes and trailing spaces
    (r'^""+\s*', ""),        # remove leading empty quotes
    (r"\s+\.", "."),         # no space before full stop
    (r"\s+,", ","),          # no space before comma
    (r",(\S)", r", \1"),     # space after comma
    (r"\(\s+", "("),         # no space after opening parenthesis
    (r"\s+\)", ")"),         # no space before closing parenthesis
    (r'\s+"', '"'),          # no space before closing quote
    (r'"\s+', '"'),          # no space after opening quote
]

# Post-determiner cleanup: "the the" → "the"
_DEDUP_DETERMINERS = [
    (r"\bthe the\b", "the"),
    (r"\bThe the\b", "The"),
    (r'"The the\b', '"The'),
]

# All substitutions in order of application
SUBSTITUTIONS = (
    _HTML_ENTITIES
    + _TYPOS
    + _ABBREVIATIONS
    + _CURRENCY
    + _DIACRITICS
    + _COUNTRY_ALIASES
    + _DETERMINERS_GPES
    + _OTHER_DETERMINERS
    + _HYPHENATED
    + _ONE_WORD
    + _REPEATED_WORDS
    + _POSSESSIVE_APOSTROPHE
    + _MISC
    + _WHITESPACE
    + _PUNCTUATION
    + _DEDUP_DETERMINERS
)

# Pre-compile all patterns
_COMPILED_SUBS = [(re.compile(pat), repl) for pat, repl in SUBSTITUTIONS]


_COMPILED_SPELLING = [
    (re.compile(pat), repl)
    for pat, repl in _HTML_ENTITIES + _TYPOS + _ABBREVIATIONS + _CURRENCY
]

_COMPILED_POSSESSIVE = [(re.compile(pat), repl) for pat, repl in _POSSESSIVE_APOSTROPHE]


def fix_possessive(caption):
    """Fix false possessive apostrophe triggers."""
    for pat, repl in _COMPILED_POSSESSIVE:
        caption = pat.sub(repl, caption)
    return caption


def fix_possessive_in_mongo(db="plotqa", collection="captions", chunksize=50_000):
    """Fix possessive apostrophe errors in captions.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    """
    query = {"lt_matches.rule.id": "POSSESSIVE_APOSTROPHE"}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_possessive_batch(batch, coll)
            batch = []
        if batch:
            _fix_possessive_batch(batch, coll)


def _fix_possessive_batch(batch, coll):
    """Apply possessive fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_possessive(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed}},
            )
        )
    coll.bulk_write(ops, ordered=False)


def fix_spelling(caption):
    """Fix typos, abbreviations, HTML entities, and currency symbols."""
    for pat, repl in _COMPILED_SPELLING:
        caption = pat.sub(repl, caption)
    return caption


def fix_spelling_in_mongo(db="plotqa", collection="captions", chunksize=50_000,
                          rule_id="MORFOLOGIK_RULE_EN_US"):
    """Fix spelling in captions that have a specific LT error.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    rule_id : str
        The LT rule ID to target.
    """
    query = {"lt_matches.rule.id": rule_id}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_spelling_batch(batch, coll)
            batch = []
        if batch:
            _fix_spelling_batch(batch, coll)


def _fix_spelling_batch(batch, coll):
    """Apply spelling fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_spelling(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed}},
            )
        )
    coll.bulk_write(ops, ordered=False)


_COMPILED_COMPOUNDS = [(re.compile(pat), repl) for pat, repl in _HYPHENATED + _ONE_WORD]


def fix_compounds(caption):
    """Fix compound words — missing hyphens and words that should be joined."""
    for pat, repl in _COMPILED_COMPOUNDS:
        caption = pat.sub(repl, caption)
    return caption


def fix_compounds_in_mongo(db="plotqa", collection="captions", chunksize=50_000):
    """Fix compound words in captions that have EN_COMPOUNDS_*, WORKER_COMPOUNDS,
    KEEPER_COMPOUNDS, or SECOND_LARGEST_HYPHEN errors.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    """
    query = {"lt_matches.rule.id": {
        "$regex": "^(EN_COMPOUNDS_|WORKER_COMPOUNDS|KEEPER_COMPOUNDS|SECOND_LARGEST_HYPHEN|NON_ANTI_JJ)"
    }}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_compounds_batch(batch, coll)
            batch = []
        if batch:
            _fix_compounds_batch(batch, coll)


def _fix_compounds_batch(batch, coll):
    """Apply compound word fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_compounds(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed}},
            )
        )
    coll.bulk_write(ops, ordered=False)


def fix_one_plural(caption):
    """Fix '1 years' → 'one year', '1 countries' → 'one country', etc."""
    return _ONE_PLURAL_RE.sub(_one_plural_repl, caption)


def fix_one_plural_in_mongo(db="plotqa", collection="captions", chunksize=50_000):
    """Fix 1 + plural noun patterns in captions that have the ONE_PLURAL error.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    """
    query = {"lt_matches.rule.id": "ONE_PLURAL"}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_one_plural_batch(batch, coll)
            batch = []
        if batch:
            _fix_one_plural_batch(batch, coll)


def _fix_one_plural_batch(batch, coll):
    """Apply one-plural fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_one_plural(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed}},
            )
        )
    coll.bulk_write(ops, ordered=False)


_COMPILED_COUNTRY_ALIASES = [(re.compile(pat), repl) for pat, repl in _COUNTRY_ALIASES]


def fix_country_aliases(caption):
    """Replace verbose country names with their common form."""
    for pat, repl in _COMPILED_COUNTRY_ALIASES:
        caption = pat.sub(repl, caption)
    return caption


def fix_country_aliases_in_mongo(db="plotqa", collection="captions", chunksize=50_000):
    """Fix country aliases in captions containing comma-separated country names.

    Targets documents with COMMA_PARENTHESIS_WHITESPACE or DOUBLE_PUNCTUATION
    errors, which are often caused by names like 'Yemen, Rep.' or 'Egypt, Arab Rep.'.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    """
    query = {"$or": [
        {"caption": {"$regex": "Rep\\."}},
        {"caption": {"$regex": "Arab Rep\\."}},
        {"caption": {"$regex": "Gambia, The"}},
    ]}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_country_aliases_batch(batch, coll)
            batch = []
        if batch:
            _fix_country_aliases_batch(batch, coll)


def _fix_country_aliases_batch(batch, coll):
    """Apply country alias fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_country_aliases(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed}},
            )
        )
    coll.bulk_write(ops, ordered=False)


_COMPILED_MISC = [(re.compile(pat), repl) for pat, repl in _MISC]


def fix_misc(caption):
    """Apply miscellaneous text fixes."""
    for pat, repl in _COMPILED_MISC:
        caption = pat.sub(repl, caption)
    return caption


def fix_misc_in_mongo(db="plotqa", collection="captions", chunksize=50_000,
                      rule_id="NODT_DOZEN"):
    """Apply miscellaneous fixes to captions matching a given LT rule.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    rule_id : str
        The LT rule ID to target.
    """
    query = {"lt_matches.rule.id": rule_id}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_misc_batch(batch, coll)
            batch = []
        if batch:
            _fix_misc_batch(batch, coll)


def _fix_misc_batch(batch, coll):
    """Apply misc fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_misc(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed}},
            )
        )
    coll.bulk_write(ops, ordered=False)


_COMPILED_DIACRITICS = [(re.compile(pat), repl) for pat, repl in _DIACRITICS]


def fix_diacritics(caption):
    """Replace ASCII approximations of names with their proper diacritical forms."""
    for pat, repl in _COMPILED_DIACRITICS:
        caption = pat.sub(repl, caption)
    return caption


def fix_diacritics_in_mongo(db="plotqa", collection="captions", chunksize=50_000):
    """Fix diacritics in captions that have any EN_DIACRITICS_REPLACE_* error.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    """
    query = {"lt_matches.rule.id": {"$regex": "^EN_DIACRITICS_REPLACE_"}}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_diacritics_batch(batch, coll)
            batch = []
        if batch:
            _fix_diacritics_batch(batch, coll)


def _fix_diacritics_batch(batch, coll):
    """Apply diacritics fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_diacritics(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed}},
            )
        )
    coll.bulk_write(ops, ordered=False)


_COMPILED_SUPERLATIVE = [(re.compile(pat), repl) for pat, repl in _OTHER_DETERMINERS]


def fix_superlatives(caption):
    """Add missing determiners before superlatives and related phrases."""
    for pat, repl in _COMPILED_SUPERLATIVE:
        caption = pat.sub(repl, caption)
    return caption


def fix_superlatives_in_mongo(db="plotqa", collection="captions", chunksize=50_000):
    """Fix missing determiners before superlatives that have the THE_SUPERLATIVE error.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    """
    query = {"lt_matches.rule.id": "THE_SUPERLATIVE"}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_superlatives_batch(batch, coll)
            batch = []
        if batch:
            _fix_superlatives_batch(batch, coll)


def _fix_superlatives_batch(batch, coll):
    """Apply superlative fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_superlatives(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed}},
            )
        )
    coll.bulk_write(ops, ordered=False)


def fix_repeated_words(caption):
    """Remove consecutive duplicate words, keeping the first occurrence."""
    return _REPEATED_WORDS_RE.sub(_dedup_word, caption)


def fix_repeated_words_in_mongo(db="plotqa", collection="captions", chunksize=50_000):
    """Fix repeated words in captions that have the ENGLISH_WORD_REPEAT_RULE error.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    """
    query = {"lt_matches.rule.id": "ENGLISH_WORD_REPEAT_RULE"}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_repeated_words_batch(batch, coll)
            batch = []
        if batch:
            _fix_repeated_words_batch(batch, coll)


def _fix_repeated_words_batch(batch, coll):
    """Apply repeated word fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_repeated_words(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed}},
            )
        )
    coll.bulk_write(ops, ordered=False)


_COMPILED_WS = [(re.compile(pat), repl) for pat, repl in _WHITESPACE]
_COMPILED_DETERMINERS = (
    [(re.compile(pat), repl) for pat, repl in _DETERMINERS_GPES + _OTHER_DETERMINERS]
    + [(re.compile(pat), repl) for pat, repl in _DEDUP_DETERMINERS]
)


_COMPILED_PUNCT = [(re.compile(pat), repl) for pat, repl in _PUNCTUATION]


def fix_punctuation(caption):
    """Fix spacing around commas, full stops, parentheses, and quotes."""
    for pat, repl in _COMPILED_PUNCT:
        caption = pat.sub(repl, caption)
    return caption.strip()


def fix_punctuation_in_mongo(db="plotqa", collection="captions", chunksize=50_000):
    """Fix punctuation spacing in captions that have the COMMA_PARENTHESIS_WHITESPACE error.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    """
    query = {"lt_matches.rule.id": "COMMA_PARENTHESIS_WHITESPACE"}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_punctuation_batch(batch, coll)
            batch = []
        if batch:
            _fix_punctuation_batch(batch, coll)


def _fix_punctuation_batch(batch, coll):
    """Apply punctuation fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_punctuation(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed}},
            )
        )
    coll.bulk_write(ops, ordered=False)


def fix_determiners(caption):
    """Add missing determiners for geographic proper nouns and other known cases."""
    for pat, repl in _COMPILED_DETERMINERS:
        caption = pat.sub(repl, caption)
    return caption


def fix_determiners_in_mongo(db="plotqa", collection="captions", chunksize=50_000):
    """Fix missing determiners in captions that have the DETERMINER_GEOGRAPHICAL_WORD error.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    """
    query = {"lt_matches.rule.id": "DETERMINER_GEOGRAPHICAL_WORD"}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_determiners_batch(batch, coll)
            batch = []
        if batch:
            _fix_determiners_batch(batch, coll)


def _fix_determiners_batch(batch, coll):
    """Apply determiner fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_determiners(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed}},
            )
        )
    coll.bulk_write(ops, ordered=False)


def fix_whitespace(caption):
    """Collapse consecutive spaces, add space before brackets, and trim."""
    for pat, repl in _COMPILED_WS:
        caption = pat.sub(repl, caption)
    return caption.strip()


def fix_whitespace_in_mongo(db="plotqa", collection="captions", chunksize=50_000,
                            rule_id="CONSECUTIVE_SPACES"):
    """Fix whitespace in captions that have a specific whitespace-related LT error.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    rule_id : str
        The LT rule ID to target, e.g. ``"CONSECUTIVE_SPACES"`` or
        ``"SPACE_BEFORE_PARENTHESIS"``.
    """
    query = {"lt_matches.rule.id": rule_id}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_whitespace_batch(batch, coll)
            batch = []
        if batch:
            _fix_whitespace_batch(batch, coll)


def _fix_whitespace_batch(batch, coll):
    """Apply whitespace fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_whitespace(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed}},
            )
        )
    coll.bulk_write(ops, ordered=False)


def fix_caption(caption):
    """Apply all text substitutions to a caption string."""
    for pat, repl in _COMPILED_SUBS:
        caption = pat.sub(repl, caption)
    caption = fix_repeated_words(caption)
    return caption.strip()


def fix_captions_in_mongo(db="plotqa", collection="captions", chunksize=50_000):
    """Apply text fixes to all captions in MongoDB that haven't been fixed yet.

    Sets ``caption_fixed: true`` on each document after applying fixes,
    so the function is idempotent.

    Parameters
    ----------
    db : str
        Name of the MongoDB database.
    collection : str
        Name of the MongoDB collection.
    chunksize : int
        Number of documents to process per batch.
    """
    query = {"caption": {"$exists": True}, "caption_fixed": {"$exists": False}}
    with MongoClient() as client:
        coll = client[db][collection]
        total = coll.count_documents(query)
        cursor = coll.find(query, {"_id": 1, "caption": 1}).batch_size(chunksize)
        batch = []
        for doc in tqdm(cursor, total=total):
            batch.append(doc)
            if len(batch) < chunksize:
                continue
            _fix_batch(batch, coll)
            batch = []
        if batch:
            _fix_batch(batch, coll)


def _fix_batch(batch, coll):
    """Apply fixes to a batch and write updates."""
    ops = []
    for doc in batch:
        fixed = fix_caption(doc["caption"])
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"caption": fixed, "caption_fixed": True}},
            )
        )
    coll.bulk_write(ops, ordered=False)


if __name__ == "__main__":
    fix_whitespace_in_mongo(rule_id="CONSECUTIVE_SPACES")
