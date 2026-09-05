/* Logique pure : révisions et validation des sauvegardes, utilisable hors ligne. */
const Learning = (() => {
  const DAY = 86400000;
  const intervals = [0, 1, 3, 7, 16, 35];
  const keys = ['conjugaison_stats', 'conjugaison_srs', 'conjugaison_difficult',
    'conjugaison_easy', 'conjugaison_daily'];

  function schedule(previous, correct, assisted, rating, now) {
    const before = previous || {box:0, seen:0, ok:0, last:0, due:0};
    const record = {...before, seen:before.seen + 1, ok:before.ok + Number(correct), last:now};
    // Refaire immédiatement une carte ne permet pas de la déclarer maîtrisée.
    const canAdvance = !before.seen || now - before.last >= DAY;
    if (!correct) {
      record.box = 0;
      record.due = now + 10 * 60000;
    } else if (assisted || rating === 'hard') {
      record.box = Math.min(before.box, 1);
      record.due = now + DAY;
    } else {
      record.box = Math.min(5, before.box + (canAdvance ? (rating === 'easy' ? 2 : 1) : 0));
      record.due = now + Math.max(1, intervals[record.box]) * DAY;
    }
    return record;
  }

  function object(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value) &&
      Object.keys(value).every(k => !['__proto__','prototype','constructor'].includes(k));
  }
  function integer(value) { return Number.isSafeInteger(value) && value >= 0; }
  function validateBackup(backup, cards) {
    if (!object(backup) || backup.app !== 'conjugaison-fr' || backup.schema !== 1 ||
        typeof backup.createdAt !== 'string' || !Number.isFinite(Date.parse(backup.createdAt)) ||
        !object(backup.data) || Object.keys(backup.data).length !== keys.length ||
        !keys.every(k => Object.hasOwn(backup.data, k))) throw new Error('Format de sauvegarde incompatible.');
    const ids = new Set(cards.map(c => c.verb + '|' + c.tense + '|' + (c.person || '')));
    const data = backup.data;
    const stats = data.conjugaison_stats;
    if (!object(stats)) throw new Error('Statistiques invalides.');
    for (const group of Object.keys(stats)) {
      if (!['tense','verb'].includes(group) || !object(stats[group])) throw new Error('Statistiques invalides.');
      const known = new Set(cards.map(c => c[group]));
      for (const [name, record] of Object.entries(stats[group])) {
        if (!known.has(name) || !object(record) || !integer(record.ok) || !integer(record.n) || record.ok > record.n)
          throw new Error('Compteurs de statistiques invalides.');
      }
    }
    const srs = data.conjugaison_srs;
    if (!object(srs)) throw new Error('Révisions invalides.');
    for (const [id, record] of Object.entries(srs)) {
      if (!ids.has(id) || !object(record) || !['box','seen','ok','last','due'].every(k => integer(record[k])) ||
          record.box > 5 || record.ok > record.seen || record.due < record.last)
        throw new Error('Échéance de révision invalide.');
    }
    for (const key of ['conjugaison_difficult','conjugaison_easy']) {
      const list = data[key];
      if (!Array.isArray(list) || list.length > cards.length || new Set(list).size !== list.length || !list.every(id => ids.has(id)))
        throw new Error('Marquages de cartes invalides.');
    }
    const easy = new Set(data.conjugaison_easy);
    if (data.conjugaison_difficult.some(id => easy.has(id))) throw new Error('Une carte est à la fois facile et difficile.');
    const daily = data.conjugaison_daily;
    if (!object(daily)) throw new Error('Routine invalide.');
    if (Object.keys(daily).length) {
      const match = typeof daily.last === 'string' && daily.last.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
      if (!match || !integer(daily.streak)) throw new Error('Routine invalide.');
      const date = new Date(Date.UTC(+match[1], +match[2] - 1, +match[3]));
      if (date.getUTCFullYear() !== +match[1] || date.getUTCMonth() !== +match[2] - 1 || date.getUTCDate() !== +match[3])
        throw new Error('Date de routine invalide.');
    }
    return data;
  }

  function backup(storage, cards, version) {
    const data = {};
    for (const key of keys) {
      const fallback = /_(easy|difficult)$/.test(key) ? '[]' : '{}';
      data[key] = JSON.parse(storage.getItem(key) || fallback);
    }
    const result = {app:'conjugaison-fr', schema:1, version, createdAt:new Date().toISOString(), data};
    validateBackup(result, cards);
    return result;
  }

  function restore(storage, candidate, cards) {
    const data = validateBackup(candidate, cards);
    const previous = keys.map(key => [key, storage.getItem(key)]);
    // La copie de récupération doit réussir avant toute modification.
    storage.setItem('conjugaison_before_restore', JSON.stringify(previous));
    try {
      for (const key of keys) storage.setItem(key, JSON.stringify(data[key]));
    } catch (error) {
      for (const [key, value] of previous) {
        if (value === null) storage.removeItem(key);
        else storage.setItem(key, value);
      }
      throw error;
    }
  }
  return {schedule, validateBackup, backup, restore};
})();
if (typeof module !== 'undefined') module.exports = Learning;
