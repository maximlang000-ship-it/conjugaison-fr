const assert = require('node:assert/strict');
const Learning = require('./learning.js');
const DAY = 86400000;
const now = 1780000000000;
const before = {box:2, seen:4, ok:3, last:now-2*DAY, due:now};
const normal = Learning.schedule(before, true, false, null, now);
const easy = Learning.schedule(before, true, false, 'easy', now);
const hard = Learning.schedule(before, true, false, 'hard', now);
const assisted = Learning.schedule(before, true, true, 'easy', now);
const failed = Learning.schedule(before, false, false, 'easy', now);
assert.ok(easy.due > normal.due && hard.due < normal.due);
assert.equal(assisted.due, now+DAY);
assert.equal(failed.box, 0);
assert.equal(failed.due, now+600000);
assert.equal(normal.seen, easy.seen); // reclasser ne recompte pas la réponse
assert.equal(before.seen, 4); // snapshot conservé
const repeated = Learning.schedule(normal, true, false, 'easy', now+60000);
assert.equal(repeated.box, normal.box);

const fs = require('node:fs');
const html = fs.readFileSync('index.html','utf8');
const cards = ['CARDS','TARGET_CARDS','COMPOUND_CARDS'].flatMap(name =>
  JSON.parse(html.match(new RegExp('const\\s+'+name+'\\s*=\\s*(\\[.*\\])\\s*;'))[1]));
const c = cards[0], id = c.verb+'|'+c.tense+'|'+c.person;
const memory = new Map([
  ['conjugaison_stats', JSON.stringify({tense:{[c.tense]:{n:4,ok:3}},verb:{[c.verb]:{n:4,ok:3}}})],
  ['conjugaison_srs', JSON.stringify({[id]:before})],
  ['conjugaison_easy', JSON.stringify([id])],
  ['conjugaison_daily', JSON.stringify({last:'2026-9-5',streak:3})],
  ['conjugaison_device','dev-local1'],
]);
const storage = {getItem:k=>memory.get(k)??null, setItem:(k,v)=>memory.set(k,v), removeItem:k=>memory.delete(k)};
const backup = Learning.backup(storage,cards,'v29');
memory.delete('conjugaison_srs');
Learning.restore(storage,JSON.parse(JSON.stringify(backup)),cards);
assert.deepEqual(JSON.parse(storage.getItem('conjugaison_srs')),{[id]:before});
assert.equal(storage.getItem('conjugaison_device'),'dev-local1');
assert.ok(storage.getItem('conjugaison_before_restore'));
for (const mutate of [
  b=>b.schema=99,
  b=>b.data.conjugaison_srs[id].box=20,
  b=>b.data.conjugaison_stats.tense[c.tense].ok=99,
  b=>b.data.conjugaison_daily.last='2026-2-31',
  b=>b.data.conjugaison_difficult.push(id),
  b=>b.data.conjugaison_easy.push('unknown'),
  b=>b.data.conjugaison_srs=JSON.parse('{"__proto__":{}}'),
]) {
  const invalid=JSON.parse(JSON.stringify(backup)); mutate(invalid);
  const state=JSON.stringify([...memory]);
  assert.throws(()=>Learning.restore(storage,invalid,cards));
  assert.equal(JSON.stringify([...memory]),state);
}
// Erreur d'écriture après le début de la restauration : restauration des valeurs antérieures.
const prior=JSON.stringify([...memory].filter(([k])=>k!=='conjugaison_before_restore'));
let writes=0;
const failing={...storage,setItem(k,v){if(++writes===3)throw Error('quota'); storage.setItem(k,v);}};
assert.throws(()=>Learning.restore(failing,backup,cards),/quota/);
assert.equal(JSON.stringify([...memory].filter(([k])=>k!=='conjugaison_before_restore')),prior);
console.log('OK: espacement, aide, reclassification, répétition immédiate, sauvegarde complète, rejets et rollback');
