# -*- coding: utf-8 -*-
"""Construit les mini-packs de verbes fréquents depuis une source golden.

La génération normale ne dépend pas de verbecc : le fichier golden, relu et
versionné, est la source de vérité. ``--verify-verbecc`` est un contrôle croisé
optionnel ; une modification de verbecc ne peut donc jamais altérer les cartes
publiées silencieusement.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT / "target_verbs_golden.json"
DEFAULT_INDEX = ROOT / "index.html"
INLINE_START = "// BEGIN GENERATED TARGET CARDS"
INLINE_END = "// END GENERATED TARGET CARDS"

EXPECTED_WAVES = {
    1: {
        "boire", "recevoir", "écrire", "lire", "conduire", "attendre",
        "tenir", "mourir", "vivre", "falloir", "croire", "connaître",
    },
    2: {
        "résoudre", "craindre", "acquérir", "naître", "suivre",
        "cueillir", "valoir", "dormir", "rire", "joindre",
    },
}

PERSONS = {
    "",
    "1re pers. du singulier",
    "2e pers. du singulier",
    "3e pers. du singulier",
    "1re pers. du pluriel",
    "2e pers. du pluriel",
    "3e pers. du pluriel",
}

SUPPORTED_TENSES = {
    "Présent", "Imparfait", "Futur simple", "Passé simple",
    "Conditionnel présent", "Subjonctif présent", "Impératif",
    "Participe présent", "Participe passé",
}

IMPERATIVE_PERSONS = {
    "2e pers. du singulier",
    "1re pers. du pluriel",
    "2e pers. du pluriel",
}

GROUP_NAME = "3e groupe"
GROUP_EXPLAIN = (
    "Verbes <b>irréguliers</b> (3e groupe) : les formes importantes sont "
    "sélectionnées pour leurs changements de radical ou leurs lettres muettes."
)


def normalized(value: str) -> str:
    """Normalise uniquement les variantes typographiques sans corriger le fond."""
    return unicodedata.normalize("NFC", value).replace("'", "’").strip()


def load_source(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def unpack_card(card: Any) -> tuple[str, str, str, str, list[str]]:
    """Lit une carte explicite de la source golden."""
    if not isinstance(card, dict):
        raise ValueError("une carte doit être un objet")
    card_id = card.get("id")
    tense = card.get("tense")
    person = card.get("person")
    answer = card.get("answer")
    variants = card.get("answerVariants", [])
    if not isinstance(variants, list):
        raise ValueError("answerVariants doit être une liste")
    return card_id, tense, person, answer, variants


def validate_source(data: dict[str, Any]) -> None:
    errors: list[str] = []
    if not isinstance(data.get("metadata"), dict):
        errors.append("metadata doit être un objet")
    if not isinstance(data.get("sources"), list) or not data.get("sources"):
        errors.append("sources doit être une liste non vide")

    packs = data.get("verbs")
    if not isinstance(packs, list):
        raise ValueError("verbs doit être une liste")

    seen_verbs: set[str] = set()
    seen_ids: set[str] = set()
    seen_cards: set[tuple[str, str, str]] = set()
    actual_waves = {1: set(), 2: set()}

    for pack in packs:
        verb = pack.get("verb", "")
        display_name = pack.get("displayName", "")
        wave = pack.get("wave")
        cards = pack.get("cards", [])
        where = verb or "<verbe manquant>"

        if verb in seen_verbs:
            errors.append(f"{where}: pack en double")
        seen_verbs.add(verb)
        if not isinstance(display_name, str) or not display_name.strip():
            errors.append(f"{where}: displayName manquant")
        if wave not in actual_waves:
            errors.append(f"{where}: vague invalide {wave!r}")
        else:
            actual_waves[wave].add(verb)
        if pack.get("group") != 3:
            errors.append(f"{where}: tous ces verbes doivent être du 3e groupe")
        if not isinstance(pack.get("rule"), str) or not pack["rule"].strip():
            errors.append(f"{where}: règle pédagogique manquante")
        if not 6 <= len(cards) <= 10:
            errors.append(f"{where}: {len(cards)} cartes (6 à 10 attendues)")

        for index, card in enumerate(cards, start=1):
            try:
                card_id, tense, person, answer, variants = unpack_card(card)
            except ValueError as exc:
                errors.append(f"{where}: carte {index}: {exc}")
                continue
            if not isinstance(card_id, str) or not card_id.strip():
                errors.append(f"{where}: carte {index}: id manquant")
            elif card_id in seen_ids:
                errors.append(f"{where}: id en double {card_id!r}")
            else:
                seen_ids.add(card_id)
            if tense not in SUPPORTED_TENSES:
                errors.append(f"{where}: temps inconnu {tense!r}")
            if person not in PERSONS:
                errors.append(f"{where}: personne inconnue {person!r}")
            if isinstance(tense, str) and tense.startswith("Participe") and person:
                errors.append(f"{where}/{tense}: un participe ne doit pas avoir de personne")
            if isinstance(tense, str) and not tense.startswith("Participe") and not person:
                errors.append(f"{where}/{tense}: personne manquante")
            if tense == "Impératif" and person not in IMPERATIVE_PERSONS:
                errors.append(f"{where}/{tense}: personne impossible {person!r}")
            if not isinstance(answer, str) or not answer.strip():
                errors.append(f"{where}/{tense}/{person}: réponse vide")
                continue
            if answer != normalized(answer):
                errors.append(f"{where}/{tense}/{person}: réponse non normalisée {answer!r}")
            if "<" in answer or ">" in answer:
                errors.append(f"{where}/{tense}/{person}: HTML interdit dans une réponse")
            normalized_variants: set[str] = set()
            for variant in variants:
                if not isinstance(variant, str) or not variant.strip():
                    errors.append(f"{where}/{tense}/{person}: variante vide ou invalide")
                    continue
                if variant != normalized(variant):
                    errors.append(f"{where}/{tense}/{person}: variante non normalisée {variant!r}")
                if "<" in variant or ">" in variant:
                    errors.append(f"{where}/{tense}/{person}: HTML interdit dans une variante")
                if normalized(variant) == normalized(answer):
                    errors.append(f"{where}/{tense}/{person}: variante identique à la réponse")
                if normalized(variant) in normalized_variants:
                    errors.append(f"{where}/{tense}/{person}: variante en double {variant!r}")
                normalized_variants.add(normalized(variant))
            key = (verb, str(tense), str(person))
            if key in seen_cards:
                errors.append(f"{where}/{tense}/{person}: carte en double")
            seen_cards.add(key)

    for wave, expected in EXPECTED_WAVES.items():
        missing = sorted(expected - actual_waves[wave])
        unexpected = sorted(actual_waves[wave] - expected)
        if missing:
            errors.append(f"vague {wave}: verbes manquants: {', '.join(missing)}")
        if unexpected:
            errors.append(f"vague {wave}: verbes inattendus: {', '.join(unexpected)}")

    wave_counts = {
        wave: sum(len(pack.get("cards", [])) for pack in packs if pack.get("wave") == wave)
        for wave in EXPECTED_WAVES
    }
    if wave_counts != {1: 105, 2: 95}:
        errors.append(f"répartition attendue 105/95 cartes, obtenu {wave_counts}")

    if errors:
        raise ValueError("Source golden invalide:\n- " + "\n- ".join(errors))


def build_cards(data: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for pack in data["verbs"]:
        rule_html = html.escape(pack["rule"], quote=False)
        for raw_card in pack["cards"]:
            card_id, tense, person, answer, variants = unpack_card(raw_card)
            answer_html = html.escape(answer, quote=False)
            card = {
                "id": card_id,
                "verb": pack["displayName"],
                "group": pack["group"],
                "tense": tense,
                "person": person,
                "answer": answer,
                "groupName": GROUP_NAME,
                "groupExplain": GROUP_EXPLAIN,
                "cardBack": (
                    f"<b>{answer_html}</b><br><br>"
                    '<span style="color:#666;font-size:0.9em">'
                    f"💡 {rule_html}</span>"
                ),
                "trapTip": rule_html,
                "wave": pack["wave"],
            }
            if variants:
                card["answerVariants"] = variants
            for field in ("example", "complement"):
                if field in raw_card:
                    card[field] = raw_card[field]
            if "auxiliary" in pack:
                card["auxiliary"] = pack["auxiliary"]
            cards.append(card)
    return cards


def render_js(cards: list[dict[str, Any]]) -> str:
    payload = json.dumps(cards, ensure_ascii=False, separators=(",", ":"))
    return f"// {len(cards)} targeted cards generated from target_verbs_golden.json\nconst TARGET_CARDS={payload};"


def render_inline(index_text: str, generated: str) -> str:
    if index_text.count(INLINE_START) != 1 or index_text.count(INLINE_END) != 1:
        raise ValueError("les marqueurs TARGET_CARDS sont absents ou dupliqués dans index.html")
    before, remainder = index_text.split(INLINE_START, 1)
    _, after = remainder.split(INLINE_END, 1)
    return f"{before}{INLINE_START}\n{generated}\n{INLINE_END}{after}"


def all_conjugations(node: Any) -> Iterable[str]:
    """Collecte les chaînes de formes, quelle que soit la structure verbecc."""
    if isinstance(node, dict):
        conjugations = node.get("c")
        if isinstance(conjugations, list):
            for value in conjugations:
                if isinstance(value, str):
                    yield normalized(value)
        for value in node.values():
            yield from all_conjugations(value)
    elif isinstance(node, list):
        for value in node:
            yield from all_conjugations(value)


def verify_with_verbecc(data: dict[str, Any]) -> None:
    try:
        from verbecc import CompleteConjugator
    except ImportError as exc:
        raise RuntimeError(
            "verbecc est requis seulement pour --verify-verbecc "
            "(pip install verbecc==2.0.2)"
        ) from exc

    conjugator = CompleteConjugator(lang="fr")
    mismatches: list[tuple[str, str]] = []
    for pack in data["verbs"]:
        verb = pack["verb"]
        generated = json.loads(str(conjugator.conjugate(verb)))
        available = set(all_conjugations(generated.get("moods", generated)))
        for raw_card in pack["cards"]:
            card_id, tense, person, answer, _ = unpack_card(raw_card)
            if normalized(answer) not in available:
                mismatches.append((card_id, f"{verb}/{tense}/{person}: {answer!r}"))

    known_ids = set(data.get("metadata", {}).get("knownVerbeccDivergences", []))
    known = [message for card_id, message in mismatches if card_id in known_ids]
    unexpected = [message for card_id, message in mismatches if card_id not in known_ids]
    stale_known = known_ids - {card_id for card_id, _ in mismatches}
    if known:
        print(
            "AVERTISSEMENT: divergences verbecc connues, golden de référence conservé:\n- "
            + "\n- ".join(known),
            file=sys.stderr,
        )
    if stale_known:
        raise ValueError(
            "Divergences verbecc déclarées mais non reproduites; audit requis: "
            + ", ".join(sorted(stale_known))
        )
    if unexpected:
        raise ValueError(
            "Écarts inattendus avec verbecc (aucune source n'a été modifiée):\n- "
            + "\n- ".join(unexpected)
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--check", action="store_true", help="vérifie que le bloc inline est à jour sans l'écrire")
    parser.add_argument("--verify-verbecc", action="store_true", help="compare le golden à verbecc, sans lui faire confiance comme source")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    data = load_source(args.source)
    validate_source(data)
    if args.verify_verbecc:
        verify_with_verbecc(data)
    cards = build_cards(data)
    generated = render_js(cards)
    current = args.index.read_text(encoding="utf-8")
    rendered = render_inline(current, generated)

    if args.check:
        if current != rendered:
            print(f"ERREUR: le bloc TARGET_CARDS de {args.index.name} n'est pas à jour", file=sys.stderr)
            return 1
    else:
        args.index.write_text(rendered, encoding="utf-8")

    print(f"OK: {len(cards)} cartes, {len(data['verbs'])} verbes, 2 vagues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
