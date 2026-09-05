"""Ajoute une personne je/nous/vous par couple verbe-temps via verbecc.

Les vagues A/B/C et leurs identités SRS restent inchangées. --check vérifie
les 195 nouvelles formes avec le moteur sans réécrire le golden.
"""
import argparse
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for directory in reversed([ROOT / '.tmp/verbdeps_local', ROOT / '.tmp/verbdeps']):
    if directory.is_dir():
        sys.path.insert(0, str(directory))

from verbecc import CompleteConjugator
import gen_compound_packs as packs

TENSES = {
    'Passé composé': ('indicatif', 'passé-composé'),
    'Plus-que-parfait': ('indicatif', 'plus-que-parfait'),
    'Conditionnel passé': ('conditionnel', 'passé'),
    'Futur antérieur': ('indicatif', 'futur-antérieur'),
    'Subjonctif passé': ('subjonctif', 'passé'),
}
PERSONS = [('1', 's', '1re pers. du singulier'),
           ('1', 'p', '1re pers. du pluriel'),
           ('2', 'p', '2e pers. du pluriel')]
ETRE = {'Aller', 'Venir', 'Partir', 'Mourir', 'Naître'}


def generate(data):
    engine = CompleteConjugator(lang='fr')
    base = [c for c in data['cards'] if c['wave'] != 'D']
    used = {(c['verb'], c['tense'], c['person']) for c in base}
    additions = []
    for vi, verb in enumerate(sorted(packs.EXPECTED_VERB_GROUPS)):
        if verb == 'Falloir':
            continue
        model = json.loads(str(engine.conjugate(verb.lower())))['moods']
        for ti, (tense, (mood, key)) in enumerate(TENSES.items()):
            order = PERSONS[(vi+ti)%3:] + PERSONS[:(vi+ti)%3]
            person, number, label = next(p for p in order if (verb, tense, p[2]) not in used)
            choices = [e for e in model[mood][key] if str(e.get('p')) == person and e.get('n') == number and e.get('g') in (None, 'm')]
            if not choices:
                raise ValueError(f'Forme manquante : {verb} {tense} {label}')
            answer = packs.normalized(choices[0]['c'][0])
            # L'élision de je/qu'il ne fait pas partie du groupe verbal noté.
            tokens = answer.replace('’', ' ').split()
            graded = ' '.join(tokens[-2:])
            aux, pp = graded.split()
            if aux not in packs.AUXILIARIES_BY_TENSE[tense] or graded not in answer:
                raise ValueError(f'Forme composée inattendue : {answer}')
            subject = answer[:answer.index(graded)].strip()
            hint = subject
            if verb in ETRE:
                hint += ' (masculin)' if number == 's' else ' (pluriel masculin ou mixte)'
            slug = ''.join(c for c in unicodedata.normalize('NFD',verb.lower()) if not unicodedata.combining(c))
            tip = f'Auxiliaire au temps demandé : {aux} ; participe passé : {pp}.'
            if verb in ETRE:
                tip += ' Le participe passé s’accorde avec le sujet indiqué.'
            if tense in {'Futur antérieur','Conditionnel passé'} and number == 's':
                tip += ' Distingue la terminaison du futur de celle du conditionnel.'
            additions.append(dict(id=f'compound-d-{ti}-{slug}-{person}{number}',
                verb=verb, group=packs.EXPECTED_VERB_GROUPS[verb], tense=tense,
                person=label, answer=answer, gradedForm=graded,
                subjectHint=hint, scenario=answer.replace(graded, '___') + '.',
                prompt=f'Conjugue {verb.lower()} au {tense.lower()}.',
                trapTip=tip, skill='accord_etre' if verb in ETRE else 'distinction_temps', wave='D'))
    assert len(additions) == 195
    return additions


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = packs.load_source()
    additions = generate(data)
    if args.check:
        assert additions == [c for c in data['cards'] if c['wave'] == 'D'], 'Vague D différente du moteur'
        print('OK : 195 formes je/nous/vous vérifiées avec verbecc')
    else:
        data['cards'] = [c for c in data['cards'] if c['wave'] != 'D'] + additions
        data['metadata']['cardCount'] = len(data['cards'])
        data['metadata']['waveCounts'] = dict(Counter(c['wave'] for c in data['cards']))
        data['metadata']['personExpansion'] = 'D : une forme je/nous/vous supplémentaire pour les 39 verbes personnels à chacun des cinq temps ; générée avec verbecc.'
        packs.validate_source(data)
        packs.DEFAULT_SOURCE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('OK : ajout de 195 cartes, anciennes identités conservées')
