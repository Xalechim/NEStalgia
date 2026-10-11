// Screenshot carousels: a row of slides you can swipe or scroll; this adds the arrows, the dots and a counter.
(function () {
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  Array.prototype.forEach.call(document.querySelectorAll(".carousel"), function (c) {
    var track = c.querySelector(".car-track");
    if (!track || track.children.length < 2) return;
    var slides = Array.prototype.slice.call(track.children), n = slides.length, cur = 0;

    function el(tag, cls, text) { var e = document.createElement(tag); e.className = cls; if (text) e.textContent = text; return e; }
    var bar = el("div", "car-bar");
    var prev = el("button", "car-btn", "‹"), next = el("button", "car-btn", "›");
    prev.type = next.type = "button";
    prev.setAttribute("aria-label", "Previous screenshot");
    next.setAttribute("aria-label", "Next screenshot");
    var dots = el("div", "car-dots"), count = el("span", "car-count");
    count.setAttribute("aria-live", "polite");
    var dotEls = slides.map(function (s, i) {
      var d = el("button", "car-dot"); d.type = "button"; d.setAttribute("aria-label", "Screenshot " + (i + 1) + " of " + n);
      d.addEventListener("click", function () { go(i); }); dots.appendChild(d); return d;
    });
    bar.appendChild(prev); bar.appendChild(dots); bar.appendChild(count); bar.appendChild(next);
    c.appendChild(bar);

    function show(i) {
      cur = i;
      dotEls.forEach(function (d, k) { if (k === i) d.setAttribute("aria-current", "true"); else d.removeAttribute("aria-current"); });
      count.textContent = (i + 1) + " / " + n;
      prev.disabled = i === 0; next.disabled = i === n - 1;
    }
    function go(i) {
      i = Math.max(0, Math.min(n - 1, i));
      track.scrollTo({ left: i * track.clientWidth, behavior: reduce ? "auto" : "smooth" });
      show(i);
    }
    var t;
    track.addEventListener("scroll", function () {
      clearTimeout(t);
      t = setTimeout(function () { show(Math.round(track.scrollLeft / track.clientWidth)); }, 60);
    });
    track.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") { go(cur - 1); e.preventDefault(); }
      if (e.key === "ArrowRight") { go(cur + 1); e.preventDefault(); }
    });
    prev.addEventListener("click", function () { go(cur - 1); });
    next.addEventListener("click", function () { go(cur + 1); });
    c.classList.add("ready");
    show(0);
  });
})();
