/* The "haunted" article look: the team-letter tiles on the NES Baseball page. Everything else on that page is plain CSS. */
(function () {
  document.querySelectorAll(".hx-letters").forEach(function (box) {
    var tiles = box.querySelectorAll(".tiles b"), read = box.querySelector(".read"), btns = box.querySelectorAll(".words button");
    box.hidden = false;
    btns.forEach(function (b) {
      b.addEventListener("click", function () {
        var w = b.dataset.w, on = b.getAttribute("aria-pressed") === "true";
        btns.forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
        tiles.forEach(function (t) { t.classList.remove("on"); t.style.order = ""; });
        if (on) { read.textContent = "Pick a word. The tiles will do the rest."; return; }
        b.setAttribute("aria-pressed", "true");
        tiles.forEach(function (t) {
          var i = w.indexOf(t.textContent);
          if (i > -1) { t.classList.add("on"); t.style.order = i; } else { t.style.order = 9; }
        });
        read.textContent = w + ": " + b.dataset.t;
      });
    });
  });
})();
