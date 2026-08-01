import unittest
from collections import Counter
import html
from pathlib import Path

import gen_extra_packs as generator


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "target_verbs_golden.json"
INDEX = ROOT / "index.html"


class TargetPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = generator.load_source(SOURCE)
        generator.validate_source(cls.data)
        cls.cards = generator.build_cards(cls.data)
        cls.index_text = INDEX.read_text(encoding="utf-8")

    def test_expected_counts_and_unique_identity(self):
        self.assertEqual(len(self.data["verbs"]), 22)
        self.assertEqual(len(self.cards), 200)
        self.assertEqual(Counter(card["wave"] for card in self.cards), {1: 105, 2: 95})
        self.assertEqual(len({card["id"] for card in self.cards}), 200)
        srs_keys = {(card["verb"], card["tense"], card["person"]) for card in self.cards}
        self.assertEqual(len(srs_keys), 200)

    def test_packs_are_targeted_and_feedback_is_not_a_full_paradigm(self):
        sizes = [len(pack["cards"]) for pack in self.data["verbs"]]
        self.assertTrue(all(6 <= size <= 10 for size in sizes))
        self.assertTrue(all("<table" not in card["cardBack"] for card in self.cards))
        self.assertTrue(all(card["answer"] in card["cardBack"] for card in self.cards))

    def test_every_target_card_exposes_its_pack_rule_as_a_trap_tip(self):
        rules = {
            pack["displayName"]: html.escape(pack["rule"], quote=False)
            for pack in self.data["verbs"]
        }
        self.assertTrue(all(card["trapTip"] == rules[card["verb"]] for card in self.cards))
        self.assertIn("if (c.trapTip) return { tip: c.trapTip };", self.index_text)

    def test_rectified_variants_are_limited_to_connaitre_and_naitre(self):
        with_variants = [card for card in self.cards if card.get("answerVariants")]
        self.assertEqual(len(with_variants), 6)
        self.assertEqual({card["verb"] for card in with_variants}, {"Connaître", "Naître"})

    def test_falloir_and_etre_auxiliaries_are_explicit(self):
        falloir = next(pack for pack in self.data["verbs"] if pack["verb"] == "falloir")
        self.assertEqual(len(falloir["cards"]), 7)
        self.assertTrue(all(
            card["person"] in ("", "3e pers. du singulier")
            for card in falloir["cards"]
        ))
        auxiliaries = {
            pack["verb"]: pack.get("auxiliary")
            for pack in self.data["verbs"]
            if pack.get("auxiliary")
        }
        self.assertEqual(auxiliaries, {"mourir": "être", "naître": "être"})

    def test_generated_inline_block_is_current(self):
        generated = generator.render_js(self.cards)
        self.assertEqual(generator.render_inline(self.index_text, generated), self.index_text)
        self.assertNotIn('src="./target_cards.js"', self.index_text)
        self.assertEqual(
            self.index_text.count("CARDS.push(...TARGET_CARDS, ...COMPOUND_CARDS);"),
            1,
        )
        self.assertIn("// 753 cards generated", self.index_text)

    def test_runtime_accepts_variants_and_handles_examples(self):
        self.assertIn("...(c.answerVariants || [])", self.index_text)
        self.assertIn("acceptedAnswers.some", self.index_text)
        self.assertIn("'Mourir', 'Naître'", self.index_text)
        self.assertIn("if (c.verb === 'Falloir') return 'Il a <b>fallu</b> du temps.';", self.index_text)


if __name__ == "__main__":
    unittest.main()
