# Conjugaison FR — Hub du projet

PWA privée d'entraînement à la conjugaison française, pour **un seul utilisateur**
(francophone natif dont le point faible est l'**orthographe / les lettres muettes**,
pas l'usage : il connaît les formes à l'oreille mais les écrit mal). Toute la
pédagogie vise ce qui **ne s'entend pas** (double consonnes, -rais vs -rai, -i-
après y, -x, accents, passé simple écrit…). Ne jamais lui servir de rappels
triviaux (« ils mangent → -ent »).

> **Règle absolue : ne JAMAIS afficher une forme conjuguée potentiellement fausse.**
> C'est un outil qui enseigne l'orthographe — une forme erronée est pire que pas
> de forme. Générer les conjugaisons avec un moteur vérifié (**verbecc**), jamais à la main.

---

## 1. Déploiement (lire en premier)

- **Repo GitHub** : `https://github.com/ultramax333/conjugaison-fr` (branche `master`, Pages depuis la racine).
- **URL live (PWA)** : `https://ultramax333.github.io/conjugaison-fr/`
- ⚠️ Le compte a été renommé `maximlang000-ship-it` → **`ultramax333`**. L'ancienne URL `maximlang000-ship-it.github.io/...` renvoie **404**. Le `git remote` local pointe déjà sur `ultramax333`.
- **Déployer = commit + push sur `master`.** GitHub Pages sert automatiquement. Pas de build.
- **À CHAQUE déploiement, bumper DEUX numéros de version** (sinon le service worker ressert l'ancien cache et le téléphone ne voit rien) :
  1. `sw.js` : `const CACHE = 'conjugaison-vN'` → `vN+1`
  2. `index.html` : `const APP_VERSION = 'vN'` → `vN+1` (affiché en pastille bleue en haut de chaque écran)
- Version actuelle : **v23**.
- Depuis v20, un handler `controllerchange` **recharge l'app automatiquement** quand un nouveau SW prend la main → l'utilisateur n'a plus à rouvrir manuellement.

---

## 2. Architecture

- **Fichier unique** : [index.html](index.html) (~3800 lignes) contient tout — CSS, HTML des 6 écrans, données JS, logique. Pas de framework, pas de dépendance runtime, 100 % offline.
- [sw.js](sw.js) : service worker cache-first (`skipWaiting` + `clients.claim`).
- [manifest.json](manifest.json), `icon-192.png`, `icon-512.png` : PWA installable.
- Thème sombre bleu nuit, mobile-first (cible : Google Pixel 9a, ~411 px). Variables CSS : `--bg #0f172a`, `--blue`, `--blue-dim`, `--blue-border`, `--green`, `--amber`, `--red`, `--surface`, `--text`, `--text-muted`, `--text-dim`, `--border`.

### Écrans (togglés par `showScreen(id)`)
`screen-select` (menu/filtres) · `screen-daily` · `screen-fiche` · `screen-quiz` · `screen-result` · `screen-final`. Chaque `<div id="screen-*">` a un `.header` avec `.header-title`; la pastille `.app-version` y est ajoutée par JS au boot.

---

## 3. Données (dans index.html)

| Structure | Contenu |
|-----------|---------|
| `CARDS` | **753 cartes** du quiz, générées depuis un deck Anki. 18 verbes × 10 temps. Champs : `verb, group, tense, person, answer, groupName, groupExplain, cardBack`. `answer` inclut le pronom + élision (« je parle », « j'aurai », « que je coure »). |
| `EXC` | **45 exceptions** clé `"Verbe\|Temps"` → `{hl:[...], rule}`. `hl` = sous-chaînes à surligner en rouge dans la réponse (radicaux irréguliers, doubles muets, -yi-, dû, PP être…). Sert écran résultat ET Daily. |
| `PIEGES` | **37 pièges** person-spécifiques (homophones, formes surprenantes). Affichés dans un encart ambre sur l'écran résultat, **masqués si une `EXC` couvre déjà la carte**. |
| `VERB_COMPLEMENT` | Complément neutre par verbe (parler→français, courir→vite) pour les phrases-repères. 18 verbes du deck. |
| `TENSE_FRAME` | Cadre de phrase par temps (« S'il le fallait, … » pour le conditionnel, « Il faut … » pour le subjonctif). |
| `DAILY_VERBS` | **27 verbes-pièges hors deck** (asseoir, essuyer, envoyer, manger, appeler…). Généré par verbecc, **collé tel quel** dans index.html. Format : `{verbe: {group, forms:{Temps:[6 formes]}, trap:{tense,hl,rule}}}`. |
| `TENSE_HELP` | Explications d'emploi par temps (panneau Aide + écran résultat). |

**18 verbes du deck** : Parler, Finir, Être, Avoir, Aller, Venir, Partir, Ouvrir, Courir, Prendre, Mettre, Dire, Faire, Voir, Pouvoir, Vouloir, Devoir, Savoir.
**10 temps** : Présent, Imparfait, Futur simple, Passé simple, Conditionnel présent, Subjonctif présent, Impératif, Participe présent, Participe passé, Gérondif.
Pouvoir-Impératif n'existe pas (exclu). Formes non-personnelles : person = `''`.

---

## 4. Fonctionnalités par écran

- **screen-select (menu)** : stats points faibles (par temps/verbe), **session de répétition espacée** (Leitner : compteurs dû/nouvelles, tailles 10/20/30/Tout), filtres temps/verbe/groupe/difficile/piège, bloc **☁️ Synchronisation**, **mémo des temps** repliable, boutons `📅 Ma routine du jour` et `📖 Fiche révision`.
- **screen-daily** (`showDaily`/`renderDaily`) : routine à **recopier à la main**. Verbe du jour tiré du `DAILY_POOL` (40 = 13 verbes deck avec EXC + 27 `DAILY_VERBS`), tournant par `_dayIndex()`. Réponses **cachées** (amorces « je … ») jusqu'au bouton « 👁 Voir les réponses ». Rappel des pièges muets niveau natif. Streak 🔥 (`markDailyDone`).
- **screen-fiche** (`showFiche`) : **concordance des temps, contenu 100 % statique** (6 sections : subjonctif vs indicatif + piège certain/incertain ; double subjonctif ; subjonctif après toute principale ; hypothèse « si » ; futur dans le passé ; tableau discours indirect).
- **screen-quiz** (`showCard`/`validate`) : question (verbe + temps + personne), choix du groupe, saisie + boutons d'accents, panneau Aide. Champ `#answer-input` a un **anti-autocorrection** (`onbeforeinput` bloque `insertReplacementText`).
- **screen-result** : badge correct/incorrect avec réponse **surlignée en rouge** sur la partie exception, encart Exception (EXC) ou Piège (PIEGES), **phrase-repère** (buildExample), 3 boutons TTS, verso Anki.
- **screen-final** : score, cartes ratées, difficiles.

### Fonctions clés
`start(cards)` · `showCard()` · `validate()` · `buildSession(pool,size)` (SRS) · `srsUpdate(card,isOk)` · `highlightAnswer(c)`/`_hl(str,arr)` (surlignage rouge) · `buildExample(c)` (phrase-repère) · `cardException(c)`/`findPiege(c)` · `getFilteredCards()` · `syncNow(silent)` · `showDaily/showFiche/showSelect`.

---

## 5. localStorage (par origine — repart de zéro si l'URL change)

| Clé | Contenu |
|-----|---------|
| `conjugaison_difficult` | Set des cartes marquées difficiles |
| `conjugaison_stats` | `{tense:{...}, verb:{...}}` avec `{ok,n}` — agrégé, PAS par carte |
| `conjugaison_srs` | Boîtes de Leitner **par carte** `{box,seen,ok,last,due}` |
| `conjugaison_daily` | `{last:'YYYY-M-D', streak:N}` |
| `conjugaison_sync_url` / `_sync_last` | URL du script Google + horodatage dernière synchro |
| `conjugaison_device` | id d'appareil aléatoire |

---

## 6. Synchronisation cloud (stats → Google Sheet)

- Script Apps Script : [google_apps_script.gs](google_apps_script.gs) (non déployé automatiquement ; l'utilisateur l'a collé dans son Sheet).
- POST `text/plain` vers l'endpoint `/exec` (déployé « Tout le monde »). Le « ✓ » de l'app est **optimiste** (s'affiche même en cas d'échec CORS) → pour vérifier la vraie réception, lire le Sheet.
- Auto-sync à la fin de chaque série (`showFinal`) + bouton manuel.
- **Google Sheet** : titre « Conjugaison stats », `fileId 1xljdHfBp92H_uCbyaxHHFTa6olBfGXiVcARgZnqbbZM`, compte maximlang000@gmail.com. Onglets : Historique (1 ligne/sync + JSON brut), Résumé temps, Résumé verbes (pire score en haut).
- **Un LLM peut lire ce Sheet directement** via le connecteur Google Drive (`read_file_content`, fileId ci-dessus) — pas besoin de copier-coller. Dernière lecture connue : 142 réponses, 65 % ; points faibles **Conditionnel présent 19 %**, **Subjonctif présent 38 %** ; Présent/Imparfait maîtrisés.

---

## 7. Générateurs (dev-time, NON suivis par git)

Régénérer les données au lieu de taper des formes à la main.

- [gen_cards.py](gen_cards.py) : lit `conjugaison_français.txt` (deck Anki, non commité) → `cards_output.js` (les 753 cartes). Réordonne [je,nous,tu,vous,il,ils]→[je,tu,il,nous,vous,ils], applique l'élision, saute « N'existe pas ».
- [gen_daily_verbs.py](gen_daily_verbs.py) : conjugue une liste `POOL` de verbes-pièges avec **verbecc** → `daily_verbs.js` (= `const DAILY_VERBS`), à **recoller** dans index.html. Setup : `pip install verbecc tzdata`. API : `from verbecc import CompleteConjugator; CompleteConjugator(lang='fr').conjugate(v)` puis `json.loads(str(r))`. **Vérifier chaque forme** — verbecc s'est trompé sur `haïr` (« j'hais »), retiré. Étendre le pool = ajouter une ligne (verbe → group, trap tense, hl, rule) et relancer.
- Historiquement, les modifs d'index.html ont été faites via des scripts Python `patch_*.py` (remplacements de chaînes idempotents) puis supprimés. On peut aussi éditer directement.

---

## 8. Gotchas

- **Bumper SW + APP_VERSION à chaque push**, sinon rien ne change côté PWA.
- **Vérifier en preview avec un cache-buster** : `location.href = location.href.split('?')[0] + '?v=' + Date.now()` (un `reload()` simple ressert le cache du SW).
- `preview_screenshot` peut timeout (fichier volumineux) → privilégier `preview_eval` (DOM) pour vérifier.
- Ne pas confondre `EXC` (par temps, surlignage rouge, écran résultat + Daily) et `PIEGES` (par personne, encart ambre) — EXC prime.
- Changer d'URL/compte = localStorage vidé côté client (stats agrégées récupérables via le Sheet, mais SRS/streak perdus).
- Écran quiz volontairement compact pour tenir sur un écran de téléphone avec le clavier ouvert.

---

## 9. Pistes non faites

Re-test immédiat des erreurs dans la série · feedback fin « accent manquant vs mauvaise terminaison » · objectif quotidien + rappel planifié · élargir le `DAILY_POOL` ou prioriser la rotation sur les familles les plus ratées · ajouter des verbes-modèles piégeux au **quiz** (actuellement figé à 18).
