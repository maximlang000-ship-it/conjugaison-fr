const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const index = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');

function inlineCards(section, variable) {
  const start = index.indexOf(`// BEGIN GENERATED ${section} CARDS`);
  const end = index.indexOf(`// END GENERATED ${section} CARDS`, start);
  assert.ok(start >= 0 && end > start, `Bloc ${section} absent`);
  const match = index.slice(start, end).match(new RegExp(`const\\s+${variable}\\s*=\\s*(\\[.*\\])\\s*;`, 's'));
  assert.ok(match, `Tableau ${variable} absent`);
  return JSON.parse(match[1]);
}

const cards = [
  ...inlineCards('HISTORICAL', 'CARDS'),
  ...inlineCards('TARGET', 'TARGET_CARDS'),
  ...inlineCards('COMPOUND', 'COMPOUND_CARDS'),
];
assert.equal(cards.length, 1358, 'Cartes historiques et nouvelles formes présentes');

const quizStart = index.indexOf('<div id="screen-quiz">');
const quizEnd = index.indexOf('<div id="screen-result">', quizStart);
assert.ok(quizStart >= 0 && quizEnd > quizStart);
const quizHtml = index.slice(quizStart, quizEnd);
assert.doesNotMatch(quizHtml, /q-prompt|q-scenario|q-piege-badge|btn-easy|btn-difficult|___/);

// DOM simulé : exécute le vrai showCard pour chaque carte, sans navigateur.
const nodes = new Map([...quizHtml.matchAll(/id="([^"]+)"/g)].map(([, id]) => {
  const classes = new Set();
  return [id, {
    textContent: '', innerHTML: '', value: '', placeholder: '', style: {},
    focus() {},
    classList: {
      add: name => classes.add(name),
      remove: name => classes.delete(name),
      contains: name => classes.has(name),
    },
  }];
}));
const context = vm.createContext({
  queue: [], current: 0, selectedGroup: 3, helpOpen: true,
  TENSE_HELP: Object.fromEntries(cards.map(c => [c.tense, 'Aide seulement sur demande'])),
  document: {getElementById(id) {
    assert.ok(nodes.has(id), `Élément absent du quiz : ${id}`);
    return nodes.get(id);
  }},
  _resetTts() {}, updateProgress() {}, setTimeout() {},
  showScreen(id) { assert.equal(id, 'screen-quiz'); },
});
const start = index.indexOf('function showCard(');
const end = index.indexOf('function selectGroup(', start);
assert.ok(start >= 0 && end > start);
vm.runInContext(index.slice(start, end), context);

for (const card of cards) {
  // Un accès au scénario, à l'exemple ou à la règle avant réponse est interdit.
  context.queue = [new Proxy(card, {get(target, key) {
    assert.ok(!['prompt', 'scenario', 'trapTip', 'cardBack'].includes(key), `Fuite avant réponse : ${key}`);
    return target[key];
  }})];
  nodes.get('help-panel').classList.add('visible');
  nodes.get('answer-input').value = 'ancienne réponse';
  context.showCard();
  assert.equal(nodes.get('q-verb').textContent, card.verb);
  assert.equal(nodes.get('q-tense').textContent, card.tense);
  assert.equal(nodes.get('q-person-wrap').style.display, card.person ? '' : 'none');
  if (card.person) assert.ok(nodes.get('q-person').textContent.startsWith(card.person));
  assert.equal(nodes.get('answer-input').value, '');
  assert.equal(nodes.get('answer-input').placeholder, 'Écris la forme conjuguée…');
  assert.equal(nodes.get('answer-question-label').textContent, 'Ta conjugaison');
  assert.equal(nodes.get('help-panel').classList.contains('visible'), false);
  const question = ['q-verb', 'q-tense', 'q-person', 'answer-question-label']
    .map(id => nodes.get(id).textContent).join(' ');
  assert.doesNotMatch(question, /___|complète|piège|difficile|ex\s*:/i);
}

console.log(`OK: format original sans phrase à trous sur les ${cards.length} cartes`);
