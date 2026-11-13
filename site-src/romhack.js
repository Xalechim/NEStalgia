/* The "romhack" article look: a drag-to-compare slider over each hack's original and hacked screenshots.
   Without this script the page still shows the hacked screenshot (the box's own background). */
(function () {
  var calm = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.querySelectorAll(".cmp").forEach(function (box) {
    var top = document.createElement("div"); top.className = "cmp-top";
    var line = document.createElement("div"); line.className = "cmp-line";
    var l = document.createElement("span"); l.className = "cmp-tag l"; l.textContent = "Original";
    var r = document.createElement("span"); r.className = "cmp-tag r"; r.textContent = "Hacked";
    var range = document.createElement("input");
    range.type = "range"; range.min = 0; range.max = 100; range.value = 50; range.className = "cmp-range";
    range.setAttribute("aria-label", "Slide to compare the original game (left) with the hack (right)");
    box.append(top, line, l, r, range);
    function set(v) { box.style.setProperty("--p", v + "%"); }
    set(50);
    range.addEventListener("input", function () { set(range.value); });
    if (calm || !("IntersectionObserver" in window)) return;
    var seen = new IntersectionObserver(function (es) {  // one small sweep the first time it scrolls into view, to hint that it moves
      if (!es[0].isIntersecting) return;
      seen.disconnect();
      var t0 = null, path = [[0, 50], [450, 85], [1000, 15], [1500, 50]];
      (function step(t) {
        if (t0 === null) t0 = t;
        var e = t - t0, v = 50;
        for (var i = 1; i < path.length; i++) {
          if (e <= path[i][0]) { var a = path[i - 1], b = path[i]; v = a[1] + (b[1] - a[1]) * (e - a[0]) / (b[0] - a[0]); break; }
          v = path[i][1];
        }
        if (document.activeElement === range) return;
        range.value = v; set(v);
        if (e < 1500) requestAnimationFrame(step);
      })(performance.now());
    }, { threshold: 0.6 });
    seen.observe(box);
  });
})();
