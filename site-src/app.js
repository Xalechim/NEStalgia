// Filter/sort for the episode list. Cards carry data-* attributes; no framework needed.
// The chosen filters live in the page address (?verdict=essential&genre=rpg), so a filtered list can be shared.
(function () {
  var grid = document.getElementById("grid");
  if (!grid) return;
  var cards = Array.prototype.slice.call(grid.children);
  var q = document.getElementById("q");
  var count = document.getElementById("count");
  var clear = document.getElementById("clear-filters");
  var typeBtns = document.querySelectorAll("[data-filter]");
  var verdictBtns = Array.prototype.slice.call(document.querySelectorAll("button[data-verdict]"));
  var fields = Array.prototype.slice.call(document.querySelectorAll("[data-f]"));
  var type = "all", newest = true;
  if (grid.dataset.sort === "oldest") newest = false;

  function all(list, fn) { Array.prototype.forEach.call(list, fn); }

  // ---- read the address
  var params = new URLSearchParams(location.search);
  if (params.get("q")) q.value = params.get("q");
  if (params.get("type")) type = params.get("type");
  if (params.get("sort") === "oldest") newest = false;
  if (params.get("sort") === "newest") newest = true;
  var chosen = (params.get("verdict") || "").split(",").filter(Boolean);
  verdictBtns.forEach(function (b) { b.setAttribute("aria-pressed", chosen.indexOf(b.dataset.verdict) !== -1 ? "true" : "false"); });
  fields.forEach(function (f) { if (params.get(f.dataset.f)) f.value = params.get(f.dataset.f); });

  var names = { dev: new Set(), pub: new Set() };
  cards.forEach(function (c) {
    ["dev", "pub"].forEach(function (k) { (c.dataset[k] || "").split("|").forEach(function (n) { if (n) names[k].add(n); }); });
  });

  function has(c, key, term) { return (" " + (c.dataset[key] || "") + " ").indexOf(" " + term + " ") !== -1; }

  function matches(c, term, verdicts) {
    if (type !== "all" && c.dataset.type !== type) return false;
    if (term && c.dataset.title.indexOf(term) === -1 && c.dataset.num !== term) return false;
    if (verdicts.length && verdicts.indexOf(c.dataset.verdict) === -1) return false;
    for (var i = 0; i < fields.length; i++) {
      var key = fields[i].dataset.f, val = fields[i].value.trim().toLowerCase();
      if (!val) continue;
      if (key === "has") { if (!has(c, "has", val)) return false; }
      else if (key === "dev" || key === "pub") {
        var list = c.dataset[key] || "";
        // a full name from a tag or the list matches that company only ("nintendo" is not "nintendo research & development 1");
        // anything else you type matches as a fragment
        if (names[key].has(val) ? ("|" + list + "|").indexOf("|" + val + "|") === -1 : list.indexOf(val) === -1) return false;
      }
      else if ((c.dataset[key] || "") !== val) return false;
    }
    return true;
  }

  function save(verdicts) {
    var p = new URLSearchParams();
    if (q.value.trim()) p.set("q", q.value.trim());
    if (type !== "all") p.set("type", type);
    if (newest === (grid.dataset.sort !== "oldest")) { /* default order: leave it out of the address */ }
    else p.set("sort", newest ? "newest" : "oldest");
    if (verdicts.length) p.set("verdict", verdicts.join(","));
    fields.forEach(function (f) { if (f.value.trim()) p.set(f.dataset.f, f.value.trim()); });
    var s = p.toString();
    history.replaceState(null, "", location.pathname + (s ? "?" + s : ""));
  }

  function render() {
    var term = q.value.trim().toLowerCase();
    var verdicts = verdictBtns.filter(function (b) { return b.getAttribute("aria-pressed") === "true"; })
                              .map(function (b) { return b.dataset.verdict; });
    var shown = 0;
    cards.forEach(function (c) {
      var ok = matches(c, term, verdicts);
      c.hidden = !ok;
      if (ok) shown++;
    });
    // The number on each verdict button: how many games would match with that verdict under every OTHER filter chosen
    // (so Season 7 shows how many Essentials there are in season 7, and picking a verdict doesn't zero out the others).
    verdictBtns.forEach(function (b) {
      var n = 0;
      cards.forEach(function (c) { if (matches(c, term, [b.dataset.verdict])) n++; });
      var span = b.querySelector("span");
      if (span) span.textContent = n;
    });
    var ordered = cards.slice().sort(function (a, b) {
      return newest ? b.dataset.date.localeCompare(a.dataset.date) : a.dataset.date.localeCompare(b.dataset.date);
    });
    ordered.forEach(function (c) { grid.appendChild(c); });
    all(typeBtns, function (x) { x.setAttribute("aria-pressed", x.dataset.filter === type ? "true" : "false"); });
    document.getElementById("sort").textContent = newest ? "Newest first" : "Oldest first";
    var active = verdicts.length || fields.some(function (f) { return f.value.trim(); });
    if (clear) clear.hidden = !active;
    count.textContent = shown + " of " + cards.length + " shown" + (shown === 0 ? ". Try removing a filter." : "");
    save(verdicts);
  }

  q.addEventListener("input", render);
  all(typeBtns, function (b) {
    b.addEventListener("click", function () { type = b.dataset.filter; render(); });
  });
  verdictBtns.forEach(function (b) {
    b.addEventListener("click", function () {
      b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") === "true" ? "false" : "true");
      render();
    });
  });
  fields.forEach(function (f) { f.addEventListener("input", render); f.addEventListener("change", render); });
  if (clear) clear.addEventListener("click", function () {
    verdictBtns.forEach(function (b) { b.setAttribute("aria-pressed", "false"); });
    fields.forEach(function (f) { f.value = ""; });
    render();
  });
  document.getElementById("sort").addEventListener("click", function () { newest = !newest; render(); });
  render();
})();
