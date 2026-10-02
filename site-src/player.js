// Clickable timestamps: play the episode from that point in the page's audio player.
//  - Transcript/Links timestamps carry data-t (seconds on the final mix). The podcast host's audio can be shifted by an inserted
//    pre-roll, so each episode has a measured shift (data-offsets on .ep) that we add, plus an optional listener nudge.
//  - A small floating player appears when the main player is scrolled out of view.
//  - The paragraph being played is highlighted.
(function () {
  var host = document.querySelector(".ep");
  var audio = document.getElementById("player");
  if (!host || !audio || !document.querySelector("[data-t]")) return;

  var anchors;
  try { anchors = JSON.parse(host.getAttribute("data-offsets") || "[[0,0]]"); } catch (e) { anchors = [[0, 0]]; }
  var known = !!host.getAttribute("data-offsets");
  var KEY = "nestalgia-sync-" + (host.getAttribute("data-ep") || "x");
  var nudge = 0;
  try { nudge = parseFloat(localStorage.getItem(KEY)) || 0; } catch (e) {}

  function offsetAt(t) {
    var o = 0;
    for (var i = 0; i < anchors.length; i++) if (t >= anchors[i][0]) o = anchors[i][1];
    return o;
  }
  function toAudio(t) { return Math.max(0, t + offsetAt(t) + nudge); }
  function toMix(a) {
    var t = a - nudge;
    for (var i = anchors.length - 1; i >= 0; i--) if (t - anchors[i][1] >= anchors[i][0]) return t - anchors[i][1];
    return t - anchors[0][1];
  }
  function fmt(s) {
    s = Math.max(0, Math.floor(s || 0));
    var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    return (h ? h + ":" + (m < 10 ? "0" : "") : "") + m + ":" + (sec < 10 ? "0" : "") + sec;
  }

  function seek(t) {
    var target = toAudio(t);
    function go() {
      audio.currentTime = target;
      var p = audio.play();
      if (p && p.catch) p.catch(function () {});
    }
    if (audio.readyState >= 1) go();
    else { audio.addEventListener("loadedmetadata", go, { once: true }); audio.preload = "auto"; audio.load(); }
  }

  document.addEventListener("click", function (e) {
    var b = e.target.closest("button[data-t]");
    if (b) { seek(parseFloat(b.getAttribute("data-t"))); return; }
    var n = e.target.closest("button[data-nudge]");
    if (n) {
      var v = parseFloat(n.getAttribute("data-nudge"));
      nudge = v === 0 ? 0 : nudge + v;
      try { localStorage.setItem(KEY, String(nudge)); } catch (er) {}
      showSync();
    }
  });

  function showSync() {
    var base = known ? offsetAt(0) : 0;
    var text = (known ? "host audio is " + (base >= 0 ? "+" : "") + base.toFixed(1) + "s from the transcript" : "no shift measured") +
               (nudge ? ", your adjustment " + (nudge > 0 ? "+" : "") + nudge + "s" : "");
    Array.prototype.forEach.call(document.querySelectorAll(".sync-val"), function (o) { o.textContent = "(" + text + ")"; });
  }
  showSync();

  // highlight the paragraph being played
  var paras = Array.prototype.slice.call(document.querySelectorAll("p[data-t]")).map(function (p) {
    return { el: p, t: parseFloat(p.getAttribute("data-t")) };
  });
  var lastIdx = -1;
  function highlight() {
    if (!paras.length) return;
    var mix = toMix(audio.currentTime), idx = -1;
    for (var i = 0; i < paras.length; i++) { if (paras[i].t <= mix) idx = i; else break; }
    if (idx === lastIdx) return;
    if (lastIdx >= 0) paras[lastIdx].el.classList.remove("now");
    if (idx >= 0 && !audio.paused) paras[idx].el.classList.add("now");
    lastIdx = idx;
  }

  // floating mini player
  var bar = document.createElement("div");
  bar.className = "mini";
  bar.hidden = true;
  bar.innerHTML = '<button type="button" class="mini-play" aria-label="Play or pause">&#9654;</button>' +
    '<input type="range" class="mini-seek" min="0" max="100" step="1" value="0" aria-label="Seek">' +
    '<span class="mini-time">0:00</span><a class="mini-top" href="#player">Player &uarr;</a>';
  document.body.appendChild(bar);
  var playBtn = bar.querySelector(".mini-play"), seekBar = bar.querySelector(".mini-seek"), timeEl = bar.querySelector(".mini-time");
  var mainVisible = true;
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (en) { mainVisible = en[0].isIntersecting; update(); }).observe(audio);
  }

  function update() {
    var started = !audio.paused || audio.currentTime > 0;
    bar.hidden = mainVisible || !started;
    document.body.classList.toggle("has-mini", !bar.hidden);
    playBtn.innerHTML = audio.paused ? "&#9654;" : "&#10074;&#10074;";
    if (audio.duration) {
      seekBar.max = Math.floor(audio.duration);
      seekBar.value = Math.floor(audio.currentTime);
    }
    timeEl.textContent = fmt(audio.currentTime) + (audio.duration ? " / " + fmt(audio.duration) : "");
    highlight();
  }
  ["timeupdate", "play", "pause", "loadedmetadata", "durationchange", "seeked", "ended"].forEach(function (ev) { audio.addEventListener(ev, update); });
  playBtn.addEventListener("click", function () { if (audio.paused) audio.play(); else audio.pause(); });
  seekBar.addEventListener("input", function () { audio.currentTime = parseFloat(seekBar.value); });
})();
