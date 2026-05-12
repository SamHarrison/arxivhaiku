#!/usr/bin/env python3
"""Step 4: quality filters.

Drop rules (CLAUDE.md §Step 4):
  - LDNOOBW profanity (substring; case-insensitive)
  - Manual brand blocklist
  - Plural-with-singular: word ends in 's' and a 3-5 letter singular is in the
    candidate set
  - Past-tense-with-base: ends in 'ed' and base verb exists in candidate set
    (exception: WordNet-adjectival forms)
  - Gerund-with-base: ends in 'ing' and base verb exists
    (exception: WordNet-adjectival forms)
  - Comparative/superlative: ends in 'er'/'est' and base form exists
  - Body parts / medical / clinical
  - Demographic / religion / political identity

Every dropped word goes to data/04_quality_filtered.tsv with drop_reason.
Words are NOT physically removed at this stage — we keep them with drop_reason
so downstream can audit. The selection step filters drop_reason.notna()."""
from __future__ import annotations
import re
import sys
from pathlib import Path
import pandas as pd
from nltk.corpus import wordnet as wn

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "03_length_filtered.tsv"
OUT = ROOT / "data" / "04_quality_filtered.tsv"
RAW = ROOT / "data" / "raw"


# --- Manual blocklists ---

# Brands: drop even if dictionary words. Extended from CLAUDE.md starter.
BRAND_BLOCKLIST = {
    # CLAUDE.md starter list
    "apple", "delta", "prime", "dodge", "tesla", "shell", "total", "sharp",
    "sears", "kraft", "cisco", "intel", "adobe", "lotus", "pixar", "nokia",
    "mazda", "lexus", "honda", "virgin", "target", "mango", "ralph", "prada",
    "gucci", "tommy", "omega", "rolex", "swiss", "fiber", "fanta", "smart",
    "vichy", "bayer", "basic", "motel", "exxon", "abbey", "swatch", "casio",
    "kodak", "atari", "sanyo", "amazon", "google", "oracle", "redhat", "vmware",
    "fender", "gibson", "marlin", "ranger", "bronco", "taurus", "corona",
    "modelo", "patron", "prozac", "xanax", "viagra", "tylenol", "advil",
    "motrin", "boeing", "airbus",
    # Additional brands encountered during build
    "ebay", "yahoo", "ralph", "rolls", "buick", "lexus", "subaru", "toyota",
    "ford", "chevy", "nasa", "yelp", "uber", "lyft", "stark", "wayne",
    "trump", "obama", "biden", "bezos", "musk", "nestle", "kraft", "tesla",
    "ikea", "lego", "marvel", "disney", "netflix", "spotify", "venmo",
    "paypal", "stripe", "bitcoin", "ether", "solana", "ripple", "binance",
    "kleenex", "xerox", "thermos", "velcro", "tabasco", "pepsi", "spam",
    "google", "alexa", "siri", "cortana", "twitch", "reddit", "vimeo",
    "skype", "zoom", "slack", "github", "gitlab", "linux", "ubuntu", "fedora",
    "debian", "django", "flask", "rails", "azure", "lambda",  # cloud/tech
    "nestl", "pepsi", "audi", "bmw", "lexus", "rover", "harley", "ducati",
    "vespa", "fiat", "honda", "kia", "lexus", "mini", "tata", "volvo",
    "pyrex", "yamaha", "denon", "garmin", "fitbit", "redbull",
    "nike", "puma", "vans", "adidas", "converse", "nike", "swoosh",
    "lucite", "kevlar", "lycra", "nylon", "spandex", "rayon",
    "rolex", "fossil", "gucci", "armani", "chanel",
    "splenda", "asus", "dell", "lenovo", "acer",
    # Award names / proper-noun-ish
    "oscar", "emmy", "nobel", "tony", "grammy",
}

# Formal/clinical adjectives — CLAUDE.md starter, extended
FORMAL_ADJ_BLOCKLIST = {
    "viable", "optimal", "nominal", "fiscal", "axial", "modal", "civic",
    "urban", "legal", "formal", "lateral", "neutral", "partial", "mutual",
    "valid", "robust", "static", "generic", "atomic", "kinetic", "organic",
    "chronic", "acute", "latent", "implicit", "explicit", "discrete",
    "finite", "definite", "concrete",  # corp/legal feeling
    "annual", "binary", "linear", "manual", "median", "metric", "minor",
    "major", "marine", "mental", "moral", "nasal", "naval", "neural",
    "ocular", "penal", "polar", "postal", "rural", "social", "solar",
    "spinal", "subtle", "tactic", "tonal", "tropic", "verbal", "vital",
    "vocal", "thermal", "tribal", "racial",
    # Corp/tech jargon adjectives
    "agile", "scrum", "lean", "kanban", "iso", "raw", "beta", "alpha",
}

# Abstract/corporate noun blocklist — CLAUDE.md starter, extended
ABSTRACT_NOUN_BLOCKLIST = {
    "factor", "system", "method", "policy", "region", "entity", "concept",
    "metric", "vector", "matrix", "module", "schema", "vendor", "client",
    "server", "agent", "action", "status", "output", "input", "format",
    "record", "search", "source", "target", "sample", "sector", "segment",
    "budget", "profit", "margin", "asset", "share", "equity",
    "thing", "stuff", "issue", "case", "fact", "point", "term", "type",
    "kind", "form", "way", "rate", "ratio", "scope", "phase", "stage",
    "trend", "topic", "theme", "trait", "merit", "ethic", "norm", "rule",
    "duty", "task", "goal", "plan", "scheme", "intent", "logic",
    "data", "info", "stat", "model", "trial", "audit", "cycle", "scale",
    "level", "tier", "grade", "class", "rank", "rate", "score", "value",
}

# Body parts / medical / anatomy — drop from noun pool
BODY_MEDICAL = {
    "liver", "colon", "tumor", "ulcer", "nerve", "spine", "bowel", "lung",
    "heart", "lungs", "throat", "tongue", "thigh", "groin", "torso",
    "thumb", "elbow", "ankle", "wrist", "skull", "femur", "pelvis", "uterus",
    "ovary", "testis", "vagina", "vulva", "penis", "scrotum", "rectum",
    "anus", "anal", "nipple", "areola", "labia", "clitor", "glans",
    "kidney", "gland", "spleen", "tonsil", "tendon", "muscle", "bone",
    "blood", "plasma", "marrow", "tissue", "membrane",
    "tumour", "cancer", "stroke", "polyp", "lesion", "wound", "scar",
    "bruise", "rash", "boil", "cyst", "sore", "burn", "wart",
    "fever", "cough", "cramp", "spasm", "ache", "pain",
    "virus", "germ", "fungus", "mold", "mould",
    "vomit", "feces", "fecal", "urine", "sweat", "mucus", "saliva",
    "phlegm", "snot", "pus", "drool", "pee", "poop", "fart", "burp",
    "rectum", "septum", "cornea", "iris", "retina", "pupil",
    "vein", "artery", "vessel", "fibre", "fiber",
    # Diseases/conditions
    "rabies", "tetnus", "ebola", "polio", "mumps", "measles", "lupus",
    "gout", "asthma", "edema", "anemia", "sepsis", "shock", "trauma",
}

# Demographics / religion / politics
DEMOGRAPHIC = {
    "negro", "honkey", "honky", "cracker", "yankee",
    "gypsy", "redneck", "papist", "infidel", "heathen", "pagan",
    "muslim", "hindu", "jewish", "christian", "catholic", "atheist",
    "tory", "whig", "nazi", "fascist", "leftie", "lefty",
    "tribe", "tribal", "creed", "race", "racial", "ethnic", "caste",
    "harlem", "ghetto", "barrio", "shtetl", "favela",
    "queer", "tranny",  # reclaimed/slur — too risky for random pairing
    "gypsy", "kraut", "gook", "wog", "spic", "chink",  # ethnic slurs
    "kike", "nip", "jap", "jew",  # religious/ethnic slurs
    "dago", "wop", "polack", "paki",
    "redski", "savage", "primitive",
    "mason", "papal",
    "kushi", "shvar",  # foreign-language slurs that surface in EN lists
    # Religions / sects (extending CLAUDE.md demographic rule)
    "shinto", "bahai", "jain", "amish", "quaker", "sufi", "sikh", "shia",
    "sunni", "wahab", "wahabi", "salafi", "zen", "tao", "taoism",
    "vedic", "hindu", "judaic", "tantra", "tantric", "voodoo",
    "kabbal", "torah", "koran", "quran", "psalm", "bible", "rabbi",
    "imam", "monk", "nun", "swami", "guru", "zen", "deist",
    # Hot-button proper nouns / political figures
    "hitler", "stalin", "lenin", "mao", "trump", "obama", "biden",
    "putin", "kim", "castro", "thatcher", "bush", "reagan", "nixon",
    "kennedy", "clinton", "johnson", "carter",
    # Country/region words that sneak in (lowercase form)
    "seoul", "tokyo", "paris", "miami", "boston", "lagos", "cairo",
    "dubai", "denver", "moscow", "beijing", "kabul", "havana",
    "iran", "iraq", "syria", "libya", "yemen", "haiti", "cuba",
    "china", "japan", "egypt", "spain", "italy", "korea", "brazil",
    "ghana", "kenya", "sudan", "tibet", "tonga", "samoa", "guam",
    "zaire", "congo", "qatar", "oman", "burma", "nepal", "bhutan",
    "ceylon", "norse", "saxon", "celtic", "aryan",
    # Acronyms / org names that look like words
    "nasa", "fbi", "cia", "nsa", "dea", "irs", "nist", "nato", "opec",
    "aids", "hiv", "covid", "ebola", "zika", "sars", "mrsa",
    # Demonyms / nationality adjectives — all problematic in random pairings
    "indian", "irish", "polish", "french", "german", "arab", "asian",
    "afro", "latin", "anglo", "anglo", "saxon", "celtic", "norse",
    "greek", "roman", "slavic", "romany", "berber", "bantu",
    "hindi", "urdu", "tamil", "thai", "malay", "khmer", "korean",
    "iraqi", "irani", "afghan", "uzbek", "kurd", "bosnia",
    "boer", "zulu", "creole", "cajun", "tatar", "magyar",
    "uigur", "uighur", "hutu", "tutsi", "ainu",
    # Religious adjectives
    "papal", "monkly", "saintly", "cleric",
    # Additional demonyms / proper-noun-style demographics
    "maori", "ethiop", "ethnic", "racism", "racist", "sexism",
    "ageism", "homosex", "ableism",
    # Comprehensive demonym list (nationalities, languages, peoples)
    # Used as a hard blocklist because the proper-noun heuristic has
    # imperfect recall for words with mixed lexnames.
    "afghan", "african", "albanian", "algerian", "american", "arab", "arabian",
    "argentine", "asian", "aussie", "austrian", "aztec",
    "bahai", "bantu", "basque", "belgian", "bengali", "berber", "bolivian",
    "bosnian", "brazil", "british", "briton", "bulgar", "burmese",
    "cajun", "celt", "celtic", "chilean", "chinese", "cuban", "creole",
    "croat", "czech",
    "danish", "delian", "doric", "dutch",
    "english", "eskimo", "ethiop",
    "fijian", "filipi", "finnish", "flemish", "french",
    "gaelic", "german", "greek", "gypsy",
    "haitian", "hebrew", "hindi", "hindu", "hispanic", "hutu",
    "iberian", "ibsen", "indian", "iranian", "iraqi", "irish", "italian",
    "jain", "japanese", "javan", "jordan", "jewish",
    "kashmir", "khmer", "korean", "kurd", "kuwaiti",
    "lao", "laotian", "latin", "lao",
    "magyar", "malay", "maltese", "manx", "maori", "mayan", "mexican",
    "moor", "moorish", "moroccan", "muslim",
    "navajo", "negro", "nepali", "nigerian", "nordic", "norman", "norse",
    "norwegian",
    "oriental",
    "pacifist",  # also too political
    "paki", "palest", "panamanian", "papuan", "parsee", "persian", "polish",
    "portug", "puerto",
    "quaker",
    "roma", "roman", "romany", "russian", "rwandan",
    "samoan", "saxon", "scots", "scotch", "scottish", "semite", "semitic",
    "serbian", "sherpa", "shia", "shiite", "shinto", "sikh", "slavic", "slav",
    "slovak", "somali", "spanish", "sudan", "sunni", "swede", "swiss",
    "syrian",
    "tamil", "tatar", "thai", "tibetan", "tongan", "turk", "turkish", "tutsi",
    "uighur", "ukrain", "uzbek",
    "vatican", "vietnam",
    "walloon", "welsh",
    "yankee", "yemeni", "yiddish",
    "zulu",
    # Religious / cult / sect terms
    "shiism", "shiite", "sufism", "deism", "theism", "creed",
    "christ", "jesus", "satan", "allah", "yahweh", "vishnu", "shiva",
    "buddha", "krishna", "moses", "noah", "jonah", "judas", "mary",
    "pope", "popes", "rabbi", "imam", "mufti", "lama", "monk",
    "shrine", "altar", "crypt", "abbey", "abbess", "cantor", "priest",
    "hymn", "psalm", "chant", "vesper",
    # Hate groups / extremist
    "klan", "kkk", "nazi", "nazis", "nazism", "fascism", "fascist",
    "isis", "qaeda", "taliban", "junta", "putsch",
    # Demonym variants and ethnic identifiers
    "aryan", "anglo", "gaelic", "frank", "franks", "saxon", "norse",
    "magyar", "scot", "scots", "kurd", "kurds", "ainu", "boer",
    "sicil", "sikh", "sikhs", "amish", "ulema",
    # Dangerous historical references
    "shoah", "gulag", "lynch", "noose", "scalp", "raped", "raper",
    # Extremism/violence further
    "jihad", "fatwa", "hadith", "sharia",
    # Body-part/medical noun expansion
    "femur", "tibia", "ulnar", "uvula", "cervix", "vagina",
    "bowels", "rectal", "rectum", "septic", "septum",
    "embryo", "foetus", "fetus",
    # Disease
    "polio", "ebola", "syphi", "gonor", "herp", "herpes", "pox",
    "tumor", "tumour", "edema", "lupus", "ulcer",
    # Slurs / offensive group references
    "mammy", "uncle",  # mammy is a known slur
    "schizo", "psycho", "moron", "idiot", "retard", "spaz",
    "pommy", "pommie", "yob", "yobs", "limey", "limeys",
    "nigger", "negro", "darky", "darkie", "blacky",  # ensure full coverage
    "wetbk", "spick", "spik",
    "hooker", "whore", "slut",
    "bint", "tart", "skank", "thot",
}

# Death, weapons, violence — keep aliases family-friendly
VIOLENCE = {
    "killer", "murder", "rapist", "kill", "stab", "shoot", "slash",
    "rifle", "pistol", "bullet", "bomb", "bombs", "grenade",
    "saber", "sabre", "dagger", "blade", "sword", "musket",
    "noose", "gallow", "scaffold", "corpse", "carcas", "carrion",
    "casket", "coffin", "morgue", "grave", "tomb",
    "war", "warrior", "soldier", "troop", "siege",
    "cancer", "death", "dead", "die", "died", "dying", "dies",
    "hostag", "kidnap", "ransom",
    "racist", "sexist", "bigot",
    "demon", "satan", "devil", "hell",
}

# Words too sexual or scatological for random pairing
SEXUAL_SCATO = {
    "sexy", "horny", "naked", "nude", "lewd", "smut",
    "boob", "booty", "butt", "cheek",  # body parts in suggestive pairings
    "thong", "panty", "bikini", "lingerie",
    "orgy", "kink", "fetish", "porn", "smut",
    "harem", "hooker",
    "sperm", "semen", "ovum",
    "lust", "lusty",
    "nooky", "nookie", "prick", "pricks", "wank", "tit", "tits",
    "tush", "ass", "asses", "rump", "humped", "humpy",
    "jock", "jocks", "schlong", "phalli",
}


def load_google_top(n: int = 10000) -> set[str]:
    return set(
        w.strip().lower()
        for w in (RAW / "google_10000.txt").read_text().splitlines()
        if w.strip()
    )


def load_common_words() -> set[str]:
    """Common words (used to NOT flag as proper noun)."""
    out: set[str] = set()
    for fname in ("wordle_answers.txt", "wordle_allowed_guesses.txt", "eff_large_wordlist.txt", "bip39_english.txt"):
        for line in (RAW / fname).read_text().splitlines():
            line = line.strip()
            if "\t" in line: line = line.split("\t")[-1]
            if line: out.add(line.lower())
    return out


def load_ldnoobw() -> set[str]:
    """LDNOOBW: load profanity blocklist (lowercase, exact match — not substring,
    because substring matching causes massive false positives like 'class' matching 'ass')."""
    s = set()
    for line in (RAW / "ldnoobw_en.txt").read_text().splitlines():
        line = line.strip().lower()
        if line and " " not in line:  # keep only single-word entries
            s.add(line)
    return s


def is_wordnet_adjectival_participle(word: str) -> bool:
    """Has a WordNet adjective synset where it's used as adjective (not just past-tense form).
    Heuristic: at least one ADJ or ADJ_SAT synset exists for the surface form."""
    return bool(wn.synsets(word, pos=wn.ADJ)) or bool(wn.synsets(word, pos=wn.ADJ_SAT))


def looks_like_proper_noun(word: str, google_top: set[str], common_set: set[str]) -> bool:
    """Heuristic: a word is likely a proper noun.

    Uses WordNet's `instance_hypernyms()` — the canonical proper-noun marker
    in WordNet ontology. A synset with instance_hypernyms means "this is an
    instance of X" rather than "this is a kind of X". E.g., Edison
    instance_of(inventor); Pangaea instance_of(continent).

    Rules (any one triggers proper-noun flag):
      A) ALL noun synsets have instance_hypernyms (e.g., edison, pangaea, bennett).
      B) Lexnames ⊆ {noun.person, noun.location, noun.communication} AND
         word not in common_set.
      C) Has any synset that is an instance, AND lexnames ⊆ proper_lex.

    'friend' has no instance_hypernyms → NOT flagged.
    'italian' (noun.person+noun.communication) → flagged by rule B.
    'edison' (all instances) → flagged by rule A.
    """
    syns = wn.synsets(word, pos=wn.NOUN)
    if not syns:
        return False
    # Rule A: all synsets are instances
    instance_count = sum(1 for s in syns if s.instance_hypernyms())
    if instance_count == len(syns):
        return True
    # Rule B: all lexnames are proper-leaning and word isn't a common-list word
    lex = {s.lexname() for s in syns}
    proper_lex = {"noun.person", "noun.location", "noun.communication"}
    if lex.issubset(proper_lex):
        if word not in common_set:  # common_set includes wordle/eff/bip39 but NOT google
            return True
    # Rule B': demonym signature — noun.person AND noun.communication AND
    # nothing else outside proper_lex. This is the WordNet pattern for
    # nationality words (dutch, french, italian, indian). These should be
    # flagged even if they appear in common_set because the demonym usage
    # is the dominant one.
    if {"noun.person", "noun.communication"}.issubset(lex) and lex.issubset(proper_lex):
        return True
    # Rule C: majority of synsets are instances (e.g., mars has 2 of 4 → still proper-feel)
    if instance_count >= 2 and instance_count / len(syns) >= 0.5:
        # Also require word not be in common set (protects 'march' etc.)
        if word not in common_set:
            return True
    # Rule D: any synset is an instance AND no non-proper lex
    if instance_count > 0 and lex.issubset(proper_lex | {"noun.object"}):
        return True
    # Rule E: any synset is an instance AND word not in common — catches
    # `merlin` (1 instance + 1 animal), `procyon` (1 instance + 1 animal)
    # when they aren't common-list words. We use a stricter common test
    # here: only google_top counts (NOT wordle, because some proper nouns
    # are in wordle).
    if instance_count > 0 and word not in google_top:
        return True
    return False


def lemma_exists(form: str) -> bool:
    """Check if a candidate base form has any WordNet entry."""
    return bool(wn.synsets(form))


def main() -> int:
    df = pd.read_csv(IN, sep="\t", keep_default_na=False, na_values=[])
    df["word"] = df["word"].astype(str)
    # Defensive: drop any rows whose word isn't 4-7 a-z chars
    bad_word = ~df["word"].str.match(r"^[a-z]{4,7}$")
    if bad_word.any():
        print(f"WARNING: dropping {bad_word.sum()} malformed word rows: {df[bad_word].word.tolist()[:5]}")
        df = df[~bad_word].reset_index(drop=True)
    print(f"input: {len(df)} candidates")

    candidate_set = set(df.word)
    drop_reason: dict[str, str] = {}
    google_top = load_google_top()
    common_set = load_common_words()

    # LDNOOBW — exact match
    ldnoobw = load_ldnoobw()
    for w in df.word:
        if w in ldnoobw:
            drop_reason.setdefault(w, f"profanity:ldnoobw_exact")

    # Substring profanity: certain LDNOOBW words are SAFE to substring-match
    # (long, unambiguous). This catches 'bitchy', 'fuckup', 'asshole-style' forms.
    SUBSTRING_PROFANITY = (
        "bitch", "fuck", "shit", "cunt", "cock", "dick",
        "ass", "anal", "anus", "boob", "tits", "porn",
        "wank", "rape", "fag", "dyke", "slut", "whore",
        "klan", "nazi", "kkk", "spic", "chink", "gook",
        "kike", "wetb", "negro", "darki",
        "scat", "horny",
    )
    for w in df.word:
        if w in drop_reason: continue
        # Skip 'ass' substring check — too many false positives ('class', 'bass')
        for sub in SUBSTRING_PROFANITY:
            if sub == "ass":
                # only match if word IS 'ass*' or *'-ass' (handled by pair audit)
                if w == "ass" or w.startswith("asse") or w.startswith("assh"):
                    drop_reason.setdefault(w, f"profanity_substr:{sub}")
                    break
            elif sub in w:
                drop_reason.setdefault(w, f"profanity_substr:{sub}")
                break

    # Brand blocklist
    for w in df.word:
        if w in BRAND_BLOCKLIST:
            drop_reason.setdefault(w, "brand:manual")

    # Body/medical
    for w in df.word:
        if w in BODY_MEDICAL:
            drop_reason.setdefault(w, "body_medical:manual")

    # Demographics
    for w in df.word:
        if w in DEMOGRAPHIC:
            drop_reason.setdefault(w, "demographic:manual")

    # Violence
    for w in df.word:
        if w in VIOLENCE:
            drop_reason.setdefault(w, "violence:manual")

    # Sexual/scato
    for w in df.word:
        if w in SEXUAL_SCATO:
            drop_reason.setdefault(w, "sexual_scato:manual")

    # Proper nouns: applied to both noun-tagged and adj-tagged candidates
    # because demonym adjectives (dutch, indian, french) have noun forms
    # that fail the proper-noun heuristic.
    for w in df.word:
        if w in drop_reason:
            continue
        if looks_like_proper_noun(w, google_top, common_set):
            drop_reason.setdefault(w, "proper_noun:lex_heuristic")

    # Plural-with-singular: -s and 3-5 letter base in set
    for w in df.word:
        if w in drop_reason:
            continue
        if len(w) >= 5 and w.endswith("s") and not w.endswith("ss"):
            # Try removing 's'
            base_s = w[:-1]
            # Try removing 'es' for -ches/-shes/-xes/-ses/-zes
            base_es = w[:-2] if w.endswith(("ches", "shes", "xes", "ses", "zes")) else None
            # Try -ies → -y (cherries → cherry)
            base_ies = (w[:-3] + "y") if w.endswith("ies") else None
            for base in (base_s, base_es, base_ies):
                if base and 3 <= len(base) <= 5 and base in candidate_set:
                    drop_reason.setdefault(w, f"plural:{base}")
                    break

    # Past-tense (-ed) with base verb. Exception: WordNet-adjectival.
    for w in df.word:
        if w in drop_reason:
            continue
        if len(w) >= 5 and w.endswith("ed"):
            if is_wordnet_adjectival_participle(w):
                continue  # tired, fancy, aged → keep
            # Reference adj list also exempts (haikunator uses 'aged', 'weathered')
            row = df[df.word == w].iloc[0]
            if row.ref_adj:
                continue
            # Base verb candidates: -ed → '' ; -d → '' (for 'used' → 'use'); -ied → -y
            bases = [w[:-2], w[:-1]]  # baked → bake or baked → bak
            if w.endswith("ied"):
                bases.append(w[:-3] + "y")
            for b in bases:
                if 3 <= len(b) <= 5 and lemma_exists(b):
                    drop_reason.setdefault(w, f"past_tense:{b}")
                    break

    # Gerund (-ing) with base verb. Exception: WordNet-adjectival or ref_adj.
    for w in df.word:
        if w in drop_reason:
            continue
        if len(w) >= 5 and w.endswith("ing"):
            if is_wordnet_adjectival_participle(w):
                continue
            row = df[df.word == w].iloc[0]
            if row.ref_adj:
                continue
            bases = [w[:-3], w[:-3] + "e"]  # baking → bak / bake
            for b in bases:
                if 3 <= len(b) <= 5 and lemma_exists(b):
                    drop_reason.setdefault(w, f"gerund:{b}")
                    break

    # Comparative/superlative: drop if base adjective form exists in WordNet
    # (regardless of whether base is in our candidate_set, since the base may
    # be 3 letters which is below our minimum). Protect nouns ending in -er
    # by requiring word to be tagged is_adjective.
    word_to_row = {r.word: r for r in df.itertuples()}
    for w in df.word:
        if w in drop_reason:
            continue
        row = word_to_row[w]
        if not row.wn_adj and not row.ref_adj:
            continue  # noun-only words ending in -er (archer, butler) survive
        if len(w) >= 5 and w.endswith("er"):
            # bigger→big, finer→fine, gooier→goo (irregular vowel-mod handled crudely)
            for b in (w[:-2], w[:-1], w[:-3] + "y" if w.endswith("ier") else None):
                if b and 3 <= len(b) <= 6 and is_wordnet_adjectival_participle(b):
                    drop_reason.setdefault(w, f"comparative:{b}")
                    break
        elif len(w) >= 6 and w.endswith("est"):
            for b in (w[:-3], w[:-2], w[:-4] + "y" if w.endswith("iest") else None):
                if b and 3 <= len(b) <= 6 and is_wordnet_adjectival_participle(b):
                    drop_reason.setdefault(w, f"superlative:{b}")
                    break

    # Formal/clinical (adjective-pool only — but stored regardless)
    for w in df.word:
        if w in drop_reason:
            continue
        if w in FORMAL_ADJ_BLOCKLIST:
            drop_reason.setdefault(w, "formal_clinical:adj_manual")

    # Abstract/corporate (noun-pool tone — but stored regardless; the selection
    # step will tone-score them down rather than hard-drop)
    # Actually: hard-drop only if the word is noun-only. If it has adjective
    # synsets too, the adjective pool might still want it.
    for w in df.word:
        if w in drop_reason:
            continue
        if w in ABSTRACT_NOUN_BLOCKLIST:
            row = df[df.word == w].iloc[0]
            if not row.is_adjective:
                drop_reason.setdefault(w, "abstract_corporate:noun_manual")

    # Commonality column: marks words whose only attestation is the giant
    # english_alpha wordlist. We don't HARD DROP these (would under-supply
    # the pools) but we expose `is_corroborated` so Step 6/7 can prefer
    # corroborated words. Corroborated = appears in any curated source.
    CORROBORATING = {
        "heroku_adj", "heroku_nouns", "haikunatorjs_adj", "haikunatorjs_nouns",
        "moby_adj", "wordle_answers", "wordle_guesses", "google_10000",
        "eff", "bip39", "simple_adjectives",
    }
    df["is_corroborated"] = df.source_set.apply(
        lambda s: int(bool(set(s.split(",")) & CORROBORATING))
    )

    # Hard drop: english_alpha-only noun-only candidates whose WordNet
    # lexnames are entirely within noun.animal/noun.plant. The 4-7 letter
    # expansion gives us enough inventory to remove these obscure biology
    # genus/species names outright (psylla, arundo, cleome, hyrax).
    flags = []
    for row in df.itertuples():
        w = row.word
        srcs = set(row.source_set.split(","))
        if (srcs & CORROBORATING) or row.is_adjective:
            flags.append(0); continue
        if not row.is_noun:
            flags.append(0); continue
        syns = wn.synsets(w, pos=wn.NOUN)
        lex = {s.lexname() for s in syns}
        if lex.issubset({"noun.animal", "noun.plant"}):
            if w not in drop_reason:
                drop_reason.setdefault(w, "biology_genus:hard")
            flags.append(1)
        else:
            flags.append(0)
    df["biology_obscure"] = flags

    # Hard drop: english_alpha-only NOUN-ONLY candidates whose only WordNet
    # lexnames are ABSTRACT (noun.act, noun.state, noun.attribute,
    # noun.communication, noun.cognition, noun.relation, noun.quantity).
    # Keep candidates with at least one CONCRETE lexname (artifact, food,
    # body, animal, plant, object, substance, location) — these are real
    # nouns worth including even if english_alpha is the only source.
    ABSTRACT_LEX = {"noun.act", "noun.state", "noun.attribute",
                    "noun.communication", "noun.cognition", "noun.relation",
                    "noun.quantity", "noun.event", "noun.feeling",
                    "noun.linkdef", "noun.tops", "noun.motive",
                    "noun.possession", "noun.time", "noun.process",
                    "noun.group", "noun.person"}
    for row in df.itertuples():
        w = row.word
        if w in drop_reason: continue
        srcs = set(row.source_set.split(","))
        if (srcs & CORROBORATING) or row.is_adjective: continue
        if not row.is_noun: continue
        syns = wn.synsets(w, pos=wn.NOUN)
        lex = {s.lexname() for s in syns}
        if lex.issubset(ABSTRACT_LEX):
            drop_reason.setdefault(w, "uncorroborated_abstract_noun:hard")

    # Words containing non-letter-only edge cases (shouldn't happen after Step 2 but verify)
    for w in df.word:
        if not re.match(r"^[a-z]{4,7}$", w):
            drop_reason.setdefault(w, "non_alpha")

    # Apply
    df["drop_reason"] = df.word.map(drop_reason).fillna("")
    n_kept = (df.drop_reason == "").sum()
    print(f"dropped: {len(df) - n_kept}; kept: {n_kept}")
    reason_counts = df[df.drop_reason != ""].drop_reason.str.split(":", n=1, expand=True)[0].value_counts()
    print("drop_reason counts:")
    for r, c in reason_counts.items():
        print(f"  {r:30s} {c:>5}")

    df = df.sort_values("word").reset_index(drop=True)
    df.to_csv(OUT, sep="\t", index=False)
    print(f"Wrote {OUT}")

    # adj/noun supply after filtering
    kept = df[df.drop_reason == ""]
    print(f"\nKept supply: {(kept.is_adjective==1).sum()} adj, {(kept.is_noun==1).sum()} nouns, "
          f"{((kept.is_adjective==1)&(kept.is_noun==1)).sum()} both")
    return 0


if __name__ == "__main__":
    sys.exit(main())
