import re, json
import sys, io
from pathlib import Path

GROUPS = {
    "Parler": (1, "1er groupe", "Verbes en <b>-er</b> (~90&nbsp;% des verbes). Terminaisons régulières, radical stable."),
    "Finir":  (2, "2e groupe",  "Verbes en <b>-ir</b> avec infixe <b>-iss-</b> au pluriel (<i>finissons</i>). ≠ partir, venir (sans -iss-)."),
}
G3 = "Verbes <b>irréguliers</b> (3e groupe) : radical et terminaisons à mémoriser pour chaque temps."
for v in ["Être","Avoir","Aller","Venir","Partir","Ouvrir","Courir","Prendre","Mettre","Dire","Faire","Voir","Pouvoir","Vouloir","Devoir","Savoir"]:
    GROUPS[v] = (3, "3e groupe", G3)

PERSONS6 = ["1re pers. du singulier","2e pers. du singulier","3e pers. du singulier",
            "1re pers. du pluriel","2e pers. du pluriel","3e pers. du pluriel"]
PERSONS_IMP = ["2e pers. du singulier","1re pers. du pluriel","2e pers. du pluriel"]
VOWELS = 'aeiouâàäéèêëîïôùûüœæAEIOUÂÀÄÉÈÊËÎÏÔÙÛÜŒÆ'
ELIDABLE_PRONOUN_RE = re.compile(
    r'(?P<que>que )?je(?:&nbsp;|\s)+(?=(?:<[^>]+>)*[' + VOWELS + r'])',
    re.IGNORECASE,
)
INVALID_ELISION_RE = re.compile(
    r'(?<![\w’\'])\b(?:que )?je(?:&nbsp;|\s)+(?:<[^>]+>)*[' + VOWELS + r']',
    re.IGNORECASE,
)

def elide(text):
    if re.match(r'^que je [' + VOWELS + r']', text):
        return "que j’" + text[7:]
    if re.match(r'^je [' + VOWELS + r']', text):
        return "j’" + text[3:]
    return text

def elide_html(text):
    """Apply the same elision to visible HTML while preserving its tags."""
    return ELIDABLE_PRONOUN_RE.sub(
        lambda match: "que j’" if match.group('que') else "j’",
        text,
    )

def validate_elisions(generated_cards):
    """Fail generation if a visible vowel-initial form still follows 'je'."""
    errors = []
    for card in generated_cards:
        for field in ('answer', 'cardBack'):
            if INVALID_ELISION_RE.search(card[field]):
                errors.append(f"{card['verb']} / {card['tense']} / {field}")
    if errors:
        raise ValueError('Invalid elision(s): ' + ', '.join(sorted(set(errors))))

def first_bold(html):
    m = re.search(r'<b>(.*?)</b>', html, re.DOTALL)
    if not m: return ''
    return re.sub(r'<[^>]+>', '', m.group(1)).replace('&nbsp;', ' ').strip()

def clean_td(html):
    t = html.replace('&nbsp;', ' ')
    return ' '.join(re.sub(r'<[^>]+>', '', t).split())

def parse_table(html):
    tds = re.findall(r'<td[^>]*>(.*?)</td>', html, re.DOTALL)
    if len(tds) < 6: return []
    # file order: je,nous,tu,vous,il,ils → quiz order: je,tu,il,nous,vous,ils
    return [elide(clean_td(tds[i])) for i in [0,2,4,1,3,5]]

def parse_imp(html):
    bolds = re.findall(r'<b>(.*?)</b>', html)
    out = []
    for b in bolds:
        t = re.sub(r'<[^>]+>', '', b).replace('&nbsp;', ' ').strip()
        if t and 'emploi' not in t.lower():
            out.append(t)
        if len(out) == 3: break
    return out

def unescape(s):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s.replace('""', '"')

cards = []
with open(r'conjugaison_français.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line in lines:
    line = line.rstrip('\n')
    if line.startswith('#') or '\t' not in line: continue
    parts = line.split('\t', 2)
    name_tense = parts[0].strip()
    cb = elide_html(unescape(parts[1])) if len(parts) > 1 else ''
    m = re.match(r'^(.+?) - (.+)$', name_tense)
    if not m: continue
    verb, tense = m.group(1).strip(), m.group(2).strip()
    if verb not in GROUPS: continue
    gn, gname, gexpl = GROUPS[verb]

    def card(person, answer):
        return {'verb': verb, 'group': gn, 'tense': tense, 'person': person,
                'answer': answer, 'groupName': gname, 'groupExplain': gexpl, 'cardBack': cb}

    if tense in ('Présent','Imparfait','Futur simple','Passé simple','Conditionnel présent','Subjonctif présent'):
        for i, f in enumerate(parse_table(cb)):
            if f:
                cards.append(card(PERSONS6[i], re.sub(r'\s*\(.*?\)', '', f).strip()))
    elif tense == 'Impératif':
        if 'existe pas' in cb: continue
        for i, f in enumerate(parse_imp(cb)[:3]):
            if f: cards.append(card(PERSONS_IMP[i], f))
    elif tense in ('Participe présent','Participe passé','Gérondif'):
        f = first_bold(cb)
        if f: cards.append(card('', f))

validate_elisions(cards)
rendered = f'// {len(cards)} cards generated\nconst CARDS = ' + json.dumps(cards, ensure_ascii=False) + ';'
io.open('cards_output.js', 'w', encoding='utf-8').write(rendered + '\n')

if '--inline-index' in sys.argv or '--check-index' in sys.argv:
    index_path = Path('index.html')
    index_text = index_path.read_text(encoding='utf-8')
    start_marker = '// BEGIN GENERATED HISTORICAL CARDS'
    end_marker = '// END GENERATED HISTORICAL CARDS'
    if index_text.count(start_marker) != 1 or index_text.count(end_marker) != 1:
        raise ValueError('Historical card markers are absent or duplicated in index.html')
    before, rest = index_text.split(start_marker, 1)
    _, after = rest.split(end_marker, 1)
    updated = before + start_marker + '\n' + rendered + '\n' + end_marker + after
    if '--check-index' in sys.argv:
        if updated != index_text:
            raise ValueError('Historical CARDS block is not up to date')
    else:
        index_path.write_text(updated, encoding='utf-8')

sys.stdout.buffer.write(f'{len(cards)} cards generated OK\n'.encode('utf-8'))
