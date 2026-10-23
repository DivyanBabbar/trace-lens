const $ = (selector) => document.querySelector(selector);
const form = $("#analysisForm");
const notice = $("#notice");
const demoButtons = [$("#loadDemo"), $("#emptyDemo")];
const analyzeButton = $("#analyzeButton");
const formatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

function setNotice(message, state = "ready") {
  notice.textContent = message;
  notice.dataset.state = state;
}

function setBusy(busy) {
  analyzeButton.disabled = busy;
  demoButtons.forEach((button) => {
    button.disabled = busy;
  });
  analyzeButton.querySelector("span").textContent = busy ? "…" : "→";
  analyzeButton.firstChild.textContent = busy ? "Analyzing… " : "Analyze incident window ";
}

function asLocalDateTime(value) {
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function asIsoDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    throw new Error("Enter a valid start and end time.");
  }
  return date.toISOString();
}

function makeElement(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatTime(value) {
  return formatter.format(new Date(value));
}

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : "The request could not be completed.");
  }
  return body;
}

function renderHypothesis(hypothesis) {
  const card = makeElement("article", "hypothesis");
  const top = makeElement("div", "hypothesis-top");
  const service = makeElement("div", "lead-service");
  service.append(
    makeElement("span", "rank", String(hypothesis.rank).padStart(2, "0")),
    makeElement("h3", "", hypothesis.service),
  );
  const confidence = Math.round(hypothesis.confidence * 100);
  top.append(service, makeElement("span", "confidence", `${confidence}% SCORE`));
  card.append(top, makeElement("p", "hypothesis-title", hypothesis.title));

  const scoreTrack = makeElement("div", "score-track");
  scoreTrack.setAttribute("role", "progressbar");
  scoreTrack.setAttribute("aria-label", `${hypothesis.service} evidence score`);
  scoreTrack.setAttribute("aria-valuemin", "0");
  scoreTrack.setAttribute("aria-valuemax", "100");
  scoreTrack.setAttribute("aria-valuenow", String(confidence));
  const score = document.createElement("span");
  score.style.width = `${confidence}%`;
  scoreTrack.append(score);
  card.append(scoreTrack);

  const details = makeElement("div", "lead-details");
  const evidence = document.createElement("div");
  evidence.append(makeElement("span", "detail-label", "SUPPORTING EVIDENCE"));
  hypothesis.evidence.slice(0, 4).forEach((item) => {
    const line = makeElement("p", "evidence-item");
    const source = makeElement("b", "", `${item.kind} · ${item.name}`);
    line.append(source, document.createTextNode(` — ${item.message || item.service}`));
    evidence.append(line);
  });
  const checks = document.createElement("div");
  checks.append(makeElement("span", "detail-label", "NEXT CHECKS"));
  const list = document.createElement("ul");
  list.className = "checks";
  hypothesis.suggested_checks.forEach((check) => list.append(makeElement("li", "", check)));
  checks.append(list);
  details.append(evidence, checks);
  card.append(details);
  return card;
}

function renderTimelineItem(event) {
  const item = makeElement("li", "timeline-item");
  item.dataset.severity = event.severity;
  item.append(makeElement("span", "timeline-dot"), makeElement("time", "event-time", formatTime(event.timestamp)));
  const copy = makeElement("div", "event-copy");
  const title = makeElement("b", "", `${event.service} · ${event.name}`);
  copy.append(title, document.createTextNode(` — ${event.message || event.kind}`));
  copy.append(makeElement("span", "event-meta", `${event.kind.toUpperCase()} · ${event.severity.toUpperCase()}`));
  item.append(copy);
  return item;
}

function renderReport(report) {
  const services = new Set(report.timeline.map((event) => event.service));
  const lead = report.hypotheses[0];
  $("#signalCount").textContent = String(report.timeline.length);
  $("#serviceCount").textContent = String(services.size);
  $("#leadConfidence").textContent = lead ? `${Math.round(lead.confidence * 100)}%` : "—";
  $("#windowSummary").textContent = `${formatTime(report.started_at)} – ${formatTime(report.ended_at)}`;
  $("#impactSummary").textContent = report.impact_summary;
  $("#hypothesisCount").textContent = `${report.hypotheses.length} ${report.hypotheses.length === 1 ? "LEAD" : "LEADS"}`;
  $("#timelineCount").textContent = `${report.timeline.length} EVENTS`;

  const hypotheses = $("#hypotheses");
  hypotheses.replaceChildren();
  if (report.hypotheses.length) {
    report.hypotheses.forEach((hypothesis) => hypotheses.append(renderHypothesis(hypothesis)));
  } else {
    hypotheses.append(makeElement("p", "empty-state", "No service hypothesis met the ranking rules in this time window."));
  }
  const timeline = $("#timeline");
  timeline.replaceChildren(...report.timeline.map(renderTimelineItem));
  $("#disclaimer").textContent = report.disclaimer;
  $("#emptyState").hidden = true;
  $("#results").hidden = false;
}

async function analyzeWindow(payload) {
  setBusy(true);
  setNotice("Comparing deployments, errors, severity, and downstream signals…", "busy");
  try {
    const report = await request("/v1/incidents/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderReport(report);
    setNotice(`Analysis complete. ${report.timeline.length} signals reviewed across ${new Set(report.timeline.map((event) => event.service)).size} services.`, "ready");
  } catch (error) {
    setNotice(error.message || "Analysis failed. Check the time window and try again.", "error");
  } finally {
    setBusy(false);
  }
}

async function loadDemo() {
  setBusy(true);
  setNotice("Loading six synthetic signals across four services…", "busy");
  try {
    const demo = await request("/v1/demo/load", { method: "POST" });
    $("#startTime").value = asLocalDateTime(demo.started_at);
    $("#endTime").value = asLocalDateTime(demo.ended_at);
    $("#serviceFilter").value = "";
    const report = await request("/v1/incidents/analyze", {
      method: "POST",
      body: JSON.stringify({ started_at: demo.started_at, ended_at: demo.ended_at }),
    });
    renderReport(report);
    setNotice(`${demo.accepted} synthetic signals loaded. Review the ranked lead and its evidence below.`, "ready");
  } catch (error) {
    setNotice(error.message || "The demo scenario could not be loaded.", "error");
  } finally {
    setBusy(false);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const startedAt = asIsoDateTime($("#startTime").value);
    const endedAt = asIsoDateTime($("#endTime").value);
    if (new Date(endedAt) <= new Date(startedAt)) {
      throw new Error("End time must be later than start time.");
    }
    const payload = { started_at: startedAt, ended_at: endedAt };
    const service = $("#serviceFilter").value.trim();
    if (service) payload.service = service;
    await analyzeWindow(payload);
  } catch (error) {
    setNotice(error.message, "error");
  }
});

demoButtons.forEach((button) => button.addEventListener("click", loadDemo));

const now = new Date();
$("#startTime").value = asLocalDateTime(new Date(now.getTime() - 15 * 60_000));
$("#endTime").value = asLocalDateTime(now);
request("/health")
  .then((health) => {
    if (health.signals) {
      $("#signalCount").textContent = String(health.signals);
    }
  })
  .catch(() => setNotice("The API is not responding yet. Refresh after the service starts.", "error"));
