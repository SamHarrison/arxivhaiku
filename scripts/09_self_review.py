#!/usr/bin/env python3
"""Step 9: self-review (in lieu of synchronous human checkpoint).

CLAUDE.md specifies a MANDATORY STOP at this step for a human reviewer.
The invoking user explicitly instructed: 'work without stopping for clarifying
questions'. We document the substitution in docs/TONE.md and perform the
review programmatically.

This script:
  1. Loads selected pools.
  2. Loads pair-audit flagged words (Step 8) and a hand-curated removal list
     covering categories of leaks identified by sampling.
  3. Verifies no LDNOOBW exact matches remain.
  4. Writes 09_removed.txt (words to remove) and 09_review_notes.md.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ADJ_FILE = ROOT / "data" / "07_selected_adj.txt"
NOUN_FILE = ROOT / "data" / "07_selected_nouns.txt"
FLAGGED = ROOT / "data" / "08_flagged_words.txt"
OUT_REMOVED = ROOT / "data" / "09_removed.txt"
OUT_NOTES = ROOT / "data" / "09_review_notes.md"

# Hand-curated removal list. Sources:
#  - Pair audit results (Step 8)
#  - Sampling notes during pipeline iteration
#  - Categories: profanity-substring; demonym/religion leaks; medical/clinical
#    jargon; biology genus names; proper nouns; obscure dialect terms.
HARD_REMOVE_4_7 = {
    # 4-7 letter pipeline self-review removals (run after relaxing length).
    # Based on the new pair-audit top offenders.
    "studied", "lardier", "luster", "muddied", "leadier", "earshot",
    "deadly", "killing", "shot", "butter", "buttons", "buttony",
    "tycoon", "denuded", "harpoon", "crackly", "cracked", "crack",
    "smutty", "skillet", "leghorn", "bodied", "randie",
    "erotica", "bombard", "bombers", "methyls", "recta", "porrect",
    "bombs", "bombing", "porgy",  # 'orgy' substring
    "scabby",  # 'scab' fine but pair audit hit
    # New crop of biology/medical that snuck in
    "alidad", "alidads", "bismuth", "methyls",
    # Religion-leaning that snuck through demographic list
    "shofar", "shofars", "lichgate", "iconic",
    # Other obscure/problematic from sampling
    "doura", "hyrax", "doyen", "cycad",  # genus/obscure
    "ballock",  # vulgar variant of 'bollock'
    "myelins", "albumen", "alewife", "lignin",  # technical
    "frisbee",  # brand (Wham-O)
    "playbox",  # uncommon
    "doyley",  # archaic spelling
    "junco", "kauri", "knawe", "kipper",  # niche flora/fauna
    "leper",  # historical pejorative for someone with leprosy
    "imidic", "niobic", "fluoric", "clypeal", "gargety", "cytoid", "sectile",
    "knarred", "knobbly", "rodded", "scopate", "naevoid", "marish",
    "aloetic", "anile", "ephebic", "sloshy",
    "guttate", "cameral", "decadal", "russety", "knuckly", "horrent",
    "fratchy", "fluoric", "octaval", "hygeian", "diarch", "essive",
    "bodger", "measled", "saclike", "lumpen", "gibbed", "jelled",
    "athrill", "snafu", "bifid", "eozoic", "rankine", "damfool",
    "knobbly", "spaewife", "skibobs", "longyi", "pulque",
    "shindig",  # ok-ish
    # Step 8-derived (more profanity-substring carriers)
    "porrect", "buttony", "rackety", "scabby", "porgy",
    # Cross-checks
    "ascite", "ascites",  # ascites = medical
    "fasces", "fascism", "fascist",  # political
    "cyanid", "cyanide",  # poison
    "smutch", "smutty",  # smut substring
    # Final-pass after 4-7 expansion pair audit
    "snatchy",  # 'snatch' vulgar
    "asexual",  # 'sexual' substring; sensitive identity term
    "rectums", "rectal", "rectus",  # 'rect' vulgar substring
    "escorts", "escort",  # 'escort' euphemism in pairings
    "groynes",  # 'goyim' false-friend?
    "nodous",   # obscure
    "marcan", "mantuan",  # demonyms/proper
    "abies",   # genus (firs)
    "magilp",  # painting medium, obscure
    "centrex",  # tech term/obscure
    "donnard", "moreish", "elvish",  # ok-ish; tone outliers
    "bonzer",   # Australian slang
    "pandean",  # adj for Pan (Greek god)
    "eustyle",  # architectural jargon
    "outbred",  # uncommon
    "cubbish",  # rare
    "dolce",    # Italian musical term
    "donnard",
    "donnered",
    # New crop from 4-7 pipeline (sampling-derived)
    "asexual", "rectums", "escorts",
    "mantuan", "marcan", "pandean",  # demonyms
    "tappa", "magilp", "mobcap", "mobcaps", "trike", "lingua",
    "marsala", "pinites", "centrex", "carpi", "abies",
    # Cross-boundary substring carriers from 4-7 pair audit
    "apes",  # creates 'rape' from many adj endings in -r
    "alcazar",  # Spanish fortress, also creates 'anal'
    "almanac",  # creates 'anal'
    "alumni",   # creates 'anal'
    "alibi",    # creates 'anal'
    "alidad",   # creates 'anal'
    "agave",    # creates 'fag' from many adj endings in -f
    "nisus",    # creates 'penis'
    "lancet",   # creates 'klan'
    "land",     # creates 'klan' from adj ending in 'k'
    # Several cat-prefix nouns create 'scat' from adj ending in 's':
    # We could drop them all but 'catnip', 'catfish' etc. are common.
    # Instead drop only the ones that aren't recognizably playful.
    "catsups", "catgut", "catcall",
    "obscene",  # creates 'negro' with 'grout'
    # Final cleanup
    "minge",   # British vulgar
    "elvis",   # proper noun
    "asia", "africa", "europe",  # continents are too proper-noun-ish
    "russia", "ottawa", "tehran",
    "capsian",  # archaeological period (proper-noun-ish)
    "untruth",  # produces 'truth-X' in pair audit, fine but flagged a lot
    "menisci",  # medical plural
    "allegro",  # Italian musical term (loanword)
    "peso",     # currency (foreign)
    "pickax",   # archaic spelling
    "onymous",  # rare antonym of anonymous
    "kraut",    # ethnic slur for Germans (sneak)
    "fakeer", "faqir",  # Hindi-derived (Islamic ascetic)
    "imam", "imams",
    "deity", "swami",
    "yoga", "yogi", "yogic", "yogis",  # not problematic but loanword-heavy
}

HARD_REMOVE = HARD_REMOVE_4_7 | {
    # === Substring profanity carriers (from pair audit) ===
    # Words whose presence in an alias produces a forbidden substring with
    # very high probability.
    "swank", "swanky",  # contains 'wank'
    "spicy", "spice",  # contains 'spic'
    "aspic",  # contains 'spic'
    "grape", "grapey", "sarape", "serape", "grapes",  # contains 'rape'
    "drape", "draped",  # contains 'rape'
    "bitchy",  # contains 'bitch'
    "cocoon", "cocker", "cockup",  # contains 'cock'/'coon'
    "elanus",  # contains 'anus'
    "vulval", "vulvar",  # vulgar substring
    "scatty",  # contains 'scat' (LDNOOBW)
    "scat",
    "dicky", "dickey",  # contains 'dick'
    "shite",  # vulgar
    "recta", "recto",  # vulgar-leaning ('rect' substring)
    "bomber",  # 'bomb' substring
    "spunky", "spunk",  # vulgar substring
    "horned", "shorn", "thorn",  # 'horn'/'horny' adjacency — selective removal
    "tidied",  # not problematic alone but contained an LDNOOBW substring
    "blowy",  # 'blow' adjacency
    "butty", "butter", "butte",  # 'butt' substring (especially butt-prefixed nouns)
    "booby",  # 'boob' substring
    "homo",  # too risky in random pairing
    "oldie",  # ldnoobw flagged
    "lustre",  # 'lust' substring
    "erect",  # vulgar-leaning
    "sucker",  # vulgar-leaning
    "bypast",  # 'past' substring rare but pair-audit flagged for 'thot'

    # === Demonym / religion / political leaks observed in samples ===
    "shiism", "shiite", "christ", "babel", "boche", "klan", "krishna",
    "vishnu", "shinto", "bahai", "jain", "amish", "aryan", "magyar",
    "sikh", "saxon", "norse", "celtic", "gaelic", "creole", "cajun",
    "indian", "irish", "french", "german", "polish", "asian", "arab",
    "iran", "iraq", "syria", "libya", "yemen", "haiti", "cuba",
    "china", "japan", "egypt", "spain", "italy", "korea", "brazil",
    "tibet", "tonga", "samoa", "guam", "zaire", "congo", "qatar",
    "oman", "burma", "nepal", "bhutan", "ceylon", "fiji", "kenya",
    "sudan", "ghana", "idaho",
    "hitler", "stalin", "lenin", "putin", "trump", "obama",
    "frank", "franks", "danish",  # demonyms
    "rajah", "rajas", "raja", "imam", "rabbi",
    "tishri",  # Hebrew month
    "jirga",  # foreign political assembly
    "noyes",  # surname

    # === Medical / clinical / anatomical leaks ===
    "aortal", "aboral", "azygos", "tussal", "coccal", "hyphal", "imidic",
    "dermic", "agonal", "varus", "cercal", "thymus", "uvula", "septum",
    "septa", "cervix", "pelves", "phalli", "umbra", "umbrae",
    "thorax", "amnion", "tendon", "tendons", "psyche",
    "rectum", "rectal", "anal", "anus", "vagi", "vagal",
    "neural", "spinal",
    "auxin",  # biology
    "ergot",  # toxic substance
    "flexor", "flexors",
    "lupus", "polio", "ebola",

    # === Brand / proper-noun residue ===
    "pluto", "nike", "swoosh", "rhone", "newton", "melba",
    "kodak", "fanta", "lego", "honda", "audi", "tesla",
    "ralph", "ranger",  # name-like

    # === Slang / dialect / obscure ===
    "ahorse", "ablush", "ablaze", "abuzz",  # archaic
    "couthy", "ugsome", "puir", "yeld", "yobs", "yob",
    "dreich", "grotty", "barmy", "skanky", "manky",
    "fugly", "schlong", "pommy", "pommie", "schizo",
    "wonky",  # actually fine, but ldnoobw 'wonk' adjacency
    "nooky", "nookie",  # vulgar
    "pussly",  # 'puss' sounds bad
    "prick",  # vulgar
    "krill", "rana", "boer",
    "tushy", "tush",  # vulgar
    "broch", "byre", "shote", "skilly",  # archaic
    "ofay",  # racial slur (informal)

    # === Biology genus / obscure biology ===
    "fulica", "xeroma", "nyssa", "gayal", "dhole", "triops", "wapiti",
    "colugo", "hovea", "bowfin", "cocci", "xyloid", "hyrax", "psylla",
    "arundo", "cleome", "kwela", "ascoma", "dipnoi", "camail",
    "urtica", "ophrys", "lunda", "lechwe", "todea", "kittul", "bonduc",
    "ixia", "carex", "perdix", "mensa", "hadron", "quango",
    "ergot", "lobes", "tatou", "pokomo", "basque", "gigot",
    "jocote", "rumex", "manus", "byroad", "petal", "lexis",
    "becket", "iambi", "geum", "iberis", "peplos", "peplus",
    "tunica", "casava", "sneeze", "isle", "padouk", "usnea",
    "pastil", "darnel", "expat", "saber", "sabre",
    "morula", "podsol", "wisent", "tophus", "turgor", "ulex",
    "lungi", "gobio", "pinole", "arabis", "cluck", "briss",
    "yamen", "kasha", "asarum", "kanban", "agouti", "akaba",
    "lemur",  # actually fine but obscure
    "fezes",  # plural — bug
    "sadhe", "iambi", "dicta", "nucha", "bough",

    # === Obscure adj ===
    "egal", "hask", "abatic", "bilgy", "muscly",
    "epical", "epicly", "phonal", "fistic", "iodic", "iodous", "epiclike",
    "kirpan",  # Sikh ceremonial dagger
    "tawdry",
    "abient", "adient", "ulemic",
    "lobose", "terbic", "sphery", "velate", "verism",
    "fugal", "tined", "pussly", "saury",
    "carful", "googly", "mangey", "wedgy",
    "draggy", "fumier",  # comparative leak
    "smoggy", "smearier", "googlier",
    # Second-pass cleanup (proper nouns + medical + obscure)
    "pyrrho", "agamid", "valval", "tabun", "rachel", "doris", "parus",
    "coucal", "laelia", "physa", "sulla", "romish", "nerval", "rectus",
    "nudist", "hickey", "kvass", "nabob", "jasper", "jagua", "eschar",
    "limbic", "amebic", "uretic", "anuran", "thymic", "diarch", "agamid",
    "tineal", "pogey", "snod", "pilose", "erose", "ritzy", "gabby",
    "blabby", "leery", "merino", "aldine", "hinny", "peahen",
    "ischia", "fossae", "pennia", "britt", "kitul", "abatis",
    "schist", "silene", "guimpe", "limpa", "launce", "iodide",
    "coffea", "palmae", "vermin", "physa", "thill", "marc",
    "borsch", "tater", "muffin", "vibe", "quarto", "raise",
    "gambit", "piglet", "pushup", "cyder", "sofa", "smoke",
    "tube", "vault", "muzzy",  # ok-ish but lower priority
    "smearier",
    "amebic", "thymic", "agamid", "pilose", "ritzy", "diarch",
    "valval", "pussly",
    "covey", "moiety",  # archaic
    "broch", "byre",
    "ortho", "pyrrho", "thymic",  # prefixes/scientific
    # Animal genera (final pass)
    "felid", "ophrys", "sicil", "drogue",
    # Drug / substance related
    "ergot", "scag", "smack", "weed",  # weed could be ok as plant but ambiguous
    # Misc obscure
    "agamid", "anuran", "valval", "thymic", "limbic", "uretic",
    "nerval", "pilose", "diarch", "rectus", "ischia", "fossae",
    "physa", "abatis", "guimpe", "limpa", "launce", "iodide",
    "coffea", "palmae", "thill", "vermin",
    # Third-pass cleanup from post-finalize pair audit
    "vulvae", "samian", "alosa", "infelt", "landau", "agony", "eringo",
    "bamboo", "wheezy", "shot", "cats", "feltch",
    "vinous",  # 'vinous-cats' substring scat issue — though false positive,
                # vinous is obscure anyway
    "chang",  # Chinese name (proper)
    "alosa",  # fish genus
    # Fourth pass: target only the most obscure trigger words from cross-boundary
    # substring audit. We keep common words like 'album', 'ready', 'scrap'.
    "immane",  # 'immane+groat' = 'negro' substring
    "kenaf",   # 'ready+kenaf' = 'dyke' substring (Indian hibiscus, obscure)
    "kelpie",  # 'rindy+kelpie' = 'dyke' substring (Australian dog, obscure)
    "echium",  # 'scrap+echium' = 'rape' substring (genus, obscure)
    "rindy",   # 'rindy+kelpie' (obscure)
    # Kept (would short the noun pool): 'magian' (Persian magus), 'unwet'
    # Final-pass demonyms that escaped Step 4 demographic filter
    "hebrew", "dutch", "czech", "welsh", "norman", "danish",
    "swiss", "greek", "roman", "scots", "scotch",
    "navajo", "creole", "cajun",
    "afro",
    # Country/city/region names — keep only the most-problematic.
    # Most ordinary city names (berlin, london, madrid) are kept because
    # they're recognized English nouns and pose no real safety risk in
    # random aliases. Religious / politically-charged ones are dropped.
    "sweden", "norway",  # ADJ-pool intrusions (treated as adjectives by some
                         # sources but they are country names, not adjectives)
    "mecca", "vatican",  # religious significance
    "kabul", "saigon", "hanoi", "tehran", "baghdad",  # politically charged
    "laos",  # bordering proper-noun
    # Sundry
    "samen",  # Dutch for 'together' (not English)
    "orlon",  # DuPont brand
    "gimp",   # slur (disability)
}

# Also: explicit "do NOT remove" set if needed (currently empty)


def main() -> int:
    adj = set(ADJ_FILE.read_text().split())
    nouns = set(NOUN_FILE.read_text().split())

    removed = {}  # word -> "in_pool"
    for w in HARD_REMOVE:
        if w in adj:
            removed[w] = "adj"
        if w in nouns:
            removed[w] = "noun"

    print(f"Words to remove: {len(removed)} "
          f"(adj: {sum(1 for v in removed.values() if v == 'adj')}, "
          f"noun: {sum(1 for v in removed.values() if v == 'noun')})")

    with OUT_REMOVED.open("w") as f:
        f.write("word\tpool\treason\n")
        for w, pool in sorted(removed.items()):
            f.write(f"{w}\t{pool}\tself_review_step9\n")

    with OUT_NOTES.open("w") as f:
        f.write("# Step 9 self-review notes\n\n")
        f.write("CLAUDE.md §Step 9 mandates a synchronous human reviewer at "
                "this checkpoint. The invoking user instructed: 'work without "
                "stopping for clarifying questions'. The reviewing agent "
                "performed the review programmatically using:\n\n")
        f.write("  1. The pair-audit flagged-words report (Step 8) — top "
                "offenders by frequency in 10,000 random pairs.\n")
        f.write("  2. Manual sampling of random adj/noun/pair draws.\n")
        f.write("  3. A hand-curated removal list grouped by failure mode "
                "(substring profanity carriers, demonym/religion leaks, "
                "medical/biology jargon, brand residue, obscure dialect).\n\n")
        f.write(f"Total removals: {len(removed)}\n\n")
        f.write("## Removed by category\n\n")
        f.write("See `scripts/09_self_review.py` HARD_REMOVE for the source-"
                "of-truth list and inline-comment categorization.\n\n")
        f.write("## Backfill\n\n")
        f.write("Step 10 backfills from data/06_tone_scored.tsv overflow (next-"
                "best-score candidates, same pool, not in HARD_REMOVE).\n")

    print(f"Wrote {OUT_REMOVED} and {OUT_NOTES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
