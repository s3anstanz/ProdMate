// ProdMate guided report: live reload. Inlined into report.html by scripts/report.py.
// When the page is served by scripts/report_server.py, poll its version endpoint and
// reload when ProdMate rewrites the report. Opened as a file, it does nothing.
(function () {
  if (location.protocol !== "http:") return;
  var seen = null;
  function check() {
    fetch("/__prodmate/version", { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        if (seen !== null && data.version !== seen) location.reload();
        seen = data.version;
      })
      .catch(function () { /* server stopped: keep showing the last version */ });
  }
  check();
  setInterval(check, 2000);
})();
