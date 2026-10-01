// Tabs on episode pages: Show notes / Links / Transcript. Deep-linkable (#links, #transcript).
(function () {
  var box = document.querySelector(".tabs");
  if (!box) return;
  var tabs = Array.prototype.slice.call(box.querySelectorAll('[role="tab"]'));

  function show(tab, focus) {
    tabs.forEach(function (t) {
      var on = t === tab;
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
    if (focus) tab.focus();
  }

  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () {
      show(t);
      history.replaceState(null, "", "#" + t.id.replace("t-", ""));
    });
    t.addEventListener("keydown", function (e) {
      var j = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : -1;
      if (j >= 0) { e.preventDefault(); show(tabs[(j + tabs.length) % tabs.length], true); }
    });
  });

  function fromHash() {
    var want = document.getElementById("t-" + location.hash.slice(1));
    show(want && tabs.indexOf(want) >= 0 ? want : tabs[0]);
  }
  window.addEventListener("hashchange", fromHash);
  fromHash();
})();
