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
- Version applicative : **v29**. Git utilise ses propres identifiants ; un échec de `gh auth status` ne suffit pas à conclure que le push est bloqué.
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
| `CARDS` | **1 358 cartes** au runtime : 753 cartes historiques du deck + 200 `TARGET_CARDS` + 405 `COMPOUND_CARDS`. Toutes les 1 163 anciennes identités restent inchangées. |
| `TARGET_CARDS` | **200 mini-cartes ciblées**, 22 verbes en deux vagues (105 + 95), générées inline depuis `target_verbs_golden.json`. Chaque pack contient 6 à 10 formes vérifiées, pas un paradigme complet. Sa règle pédagogique est copiée dans `trapTip`, ce qui rend toutes les cartes du pack visibles avec le filtre « Pièges fréquents » et dans le feedback existant. |
| `COMPOUND_CARDS` | **405 cartes**, vagues A45/B24/C141/D195. Les 200 couples `40 verbes × 5 temps` restent couverts. D ajoute une personne je/nous/vous par couple pour les 39 verbes personnels ; Falloir reste impersonnel. `subjectHint` précise le genre/nombre quand nécessaire, `trapKinds` décrit les critères de piège. Les scénarios ne sont utilisés qu'après réponse. |
| `EXC` | **45 exceptions** clé `"Verbe\|Temps"` → `{hl:[...], rule}`. `hl` = sous-chaînes à surligner en rouge dans la réponse (radicaux irréguliers, doubles muets, -yi-, dû, PP être…). Sert écran résultat ET Daily. |
| `PIEGES` | **37 pièges** person-spécifiques (homophones, formes surprenantes). `findPiege(c)` renvoie d'abord le `trapTip` des packs ciblés, puis consulte ce tableau. Affichés dans un encart ambre sur l'écran résultat, **masqués si une `EXC` couvre déjà la carte**. |
| `VERB_COMPLEMENT` | Complément neutre par verbe (parler→français, boire→de l'eau) pour les phrases-repères. 40 verbes du quiz. |
| `TENSE_FRAME` | Cadre de phrase par temps (« S'il le fallait, … » pour le conditionnel, « Il faut … » pour le subjonctif). |
| `DAILY_VERBS` | **27 verbes-pièges hors deck** (asseoir, essuyer, envoyer, manger, appeler…). Généré par verbecc, **collé tel quel** dans index.html. Format : `{verbe: {group, forms:{Temps:[6 formes]}, trap:{tense,hl,rule}}}`. |
| `TENSE_HELP` | Explications d'emploi par temps (panneau Aide + écran résultat). |

**18 verbes du deck** : Parler, Finir, Être, Avoir, Aller, Venir, Partir, Ouvrir, Courir, Prendre, Mettre, Dire, Faire, Voir, Pouvoir, Vouloir, Devoir, Savoir.
**15 temps/formes** : Présent, Imparfait, Futur simple, Passé simple, Conditionnel présent, Subjonctif présent, Impératif, Participe présent, Participe passé, Gérondif, Passé composé, Plus-que-parfait, Conditionnel passé, Futur antérieur, Subjonctif passé.
Pouvoir-Impératif n'existe pas (exclu). Formes non-personnelles : person = `''`.

---

## 4. Fonctionnalités par écran

- **screen-select (menu)** : stats points faibles (par temps/verbe), **session de répétition espacée** (Leitner : compteurs dû/nouvelles, tailles 10/20/30/Tout), filtres temps/verbe/groupe/difficile/piège, bloc **☁️ Synchronisation**, **mémo des temps** repliable, boutons `📅 Ma routine du jour` et `📖 Fiche révision`.
- **screen-daily** (`showDaily`/`renderDaily`) : routine de **rappel actif** : écrire de mémoire, révéler, comparer, cacher puis réécrire uniquement les formes ratées. Verbe du jour tiré du `DAILY_POOL` (40 = 13 verbes deck avec EXC + 27 `DAILY_VERBS`), tournant par `_dayIndex()`. Réponses **cachées** (amorces « je … ») jusqu'au bouton « 👁 Voir les réponses ». Rappel des pièges muets niveau natif. Streak 🔥 (`markDailyDone`).
- **screen-fiche** (`showFiche`) : **concordance des temps, contenu 100 % statique** (6 sections : subjonctif vs indicatif + piège certain/incertain ; double subjonctif ; subjonctif après toute principale ; hypothèse « si » ; futur dans le passé ; tableau discours indirect).
- **screen-quiz** (`showCard`/`validate`) : format unique **verbe + temps + personne**, pour les formes simples comme composées. **Jamais de phrase à trous, d'exemple de conjugaison dans le champ ni de badge piège/difficile avant la réponse.** Les temps composés précisent seulement le sujet et la contrainte d'accord indispensable (COD antéposé), sans phrase. Les scénarios complétés sont réservés à la correction. Choix facultatif du groupe sur les cartes simples, saisie + boutons d'accents, panneau Aide volontaire. Le texte seul active Valider/Entrée. Champ `#answer-input` a un **anti-autocorrection** (`onbeforeinput` bloque `insertReplacementText`).
- **Notation du quiz** : seule la forme verbale est comptabilisée. Pour une forme simple, elle est cherchée comme mot Unicode exact dans toute la saisie ; amorce/pronom, négation, ponctuation, complément et choix du groupe ne pénalisent pas (`que ts ailles`, `que tu n'ailles pas` et `que tu ailles.` valident tous `ailles`; `aille` reste faux). Pour un temps composé, `gradedForm` vérifie auxiliaire + participe + accord, tout en ignorant le sujet, le contexte, les négations et des adverbes usuels ; `a écrit`, `avait écrit` et `aurait écrit` restent donc distincts. Le choix du groupe est masqué sur ces cartes.
- **screen-result** : badge correct/incorrect avec réponse **surlignée en rouge** sur la partie exception, encart Exception (EXC) ou Piège (PIEGES), **phrase-repère** (buildExample), 3 boutons TTS, verso Anki.
- **screen-final** : score, cartes ratées, difficiles.

### Fonctions clés
`start(cards)` · `showCard()` · `validate()` · `buildSession(pool,size)` (SRS) · `srsUpdate(card,isOk)` · `highlightAnswer(c)`/`_hl(str,arr)` (surlignage rouge) · `buildExample(c)` (phrase-repère) · `cardException(c)`/`findPiege(c)` · `getFilteredCards()` · `syncNow(silent)` · `showDaily/showFiche/showSelect`.

---

## 5. localStorage (par origine — repart de zéro si l'URL change)

Depuis v29, `learning.js` gère le calcul des échéances et la sauvegarde complète JSON. Le score dépend toujours uniquement de la conjugaison. Une réponse aidée est repérée même après fermeture de l'aide et revient sous 1 jour ; une erreur sous 10 minutes. Facile accélère de deux boîtes, Difficile ramène au maximum à la boîte 1 / 1 jour. Une répétition dans les 24 h n'augmente pas la boîte. Reclasser une réponse ne recompte jamais les statistiques. Les marquages personnels persistants sont appliqués aux prochaines réponses ; Facile ne transforme jamais une erreur en réussite.

Le filtre Difficiles utilise `isDifficultCard` : union des formes-pièges (`isTrapCard`) et des marquages personnels. Facile retire le marquage personnel Difficile, sans effacer le caractère linguistiquement piégeux de la forme. Les conseils `trapTip` sont indépendants de la classification des temps composés.

Exporter/Importer sauvegarde stats, échéances SRS, marquages et routine. Validation stricte avant import, confirmation de remplacement dans l'interface, copie de récupération dans `conjugaison_before_restore` et rollback en cas d'erreur d'écriture. L'identité de l'appareil et la configuration Google ne sont pas remplacées. Google reste une synchronisation de stats uniquement.

| Clé | Contenu |
|-----|---------|
| `conjugaison_difficult` | Set des cartes marquées difficiles |
| `conjugaison_easy` | Set des cartes marquées faciles, exclusif des marquages difficiles |
| `conjugaison_stats` | `{tense:{...}, verb:{...}}` avec `{ok,n}` — agrégé, PAS par carte |
| `conjugaison_srs` | Boîtes de Leitner **par carte** `{box,seen,ok,last,due}` |
| `conjugaison_daily` | `{last:'YYYY-M-D', streak:N}` |
| `conjugaison_sync_url` / `_sync_last` | URL du script Google + horodatage dernière synchro |
| `conjugaison_device` | id d'appareil aléatoire |

---

## 6. Synchronisation cloud (stats → Google Sheet)

- Script Apps Script : [google_apps_script.gs](google_apps_script.gs) (non déployé automatiquement ; l'utilisateur l'a collé dans son Sheet).
- POST `text/plain` vers l'endpoint `/exec` (déployé « Tout le monde »), afin de rester une requête CORS simple. L'app n'affiche « Synchronisation confirmée » et ne met à jour la date de dernière sync qu'après une réponse JSON `{ok:true}` du script. Une erreur réseau/CORS reste signalée comme un envoi non confirmé.
- GET `/exec` sert uniquement de contrôle de santé et n'écrit jamais dans le Sheet. Seuls les POST avec un payload de stats valide peuvent modifier les onglets.
- Auto-sync à la fin de chaque série (`showFinal`) + bouton manuel. Le POST utilise `keepalive:true` pour réduire le risque d'annulation si la PWA est quittée juste après la série.
- **Google Sheet** : titre « Conjugaison stats », `fileId 1xljdHfBp92H_uCbyaxHHFTa6olBfGXiVcARgZnqbbZM`, compte maximlang000@gmail.com. Onglets : Historique (1 ligne/sync + JSON brut), Résumé temps, Résumé verbes (pire score en haut).
- **Un LLM peut lire ce Sheet directement** via le connecteur Google Drive (`read_file_content`, fileId ci-dessus) — pas besoin de copier-coller. Dernière lecture connue : 142 réponses, 65 % ; points faibles **Conditionnel présent 19 %**, **Subjonctif présent 38 %** ; Présent/Imparfait maîtrisés.

---

## 7. Générateurs (dev-time, suivis par git)

Régénérer les données au lieu de taper des formes à la main.

- [gen_cards.py](gen_cards.py) : lit `conjugaison_français.txt` (deck Anki, non commité) → `cards_output.js` (les 753 cartes). Réordonne [je,nous,tu,vous,il,ils]→[je,tu,il,nous,vous,ils], applique l'élision, saute « N'existe pas ». `--inline-index` régénère le bloc historique délimité dans `index.html`; `--check-index` vérifie qu'il est à jour.
- [gen_daily_verbs.py](gen_daily_verbs.py) : conjugue une liste `POOL` de verbes-pièges avec **verbecc** → `daily_verbs.js` (= `const DAILY_VERBS`), à **recoller** dans index.html. Setup : `pip install verbecc tzdata`. API : `from verbecc import CompleteConjugator; CompleteConjugator(lang='fr').conjugate(v)` puis `json.loads(str(r))`. **Vérifier chaque forme** — verbecc s'est trompé sur `haïr` (« j'hais »), retiré. Étendre le pool = ajouter une ligne (verbe → group, trap tense, hl, rule) et relancer.
- [gen_extra_packs.py](gen_extra_packs.py) : valide `target_verbs_golden.json` puis régénère le bloc inline `TARGET_CARDS` dans `index.html`. `--check` vérifie que l'inline est à jour ; `--verify-verbecc` fait un contrôle croisé sans remplacer le golden. Les six formes personnelles de `falloir`, absentes de verbecc 2.0.2, sont une divergence déclarée et restent fondées sur Le Robert/Académie.
- [gen_compound_packs.py](gen_compound_packs.py) : valide `compound_tenses_golden.json` et régénère le bloc inline `COMPOUND_CARDS`. `--check-index` contrôle l'inline et `--write-index` le met à jour. Les formes sont relues et sourcées Académie française/OQLF.
- [gen_compound_persons.py](gen_compound_persons.py) : génère D avec verbecc ; `--check` compare les 195 formes au moteur. Dépendances locales `.tmp/verbdeps_local` + `.tmp/verbdeps`. Les tests contrôlent aussi les auxiliaires et participes sur une référence indépendante relue.

Vérifications : `python -B -m unittest discover`, les trois checks de générateurs, `node test_input_matching.js`, `node test_quiz_format.js`, `node test_learning.js`, `node test_app_flow.js`. Les deux derniers contrôlent sauvegarde/restitution/rollback et le parcours JavaScript complet avec DOM simulé ; ils ne remplacent pas une vérification visuelle sur téléphone.
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
