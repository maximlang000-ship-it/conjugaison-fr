import json
import re
import unittest
from collections import Counter
from pathlib import Path

import gen_compound_packs as generator


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "compound_tenses_golden.json"
INDEX = ROOT / "index.html"

COMPOUND_TENSES = {
    "Passé composé",
    "Plus-que-parfait",
    "Conditionnel passé",
    "Futur antérieur",
    "Subjonctif passé",
}

# Garde-fou volontairement explicite : si un verbe disparaît du runtime, le
# test ne doit pas réduire silencieusement la couverture attendue.
EXPECTED_RUNTIME_VERBS = {
    "Acquérir", "Aller", "Attendre", "Avoir", "Boire", "Conduire",
    "Connaître", "Courir", "Craindre", "Croire", "Cueillir", "Devoir",
    "Dire", "Dormir", "Écrire", "Être", "Faire", "Falloir", "Finir",
    "Joindre", "Lire", "Mettre", "Mourir", "Naître", "Ouvrir", "Parler",
    "Partir", "Pouvoir", "Prendre", "Recevoir", "Résoudre", "Rire",
    "Savoir", "Suivre", "Tenir", "Valoir", "Venir", "Vivre", "Voir",
    "Vouloir",
}


def _inline_cards(index_text, start_marker, end_marker, variable):
    """Lit un tableau JSON généré sans exécuter le JavaScript."""
    block = index_text.split(start_marker, 1)[1].split(end_marker, 1)[0]
    match = re.search(
        rf"const\s+{re.escape(variable)}\s*=\s*(\[.*\])\s*;",
        block,
        re.DOTALL,
    )
    if not match:
        raise AssertionError(f"tableau inline {variable} introuvable")
    return json.loads(match.group(1))


EXPECTED_FORMS = {
    "Passé composé": {
        "ai écrit", "as pris", "a fait", "avons vu", "avez reçu", "ont dû",
        "est venue", "sont parties", "est né", "sont mortes", "ai ouvert",
        "a résolu", "ai lues", "a prises", "ont faites",
    },
    "Plus-que-parfait": {
        "avais écrit", "avais pris", "avait fait", "avions vu", "aviez reçu",
        "avaient dû", "était venue", "étaient parties", "était né",
        "étaient mortes", "avais ouvert", "avait résolu", "avais lues",
        "avait prises", "avaient faites",
    },
    "Conditionnel passé": {
        "aurais écrit", "aurais pris", "aurait fait", "aurions vu",
        "auriez reçu", "auraient dû", "serait venue", "seraient parties",
        "serait né", "seraient mortes", "aurais ouvert", "aurait résolu",
        "aurais lues", "aurait prises", "auraient faites",
    },
    "Futur antérieur": {
        "aurai fini", "auras écrit", "aura résolu", "aurons acquis",
        "aurez reçu", "auront conduit", "seront parties", "seront morts",
        "seront nées", "aura écrites", "aura faites", "aurons reçues",
    },
    "Subjonctif passé": {
        "ait lu", "aies pu", "aient reçu", "ait résolu", "ayez dit",
        "aient écrit", "soient parties", "soient mortes", "soient nées",
        "ait écrites", "aient prises", "ayons reçue",
    },
}


class CompoundPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = generator.load_source(SOURCE)
        generator.validate_source(cls.data)
        cls.cards = generator.build_cards(cls.data)
        cls.index_text = INDEX.read_text(encoding="utf-8")
        cls.historical_cards = _inline_cards(
            cls.index_text,
            "// BEGIN GENERATED HISTORICAL CARDS",
            "// END GENERATED HISTORICAL CARDS",
            "CARDS",
        )
        cls.target_cards = _inline_cards(
            cls.index_text,
            "// BEGIN GENERATED TARGET CARDS",
            "// END GENERATED TARGET CARDS",
            "TARGET_CARDS",
        )

    def test_reviewed_counts_per_wave_and_tense(self):
        self.assertEqual(len(self.cards), 405)
        self.assertEqual(
            Counter(card["wave"] for card in self.cards),
            {"A": 45, "B": 24, "C": 141, "D": 195},
        )
        self.assertEqual(set(card["tense"] for card in self.cards), COMPOUND_TENSES)
        self.assertTrue(all(
            count >= len(EXPECTED_RUNTIME_VERBS)
            for count in Counter(card["tense"] for card in self.cards).values()
        ))

    def test_audited_forms_are_exact(self):
        actual = {
            tense: {card["gradedForm"] for card in self.cards if card["tense"] == tense}
            for tense in EXPECTED_FORMS
        }
        for tense, audited_forms in EXPECTED_FORMS.items():
            self.assertLessEqual(audited_forms, actual[tense])

    def test_srs_identities_and_ids_are_unique(self):
        self.assertEqual(len({card["id"] for card in self.cards}), len(self.cards))
        identities = [
            (card["verb"], card["tense"], card["person"])
            for card in self.cards
        ]
        self.assertEqual(len(set(identities)), len(identities))

    def test_every_runtime_verb_has_every_compound_tense(self):
        runtime_verbs = {
            card["verb"] for card in self.historical_cards + self.target_cards
        }
        self.assertEqual(runtime_verbs, EXPECTED_RUNTIME_VERBS)
        self.assertEqual(len(runtime_verbs), 40)

        covered_pairs = {(card["verb"], card["tense"]) for card in self.cards}
        expected_pairs = {
            (verb, tense)
            for verb in runtime_verbs
            for tense in COMPOUND_TENSES
        }
        self.assertEqual(covered_pairs, expected_pairs)
        self.assertEqual(len(covered_pairs), 200)

    def test_falloir_is_only_third_person_singular(self):
        falloir_cards = [card for card in self.cards if card["verb"] == "Falloir"]
        self.assertEqual({card["tense"] for card in falloir_cards}, COMPOUND_TENSES)
        self.assertTrue(falloir_cards)
        self.assertEqual(
            {card["person"] for card in falloir_cards},
            {"3e pers. du singulier"},
        )

    def test_only_the_verbal_group_is_graded(self):
        for card in self.cards:
            self.assertNotIn(card["answer"], (card["gradedForm"],))
            self.assertIn(card["gradedForm"], card["answer"])
            self.assertTrue(card["compound"])
            forms = [card["gradedForm"], *card.get("gradedVariants", [])]
            allowed_auxiliaries = {
                value.casefold()
                for value in generator.AUXILIARIES_BY_TENSE[card["tense"]]
            }
            for form in forms:
                words = form.split()
                self.assertEqual(
                    len(words), 2,
                    f"{card['id']}: gradedForm doit être auxiliaire + participe",
                )
                self.assertIn(words[0].casefold(), allowed_auxiliaries, card["id"])

    def test_auxiliary_choice_is_not_a_learning_target(self):
        forbidden = (
            "choisis l’auxiliaire", "choisir l’auxiliaire", "avoir ou être",
            "choix de l’auxiliaire", "choix entre avoir et être",
        )
        for raw in self.data["cards"]:
            skill = raw["skill"].casefold().replace("_", " ")
            self.assertNotIn("choix auxiliaire", skill)
            self.assertFalse("avoir" in skill and "être" in skill)
            pedagogy = (
                f"{raw['scenario']} {raw.get('prompt', '')} {raw['trapTip']}"
            ).casefold()
            self.assertFalse(any(phrase in pedagogy for phrase in forbidden))

    def test_agreement_cards_cover_etre_and_preceding_cod_in_every_tense(self):
        by_tense_and_skill = Counter(
            (card["tense"], card["skill"]) for card in self.cards
        )
        for tense in EXPECTED_FORMS:
            self.assertGreaterEqual(by_tense_and_skill[tense, "accord_etre"], 2)
            self.assertEqual(by_tense_and_skill[tense, "accord_cod_avant"], 3)

    def test_generated_cards_expose_scenario_and_safe_feedback(self):
        for raw, card in zip(self.data["cards"], self.cards):
            self.assertEqual(raw["scenario"].count("___"), 1)
            self.assertEqual(card["scenario"], raw["scenario"])
            self.assertTrue(card["prompt"])
            self.assertEqual(card["trapTip"], raw["trapTip"])
            self.assertIn(card["answer"], card["cardBack"])
            self.assertIn("Le groupe du verbe n’est pas évalué", card["groupExplain"])

    def test_recu_is_not_taught_with_a_nonexistent_circumflex(self):
        tips = " ".join(card["trapTip"] for card in self.cards).casefold()
        self.assertNotIn("circonflexe de reçu", tips)

    def test_rendered_payload_has_stable_hook(self):
        rendered = generator.render_js(self.cards)
        self.assertIn("const COMPOUND_CARDS=", rendered)
        self.assertIn("405 compound-tense cards", rendered)
        self.assertIn('"gradedForm":"ai écrit"', rendered)

    def test_generated_inline_is_up_to_date(self):
        generated = generator.render_js(self.cards)
        self.assertEqual(
            self.index_text,
            generator.render_inline(self.index_text, generated),
        )

    def test_person_expansion_is_canonical_and_preserves_legacy_cards(self):
        expanded = [c for c in self.cards if c['wave'] == 'D']
        self.assertEqual(len(expanded), 195)
        self.assertEqual(len([c for c in self.cards if c['wave'] != 'D']), 210)
        # Référence indépendante du moteur : participes relus à l'audit initial.
        participles = dict(zip(
            'Parler Finir Acquérir Aller Attendre Avoir Boire Conduire Connaître Courir Craindre Croire Cueillir Devoir Dire Dormir Écrire Être Faire Joindre Lire Mettre Mourir Naître Ouvrir Partir Pouvoir Prendre Recevoir Résoudre Rire Savoir Suivre Tenir Valoir Venir Vivre Voir Vouloir'.split(),
            'parlé fini acquis allé attendu eu bu conduit connu couru craint cru cueilli dû dit dormi écrit été fait joint lu mis mort né ouvert parti pu pris reçu résolu ri su suivi tenu valu venu vécu vu voulu'.split(),
        ))
        forms = {
            'Passé composé': [['ai','avons','avez'], ['suis','sommes','êtes']],
            'Plus-que-parfait': [['avais','avions','aviez'], ['étais','étions','étiez']],
            'Conditionnel passé': [['aurais','aurions','auriez'], ['serais','serions','seriez']],
            'Futur antérieur': [['aurai','aurons','aurez'], ['serai','serons','serez']],
            'Subjonctif passé': [['aie','ayons','ayez'], ['sois','soyons','soyez']],
        }
        people = ['1re pers. du singulier','1re pers. du pluriel','2e pers. du pluriel']
        for card in expanded:
            person = people.index(card['person'])
            etre = card['verb'] in {'Aller','Venir','Partir','Mourir','Naître'}
            pp = participles[card['verb']] + ('s' if etre and person > 0 else '')
            expected = forms[card['tense']][int(etre)][person] + ' ' + pp
            self.assertEqual(card['gradedForm'], expected, card['id'])
            if etre:
                self.assertIn('masculin', card['subjectHint'])
        pairs = {(c['verb'],c['tense']) for c in expanded}
        self.assertEqual(len(pairs), 195)


if __name__ == "__main__":
    unittest.main()
