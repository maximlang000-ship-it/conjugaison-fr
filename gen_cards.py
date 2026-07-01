import re, json

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

def elide(text):
    if re.match(r'^que je [' + VOWELS + r']', text):
        return "que j’" + text[7:]
    if re.match(r'^je [' + VOWELS + r']', text):
        return "j’" + text[3:]
    return text

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
    cb = unescape(parts[1]) if len(parts) > 1 else ''
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

import sys, io
out = io.open('cards_output.js', 'w', encoding='utf-8')
out.write(f'// {len(cards)} cards generated\n')
out.write('const CARDS = ' + json.dumps(cards, ensure_ascii=False) + ';\n')
out.close()
sys.stdout.buffer.write(f'{len(cards)} cards generated OK\n'.encode('utf-8'))
