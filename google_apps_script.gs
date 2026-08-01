/**
 * Conjugaison FR — réception des stats dans un Google Sheet
 *
 * INSTALLATION (une seule fois) :
 *  1. Va sur https://sheets.google.com → crée une feuille vide.
 *  2. Menu  Extensions → Apps Script.
 *  3. Efface tout et colle ce fichier.
 *  4. Clique sur  Déployer → Nouveau déploiement.
 *  5. Type : « Application Web ».
 *       - Exécuter en tant que : Moi
 *       - Qui a accès        : Tout le monde
 *  6. Déploie, autorise l'accès, COPIE l'URL qui finit par /exec.
 *  7. Colle cette URL dans l'app (écran filtres → Synchronisation).
 *
 * Pour mettre à jour le code plus tard : Déployer → Gérer les déploiements
 * → crayon → Version « Nouvelle version » → Déployer (l'URL reste la même).
 */

function doPost(e) { return handlePost(e); }
function doGet() {
  return json({ ok: true, service: 'Conjugaison FR sync', write: false });
}

function handlePost(e) {
  var data;
  try {
    if (!e || !e.postData || !e.postData.contents) {
      throw new Error('Payload manquant');
    }
    data = JSON.parse(e.postData.contents);
    if (!validPayload(data)) throw new Error('Payload invalide');
  } catch (err) {
    return json({ ok: false, error: String(err) });
  }

  var lock = LockService.getScriptLock();
  try { lock.waitLock(20000); } catch (err) {}
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var stats  = data.stats;
    var device = data.device;
    var ts     = data.ts;

    // Total global
    var totalN = 0, totalOk = 0;
    if (stats.tense) {
      Object.keys(stats.tense).forEach(function (k) {
        totalN  += stats.tense[k].n;
        totalOk += stats.tense[k].ok;
      });
    }
    var pct = totalN ? Math.round(totalOk / totalN * 100) : 0;

    // ── Onglet « Historique » : 1 ligne par synchro ──────────
    var hist = ss.getSheetByName('Historique') || ss.insertSheet('Historique');
    if (hist.getLastRow() === 0) {
      hist.appendRow(['Date', 'Appareil', 'Total réponses', 'Score %', 'JSON brut']);
    }
    // Anti-doublon : même appareil + même horodatage que la dernière ligne
    var skip = false;
    var last = hist.getLastRow();
    if (last >= 2) {
      var prev = hist.getRange(last, 1, 1, 2).getDisplayValues()[0];
      if (prev[0] === ts && prev[1] === device) skip = true;
    }
    if (!skip) {
      hist.appendRow([ts, device, totalN, pct, JSON.stringify(stats)]);
    }

    // ── Onglets résumé (reconstruits à chaque fois, pire score d'abord) ──
    writeSummary(ss, 'Résumé temps',  stats.tense);
    writeSummary(ss, 'Résumé verbes', stats.verb);

    return json({ ok: true, total: totalN, pct: pct });
  } catch (err) {
    return json({ ok: false, error: String(err) });
  } finally {
    try { lock.releaseLock(); } catch (err) {}
  }
}

function validPayload(data) {
  if (!isObject(data) ||
      typeof data.device !== 'string' || !/^dev-[a-z0-9]{6}$/.test(data.device) ||
      !isIsoTimestamp(data.ts) ||
      !isObject(data.stats) || !isObject(data.stats.tense) || !isObject(data.stats.verb)) {
    return false;
  }
  return validStatsGroup(data.stats.tense) && validStatsGroup(data.stats.verb);
}

function validStatsGroup(group) {
  var keys = Object.keys(group);
  if (keys.length > 100) return false;
  return keys.every(function (key) {
    var item = group[key];
    return key.length > 0 && key.length <= 100 && !/^[=+\-@]/.test(key) && isObject(item) &&
      isCounter(item.ok) && isCounter(item.n) && item.ok <= item.n;
  });
}

function isIsoTimestamp(value) {
  if (typeof value !== 'string' ||
      !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)) return false;
  var date = new Date(value);
  return !isNaN(date.getTime()) && date.toISOString() === value;
}

function isCounter(value) {
  return typeof value === 'number' && isFinite(value) &&
    value >= 0 && Math.floor(value) === value;
}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function writeSummary(ss, name, data) {
  var sh = ss.getSheetByName(name) || ss.insertSheet(name);
  sh.clear();
  sh.appendRow(['Nom', 'Réussis', 'Total', '%']);
  if (!data) return;
  var rows = Object.keys(data).map(function (k) {
    var n = data[k].n, ok = data[k].ok;
    return [k, ok, n, n ? Math.round(ok / n * 100) : 0];
  }).sort(function (a, b) { return a[3] - b[3]; }); // pire % en haut
  rows.forEach(function (r) { sh.appendRow(r); });
}

function json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
