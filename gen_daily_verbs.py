# -*- coding: utf-8 -*-
"""Génère un dataset de verbes-pièges (formes correctes via verbecc) pour la Daily."""
import io, json
from verbecc import CompleteConjugator

cc = CompleteConjugator(lang='fr')

# Temps voulus -> chemin verbecc (mood, tense)
TENSES = {
    'Présent':              ('indicatif',    'présent'),
    'Imparfait':            ('indicatif',    'imparfait'),
    'Futur simple':         ('indicatif',    'futur-simple'),
    'Conditionnel présent': ('conditionnel', 'présent'),
    'Subjonctif présent':   ('subjonctif',   'présent'),
}
# ordre canonique (personne, nombre)
ORDER = [('1','s'), ('2','s'), ('3','s'), ('1','p'), ('2','p'), ('3','p')]

def pick6(entries):
    out = []
    for (p, n) in ORDER:
        cand = [e for e in entries if str(e.get('p')) == p and e.get('n') == n]
        if not cand:
            out.append('')
            continue
        # préférer le masculin (g absent ou 'm')
        masc = [e for e in cand if e.get('g') in (None, 'm')]
        e = (masc or cand)[0]
        c = e.get('c') or ['']
        out.append(c[0])
    return out

def forms_for(verb):
    data = json.loads(str(cc.conjugate(verb)))
    moods = data['moods']
    res = {}
    for label, (mood, tense) in TENSES.items():
        try:
            res[label] = pick6(moods[mood][tense])
        except Exception:
            res[label] = []
    return res

# ── Pool de verbes-pièges + métadonnées (tense du piège, surlignage, règle) ──
# hl = sous-chaînes à surligner en rouge dans les formes du temps-piège
POOL = {
    'essuyer':    {'group':1, 'trap':'Imparfait',            'hl':['yi'],    'rule':"À nous/vous, un <b>i</b> muet après le y : nous essu<b>yi</b>ons, vous essu<b>yi</b>ez. Pareil au subjonctif."},
    'appuyer':    {'group':1, 'trap':'Imparfait',            'hl':['yi'],    'rule':"Nous appu<b>yi</b>ons, vous appu<b>yi</b>ez : le -i- après y ne s'entend pas."},
    'ennuyer':    {'group':1, 'trap':'Subjonctif présent',   'hl':['yi'],    'rule':"Que nous ennu<b>yi</b>ons, que vous ennu<b>yi</b>ez (i muet après y)."},
    'employer':   {'group':1, 'trap':'Futur simple',         'hl':['ie'],    'rule':"Le y devient <b>i</b> devant e muet : j'emplo<b>ie</b>rai."},
    'nettoyer':   {'group':1, 'trap':'Futur simple',         'hl':['ie'],    'rule':"y → <b>i</b> au futur : je netto<b>ie</b>rai (et à l'imparfait : nous netto<b>yi</b>ons)."},
    'envoyer':    {'group':1, 'trap':'Futur simple',         'hl':['enverr'],'rule':"Futur <b>irrégulier</b> : j'<b>enverr</b>ai (et non envoyerai). Deux r ! Idem au conditionnel."},
    'payer':      {'group':1, 'trap':'Présent',              'hl':['ie','ye'],'rule':"Deux orthographes admises : je <b>paie</b> ou je <b>paye</b>. À l'imparfait : nous pa<b>yi</b>ons."},
    'manger':     {'group':1, 'trap':'Imparfait',            'hl':['ge'],    'rule':"On garde le <b>e</b> devant a/o : nous man<b>ge</b>ons, je man<b>ge</b>ais (sinon le g durcirait)."},
    'nager':      {'group':1, 'trap':'Présent',              'hl':['ge'],    'rule':"e gardé devant o : nous na<b>ge</b>ons."},
    'commencer':  {'group':1, 'trap':'Présent',              'hl':['ç'],     'rule':"Cédille devant a/o : nous commen<b>ç</b>ons (sinon le c durcirait)."},
    'lancer':     {'group':1, 'trap':'Imparfait',            'hl':['ç'],     'rule':"Cédille devant a : je lan<b>ç</b>ais, nous lancions."},
    'étudier':    {'group':1, 'trap':'Imparfait',            'hl':['ii'],    'rule':"<b>Double i</b> à nous/vous : nous étud<b>ii</b>ons, vous étud<b>ii</b>ez (radical en -i + terminaison -ions)."},
    'crier':      {'group':1, 'trap':'Imparfait',            'hl':['ii'],    'rule':"<b>Double i</b> : nous cr<b>ii</b>ons, vous cr<b>ii</b>ez."},
    'travailler': {'group':1, 'trap':'Imparfait',            'hl':['illi'],  'rule':"nous trava<b>illi</b>ons, vous trava<b>illi</b>ez : le -i- s'ajoute après -ill-."},
    'gagner':     {'group':1, 'trap':'Imparfait',            'hl':['gni'],   'rule':"nous ga<b>gni</b>ons, vous ga<b>gni</b>ez : -i- après gn (presque muet)."},
    'appeler':    {'group':1, 'trap':'Présent',              'hl':['ll'],    'rule':"Double l devant e muet : j'appe<b>ll</b>e, ils appe<b>ll</b>ent (mais nous appelons)."},
    'jeter':      {'group':1, 'trap':'Présent',              'hl':['tt'],    'rule':"Double t devant e muet : je je<b>tt</b>e, ils je<b>tt</b>ent (mais nous jetons)."},
    'acheter':    {'group':1, 'trap':'Présent',              'hl':['è'],     'rule':"Accent grave : j'ach<b>è</b>te, ils ach<b>è</b>tent (mais nous achetons)."},
    'lever':      {'group':1, 'trap':'Présent',              'hl':['è'],     'rule':"Accent grave : je l<b>è</b>ve (mais nous levons)."},
    'créer':      {'group':1, 'trap':'Présent',              'hl':['ée'],    'rule':"Le é du radical reste : je cr<b>ée</b>, ils cr<b>ée</b>nt. (participe passé : créé)."},
    'asseoir':    {'group':3, 'trap':'Présent',              'hl':['ie','oi'],'rule':"<b>Deux conjugaisons</b> admises : j'ass<b>ie</b>ds ou j'ass<b>oi</b>s. Toutes deux correctes."},
    'rire':       {'group':3, 'trap':'Imparfait',            'hl':['ii'],    'rule':"<b>Double i</b> à nous/vous : nous r<b>ii</b>ons, vous r<b>ii</b>ez."},
    'croire':     {'group':3, 'trap':'Imparfait',            'hl':['yi'],    'rule':"nous cro<b>yi</b>ons, vous cro<b>yi</b>ez : -i- après y."},
    'fuir':       {'group':3, 'trap':'Imparfait',            'hl':['yi'],    'rule':"nous fu<b>yi</b>ons, vous fu<b>yi</b>ez : -i- après y."},
    'vaincre':    {'group':3, 'trap':'Présent',              'hl':['nc'],    'rule':"3ᵉ pers. sing. : il vai<b>nc</b> (pas de -t !). Pluriel : ils vainquent."},
    'connaître':  {'group':3, 'trap':'Présent',              'hl':['î'],     'rule':"Accent circonflexe sur le i devant t : il conna<b>î</b>t."},
    'plaire':     {'group':3, 'trap':'Présent',              'hl':['î'],     'rule':"Circonflexe : il pla<b>î</b>t (3ᵉ pers. sing.)."},
}

out = {}
errors = []
for verb, meta in POOL.items():
    try:
        f = forms_for(verb)
        out[verb] = {'group': meta['group'], 'forms': f, 'trap': {'tense': meta['trap'], 'hl': meta['hl'], 'rule': meta['rule']}}
    except Exception as ex:
        errors.append(verb + ': ' + str(ex))

io.open('daily_verbs.js', 'w', encoding='utf-8').write('const DAILY_VERBS = ' + json.dumps(out, ensure_ascii=False, indent=1) + ';\n')
print('OK', len(out), 'verbes générés ; erreurs:', errors)
# aperçu de quelques verbes tricky
import sys
for v in ['asseoir','essuyer','envoyer','appeler','haïr','vaincre']:
    if v in out:
        line = v + ' | présent: ' + str(out[v]['forms'].get('Présent')) + ' | imparfait: ' + str(out[v]['forms'].get('Imparfait'))
        sys.stdout.buffer.write((line + '\n').encode('utf-8'))
