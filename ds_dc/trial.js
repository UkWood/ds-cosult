"use strict";

const byId = id => document.getElementById(id);
const timeline = byId("timeline");
const notice = byId("notice");
const question = byId("question");
const model = byId("model");
const scope = byId("scope");
const selected = new Set();
const safeHosts = new Set(["www.mnppsaturn.ru", "mnppsaturn.ru", "ukwood.github.io"]);
const modes = {
  offline: "Офлайн · провайдер отключён",
  mock: "Проверочный режим · синтетические ответы",
  live: "LIVE · отправка может повлечь расходы",
};
const messages = {
  full: "Ответ подтверждён по выбранному вопросу.",
  partial: "Подтверждена часть ответа.",
  reference: "Доступны сведения из источников.",
  needs_support: "В доступных документах не удалось подтвердить ответ.",
  clarification: "Уточните модель, модификацию или назначение.",
  unavailable: "Документация для ответа недоступна.",
  not_ready: "Досье для этого запроса недоступно.",
  incomplete_dossier: "Документы для выбранной области недоступны.",
  sizing_unavailable: "Не удалось рассчитать объём запроса. Отправки в DeepSeek не было.",
  offline: "Офлайн-режим. DeepSeek отключён.",
  offline_no_provider: "Офлайн-режим. DeepSeek отключён.",
  domain_denied: "Введите технический вопрос о продукции «Сатурна».",
  invalid_request: "Проверьте введённые данные.",
  invalid_contract: "Ответ модели не прошёл проверку формата.",
  invalid_candidate: "Ответ модели не прошёл проверку формата.",
  over_cap: "Объём досье превышает лимит. Уточните вопрос или выберите область документации.",
  budget_exhausted: "Достигнут предел расходов запуска.",
  provider_unknown: "Итог операции и расходы неизвестны. Проверьте DeepSeek Usage.",
  provider_overage: "Использование превысило подтверждённый предел. Проверьте DeepSeek Usage.",
  provider_contract_drift: "Ответ DeepSeek отличается от принятого контракта.",
  provider_unavailable: "DeepSeek недоступен.",
  native_state_unavailable: "Не удалось подтвердить состояние операций. Проверьте журнал и DeepSeek Usage.",
  file_unavailable: "Не удалось открыть проверенный PDF.",
  provider_file_limit: "Превышено допустимое количество PDF.",
  invalid_native_request: "Запрос не прошёл локальную проверку перед отправкой в DeepSeek.",
  duplicate_request: "Этот запрос уже был принят.",
  activation_required: "Для входа в live-сеанс откройте ссылку из окна запуска стенда.",
  incomplete_finish: "Модель не завершила ответ.",
  session_denied: "Сеанс истёк или открыт в другом браузере. Проверьте состояние.",
  in_flight: "Предыдущий запрос ещё обрабатывается.",
  request_conflict: "Этот идентификатор уже использован. Проверьте состояние сеанса.",
  request_unavailable: "Запись недоступна в журнале.",
  journal_unavailable: "Не удалось сохранить данные в локальный журнал.",
  local_error: "Запрос завершился с ошибкой. Расходы неизвестны. Проверьте DeepSeek Usage.",
};
const unavailable = "Недоступно";
let csrf = null;
let state = null;
let expertMode = false;
let busy = false;
let networkUnknown = false;
function ownerCapabilityFromFragment() {
  if (!location.hash.startsWith("#owner=")) return null;
  const capability = location.hash.slice("#owner=".length);
  history.replaceState(null, "", location.pathname + location.search);
  return capability;
}
let ownerCapability = ownerCapabilityFromFragment();

function add(parent, tag, text, className) {
  const child = document.createElement(tag);
  if (text !== undefined && text !== null) child.textContent = text;
  if (className) child.className = className;
  parent.append(child);
  return child;
}

function message(code) {
  return messages[code] || indicator(code);
}

function indicator(value) {
  return typeof value === "string" && value ? value : unavailable;
}

function errorText(error) {
  return error instanceof RequestError ? message(error.status) : "Не удалось связаться с локальным стендом.";
}

function sourceURL(raw, page) {
  if (typeof raw !== "string") return null;
  try {
    const url = new URL(raw);
    if (url.protocol !== "https:" || !safeHosts.has(url.hostname) || url.username ||
        url.password || url.port || url.search) return null;
    if (url.hostname === "ukwood.github.io" && !url.pathname.startsWith("/Saturn-Main-Site/")) return null;
    if (url.hash && !/^#page=[1-9][0-9]{0,3}$/.test(url.hash)) return null;
    if (Number.isInteger(page) && page > 0 && !url.hash) url.hash = "page=" + page;
    return url;
  } catch {
    return null;
  }
}

function sourceLink(parent, raw, page, label) {
  const url = sourceURL(raw, page);
  if (!url) return;
  let name;
  try {
    name = decodeURIComponent(url.pathname);
  } catch {
    name = url.pathname;
  }
  const link = add(parent, "a", (label || name || url.hostname) + (page ? " · стр. " + page : ""));
  link.href = url.href;
  link.target = "_blank";
  link.rel = "noreferrer noopener";
}

function citations(parent, sources) {
  const links = new Map();
  for (const source of Array.isArray(sources) ? sources : []) {
    if (!source) continue;
    const url = sourceURL(source.url, source.page);
    if (url && !links.has(url.href)) links.set(url.href, source);
  }
  if (!links.size) return;
  const details = add(parent, "details");
  add(details, "summary", "Источники");
  details.open = true;
  const list = add(details, "ul");
  for (const source of links.values()) {
    sourceLink(add(list, "li"), source.url, source.page, source.label || source.title);
  }
}

function bulletList(parent, title, values) {
  if (!Array.isArray(values) || !values.some(value => typeof value === "string" && value)) return;
  add(parent, "strong", title);
  const list = add(parent, "ul");
  for (const value of values) {
    if (typeof value === "string" && value) add(list, "li", value);
  }
}

function readableJSON(parent, value) {
  if (!value || (typeof value === "object" && !Object.keys(value).length)) {
    add(parent, "p", unavailable);
    return;
  }
  add(parent, "pre", JSON.stringify(value, null, 2));
}

function detailsBox(parent, title, content) {
  const section = add(parent, "details");
  add(section, "summary", title);
  readableJSON(section, content);
}

function option(select, value, label) {
  add(select, "option", label).value = value;
}

function chooseModel(choices = []) {
  model.replaceChildren();
  option(model, "", "Без выбора");
  if (Array.isArray(choices)) {
    for (const choice of choices) {
      if (choice?.id && choice?.label) option(model, choice.id, choice.label);
    }
  }
  byId("model-field").hidden = model.options.length <= 1;
}

class RequestError extends Error {
  constructor(status) {
    super(status);
    this.status = status;
  }
}

async function read(route, body) {
  const options = {cache: "no-store", credentials: "same-origin", redirect: "error"};
  if (body !== undefined) {
    options.method = "POST";
    options.headers = {"Content-Type": "application/json", "X-CSRF-Token": csrf};
    options.body = JSON.stringify(body);
  }
  const response = await fetch(route, options);
  const result = await response.json();
  if (!response.ok) throw new RequestError(result.status);
  return result;
}

function updateButtons() {
  byId("send").disabled = !csrf || busy || !!state?.pending || networkUnknown;
  byId("reset").disabled = !csrf || busy || !!state?.pending;
  byId("expert").disabled = !csrf;
  byId("refresh").hidden = !networkUnknown && !state?.pending;
  byId("refresh").disabled = busy;
  byId("export-selected").disabled = !selected.size;
}

function reviewField(form, title, tag, value, limit) {
  const label = add(form, "label", title);
  const field = add(label, tag);
  field.value = value || "";
  if (limit) field.maxLength = limit;
  return field;
}

function reviewForm(parent, request, prior) {
  const form = add(parent, "form", null, "review-form");
  const rating = reviewField(form, "Оценка ответа", "select", "");
  option(rating, "", "Без оценки");
  option(rating, "correct", "Корректен и полезен");
  option(rating, "partial", "Частично корректен");
  option(rating, "incorrect", "Ошибочен");
  option(rating, "not_found", "Информация есть, но не найдена");
  rating.value = prior?.rating || "";
  const comment = reviewField(form, "Примечание", "textarea", prior?.comment, 2000);
  const expected = reviewField(form, "Ожидаемая информация", "textarea", prior?.expected, 2000);
  const reference = reviewField(form, "Ссылка на документацию «Сатурна»", "input", prior?.reference, 512);
  reference.type = "url";
  const submit = add(form, "button", "Сохранить оценку");
  const status = add(form, "p", prior?.utc ? "Последнее сохранение " + prior.utc : "", "review-notice");
  status.setAttribute("role", "status");
  form.addEventListener("submit", async event => {
    event.preventDefault();
    submit.disabled = true;
    try {
      const result = await read("/feedback", {
        request, rating: rating.value || null, comment: comment.value,
        expected: expected.value, reference: reference.value.trim(),
      });
      status.textContent = "Оценка сохранена " + result.feedback.utc;
    } catch (error) {
      status.textContent = errorText(error);
    } finally {
      submit.disabled = false;
    }
  });
}

function costUSD(microUSD) {
  if (!Number.isFinite(microUSD)) return unavailable;
  return (microUSD / 1e6).toLocaleString("ru-RU", {minimumFractionDigits: 2,
    maximumFractionDigits: 6}) + " USD";
}

function showFinancials(parent, telemetry) {
  const {estimated_micro_usd, known_micro_usd, held_micro_usd, cost_state, budget, ...details} = telemetry || {};
  const unknown = held_micro_usd > 0 || cost_state === "unknown" ||
    (known_micro_usd === null && (details.chat_attempted || details.upload?.attempted));
  const rows = [
    ["Локальная оценка", costUSD(estimated_micro_usd)],
    ["Расчёт по подтверждённым операциям", costUSD(known_micro_usd)],
  ];
  if (unknown) rows.push(["Итог начисления", "Неизвестен · проверьте DeepSeek Usage"]);
  if (budget) {
    rows.push(["Подтверждено за запуск", costUSD(budget.known_micro_usd)],
              ["Удержано в резерве за запуск", costUSD(budget.held_micro_usd)],
              ["Доступный остаток лимита запуска", costUSD(budget.remaining_micro_usd)]);
  }
  const list = add(parent, "dl", null, "financials");
  for (const [label, value] of rows) {
    add(list, "dt", label);
    add(list, "dd", value);
  }
  detailsBox(parent, "Диагностика, время, usage и операции", details);
}

function showExpert(parent, result) {
  const report = result.report || {};
  const b = report.B;
  const a = report.A;
  add(parent, "h3", "B — фактический ответ консультанта");
  add(parent, "p", b?.answer || unavailable, "answer");
  const {answer: _answer, ...verified} = b || {};
  detailsBox(parent, "Подтверждённые элементы B", verified);
  add(parent, "h3", "A — формулировки модели до проверки");
  add(parent, "p", "Сведения из A могут содержать ошибки.", "draft");
  const draft = typeof a === "string" ? a : a?.answer_candidate || a?.candidate_answer || a?.answer;
  if (draft) add(parent, "p", draft, "answer");
  detailsBox(parent, "Элементы A и причины проверки", a);
  detailsBox(parent, "Документы, страницы и контрольные суммы", report.documents || b?.citations);
  detailsBox(parent, "Профиль модели и версия запроса", report.provenance);
  showFinancials(parent, report.telemetry);
  add(parent, "p", "Сеанс " + result.session + " · запрос " + result.request);
  reviewForm(parent, result.request, result.feedback);
}

function expertPanel(card, request) {
  const panel = add(card, "details", null, "expert-data");
  panel.hidden = !expertMode;
  add(panel, "summary", "Экспертный разбор A/B и оценка");
  let loaded = false;
  panel.addEventListener("toggle", async () => {
    if (!panel.open || loaded || !expertMode) return;
    loaded = true;
    const content = add(panel, "div");
    try {
      const result = await read("/expert/" + encodeURIComponent(request));
      showExpert(content, result);
    } catch (error) {
      add(content, "p", errorText(error));
      loaded = false;
      panel.addEventListener("toggle", () => content.remove(), {once: true});
    }
  });
}

function renderTurn(turn) {
  const result = turn.answer || {};
  const card = add(timeline, "article");
  add(card, "p", turn.question, "question");
  const status = add(card, "p", result.message || message(result.status), "turn-status");
  status.dataset.status = result.status || "";
  if (result.answer) add(card, "p", result.answer, "answer");
  bulletList(card, "Что осталось уточнить", result.unresolved);
  bulletList(card, "Ограничения", result.limitations);
  citations(card, result.citations);
  if (Array.isArray(result.choices) && result.choices.length) {
    const choose = add(card, "button", "Уточнить модель", "secondary");
    choose.type = "button";
    choose.addEventListener("click", () => {
      chooseModel(result.choices);
      question.value = turn.question;
      model.focus();
    });
  }
  if (Array.isArray(result.scope_options) && result.scope_options.some(item => item?.id === "manual")) {
    const narrow = add(card, "button", "Выбрать основное руководство", "secondary");
    narrow.type = "button";
    narrow.addEventListener("click", () => {
      scope.value = "manual";
      question.value = turn.question;
      question.focus();
    });
  }
  const actions = add(card, "div", null, "turn-actions");
  if (result.answer) {
    const copy = add(actions, "button", "Копировать ответ", "secondary");
    copy.type = "button";
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(result.answer);
        notice.textContent = "Ответ скопирован.";
      } catch {
        notice.textContent = "Не удалось скопировать ответ.";
      }
    });
  }
  const label = add(actions, "label");
  label.className = "expert-only";
  label.hidden = !expertMode;
  const checkbox = add(label, "input");
  checkbox.type = "checkbox";
  checkbox.checked = selected.has(turn.request);
  label.append(" Включить в экспорт");
  checkbox.addEventListener("change", () => {
    if (checkbox.checked) selected.add(turn.request);
    else selected.delete(turn.request);
    updateButtons();
  });
  expertPanel(card, turn.request);
}

function showSession(session) {
  csrf = session.csrf;
  state = session;
  const profile = byId("profile");
  profile.textContent = modes[session.mode] || unavailable;
  profile.dataset.mode = session.mode;
  timeline.replaceChildren();
  session.timeline.forEach(renderTurn);
  if (session.pending) {
    const active = add(timeline, "article");
    add(active, "p", session.pending.question, "question");
    notice.textContent = "Запрос обрабатывается. Здесь можно проверить его состояние.";
  } else {
    notice.textContent = "";
  }
}

async function refresh() {
  busy = true;
  updateButtons();
  try {
    const ownerToken = ownerCapability;
    ownerCapability = null;
    showSession(ownerToken ? await read("/activate", {owner_token: ownerToken}) : await read("/session"));
    networkUnknown = false;
  } catch (error) {
    notice.textContent = errorText(error);
    networkUnknown = true;
  } finally {
    busy = false;
    updateButtons();
  }
}

function renderCatalog(content, entries) {
  content.replaceChildren();
  add(content, "p", "Закреплённый корпус стенда охватывает перечисленные изделия и документы.");
  const catalog = add(content, "ul");
  for (const entry of entries) {
    if (!entry) continue;
    const item = add(catalog, "li");
    if (sourceURL(entry.url)) sourceLink(item, entry.url, null, entry.label);
    else add(item, "strong", entry.label);
    if (Number.isInteger(entry.pdf_count)) {
      const summary = ["PDF " + entry.pdf_count];
      if (Number.isInteger(entry.pages)) summary.push("страниц " + entry.pages);
      add(item, "span", " · " + summary.join(", "));
    }
    bulletList(item, "Ограничения", entry.limitations);
    if (!Array.isArray(entry.documents) || !entry.documents.length) continue;
    const docs = add(item, "details");
    add(docs, "summary", "Документы");
    const list = add(docs, "ul");
    for (const doc of entry.documents) {
      if (!doc) continue;
      const row = add(list, "li");
      const label = doc.label || doc.title || doc.name;
      if (sourceURL(doc.url)) sourceLink(row, doc.url, null, label);
      else add(row, "span", label || unavailable);
      if (Number.isInteger(doc.pages)) add(row, "span", " · страниц " + doc.pages);
      if (doc.state || doc.status) add(row, "span", " · " + indicator(doc.state || doc.status));
    }
  }
}

byId("coverage").addEventListener("toggle", async () => {
  const panel = byId("coverage");
  const content = byId("catalog");
  if (!panel.open || !csrf || content.dataset.loaded) return;
  content.dataset.loaded = "true";
  try {
    const result = await read("/catalog");
    renderCatalog(content, result.catalog);
  } catch (error) {
    content.textContent = errorText(error);
    delete content.dataset.loaded;
  }
});

byId("question-form").addEventListener("submit", async event => {
  event.preventDefault();
  if (!csrf || busy || state?.pending || networkUnknown) return;
  const value = question.value;
  if (!value.trim() || [...value].length > 1200) {
    notice.textContent = "Введите вопрос длиной от 1 до 1200 символов.";
    return;
  }
  busy = true;
  updateButtons();
  notice.textContent = "Подбираю и проверяю документы…";
  try {
    const body = {request: crypto.randomUUID(), question: value, scope: scope.value};
    if (model.value) body.hint = model.value;
    const result = await read("/ask", body);
    state.timeline.push(result.turn);
    renderTurn(result.turn);
    question.value = "";
    chooseModel();
    scope.value = "full";
    notice.textContent = result.status === "ok" ? "" : message(result.status);
  } catch (error) {
    networkUnknown = !(error instanceof RequestError) ||
      ["in_flight", "request_conflict", "session_denied"].includes(error.status);
    notice.textContent = networkUnknown
      ? "Проверьте состояние сеанса перед следующим вопросом."
      : errorText(error);
  } finally {
    busy = false;
    updateButtons();
    question.focus();
  }
});

byId("refresh").addEventListener("click", refresh);
window.addEventListener("hashchange", () => {
  const supplied = ownerCapabilityFromFragment();
  if (supplied) {
    ownerCapability = supplied;
    refresh();
  }
});

byId("reset").addEventListener("click", async () => {
  if (!csrf || busy || state?.pending) return;
  busy = true;
  updateButtons();
  try {
    showSession(await read("/reset", {}));
    selected.clear();
    question.value = "";
    chooseModel();
    scope.value = "full";
    networkUnknown = false;
  } catch (error) {
    notice.textContent = errorText(error);
    networkUnknown = true;
  } finally {
    busy = false;
    updateButtons();
    question.focus();
  }
});

byId("expert").addEventListener("click", () => {
  expertMode = !expertMode;
  byId("expert").setAttribute("aria-pressed", String(expertMode));
  byId("export-panel").hidden = !expertMode;
  for (const item of timeline.querySelectorAll(".expert-data, .expert-only")) item.hidden = !expertMode;
});

async function sendExport(selection) {
  const chosen = byId("export-selected");
  const all = byId("export-all");
  chosen.disabled = all.disabled = true;
  try {
    const result = await read("/export", selection ? {requests: [...selected]} : {});
    byId("export-notice").textContent = "Сохранено в папке экспорта · " + result.file;
  } catch (error) {
    byId("export-notice").textContent = errorText(error);
  } finally {
    all.disabled = false;
    updateButtons();
  }
}

byId("export-selected").addEventListener("click", () => sendExport(true));
byId("export-all").addEventListener("click", () => sendExport(false));
refresh();
