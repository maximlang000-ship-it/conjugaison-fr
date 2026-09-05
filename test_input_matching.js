const fs = require('fs');
const path = require('path');

const index = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const start = index.indexOf('function _escapeHtml(');
const end = index.indexOf('function speak(', start);
if (start < 0 || end < 0) throw new Error('Fonctions de comparaison introuvables');

// Exécute exactement les helpers livrés par index.html, sans recopier leur logique.
eval(index.slice(start, end));

const promptHelpersStart = index.indexOf('function compoundSubject(');
const promptHelpersEnd = index.indexOf('//  INTERACTIONS QUIZ', promptHelpersStart);
if (promptHelpersStart < 0 || promptHelpersEnd < 0) {
  throw new Error('Helpers de consigne des temps composés introuvables');
}
eval(index.slice(promptHelpersStart, promptHelpersEnd));

function accepted(input, answer, variants = []) {
  return _isAcceptedVerbAnswer(input, { answer, answerVariants: variants });
}

function acceptedCompound(input, answer, gradedForm, gradedVariants = []) {
  return _isAcceptedVerbAnswer(input, { answer, gradedForm, gradedVariants });
}

const simpleCases = [
  ['pronom erroné ignoré', 'que ts ailles', 'que tu ailles', [], true],
  ['négation ignorée', 'que tu n’ailles pas', 'que tu ailles', [], true],
  ['ponctuation ignorée', 'que tu ailles.', 'que tu ailles', [], true],
  ['forme seule acceptée', 'ailles', 'que tu ailles', [], true],
  ['complément ignoré', 'demain, nous irons au marché', 'nous irons', [], true],
  ['lettre verbale manquante refusée', 'que tu aille', 'que tu ailles', [], false],
  ['mot plus long refusé', 'que tu aillespas', 'que tu ailles', [], false],
  ['accent manquant refusé sans variante', 'il connait', 'il connaît', [], false],
  ['variante rectifiée acceptée', 'il connait.', 'il connaît', ['il connait'], true],
  ['futur et conditionnel distingués', 'je parlerais', 'je parlerai', [], false],
];

for (const [label, input, answer, variants, expected] of simpleCases) {
  const actual = accepted(input, answer, variants);
  if (actual !== expected) {
    throw new Error(`${label}: ${JSON.stringify(input)} -> ${actual}, attendu ${expected}`);
  }
}

const compoundCases = [
  ['groupe verbal seul accepté', 'ai écrit', 'j’ai écrit', 'ai écrit', [], true],
  ['élision typographique acceptée', 'hier, j’ai écrit au bureau.', 'j’ai écrit', 'ai écrit', [], true],
  ['élision droite acceptée', "hier, j'ai écrit au bureau.", 'j’ai écrit', 'ai écrit', [], true],
  ['pronom erroné ignoré', 'tu ai écrit', 'j’ai écrit', 'ai écrit', [], true],
  ['contexte et complément ignorés', 'hier, nous avions résolu le problème', 'nous avions résolu', 'avions résolu', [], true],
  ['auxiliaire d’un autre temps refusé', 'j’avais écrit', 'j’ai écrit', 'ai écrit', [], false],
  ['mauvais auxiliaire refusé', 'je suis écrit', 'j’ai écrit', 'ai écrit', [], false],
  ['participe erroné refusé', 'j’ai écris', 'j’ai écrit', 'ai écrit', [], false],
  ['accord attendu accepté', 'ils sont parties hier', 'elles sont parties', 'sont parties', [], true],
  ['accord erroné refusé', 'elles sont parti hier', 'elles sont parties', 'sont parties', [], false],
  ['négation simple ignorée', 'je n’ai pas écrit', 'j’ai écrit', 'ai écrit', [], true],
  ['négation renforcée ignorée', 'je n’ai plus jamais écrit', 'j’ai écrit', 'ai écrit', [], true],
  ['adverbes usuels ignorés', 'j’ai déjà bien écrit', 'j’ai écrit', 'ai écrit', [], true],
  ['quantité ignorée', 'j’ai beaucoup écrit', 'j’ai écrit', 'ai écrit', [], true],
  ['intensité ignorée', 'j’ai très bien écrit', 'j’ai écrit', 'ai écrit', [], true],
  ['modalité ignorée', 'j’ai probablement écrit', 'j’ai écrit', 'ai écrit', [], true],
  ['rien ignoré', 'je n’ai rien écrit', 'j’ai écrit', 'ai écrit', [], true],
  ['négation avec mauvais temps refusée', 'je n’avais rien écrit', 'j’ai écrit', 'ai écrit', [], false],
  ['verbe intercalé refusé', 'j’ai voulu écrit', 'j’ai écrit', 'ai écrit', [], false],
  ['pronom inversé ignoré', 'ai-je écrit ?', 'j’ai écrit', 'ai écrit', [], true],
  ['t euphonique et pronom ignorés', 'a-t-il écrit ?', 'il a écrit', 'a écrit', [], true],
  ['autre élément verbal refusé', 'le texte a été écrit', 'il a écrit', 'a écrit', [], false],
  ['variante composée acceptée', 'elles se sont assises', 'elles se sont assises', 'sont assis', ['sont assises'], true],
  ['variante composée non implicite', 'elles se sont assises', 'elles se sont assis', 'sont assis', [], false],
];

for (const [label, input, answer, gradedForm, variants, expected] of compoundCases) {
  const actual = acceptedCompound(input, answer, gradedForm, variants);
  if (actual !== expected) {
    throw new Error(`${label}: ${JSON.stringify(input)} -> ${actual}, attendu ${expected}`);
  }
}

const hostile = `<img src=x onerror=alert(1)> & "'`;
const escaped = _escapeHtml(hostile);
if (escaped !== '&lt;img src=x onerror=alert(1)&gt; &amp; &quot;&#39;') {
  throw new Error(`échappement HTML altéré : ${escaped}`);
}

const promptCases = [
  ['sujet extrait sans révéler la forme', {compound:true, answer:'elle est venue', gradedForm:'est venue'}, 'elle'],
  ['subjonctif conservé dans le sujet', {compound:true, answer:'qu’elles aient prises', gradedForm:'aient prises'}, 'qu’elles'],
  ['carte simple sans sujet ajouté', {answer:'elle vient'}, ''],
];
for (const [label, card, expected] of promptCases) {
  const actual = compoundSubject(card);
  if (actual !== expected) throw new Error(`${label}: ${actual}, attendu ${expected}`);
}

const agreementCases = [
  ['COD féminin pluriel', {verb:'Lire', skill:'accord_cod_avant', gradedForm:'ai lues'}, 'COD féminin pluriel avant le verbe'],
  ['COD féminin singulier', {verb:'Recevoir', skill:'accord_cod_avant', gradedForm:'ayons reçue'}, 'COD féminin singulier avant le verbe'],
  ['faire sans infinitif', {verb:'Faire', skill:'accord_cod_avant', gradedForm:'ont faites'}, 'COD féminin pluriel avant le verbe, sans infinitif après'],
];
for (const [label, card, expected] of agreementCases) {
  const actual = compoundAgreementContext(card);
  if (actual !== expected) throw new Error(`${label}: ${actual}, attendu ${expected}`);
}

console.log(`OK: ${simpleCases.length + compoundCases.length} cas de comparaison + ${promptCases.length + agreementCases.length} consignes + échappement HTML`);
