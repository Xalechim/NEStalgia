// Finds each game's NES soundtrack on KHInsider and the first track longer than 30 seconds.
// KHInsider blocks scripts (Cloudflare) but works normally in a browser, so this is run IN a browser tab that is open on
// https://downloads.khinsider.com/ (for example the Claude browser pane): paste it into the page's JavaScript console.
//
// Usage, after pasting this file:
//   var r = await khLookup(455, "Nobunaga's Ambition II");   // { album, track, trackName, dur, mp3, ... } or { error }
// Run it for every title (a few at a time, with its built-in pauses), keep the results with an mp3 as rows of
//   [episode, album, track, trackName, dur, mp3]
// and save them to a JSON file for scripts/python/download_game_music.py.
// Check the album it picked: score 100+ is a title match; lower scores are partial matches worth a glance.
window.khSleep = ms => new Promise(r => setTimeout(r, ms));
window.khNorm = s => s.toLowerCase().replace(/&/g, "and").replace(/^the\s+/, "").replace(/[^a-z0-9]/g, "");
window.khSecs = d => { var p = d.split(":").map(Number); return p.length == 2 ? p[0] * 60 + p[1] : p[0] * 3600 + p[1] * 60 + p[2]; };
window.khDoc = async function (url) { await khSleep(450); var r = await fetch(url); return new DOMParser().parseFromString(await r.text(), "text/html"); };
window.khSearch = async function (q) {
  var d = await khDoc("/search?search=" + encodeURIComponent(q));
  return Array.from(d.querySelectorAll("table.albumList tr")).slice(1).map(r => {
    var tds = r.querySelectorAll("td"); if (tds.length < 5) return null; var a = tds[1].querySelector("a");
    return { title: a ? a.textContent.trim() : "", href: a ? a.getAttribute("href") : "", platform: tds[2].textContent.trim(), type: tds[3].textContent.trim(), year: tds[4].textContent.trim() };
  }).filter(Boolean);
};
window.khPick = function (title, cands) {
  var want = khNorm(title);
  var nes = cands.filter(c => /\bNES\b|Famicom|Family Computer/i.test(c.platform));
  var score = c => { var n = khNorm(c.title), s = 0; if (n === want) s += 100; else if (n.startsWith(want) || want.startsWith(n)) s += 60; else if (n.includes(want) || want.includes(n)) s += 30; else return -1;
    if (/gamerip/i.test(c.type)) s += 5; var y = +c.year; if (y >= 1985 && y <= 1994) s += 3; return s; };
  var scored = nes.map(c => [score(c), c]).filter(x => x[0] >= 0).sort((a, b) => b[0] - a[0]);
  return { best: scored[0] && scored[0][1], bestScore: scored[0] && scored[0][0], others: scored.slice(1, 3).map(x => x[1].title + " (" + x[1].year + ")") };
};
window.khLookup = async function (num, title) {
  var out = { num: num, title: title };
  var pick = null;
  for (var q of [title, title.replace(/[:\-–—].*$/, "").trim()]) { if (!q) continue; pick = khPick(title, await khSearch(q)); if (pick.best) break; }
  if (!pick || !pick.best) { out.error = "no NES album found"; return out; }
  out.album = pick.best.title; out.albumUrl = pick.best.href; out.year = pick.best.year; out.score = pick.bestScore; out.others = pick.others;
  var d = await khDoc(pick.best.href);
  var tracks = Array.from(d.querySelectorAll("#songlist tr")).filter(r => r.querySelector("td.clickable-row")).map((r, i) => {
    var a = r.querySelector("td.clickable-row a");
    return { i: i + 1, name: a.textContent.trim(), href: a.getAttribute("href"), dur: Array.from(r.querySelectorAll("td")).map(t => t.textContent.trim()).find(t => /^\d+:\d\d(:\d\d)?$/.test(t)) || "" };
  });
  var t = tracks.find(t => t.dur && khSecs(t.dur) > 30);
  if (!t) { out.error = "no track over 30 seconds"; return out; }
  out.track = t.i; out.trackName = t.name; out.dur = t.dur;
  var sd = await khDoc(t.href);
  out.mp3 = Array.from(sd.querySelectorAll("a")).map(a => a.href).find(h => /\.mp3$/i.test(h));
  if (!out.mp3) out.error = "no mp3 link on track page";
  return out;
};
