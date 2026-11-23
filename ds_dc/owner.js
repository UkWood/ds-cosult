"use strict";
const byId = id => document.getElementById(id);
const timeline = byId("timeline");
const notice = byId("notice");
const field = byId("question");
const form = document.querySelector("form");
const messages = {
  clarification: "Уточните изделие, модификацию или назначение.",
  not_ready: "У выбранной темы пока нет готового досье. Доступна навигация по источникам.",
  domain_denied: "Задайте технический вопрос без внешнего URL или инструкций для системы.",
  session_denied: "Сеанс недоступен или истёк. Обновите страницу.",
  invalid_request: "Введите вопрос длиной от 1 до 1200 символов.",
  cooldown: "Пожалуйста, подождите перед следующим вопросом.",
  series_limit: "Для продолжения обратитесь в поддержку или начните новый диалог.",
  daily_limit: "Достигнут суточный лимит вопросов.",
  budget_exhausted: "Бюджет исчерпан. Вы можете запросить источники.",
  provider_unknown: "Итог операции неизвестен. Серия остановлена до сверки.",
  provider_overage: "Использование превысило подтверждённый предел. Серия остановлена.",
  native_bound_unverified: "Верхняя граница входа не подтверждена. Запрос не отправлен.",
  calibration_observed: "Измерение калибровки сохранено в диагностике.",
  truncated_candidate: "Модель завершила ответ по лимиту. Требуется сверка.",
  invalid_candidate: "Формат ответа модели не прошёл проверку.",
  candidate_too_long: "Черновик превысил предел объёма. Вопрос сохранён для сверки.",
  over_cap: "Запрос превышает предел контекста. Уточните предмет.",
  navigation: "Источники по выбранной теме."
};

function add(parent, tag, text, className) {
  const child = document.createElement(tag);
  if (text) child.textContent = text;
  if (className) child.className = className;
  parent.append(child);
  return child;
}

function links(parent, urls) {
  const allowed = new Set(["www.mnppsaturn.ru", "ukwood.github.io", "mnppsaturn.ru"]);
  if (!urls.length) return;
  const list = add(parent, "ul");
  for (const raw of urls) {
    const url = new URL(raw);
    if (url.protocol !== "https:" || !allowed.has(url.hostname)) continue;
    const anchor = add(add(list, "li"), "a", url.pathname);
    anchor.href = url.href;
    anchor.rel = "noreferrer";
    anchor.target = "_blank";
  }
}

function render(result) {
  const card = add(timeline, "article");
  add(card, "p", result.original_question, "question");
  if (result.label) {
    const draft = add(card, "div", "", "draft");
    add(draft, "strong", result.label);
    add(draft, "div", result.candidate.answer_candidate, "answer");
  }
  if (result.confirmed_answer && result.confirmed_answer.status !== "insufficient") {
    const verified = add(card, "div", "", "verified");
    add(verified, "strong", "Подтверждённая часть");
    add(verified, "div", result.confirmed_answer.text, "answer");
  }
  if (!result.label || result.status !== "draft") {
    add(card, "p", result.message || messages[result.status] || "Ответ требует проверки. " + result.status);
  }
  links(card, result.links || []);
  if (result.decision || result.context) {
    const details = add(card, "details");
    add(details, "summary", "Источники и диагностика");
    if (result.sources) links(details, result.sources.pages.map(row => row.canonical)
      .concat(result.sources.documents.map(row => row.url)).filter(Boolean)
      .filter((url, index, all) => index === all.indexOf(url)));
    add(details, "pre", JSON.stringify(result, null, 2));
  }
}

async function request(route, body) {
  const options = body === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)
  };
  const response = await fetch(route, options);
  return response.json();
}

function busy(value) {
  byId("send").disabled = value;
  byId("reset").disabled = value;
}

async function initialize() {
  busy(true);
  try {
    const state = await request("/session");
    if (state.status !== "ok") {
      notice.textContent = messages[state.status] || "Сеанс недоступен.";
      return;
    }
    byId("profile").textContent = state.provider === "fixture" ? "Проверочный режим" : "Закрытый пилот";
    state.timeline.forEach(render);
    busy(false);
  } catch {
    notice.textContent = "Не удалось открыть сеанс.";
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  const question = field.value;
  if (!question.trim() || [...question].length > 1200) {
    notice.textContent = messages.invalid_request;
    return;
  }
  busy(true);
  notice.textContent = "Подбираю документы…";
  try {
    const result = await request("/ask", {
      request: crypto.randomUUID(), question, mode: byId("p0").checked ? "P0" : "D1"
    });
    if (result.original_question) {
      render(result);
      field.value = "";
      notice.textContent = "";
    } else {
      notice.textContent = messages[result.status] || "Запрос остановлен. " + result.status;
    }
  } catch {
    notice.textContent = "Ответ не получен. Обновите страницу, чтобы проверить журнал сеанса.";
  } finally {
    busy(false);
    field.focus();
  }
});

byId("reset").addEventListener("click", async () => {
  busy(true);
  try {
    const result = await request("/reset", {});
    if (result.status === "ok") {
      timeline.replaceChildren();
      field.value = "";
      notice.textContent = "";
    } else {
      notice.textContent = messages[result.status];
    }
  } catch {
    notice.textContent = "Не удалось начать новый диалог.";
  } finally {
    busy(false);
    field.focus();
  }
});

initialize();
