// ProdMate guided report: live reload. Inlined into report.html by scripts/report.py.
// When the page is served by scripts/report_server.py, poll its version endpoint and
// reload when ProdMate rewrites the report, keeping open sections and the scroll
// position. Opened as a file, it does nothing.
(function () {
  if (location.protocol !== "http:") return;
  var KEY = "prodmate-open";

  // A name for each fold-out that survives a re-render: the item's id for rows,
  // the heading for sections, both scoped to their app.
  function keyOf(d) {
    var app = d.closest(".app-section");
    var row = d.closest("[data-id]");
    var heading = d.querySelector(":scope > summary h2");
    var part = d.dataset.id || (row ? row.dataset.id + " " + d.className
      : heading ? heading.textContent : (d.closest(".first") ? "first " : "") + d.className);
    return (app ? app.id : "") + "|" + part;
  }

  function save() {
    var state = { y: window.scrollY, open: {} };
    document.querySelectorAll("details").forEach(function (d) { state.open[keyOf(d)] = d.open; });
    try { sessionStorage.setItem(KEY, JSON.stringify(state)); } catch (e) { /* storage blocked: reload without keeping state */ }
  }

  function restore() {
    var state = null;
    try {
      state = JSON.parse(sessionStorage.getItem(KEY) || "null");
      sessionStorage.removeItem(KEY);
    } catch (e) { /* storage blocked or unreadable: show the page as rendered */ }
    if (!state || !state.open) return;
    document.querySelectorAll("details").forEach(function (d) {
      var k = keyOf(d);
      if (Object.prototype.hasOwnProperty.call(state.open, k)) d.open = state.open[k];
    });
    window.scrollTo(0, state.y || 0);
  }

  // Start from the version of the page actually on screen, so a render that lands
  // before the first poll still reloads it.
  var meta = document.querySelector('meta[name="prodmate-render"]');
  var seen = meta ? meta.content : null;
  function check() {
    fetch("/__prodmate/version", { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        if (seen !== null && data.version !== seen) { save(); location.reload(); }
        seen = data.version;
      })
      .catch(function () { /* server stopped: keep showing the last version */ });
  }
  restore();
  check();
  setInterval(check, 2000);
})();
