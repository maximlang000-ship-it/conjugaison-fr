# -*- coding: utf-8 -*-
"""Valide et génère les cartes scénarisées des temps composés.

Le JSON relu est la source de vérité. ``gradedForm`` contient uniquement le
groupe verbal à noter (auxiliaire + participe) : le sujet et le reste de la
phrase peuvent donc comporter une coquille sans rendre la réponse fausse.
"""

from __future__ import annotations

import argparse
import html
import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT / "compound_tenses_golden.json"
DEFAULT_INDEX = ROOT / "index.html"
INLINE_START = "// BEGIN GENERATED COMPOUND CARDS"
INLINE_END = "// END GENERATED COMPOUND CARDS"

SUPPORTED_TENSES = {
    "Passé composé",
    "Plus-que-parfait",
    "Conditionnel passé",
    "Futur antérieur",
    "Subjonctif passé",
}

PERSONS = {
    "1re pers. du singulier",
    "2e pers. du singulier",
    "3e pers. du singulier",
    "1re pers. du pluriel",
    "2e pers. du pluriel",
    "3e pers. du pluriel",
}

SKILLS = {
    "distinction_temps",
    "participe_irregulier",
    "accord_etre",
    "accord_cod_avant",
    "orthographe",
}

AUXILIARIES_BY_TENSE = {
    "Passé composé": {
        "ai", "as", "a", "avons", "avez", "ont",
        "suis", "es", "est", "sommes", "êtes", "sont",
    },
    "Plus-que-parfait": {
        "avais", "avait", "avions", "aviez", "avaient",
        "étais", "était", "étions", "étiez", "étaient",
    },
    "Conditionnel passé": {
        "aurais", "aurait", "aurions", "auriez", "auraient",
        "serais", "serait", "serions", "seriez", "seraient",
    },
    "Futur antérieur": {
        "aurai", "auras", "aura", "aurons", "aurez", "auront",
        "serai", "seras", "sera", "serons", "serez", "seront",
    },
    "Subjonctif passé": {
        "aie", "aies", "ait", "ayons", "ayez", "aient",
        "sois", "soit", "soyons", "soyez", "soient",
    },
}

GROUP_NAMES = {
    1: "1er groupe",
    2: "2e groupe",
    3: "3e groupe",
}

EXPECTED_VERB_GROUPS = {
    "Parler": 1,
    "Finir": 2,
    "Être": 3,
    "Avoir": 3,
    "Aller": 3,
    "Venir": 3,
    "Partir": 3,
    "Ouvrir": 3,
    "Courir": 3,
    "Prendre": 3,
    "Mettre": 3,
    "Dire": 3,
    "Faire": 3,
    "Voir": 3,
    "Pouvoir": 3,
    "Vouloir": 3,
    "Devoir": 3,
    "Savoir": 3,
    "Boire": 3,
    "Recevoir": 3,
    "Écrire": 3,
    "Lire": 3,
    "Conduire": 3,
    "Attendre": 3,
    "Tenir": 3,
    "Mourir": 3,
    "Vivre": 3,
    "Falloir": 3,
    "Croire": 3,
    "Connaître": 3,
    "Résoudre": 3,
    "Craindre": 3,
    "Acquérir": 3,
    "Naître": 3,
    "Suivre": 3,
    "Cueillir": 3,
    "Valoir": 3,
    "Dormir": 3,
    "Rire": 3,
    "Joindre": 3,
}

GROUP_EXPLAIN = (
    "Le groupe du verbe n’est pas évalué sur cette carte : seuls le temps "
    "de l’auxiliaire, le participe passé et son accord éventuel sont notés."
)


def normalized(value: str) -> str:
    return unicodedata.normalize("NFC", value).replace("'", "’").strip()


def load_source(path: Path = DEFAULT_SOURCE) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def validate_source(data: dict[str, Any]) -> None:
    errors: list[str] = []
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("metadata doit être un objet")
        metadata = {}
    if not isinstance(data.get("sources"), list) or not data.get("sources"):
        errors.append("sources doit être une liste non vide")

    cards = data.get("cards")
    if not isinstance(cards, list):
        raise ValueError("cards doit être une liste")

    seen_ids: set[str] = set()
    seen_srs_keys: set[tuple[str, str, str]] = set()
    wave_counts: Counter[str] = Counter()
    tense_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    coverage_pairs: Counter[tuple[str, str]] = Counter()
    targeted_pairs: set[tuple[str, str]] = set()

    required_strings = (
        "id", "wave", "verb", "tense", "person", "scenario",
        "answer", "gradedForm", "skill", "trapTip",
    )

    for index, card in enumerate(cards, start=1):
        where = card.get("id") or f"carte {index}"
        if not isinstance(card, dict):
            errors.append(f"carte {index}: doit être un objet")
            continue
        for field in required_strings:
            value = card.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{where}: {field} manquant ou vide")
            elif value != normalized(value):
                errors.append(f"{where}: {field} non normalisé")

        card_id = card.get("id")
        if isinstance(card_id, str):
            if card_id in seen_ids:
                errors.append(f"{where}: id en double")
            seen_ids.add(card_id)

        group = card.get("group")
        if group not in GROUP_NAMES:
            errors.append(f"{where}: groupe invalide {group!r}")
        verb = card.get("verb")
        expected_group = EXPECTED_VERB_GROUPS.get(verb)
        if expected_group is None:
            errors.append(f"{where}: verbe hors périmètre {verb!r}")
        elif group != expected_group:
            errors.append(
                f"{where}: groupe {group!r}, attendu {expected_group} pour {verb}"
            )

        tense = card.get("tense")
        if tense not in SUPPORTED_TENSES:
            errors.append(f"{where}: temps inconnu {tense!r}")
        else:
            tense_counts[tense] += 1

        person = card.get("person")
        if person not in PERSONS:
            errors.append(f"{where}: personne inconnue {person!r}")

        skill = card.get("skill")
        if skill not in SKILLS:
            errors.append(f"{where}: compétence inconnue {skill!r}")

        wave = card.get("wave")
        if wave not in {"A", "B", "C"}:
            errors.append(f"{where}: vague inconnue {wave!r}")
        else:
            wave_counts[wave] += 1

        if isinstance(verb, str) and isinstance(tense, str):
            pair = (verb, tense)
            pair_counts[pair] += 1
            if wave == "C":
                coverage_pairs[pair] += 1
            elif wave in {"A", "B"}:
                targeted_pairs.add(pair)

        answer = card.get("answer")
        graded = card.get("gradedForm")
        if isinstance(answer, str) and isinstance(graded, str):
            if normalized(graded).casefold() not in normalized(answer).casefold():
                errors.append(f"{where}: gradedForm doit être contenu dans answer")
            words = normalized(graded).split()
            if len(words) != 2:
                errors.append(f"{where}: gradedForm doit contenir auxiliaire + participe")
            elif tense in AUXILIARIES_BY_TENSE and words[0].casefold() not in {
                value.casefold() for value in AUXILIARIES_BY_TENSE[tense]
            }:
                errors.append(
                    f"{where}: auxiliaire {words[0]!r} incompatible avec {tense}"
                )

        for variants_field in ("answerVariants", "gradedVariants"):
            variants = card.get(variants_field, [])
            if not isinstance(variants, list):
                errors.append(f"{where}: {variants_field} doit être une liste")
                continue
            if len(variants) != len(set(variants)):
                errors.append(f"{where}: doublon dans {variants_field}")
            for variant in variants:
                if not isinstance(variant, str) or not variant.strip():
                    errors.append(f"{where}: variante vide dans {variants_field}")
                elif variant != normalized(variant):
                    errors.append(f"{where}: variante non normalisée")

        if all(isinstance(card.get(field), str) for field in ("verb", "tense", "person")):
            srs_key = (card["verb"], card["tense"], card["person"])
            if srs_key in seen_srs_keys:
                errors.append(f"{where}: identité SRS en double {srs_key}")
            seen_srs_keys.add(srs_key)

    if metadata.get("cardCount") != len(cards):
        errors.append(
            f"metadata.cardCount={metadata.get('cardCount')!r}, obtenu {len(cards)}"
        )
    declared_wave_counts = metadata.get("waveCounts")
    actual_wave_counts = dict(sorted(wave_counts.items()))
    if declared_wave_counts != actual_wave_counts:
        errors.append(
            f"metadata.waveCounts={declared_wave_counts!r}, obtenu {actual_wave_counts!r}"
        )
    if not all(tense_counts[tense] for tense in set(card.get("tense") for card in cards)):
        errors.append("un temps déclaré ne contient aucune carte")

    expected_pairs = {
        (verb, tense)
        for verb in EXPECTED_VERB_GROUPS
        for tense in SUPPORTED_TENSES
    }
    actual_pairs = set(pair_counts)
    missing_pairs = sorted(expected_pairs - actual_pairs)
    unexpected_pairs = sorted(actual_pairs - expected_pairs)
    if missing_pairs:
        errors.append(f"couples verbe/temps manquants: {missing_pairs!r}")
    if unexpected_pairs:
        errors.append(f"couples verbe/temps inattendus: {unexpected_pairs!r}")

    redundant_coverage = sorted(set(coverage_pairs) & targeted_pairs)
    if redundant_coverage:
        errors.append(
            "la vague C doit seulement compléter les couples absents de A/B: "
            f"{redundant_coverage!r}"
        )
    repeated_coverage = sorted(
        pair for pair, count in coverage_pairs.items() if count != 1
    )
    if repeated_coverage:
        errors.append(f"couples répétés dans la vague C: {repeated_coverage!r}")

    coverage = metadata.get("coverage")
    expected_coverage = {
        "verbCount": len(EXPECTED_VERB_GROUPS),
        "tenseCount": len(SUPPORTED_TENSES),
        "verbTensePairCount": len(expected_pairs),
        "minimumCardsPerPair": 1,
    }
    if not isinstance(coverage, dict):
        errors.append("metadata.coverage doit être un objet")
    else:
        for field, expected in expected_coverage.items():
            if coverage.get(field) != expected:
                errors.append(
                    f"metadata.coverage.{field}={coverage.get(field)!r}, "
                    f"attendu {expected!r}"
                )
        if not isinstance(coverage.get("strategy"), str) or not coverage["strategy"].strip():
            errors.append("metadata.coverage.strategy doit être une chaîne non vide")

    if errors:
        raise ValueError("Source golden des temps composés invalide:\n- " + "\n- ".join(errors))


def build_cards(data: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for raw in data["cards"]:
        answer_html = html.escape(raw["answer"], quote=False)
        tip_html = html.escape(raw["trapTip"], quote=False)
        card = {
            "id": raw["id"],
            "verb": raw["verb"],
            "group": raw["group"],
            "tense": raw["tense"],
            "person": raw["person"],
            "answer": raw["answer"],
            "gradedForm": raw["gradedForm"],
            "prompt": raw.get(
                "prompt",
                f"Complète avec {raw['verb'].lower()} au {raw['tense'].lower()}.",
            ),
            "scenario": raw["scenario"],
            "groupName": GROUP_NAMES[raw["group"]],
            "groupExplain": GROUP_EXPLAIN,
            "cardBack": (
                f"<b>{answer_html}</b><br><br>"
                '<span style="color:#666;font-size:0.9em">'
                f"💡 {tip_html}</span>"
            ),
            "trapTip": tip_html,
            "skill": raw["skill"],
            "wave": raw["wave"],
            "compound": True,
        }
        for field in ("answerVariants", "gradedVariants"):
            if raw.get(field):
                card[field] = raw[field]
        cards.append(card)
    return cards


def render_js(cards: list[dict[str, Any]]) -> str:
    payload = json.dumps(cards, ensure_ascii=False, separators=(",", ":"))
    return (
        f"// {len(cards)} compound-tense cards generated from "
        f"compound_tenses_golden.json\nconst COMPOUND_CARDS={payload};"
    )


def render_inline(index_text: str, generated: str) -> str:
    if index_text.count(INLINE_START) != 1 or index_text.count(INLINE_END) != 1:
        raise ValueError("les marqueurs COMPOUND_CARDS sont absents ou dupliqués")
    before, remainder = index_text.split(INLINE_START, 1)
    _, after = remainder.split(INLINE_END, 1)
    return f"{before}{INLINE_START}\n{generated}\n{INLINE_END}{after}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument(
        "--check-index",
        action="store_true",
        help="vérifie le bloc inline (nécessite les marqueurs dans index.html)",
    )
    parser.add_argument(
        "--write-index",
        action="store_true",
        help="met à jour le bloc inline (nécessite les marqueurs dans index.html)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    data = load_source(args.source)
    validate_source(data)
    cards = build_cards(data)
    generated = render_js(cards)

    if args.check_index or args.write_index:
        current = args.index.read_text(encoding="utf-8")
        rendered = render_inline(current, generated)
        if args.check_index:
            if current != rendered:
                print("ERREUR: le bloc COMPOUND_CARDS n’est pas à jour")
                return 1
        else:
            args.index.write_text(rendered, encoding="utf-8")

    print(
        f"OK: {len(cards)} cartes de temps composés, "
        f"vagues {dict(Counter(card['wave'] for card in cards))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
