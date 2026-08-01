import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")


def function_block(name: str) -> str:
    start = INDEX.index(f"function {name}(")
    match = re.search(r"^}\s*$", INDEX[start:], flags=re.MULTILINE)
    if not match:
        raise AssertionError(f"Fonction {name} introuvable ou incomplète")
    return INDEX[start : start + match.end()]


class AppStaticBehaviorTests(unittest.TestCase):
    def test_only_the_conjugated_verb_affects_the_score(self):
        block = function_block("validate")
        self.assertIn("const acceptedAnswers = [c.answer, ...(c.answerVariants || [])];", block)
        self.assertIn("acceptedAnswers.some(answer => _containsVerbForm(userRaw, answer))", block)
        self.assertIn("const isOk    = conjOk;", block)
        self.assertIn("recordResult(c, isOk);", block)
        self.assertIn("srsUpdate(c, isOk);", block)
        self.assertIn("if (isOk) score++;", block)
        self.assertIn("else failedCards.push(c);", block)
        self.assertIn("(isOk ? 'correct' : 'incorrect')", block)
        self.assertIn("const groupAnswered = selectedGroup !== null;", block)
        self.assertIn("!groupAnswered ? 'non renseigné — ' + c.groupName", block)

    def test_verb_form_is_found_as_an_exact_unicode_word(self):
        tokens = function_block("_wordTokens")
        contains = function_block("_containsVerbForm")
        self.assertIn("normalize('NFC')", tokens)
        self.assertIn(r"[\p{L}\p{M}]", tokens)
        self.assertIn("word.slice(apostrophe + 1)", tokens)
        self.assertIn("_wordTokens(text).includes(expected)", contains)

    def test_group_is_optional_for_button_and_enter(self):
        can_validate = function_block("checkCanValidate")
        try_validate = function_block("tryValidate")
        self.assertIn("toggle('inactive', !hasText)", can_validate)
        self.assertNotIn("selectedGroup", can_validate)
        self.assertNotIn("selectedGroup", try_validate)
        self.assertIn("validate();", try_validate)

    def test_target_cards_are_included_in_the_trap_filter_and_feedback(self):
        find_piege = function_block("findPiege")
        filtered = function_block("getFilteredCards")
        validate = function_block("validate")
        self.assertIn("if (c.trapTip) return { tip: c.trapTip };", find_piege)
        self.assertIn("(!piegeOnly || findPiege(c))", filtered)
        self.assertIn("const piege = findPiege(c);", validate)
        self.assertIn("piege.tip", validate)

    def test_compound_cards_show_the_scenario_and_hide_group_drilling(self):
        show_card = function_block("showCard")
        validate = function_block("validate")
        self.assertIn('id="q-prompt"', INDEX)
        self.assertIn('id="q-scenario"', INDEX)
        self.assertIn("prompt.textContent = c.prompt || '';", show_card)
        self.assertIn("scenario.textContent = c.scenario || '';", show_card)
        self.assertIn("const groupDisplay = c.compound ? 'none' : '';", show_card)
        self.assertIn("const groupResultRow = c.compound ? ''", validate)
        self.assertIn("c.compound ? 'none' : ''", validate)

    def test_compound_tenses_are_available_to_filters(self):
        push = "CARDS.push(...TARGET_CARDS, ...COMPOUND_CARDS);"
        all_tenses = "const ALL_TENSES = [...new Set(CARDS.map(c => c.tense))];"
        self.assertIn(push, INDEX)
        self.assertLess(INDEX.index(push), INDEX.index(all_tenses))
        for tense in (
            "Passé composé", "Plus-que-parfait", "Conditionnel passé",
            "Futur antérieur", "Subjonctif passé",
        ):
            self.assertIn(f'"{tense}"', INDEX)

    def test_user_answer_is_escaped_before_inner_html(self):
        escape = function_block("_escapeHtml")
        block = function_block("validate")
        for entity in ("&amp;", "&lt;", "&gt;", "&quot;", "&#39;"):
            self.assertIn(entity, escape)
        self.assertIn("const userHtml = _escapeHtml(userRaw);", block)
        self.assertNotIn("${userRaw}", block)
        self.assertNotRegex(block, r"['\"]\s*\+\s*userRaw")

    def test_expired_streak_is_rendered_as_zero(self):
        block = function_block("renderStreak")
        self.assertIn("st.last === today || st.last === yesterday", block)
        self.assertRegex(block, r"\? \(st\.streak \|\| 0\) : 0")

    def test_service_worker_reload_is_deferred_until_menu(self):
        show_select = function_block("showSelect")
        sw_bootstrap = INDEX[INDEX.index("if ('serviceWorker' in navigator)") :]
        self.assertIn("window.__conjugaisonSwReloadPending", show_select)
        self.assertIn("menu.style.display === 'block'", sw_bootstrap)
        self.assertIn("window.__conjugaisonSwReloadPending = true;", sw_bootstrap)
        self.assertIn("showUpdateNotice();", sw_bootstrap)

    def test_app_and_cache_versions_match(self):
        app_version = re.search(r"const APP_VERSION = '(v\d+)';", INDEX)
        cache_version = re.search(r"const CACHE = 'conjugaison-(v\d+)';", SW)
        self.assertIsNotNone(app_version)
        self.assertIsNotNone(cache_version)
        self.assertEqual(app_version.group(1), cache_version.group(1))


if __name__ == "__main__":
    unittest.main()
