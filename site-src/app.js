// Filter/sort for the episode list. Cards carry data-* attributes; no framework needed.
(function () {
  var grid = document.getElementById("grid");
  if (!grid) return;
  var cards = Array.prototype.slice.call(grid.children);
  var q = document.getElementById("q");
  var count = document.getElementById("count");
  var type = "all", newest = true;

  function render() {
    var term = q.value.trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (c) {
      var ok = (type === "all" || c.dataset.type === type) &&
               (!term || c.dataset.title.indexOf(term) !== -1 || c.dataset.num === term);
      c.hidden = !ok;
      if (ok) shown++;
    });
    var ordered = cards.slice().sort(function (a, b) {
      return newest ? b.dataset.date.localeCompare(a.dataset.date) : a.dataset.date.localeCompare(b.dataset.date);
    });
    ordered.forEach(function (c) { grid.appendChild(c); });
    count.textContent = shown + " of " + cards.length + " shown";
  }

  q.addEventListener("input", render);
  Array.prototype.forEach.call(document.querySelectorAll("[data-filter]"), function (b) {
    b.addEventListener("click", function () {
      type = b.dataset.filter;
      Array.prototype.forEach.call(document.querySelectorAll("[data-filter]"), function (x) {
        x.setAttribute("aria-pressed", x === b ? "true" : "false");
      });
      render();
    });
  });
  document.getElementById("sort").addEventListener("click", function () {
    newest = !newest;
    this.textContent = newest ? "Newest first" : "Oldest first";
    render();
  });
  render();
})();
