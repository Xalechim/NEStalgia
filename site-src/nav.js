// Top menu: when the links don't fit on one line, the ones that don't fit move into a "More" dropdown.
(function () {
  var nav = document.getElementById("nav");
  if (!nav) return;
  var linksEl = nav.querySelector(".links"), more = nav.querySelector(".more");
  var btn = more.querySelector(".morebtn"), menu = more.querySelector(".menu");
  var links = Array.prototype.slice.call(linksEl.querySelectorAll("a"));
  var pending = false;

  function close() { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); }

  function fit() {
    pending = false;
    close();
    links.forEach(function (a) { linksEl.appendChild(a); });  // start from "everything visible"
    more.hidden = true;
    if (linksEl.scrollWidth <= linksEl.clientWidth + 1) return;
    more.hidden = false;                                       // the button takes room too
    var i = links.length;
    while (i > 0 && linksEl.scrollWidth > linksEl.clientWidth + 1) {
      i--;
      menu.insertBefore(links[i], menu.firstChild);
    }
    if (menu.querySelector("[aria-current]")) btn.setAttribute("aria-current", "page"); else btn.removeAttribute("aria-current");
  }

  function schedule() { if (!pending) { pending = true; requestAnimationFrame(fit); } }

  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    var open = menu.hidden;
    menu.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  });
  document.addEventListener("click", function (e) { if (!more.contains(e.target)) close(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { close(); btn.focus(); } });
  window.addEventListener("resize", schedule);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(schedule);
  fit();
})();
