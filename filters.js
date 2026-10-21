/* Filters shared by the Research and Books pages: type and topic lists plus a year list.
   Years: the last 5 stay visible; older years sit behind "Earlier", which opens once and
   closes by itself when the reader scrolls back up to the recent years. */
(function () {
  function start() {
  var wait = document.getElementById("cat-wait"), empty = null;
  var typeRail = document.getElementById("type-rail"), topicRail = document.getElementById("topic-rail"), yearRail = document.getElementById("year-rail");
  if (!yearRail) return;
  var TYPES = [["Journal article", "Journal articles"], ["Working paper", "Working papers"], ["Op-ed", "Op-eds"],
               ["Blog post", "Blog posts"], ["Book", "Books"], ["Chapter", "Chapters"]];
  var RECENT_FROM = new Date().getFullYear() - 4;
  var state = { type: "", topic: "", earlier: false, sawOlder: false };
  var rows = function () { return Array.prototype.slice.call(document.querySelectorAll("ul.entries li")); };
  var topicsOf = function (li) { return li.dataset.topics ? li.dataset.topics.split("|") : []; };
  var typesOf = function (li) { return (li.dataset.types || li.dataset.type || "").split("|"); };
  var matchType = function (li) { return !state.type || typesOf(li).indexOf(state.type) > -1; };
  var matchTopic = function (li) { return !state.topic || topicsOf(li).indexOf(state.topic) > -1; };
  var link = function (attr, val, on, label, n) {
    return '<a href="#" data-' + attr + '="' + val + '" class="' + (on ? "on" : "") + '">' + label + "&nbsp;<span>" + n + "</span></a>";
  };

  function render() {
    var last = "", years = [], topicCounts = {}, typeCounts = {}, nTopic = 0, nType = 0;
    rows().forEach(function (li) {
      var yr = li.querySelector(".yr"), okT = matchType(li), okP = matchTopic(li);
      li.removeAttribute("id");
      if (okT) { nTopic++; topicsOf(li).forEach(function (k) { topicCounts[k] = (topicCounts[k] || 0) + 1; }); }
      if (okP) { nType++; typesOf(li).forEach(function (t) { typeCounts[t] = (typeCounts[t] || 0) + 1; }); }
      if (!(okT && okP)) { li.style.display = "none"; return; }
      li.style.display = "";
      var y = yr.dataset.y;
      yr.textContent = y !== last ? y : "";
      if (y !== last) { li.id = "y" + y; years.push(y); }
      last = y;
    });
    if (typeRail) typeRail.innerHTML = link("f", "", !state.type, "All", nType) +
      TYPES.filter(function (t) { return typeCounts[t[0]]; }).map(function (t) { return link("f", t[0], state.type === t[0], t[1], typeCounts[t[0]]); }).join("");
    if (topicRail) topicRail.innerHTML = link("topic", "", !state.topic, "All", nTopic) +
      Object.keys(topicCounts).sort().map(function (k) { return link("topic", k, state.topic === k, k, topicCounts[k]); }).join("");
    var recent = years.filter(function (y) { return +y >= RECENT_FROM; }), older = years.filter(function (y) { return +y < RECENT_FROM; });
    var yl = function (y, cls) { return '<a href="#y' + y + '" data-y="' + y + '" class="' + cls + '">' + y + "</a>"; };
    yearRail.innerHTML = recent.map(function (y) { return yl(y, ""); }).join("") +
      (older.length && !state.earlier ? '<button type="button" class="more" aria-expanded="false">Earlier (' + older.length + ") ▾</button>" : "") +
      (state.earlier ? older.map(function (y) { return yl(y, "older"); }).join("") : "");
    spy();
    if (wait) { wait.classList.add("done"); wait = null; }      // loaded in time: the waiting cat is not needed
    var shown = rows().some(function (li) { return li.style.display !== "none"; });
    if (!empty) {
      empty = document.createElement("div");
      empty.className = "cat-empty";
      empty.appendChild(window.makeCat("sleep"));
      empty.appendChild(document.createTextNode("Nothing here yet."));
      var list = document.querySelector("ul.entries");
      list.parentNode.insertBefore(empty, list.nextSibling);
    }
    empty.style.display = shown ? "none" : "";
  }

  function spy() {
    var cur = null;
    yearRail.querySelectorAll("a").forEach(function (a) {
      var el = document.getElementById("y" + a.dataset.y);
      if (el && el.getBoundingClientRect().top <= 140) cur = a;
    });
    var on = cur || yearRail.querySelector("a");
    var older = on && +on.dataset.y < RECENT_FROM;
    if (state.earlier && !older && state.sawOlder) { state.earlier = false; state.sawOlder = false; render(); return; }   // scrolled back up: collapse
    if (!state.earlier && older) { state.earlier = true; state.sawOlder = true; render(); return; }                        // reading an older year: open
    if (state.earlier && older) state.sawOlder = true;
    yearRail.querySelectorAll("a").forEach(function (a) { a.classList.toggle("on", a === on); });
    if (!on) return;
    if (getComputedStyle(yearRail).flexDirection === "row")
      yearRail.scrollLeft = on.offsetLeft - yearRail.clientWidth / 2 + on.offsetWidth / 2;
    else if (on.offsetTop < yearRail.scrollTop) yearRail.scrollTop = on.offsetTop;
    else if (on.offsetTop + on.offsetHeight > yearRail.scrollTop + yearRail.clientHeight) yearRail.scrollTop = on.offsetTop + on.offsetHeight - yearRail.clientHeight;
  }

  document.addEventListener("click", function (e) {
    if (e.target.closest(".year-rail .more")) { state.earlier = true; state.sawOlder = false; render(); return; }
    var t = e.target.closest("[data-f]");
    if (t) { e.preventDefault(); state.type = t.dataset.f; render(); return; }
    var a = e.target.closest("[data-topic]");
    if (!a) return;
    e.preventDefault();
    state.topic = a.dataset.topic === state.topic ? "" : a.dataset.topic;
    render();
    if (a.classList.contains("tag")) window.scrollTo({ top: 0, behavior: "smooth" });
  });
  window.addEventListener("scroll", spy, { passive: true });
  render();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
