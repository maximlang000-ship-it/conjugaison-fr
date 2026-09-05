const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('index.html','utf8');
const storage = new Map();
function element() {
  const classes = new Set();
  return {style:{},value:'',checked:false,textContent:'',innerHTML:'',attributes:{},
    classList:{add:c=>classes.add(c),remove:c=>classes.delete(c),toggle(c,on){
      const value=on===undefined?!classes.has(c):on;
      if(value)classes.add(c);else classes.delete(c);return value;
    }},focus(){},setAttribute(k,v){this.attributes[k]=v;},appendChild(){}};
}
const nodes=new Map([...html.matchAll(/id="([^"]+)"/g)].map(([,id])=>[id,element()]));
const ctx=vm.createContext({console,URL,Blob,setTimeout(){},
  window:{scrollTo(){}},navigator:{onLine:false},
  localStorage:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
  document:{getElementById(id){assert.ok(nodes.has(id),'Élément manquant : '+id);return nodes.get(id);},
    querySelectorAll(){return [];},addEventListener(){},createElement:element},
});
vm.runInContext(fs.readFileSync('learning.js','utf8'),ctx);
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],ctx);
const run=code=>vm.runInContext(code,ctx);
assert.equal(nodes.get('screen-select').style.display,'block');
run("globalThis.card = CARDS.find(c => c.verb === 'Parler' && c.tense === 'Passé composé' && c.wave === 'C')");
assert.equal(run('isTrapCard(card)'),false);
run('queue=[card];current=0;toggleDifficult()');
assert.equal(run('isDifficultCard(card)'),true);
run('toggleEasy()');
assert.equal(run('isDifficultCard(card)'),false);
run("globalThis.trap=CARDS.find(c=>c.verb==='Dire' && c.tense==='Présent' && c.person==='2e pers. du pluriel')");
assert.equal(run('isTrapCard(trap)'),true);
nodes.get('sw-diff').checked=true;
assert.equal(run('getFilteredCards().every(isDifficultCard)'),true);
assert.equal(run('getFilteredCards().some(c=>cardId(c)===cardId(trap))'),true);
nodes.get('sw-diff').checked=false;

run('start([trap])');
nodes.get('answer-input').value=run('trap.answer');
run('validate()');
const baseline=run('srsData[cardId(trap)].due');
assert.equal(run('score'),1);
run('validate()');
assert.equal(run('score'),1); // double Entrée : un seul résultat
run('toggleEasy()');
assert.ok(run('srsData[cardId(trap)].due')>baseline);
run('toggleDifficult()');
assert.equal(run('srsData[cardId(trap)].seen'),1);
assert.equal(run('easyIds.has(cardId(trap))'),false);
assert.equal(nodes.get('btn-difficult').attributes['aria-pressed'],'true');

run('start([card]);toggleHelp();toggleHelp()');
nodes.get('answer-input').value=run('card.answer');
run('validate();toggleEasy()');
assert.equal(run('srsData[cardId(card)].due-lastReview.now'),86400000);
assert.match(nodes.get('review-status').textContent,/réponse aidée/);
run('start([card])');
nodes.get('answer-input').value='erreur';
run('validate();toggleEasy()');
assert.equal(run('srsData[cardId(card)].due-lastReview.now'),600000);
assert.equal(run('score'),0);
run('nextCard()');
assert.equal(nodes.get('screen-final').style.display,'block');
// Toutes les consignes de la routine : personne explicite, aucun blanc à compléter.
const dailyPrompts = run(String.raw`DAILY_POOL.flatMap(verb => [...new Set([
  ...DAILY_HARD_TENSES, _dailyTrap(verb)?.tense
].filter(Boolean))].flatMap(tense => [..._dailyBlock(verb, tense, null, '').matchAll(/<i class="dp">([^<]*)<\/i>/g)].map(m=>m[1])))`);
assert.ok(dailyPrompts.length > 0);
for (const prompt of dailyPrompts) {
  assert.doesNotMatch(prompt, /…|_{2,}|\.{3}/);
  assert.match(prompt, /pers\. du|Forme verbale/);
}
console.log('OK: démarrage app, filtres, quiz, double validation, boutons, aide refermée, erreur et bilan');
