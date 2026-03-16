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
    (r"\bbranche\b", "branches"),
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
    # Casing of organization names
    (r"\binternational monetary fund\b", "International Monetary Fund"),
    (r"\bworld bank\b", "World Bank"),
    # Specific product/context fixes
    (r"\bPrive\b", "Price"),
    (r"\bprive\b", "price"),
    (r"\bari treatment\b", "ARI treatment"),
    (r"\bcpia rating\b", "CPIA rating"),
    (r"\bdac donors\b", "DAC donors"),
    (r"Mauriti the US", "Mauritius"),
    (r"\bUSable\b", "usable"),
    (r"\bUSed\b", "used"),
    (r"\bUSers\b", "users"),
    (r"\bUSe\b", "use"),
    (r"\bUSing\b", "Using"),
    (r"\brdb\b", ""),
    (r"\bUndisbursed\b", ""),
    (r"\bVitamin A\b", "vitamin A"),
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
    (r"s&;p", "S&P"),
    (r"R&amp", "R&"),
    (r"r&amp", "r&"),
]

_DETERMINERS_GPES = [
    (r"\bMiddle East\b", "the Middle East"),
    (r"\bBahamas\b", "the Bahamas"),
    (r"\bCayman Islands\b", "the Cayman Islands"),
    (r"\bCentral African Republic\b", "the Central African Republic"),
    (r"\bChannel Islands\b", "the Channel Islands"),
    (r"\bComoros\b", "the Comoros"),
    (r"\bCongo\b", "the Congo"),
    (r"\bCzech Republic\b", "the Czech Republic"),
    (r"\bDominican Republic\b", "the Dominican Republic"),
    (r"\bGambia\b", "the Gambia"),
    (r"\bIsle of Man\b", "the Isle of Man"),
    (r"\bMaldives\b", "the Maldives"),
    (r"\bMarshall Islands\b", "the Marshall Islands"),
    (r"\bNetherlands\b", "the Netherlands"),
    (r"\bPhilippines\b", "the Philippines"),
    (r"\bSlovak Republic\b", "the Slovak Republic"),
    (r"\bSolomon Islands\b", "the Solomon Islands"),
    (r"\bTurks and Caicos Islands\b", "the Turks and Caicos Islands"),
    (r"\bUnited Arab Emirates\b", "the United Arab Emirates"),
    (r"\bUnited Kingdom\b", "the United Kingdom"),
    (r"\bUnited States\b", "the United States"),
    (r"\bVirgin Islands\b", "the Virgin Islands"),
    (r"\bWest Bank\b", "the West Bank"),
    (r"\bCaribbean\b", "the Caribbean"),
]

_OTHER_DETERMINERS = [
    (r"\b(in|of) Least developed\b", r"\1 the least developed"),
    (r"\bin largest city\b", "in the largest city"),
    (r"\b(in|of) Labor Market\b", r"\1 the labor market"),
    (r"\bin poorest qunitile\b", "in the poorest qunitile"),
    (r"\bIn Isle of Man\b", "In the Isle of Man"),
    (r"\bIn Turks and Caicos Islands\b", "In the Turks and Caicos Islands"),
    (r"\bin Isle of Man\b", "in the Isle of Man"),
    (r"\bin Turks and Caicos Islands\b", "in the Turks and Caicos Islands"),
    (r"\bof Isle of Man\b", "of the Isle of Man"),
    (r"\bof Turks and Caicos Islands\b", "of the Turks and Caicos Islands"),
    (r"\bpoorest\b", "the poorest"),
    (r"\blargest\b", "the largest"),
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
    (r"\bYemen, Rep\..*?\b", "Yemen"),
    (r"\bEgypt, Arab Rep\..*?\b", "Egypt"),
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
]

_REPEATED_WORDS = [
    (r"\btotal Total\b", "total"),
    (r"\bTotal total\b", "Total"),
    (r"\btotal total\b", "total"),
    (r"\bTotal Total\b", "Total"),
    (r"\bin in\b", "in"),
    (r"\baverage Average\b", "average"),
    (r"\bexpenses Expenses\b", "expenses"),
    (r"\bproduction Production\b", "production"),
    (r"\brate Rate\b", "rate"),
    (r"\bsavings Savings\b", "savings"),
]

_GENDER = [
    (r"\bfemales population\b", "female population"),
    (r"\bmales population\b", "male population"),
]

_MISC = [
    (r"\blitre\b", "liter"),
    (r"\baverage per year\b", "average annual"),
    (r"\bTwenty-\s+foot Equivalent\b", "Twenty-foot Equivalent"),
    (r"\( 0 = weak", "(0 = weak"),
    (r"mm \)", "mm)"),
]

_WHITESPACE = [
    (r"(\S)\(", r"\1 ("),  # space before bracket
    (r"\s+\(", " ("),      # collapse multiple spaces before bracket
    (r"\s+", " "),         # collapse repeated whitespace
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
    + _GENDER
    + _MISC
    + _WHITESPACE
    + _DEDUP_DETERMINERS
)

# Pre-compile all patterns
_COMPILED_SUBS = [(re.compile(pat), repl) for pat, repl in SUBSTITUTIONS]


def fix_caption(caption):
    """Apply all text substitutions to a caption string."""
    for pat, repl in _COMPILED_SUBS:
        caption = pat.sub(repl, caption)
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
