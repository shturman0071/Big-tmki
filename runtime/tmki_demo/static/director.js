let objects = [];
let briefs = {};
let contracts = [];
let financeSeries = [];
let expenses = [];
let expenseDetails = [];
let debtors = [];
let litigation = [];
let overdueItems = [];
let risks = [];
let news = [];
let todoGroups = [];
let todoFiles = {};
let dashboardMeta = null;

const agentState = {
  history: [],
  document: null,
  speaking: null,
};

const KANBOARD_BOARD_URL = "/kanboard/?controller=BoardViewController&action=show&project_id=1";
const THEME_STORAGE_KEY = "tmki_director_theme";
const DIRECTOR_THEMES = [
  { id: "tmki", label: "TMKI", hint: "Корпоративная тема по умолчанию" },
  { id: "github-dark", label: "GitHub Dark", hint: "Тёмная тема для разработки" },
  { id: "dracula", label: "Dracula", hint: "Контрастная фиолетовая" },
  { id: "nord", label: "Nord", hint: "Спокойная северная палитра" },
  { id: "iphone17", label: "iPhone 17", hint: "Светлый стиль iOS" },
];

function applyDirectorTheme(themeId) {
  const theme = DIRECTOR_THEMES.some((item) => item.id === themeId) ? themeId : "tmki";
  if (theme === "tmki") {
    delete document.body.dataset.theme;
  } else {
    document.body.dataset.theme = theme;
  }
  localStorage.setItem(THEME_STORAGE_KEY, theme);
  document.querySelectorAll(".theme-option").forEach((button) => {
    button.classList.toggle("active", button.dataset.theme === theme);
    button.setAttribute("aria-selected", button.dataset.theme === theme ? "true" : "false");
  });
  if (byId("sidebarCalendar")) mountSidebarCalendar();
}

function initDirectorThemes() {
  const grid = byId("themeGrid");
  if (!grid) return;
  grid.innerHTML = DIRECTOR_THEMES.map(
    (theme) => `
      <button type="button" class="theme-option" data-theme="${theme.id}" role="option" aria-selected="false">
        <span class="theme-swatch ${theme.id}" aria-hidden="true"></span>
        <strong>${theme.label}</strong>
        <small>${theme.hint}</small>
      </button>`
  ).join("");
  grid.addEventListener("click", (event) => {
    const button = event.target.closest(".theme-option");
    if (!button) return;
    applyDirectorTheme(button.dataset.theme || "tmki");
  });
  const saved = localStorage.getItem(THEME_STORAGE_KEY) || "tmki";
  applyDirectorTheme(saved);
}

function openSettingsDialog() {
  const dialog = byId("settingsDialog");
  if (dialog) dialog.showModal();
}

function agentName() {
  return dashboardMeta?.agent?.name || "Даша";
}

async function loadDashboardData() {
  const res = await fetch("/api/dashboard/director");
  if (!res.ok) throw new Error(`API ${res.status}`);
  const data = await res.json();
  dashboardMeta = data;
  objects = data.objects || [];
  briefs = data.briefs || {};
  contracts = data.contracts || [];
  financeSeries = data.finance_series || [];
  expenses = data.expenses || [];
  expenseDetails = data.expense_details || [];
  debtors = data.debtors || [];
  litigation = data.litigation || [];
  overdueItems = data.overdue_items || [];
  risks = data.risks || [];
  news = data.news || [];
  todoGroups = data.todo_groups || [];
  todoFiles = data.todo_files || {};
  const user = data.user || {};
  const nameEl = document.getElementById("userDisplayName");
  const roleEl = document.getElementById("userDisplayRole");
  if (nameEl) nameEl.textContent = user.display_name || "Руководитель";
  if (roleEl) roleEl.textContent = data.role_label || "Директор";
  const av = document.getElementById("userAvatar");
  if (av) av.textContent = (user.display_name || "Р")[0];
}

const byId = (id) => document.getElementById(id);
const monthNames = ["ЯНВ", "ФЕВ", "МАР", "АПР", "МАЙ", "ИЮН", "ИЮЛ", "АВГ", "СЕН", "ОКТ", "НОЯ", "ДЕК"];
const contractFilterName = { attention: "Договоры требуют внимания", active: "Активные договоры", approval: "Договоры на согласовании", expiring: "Договоры: остался 1 месяц до окончания" };
let sidebarCalendarInstance = null;

function pad2(n) {
  return String(n).padStart(2, "0");
}

function timePartsInZone(date, timeZone) {
  const fmt = new Intl.DateTimeFormat("ru-RU", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  });
  const parts = fmt.formatToParts(date);
  const get = (type) => Number(parts.find((p) => p.type === type)?.value || "0");
  return { h: get("hour"), m: get("minute"), s: get("second") };
}

function mountTimezoneClocks() {
  const root = byId("tzClocks");
  if (!root) return null;

  const zones = [
    { id: "moscow", label: "Москва", tz: "Europe/Moscow" },
    { id: "berlin", label: "Берлин", tz: "Europe/Berlin" },
    { id: "norilsk", label: "Норильск", tz: "Asia/Krasnoyarsk" },
    { id: "perm", label: "Пермь", tz: "Asia/Yekaterinburg" },
    { id: "satimola", label: "Сатимола", tz: "Asia/Almaty" }
  ];

  const ticks = Array.from({ length: 12 }).map((_, i) => {
    const a = (Math.PI * 2 * i) / 12;
    const x1 = 31 + Math.sin(a) * 25;
    const y1 = 31 - Math.cos(a) * 25;
    const x2 = 31 + Math.sin(a) * 28;
    const y2 = 31 - Math.cos(a) * 28;
    return `<line class="tick" x1="${x1.toFixed(2)}" y1="${y1.toFixed(2)}" x2="${x2.toFixed(2)}" y2="${y2.toFixed(2)}"></line>`;
  }).join("");

  root.innerHTML = zones.map((z) => `
    <div class="mini-clock" data-tz="${z.tz}">
      <div class="label">${z.label}</div>
      <svg viewBox="0 0 62 62" role="img" aria-label="${z.label}">
        <circle class="face" cx="31" cy="31" r="29"></circle>
        ${ticks}
        <line class="hand-h" data-hand="h" x1="31" y1="31" x2="31" y2="18"></line>
        <line class="hand-m" data-hand="m" x1="31" y1="31" x2="31" y2="12"></line>
        <line class="hand-s" data-hand="s" x1="31" y1="33" x2="31" y2="10"></line>
        <circle class="pin" cx="31" cy="31" r="2.2"></circle>
      </svg>
    </div>
  `).join("");

  const items = [...root.querySelectorAll(".mini-clock")].map((el) => ({
    tz: el.getAttribute("data-tz"),
    h: el.querySelector('[data-hand="h"]'),
    m: el.querySelector('[data-hand="m"]'),
    s: el.querySelector('[data-hand="s"]')
  }));

  return () => {
    const now = new Date();
    for (const it of items) {
      const { h, m, s } = timePartsInZone(now, it.tz);
      const secA = (Math.PI * 2 * s) / 60;
      const minA = (Math.PI * 2 * (m + s / 60)) / 60;
      const hourA = (Math.PI * 2 * ((h % 12) + m / 60)) / 12;
      if (it.s) it.s.setAttribute("transform", `rotate(${(secA * 180) / Math.PI} 31 31)`);
      if (it.m) it.m.setAttribute("transform", `rotate(${(minA * 180) / Math.PI} 31 31)`);
      if (it.h) it.h.setAttribute("transform", `rotate(${(hourA * 180) / Math.PI} 31 31)`);
    }
  };
}

async function openOutlook() {
  try {
    const res = await fetch("/api/app/outlook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}"
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  } catch (e) {
    alert(`Не удалось открыть Outlook: ${e.message}`);
    return null;
  }
}

function scoped(items, scope = currentScope()) {
  return scope === "all" ? items : items.filter((item) => item.scope === scope);
}

function currentScope() {
  return byId("objectFilter").value || "all";
}

function total(items, field) {
  return items.reduce((sum, item) => sum + item[field], 0);
}

function initSelectors() {
  byId("objectFilter").innerHTML = objects.map((item) => `<option value="${item.id}">${item.name}</option>`).join("");
  byId("todoScope").innerHTML = objects
    .filter((item) => item.id !== "all")
    .map((item) => `<option value="${item.id}">${item.name}</option>`)
    .join("") + `<option value="new">Новый объект</option>`;
}

function renderObjectMenu() {
  byId("objectMenu").innerHTML = objects.map((obj) => `
    <label class="object-choice ${obj.id === currentScope() ? "active" : ""}">
      <input type="checkbox" ${obj.id === currentScope() ? "checked" : ""} data-object-id="${obj.id}">
      <span><b>${obj.name}</b><small>${obj.region}</small></span>
    </label>
  `).join("");
}

function calendarThemeForDirector() {
  return document.body.dataset.theme === "iphone17" ? "light" : "dark";
}

function renderFallbackCalendar(root, cursor) {
  const months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];
  const week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
  const now = new Date();
  const year = cursor.getFullYear();
  const month = cursor.getMonth();
  const first = new Date(year, month, 1);
  const start = (first.getDay() + 6) % 7;
  const days = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < start; i += 1) cells.push(`<span class="cal-empty"></span>`);
  for (let day = 1; day <= days; day += 1) {
    const isToday = day === now.getDate() && month === now.getMonth() && year === now.getFullYear();
    cells.push(`<button type="button" class="cal-day${isToday ? " is-today" : ""}">${day}</button>`);
  }
  root.innerHTML = `
    <div class="fallback-calendar">
      <div class="fallback-cal-head">
        <button type="button" data-cal-nav="-1" aria-label="Предыдущий месяц">‹</button>
        <strong>${months[month]} ${year}</strong>
        <button type="button" data-cal-nav="1" aria-label="Следующий месяц">›</button>
      </div>
      <div class="fallback-cal-grid">
        ${week.map((d) => `<b>${d}</b>`).join("")}
        ${cells.join("")}
      </div>
    </div>`;
  root.querySelectorAll("[data-cal-nav]").forEach((btn) => {
    btn.addEventListener("click", () => {
      cursor.setMonth(cursor.getMonth() + Number(btn.dataset.calNav));
      renderFallbackCalendar(root, cursor);
    });
  });
}

function mountSidebarCalendar() {
  const root = byId("sidebarCalendar");
  if (!root) return null;
  const CalendarCtor = window.VanillaCalendarPro && window.VanillaCalendarPro.Calendar;
  if (sidebarCalendarInstance && typeof sidebarCalendarInstance.destroy === "function") {
    try { sidebarCalendarInstance.destroy(); } catch (_) { /* ignore */ }
    sidebarCalendarInstance = null;
  }
  root.innerHTML = "";
  if (!CalendarCtor) {
    renderFallbackCalendar(root, new Date());
    return null;
  }
  try {
    const calendar = new CalendarCtor(root, {
      locale: "ru",
      firstWeekday: 1,
      dateToday: new Date(),
      selectedTheme: calendarThemeForDirector(),
      displayDatesOutside: true,
    });
    calendar.init();
    sidebarCalendarInstance = calendar;
    const painted = root.matches?.("[data-vc='calendar']")
      || root.querySelector("[data-vc='calendar'], [data-vc-dates], [data-vc-date], .vc");
    if (!painted) {
      renderFallbackCalendar(root, new Date());
      return null;
    }
    return calendar;
  } catch (err) {
    console.warn("vanilla-calendar-pro init failed:", err);
    renderFallbackCalendar(root, new Date());
    return null;
  }
}

function renderDashboard() {
  const scope = currentScope();
  const scopedContracts = scoped(contracts, scope);
  const active = scopedContracts.filter((row) => row.category === "active").length;
  const approval = scopedContracts.filter((row) => row.category === "approval").length;
  const expiring = scopedContracts.filter((row) => row.category === "expiring").length;
  const money = total(scopedContracts, "amount");
  const debt = total(scoped(debtors, scope), "overdue");

  byId("contractsTotal").textContent = scopedContracts.length;
  byId("contractBreakdown").innerHTML = `
    <button type="button" data-contract-filter="active"><b>${active}</b><span>активные</span></button>
    <button type="button" data-contract-filter="approval"><b>${approval}</b><span>на согласовании</span></button>
    <button type="button" data-contract-filter="expiring"><b>${expiring}</b><span>остался 1 месяц</span></button>`;
  byId("kpiOverdue").textContent = scoped(overdueItems, scope).length;
  byId("kpiRisks").textContent = scoped(risks, scope).filter((risk) => risk.level !== "Средний").length;
  byId("kpiMoney").textContent = `${money} млн ₽`;
  byId("debtorsTotal").textContent = `${debt} млн ₽`;
  byId("debtorsPercent").textContent = `${Math.min(Math.round((debt / Math.max(money, 1)) * 100), 99)}%`;
  // aiBrief moved into AI dialog; top-card is now an entrypoint only.

  renderObjectMenu();
  renderFinanceChart();
  renderExpenses();
  renderDebtorsPreview();
  renderNews();
  renderTodo();
  renderKanban();
}

function renderFinanceChart() {
  const max = Math.max(...financeSeries.map((item) => Math.max(item.actual, item.expected, item.expenses)), 1);
  byId("financeChart").innerHTML = financeSeries.map((item) => {
    const [year, month] = item.ym.split("-");
    return `<div class="finance-month">
      <div class="bars-wrap three-bars">
        <span class="bar actual" style="height:${42 + item.actual / max * 170}px" title="Факт ${item.actual} млн ₽"><b>${item.actual}</b></span>
        <span class="bar expected" style="height:${42 + item.expected / max * 170}px" title="Ожидается ${item.expected} млн ₽"><b>${item.expected}</b></span>
        <span class="bar expense" style="height:${42 + item.expenses / max * 170}px" title="Расходы ${item.expenses} млн ₽"><b>${item.expenses}</b></span>
      </div>
      <strong>${monthNames[Number(month) - 1]}</strong>
      <small>${year}</small>
    </div>`;
  }).join("");
}

function renderExpenses() {
  const from = byId("expenseFrom").value;
  const to = byId("expenseTo").value;
  const rows = expenses.filter((item) => item.ym >= from && item.ym <= to);
  const max = Math.max(...rows.map((item) => item.amount), 1);
  byId("expenseChart").innerHTML = rows.map((item) => {
    const [year, month] = item.ym.split("-");
    return `<div class="expense-point">
      <div class="expense-marker" style="height:${50 + item.amount / max * 130}px"><b>${item.amount}</b></div>
      <strong>${monthNames[Number(month) - 1]}</strong>
      <small>${year} · ${item.marker}</small>
    </div>`;
  }).join("") || `<p class="empty-state">Нет расходов за период</p>`;
}

function renderDebtorsPreview() {
  byId("debtorsPreview").innerHTML = scoped(debtors).slice(0, 3).map((row) => `<p><b>${row.overdue} млн</b><span>${row.counterparty}</span></p>`).join("");
}

function renderNews() {
  byId("newsList").innerHTML = news.map((item) => `
    <article class="news-item" data-news-id="${item.id}">
      <label class="news-check"><input type="checkbox" data-news-check="${item.id}"><span>Отметить для отправки</span></label>
      <b>${item.country}</b><span class="news-tag">${item.tag}</span>
      <p><a href="${item.url}" target="_blank" rel="noopener noreferrer">${item.title}</a></p>
      <small>${item.source}</small>
      <div class="news-mail" id="mail-${item.id}">
        <input placeholder="email получателя" data-news-email="${item.id}">
        <a href="${buildSingleNewsMailto(item, "")}" data-news-send="${item.id}">Отправить через Outlook</a>
      </div>
    </article>`).join("");
}

function renderTodo() {
  const rows = currentScope() === "all" ? todoGroups : todoGroups.filter((group) => group.scope === currentScope());
  byId("todoGrid").innerHTML = rows.map((group) => {
    const latest = latestTodoFile(group.id);
    const fileLabel = group.xlsx_name || latest.file || "файл не найден";
    const path = encodeURIComponent(group.xlsx_path || latest.absolute_path || "");
    return `
    <button class="todo-card" type="button" data-todo-id="${group.id}"
      data-open-path="${path}"
      data-open-name="${encodeURIComponent(fileLabel)}"
      data-open-rel="${encodeURIComponent(latest.relative_path || "")}"
      title="Открыть ${fileLabel}">
      <b>${group.title}</b><span>${(group.items || []).length} задачи · ${fileLabel}</span>
      <ul>${(group.items || []).slice(0, 3).map((item) => `<li>${item.title}</li>`).join("")}</ul>
    </button>`;
  }).join("") + `<button class="todo-card add-todo" id="addTodoBtn" type="button"><strong>+</strong><span>Добавить дела</span></button>`;
  renderKanbanFilter();
}

function latestTodoFile(id) {
  const files = [...(todoFiles[id] || [])].filter(Boolean);
  files.sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")));
  const withPath = files.find((f) => f.absolute_path) || files[0];
  if (withPath) return withPath;
  return { date: today(), file: `${id}-${today()}.txt`, text: "Файл To-Do ещё не создан", absolute_path: "" };
}

function renderKanbanFilter() {
  const selected = byId("kanbanTodoFilter").value || "all";
  byId("kanbanTodoFilter").innerHTML = `<option value="all">Все списки</option>` + todoGroups.map((group) => `<option value="${group.id}">${group.title}</option>`).join("");
  byId("kanbanTodoFilter").value = [...byId("kanbanTodoFilter").options].some((opt) => opt.value === selected) ? selected : "all";
}

function renderKanban() {
  const selected = byId("kanbanTodoFilter").value || "all";
  const columns = ["Новая", "В работе", "На согласовании", "Ожидает", "Просрочена", "Выполнена"];
  const groups = todoGroups.filter((group) => (currentScope() === "all" || group.scope === currentScope()) && (selected === "all" || group.id === selected));
  const tasks = groups.flatMap((group) => group.items.map((item) => ({ ...item, group: group.title })));
  // Kanboard embed replaces the built-in kanban; keep fallback if iframe отсутствует.
  const frame = byId("kanboardFrame");
  if (frame) return;
  byId("kanbanBoard").innerHTML = columns.map((column) => {
    const cards = tasks.filter((task) => task.status === column);
    return `<div class="kanban-col"><h3>${column}</h3>${cards.map((card) => `<div class="task ${card.priority}">${card.title}<small>${card.group} · ${card.owner}</small></div>`).join("") || `<p class="kanban-empty">Нет задач</p>`}</div>`;
  }).join("");
}

function showDashboard() {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active-view"));
  byId("dashboardView").classList.add("active-view");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showListPage(type, options = {}) {
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active-view"));
  byId("listView").classList.add("active-view");
  byId("pageExtra").innerHTML = "";
  if (type === "contracts") renderContractsPage(options.filter || "attention");
  if (type === "overdue") renderOverduePage();
  if (type === "risks") renderRisksPage();
  if (type === "debtors") renderDebtorsPage();
  if (type === "expenses") renderExpensesPage();
  if (type === "todoArchive") renderTodoArchivePage(options.todoId);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderContractsPage(filter = "attention") {
  const rows = scoped(contracts).filter((row) => filter === "attention" ? row.risk !== "Низкий" : row.category === filter);
  byId("listEyebrow").textContent = "Договорный контур";
  byId("listTitle").textContent = contractFilterName[filter];
  byId("pageFilters").innerHTML = Object.entries(contractFilterName).map(([key, label]) => `<button class="filter-chip ${key === filter ? "active" : ""}" type="button" data-contract-page-filter="${key}">${label}</button>`).join("")
    + `<span class="page-note">Клик по строке открывает файл договора</span>`;
  byId("pageTableWrap").innerHTML = `<table><thead><tr>${
    ["Договор", "Контрагент", "Объект", "Статус", "Окончание", "Сумма", "Факт", "Ожидание", "Риск"]
      .map((h) => `<th>${h}</th>`).join("")
  }</tr></thead><tbody>${
    rows.map((row) => {
      const path = encodeURIComponent(row.absolute_path || "");
      const name = encodeURIComponent(row.file_name || `${row.name}.txt`);
      const rel = encodeURIComponent(row.relative_path || "");
      return `<tr class="clickable-row" data-open-path="${path}" data-open-name="${name}" data-open-rel="${rel}" title="Открыть документ">
        <td><button type="button" class="linkish">${escapeHtml(row.name)}</button></td>
        <td>${escapeHtml(row.counterparty)}</td>
        <td>${escapeHtml(row.object)}</td>
        <td>${escapeHtml(row.status)}</td>
        <td>${formatDate(row.end)}</td>
        <td>${row.amount} млн</td>
        <td>${row.actual} млн</td>
        <td>${row.expected} млн</td>
        <td>${badge(row.risk)}</td>
      </tr>`;
    }).join("") || `<tr><td colspan="9">Нет данных</td></tr>`
  }</tbody></table>`;
}

function renderOverduePage() {
  const rows = scoped(overdueItems);
  byId("listEyebrow").textContent = "Контроль сроков";
  byId("listTitle").textContent = "Список просрочек";
  byId("pageFilters").innerHTML = `<span class="page-note">Открыто из панели Просрочки</span>`;
  byId("pageTableWrap").innerHTML = table(["Просрочка", "Объект", "Тип", "Дней", "Ответственный"], rows.map((row) => [row.title, row.object, row.type, row.days, row.owner]));
}

function renderRisksPage() {
  const rows = scoped(risks);
  byId("listEyebrow").textContent = "Риск-контур";
  byId("listTitle").textContent = "Список рисков";
  byId("pageFilters").innerHTML = `<span class="page-note">Открыто из панели Риски</span>`;
  byId("pageTableWrap").innerHTML = table(["Риск", "Объект", "Категория", "Уровень", "Ответственный"], rows.map((row) => [row.title, row.object, row.category, badge(row.level), row.owner]));
}

function renderDebtorsPage() {
  const rows = scoped(debtors);
  byId("listEyebrow").textContent = "Дебиторская задолженность";
  byId("listTitle").textContent = `Дебиторка: ${total(rows, "overdue")} млн ₽`;
  byId("pageFilters").innerHTML = `<span class="page-note">Просроченные суммы по контрагентам</span>`;
  byId("pageTableWrap").innerHTML = table(["Контрагент", "Номер договора", "Сумма просрочки", "Дней просрочки"], rows.map((row) => [row.counterparty, row.contract, `${row.overdue} млн ₽`, row.days]));
  byId("pageExtra").innerHTML = `<section class="litigation"><h2>Контрагенты, с которыми судимся</h2>${table(["Контрагент", "Предмет спора", "Сумма"], litigation.map((row) => [row.counterparty, row.reason, `${row.amount} млн ₽`]))}</section>`;
}

function renderExpensesPage() {
  byId("listEyebrow").textContent = "Детализация затрат";
  byId("listTitle").textContent = `Расходы: ${total(expenseDetails, "amount")} млн ₽`;
  byId("pageFilters").innerHTML = `<span class="page-note">Категории затрат, счета, договоры, КС-2 и КС-3</span>`;
  byId("pageTableWrap").innerHTML = table(["Категория", "Счет", "Счет/документ", "Договор", "Сумма", "КС-2", "КС-3", "Статус"], expenseDetails.map((row) => [row.category, row.account, row.invoice, row.contract, `${row.amount} млн ₽`, row.ks2, row.ks3, row.status]));
}

function renderTodoArchivePage(todoId) {
  const group = todoGroups.find((item) => item.id === todoId) || todoGroups[0];
  const files = todoFiles[group.id] || [];
  const latest = latestTodoFile(group.id);
  byId("listEyebrow").textContent = "Архив To-Do";
  byId("listTitle").textContent = group.title;
  byId("pageFilters").innerHTML = `<label class="archive-search">Поиск по дате или слову <input id="todoArchiveSearch" placeholder="например: 2026-05-22 или договор"></label>
    <span class="page-note">Клик по файлу открывает документ</span>`;
  const latestPath = encodeURIComponent(latest.absolute_path || "");
  byId("pageTableWrap").innerHTML = `<div class="latest-file">
    <h2>Последний сохраненный файл</h2>
    <button type="button" class="linkish" data-open-path="${latestPath}" data-open-name="${encodeURIComponent(latest.file || "")}" data-open-rel="${encodeURIComponent(latest.relative_path || "")}">
      <strong>${escapeHtml(latest.file)}</strong>
    </button>
    <p>Дата: ${latest.date}</p>
    <p>${escapeHtml(latest.text || "")}</p>
  </div>`;
  byId("pageExtra").innerHTML = `<section class="litigation"><h2>Предыдущие файлы</h2><div id="todoArchiveResults">${todoArchiveTable(files)}</div></section>`;
}

function todoArchiveTable(files) {
  return `<table><thead><tr><th>Дата</th><th>Файл</th><th>Содержание</th></tr></thead><tbody>${
    (files || []).map((row) => {
      const path = encodeURIComponent(row.absolute_path || "");
      return `<tr class="clickable-row" data-open-path="${path}" data-open-name="${encodeURIComponent(row.file || "")}" data-open-rel="${encodeURIComponent(row.relative_path || "")}">
        <td>${escapeHtml(row.date || "")}</td>
        <td><button type="button" class="linkish">${escapeHtml(row.file || "")}</button></td>
        <td>${escapeHtml(row.text || "")}</td>
      </tr>`;
    }).join("") || `<tr><td colspan="3">Нет файлов</td></tr>`
  }</tbody></table>`;
}

async function openDashboardDoc(path, meta = {}) {
  if (!path && !(meta.group_id)) {
    alert("Файл ещё не создан на синтетическом сервере");
    return;
  }
  try {
    let openedPath = path;
    // Реальный Excel из Ту-ду открываем напрямую; synth — только fallback.
    if (path) {
      const data = await openDocFile(path);
      openedPath = data.path || path;
    } else if (meta.group_id) {
      const data = await openSynthTodo(meta.group_id, meta.file_name || "");
      openedPath = data.path || path;
    }
    const doc = {
      absolute_path: openedPath,
      relative_path: meta.relative_path || "",
      file_name: meta.file_name || (openedPath || "").split(/[/\\]/).pop(),
    };
    setAgentDocument(doc);
  } catch (err) {
    alert(`Не удалось открыть файл: ${err.message}`);
  }
}

function showObjectPage(id) {
  const obj = objects.find((item) => item.id === id) || objects[0];
  if (obj.id === "all") { showDashboard(); return; }
  document.querySelectorAll(".view").forEach((view) => view.classList.remove("active-view"));
  byId("objectView").classList.add("active-view");
  byId("objectPageTitle").textContent = obj.name;
  const c = scoped(contracts, obj.id);
  byId("objectPageContent").innerHTML = `
    <article class="panel"><h2>Профиль объекта</h2><p>${obj.region}</p><p>${obj.type}</p><p>Статус: ${obj.status}</p></article>
    <article class="panel"><h2>Финансы</h2><strong>${total(c, "amount")} млн ₽</strong><p>Факт: ${total(c, "actual")} млн ₽ · Ожидание: ${total(c, "expected")} млн ₽</p></article>
    <article class="panel"><h2>Просрочки</h2><strong>${scoped(overdueItems, obj.id).length}</strong><p>Детализация будет дополняться по мере развития проекта.</p></article>
    <article class="panel"><h2>Риски</h2><strong>${scoped(risks, obj.id).length}</strong><p>Все объекты связаны между собой, риски могут влиять на другие направления.</p></article>`;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function table(headers, rows) {
  return `<table><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("") || `<tr><td colspan="${headers.length}">Нет данных</td></tr>`}</tbody></table>`;
}

function badge(text) {
  const cls = text === "Критичный" ? "red" : text === "Высокий" ? "orange" : "green";
  return `<span class="badge ${cls}">${text}</span>`;
}

function formatDate(value) {
  return new Intl.DateTimeFormat("ru-RU").format(new Date(value));
}

function today() {
  return "2026-05-22";
}

function buildSingleNewsMailto(item, email) {
  const subject = encodeURIComponent(`TMKI: важная новость — ${item.tag}`);
  const body = encodeURIComponent(`${item.country}: ${item.title}\nИсточник: ${item.url}\nКатегория: ${item.tag}`);
  return `mailto:${encodeURIComponent(email)}?subject=${subject}&body=${body}`;
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function stopAgentSpeech() {
  if (agentState.speaking) {
    try {
      agentState.speaking.pause();
    } catch {
      /* ignore */
    }
    agentState.speaking = null;
  }
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

async function fetchAgentTts(text) {
  const res = await fetch("/api/tts/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: String(text || "").slice(0, 800) }),
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data?.audio_base64 ? data : null;
}

async function speakAgent(text, tts) {
  const t = (text || "").trim();
  if (!t) return;
  stopAgentSpeech();
  let payload = tts?.audio_base64 ? tts : await fetchAgentTts(t);
  if (!payload?.audio_base64) return;
  await new Promise((resolve, reject) => {
    const audio = new Audio(`data:${payload.mime || "audio/wav"};base64,${payload.audio_base64}`);
    agentState.speaking = audio;
    audio.onended = () => {
      agentState.speaking = null;
      resolve();
    };
    audio.onerror = () => {
      agentState.speaking = null;
      reject(new Error("audio play failed"));
    };
    audio.play().catch(reject);
  }).catch(() => {});
}

function updateAgentCorpusHint() {
  const el = byId("agentCorpusHint");
  if (!el || !dashboardMeta?.agent) return;
  const a = dashboardMeta.agent;
  el.textContent = `Поиск документов: корпус «${a.corpus_label || a.corpus_default}», папка ${a.archive_path || "—"}.`;
}

async function bootstrapKanboard() {
  const frame = byId("kanboardFrame");
  if (!frame) return;
  try {
    const res = await fetch("/api/kanboard/bootstrap", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || res.statusText);
    frame.src = KANBOARD_BOARD_URL;
  } catch {
    frame.src = "/kanboard/?controller=AuthController&action=login";
  }
}

function reloadKanboardFrame() {
  const frame = byId("kanboardFrame");
  if (!frame) return;
  const base = KANBOARD_BOARD_URL;
  frame.src = `${base}${base.includes("?") ? "&" : "?"}t=${Date.now()}`;
}

let _todoSyncMtime = null;
let _todoSyncBusy = false;

async function syncTodoKanboard({ force = false, reindex = false } = {}) {
  if (_todoSyncBusy) return null;
  _todoSyncBusy = true;
  try {
    if (!force) {
      const st = await fetch("/api/todo/kanboard-status").then((r) => r.json());
      if (st.ok && !st.changed && _todoSyncMtime != null && st.mtime === _todoSyncMtime) {
        return st;
      }
    }
    const res = await fetch("/api/todo/sync-kanboard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reindex }),
    });
    const data = await res.json();
    if (!res.ok || data.ok === false) throw new Error(data.error || res.statusText);
    _todoSyncMtime = data.mtime;
    reloadKanboardFrame();
    return data;
  } catch (err) {
    console.warn("todo→kanboard sync:", err);
    return null;
  } finally {
    _todoSyncBusy = false;
  }
}

function mountTodoKanboardSync() {
  syncTodoKanboard({ force: true });
  setInterval(() => {
    syncTodoKanboard({ force: false });
  }, 15000);
}

function updateAgentDocHint() {
  const hint = byId("agentDocHint");
  if (!hint) return;
  const doc = agentState.document;
  if (!doc) {
    hint.hidden = true;
    hint.textContent = "";
    return;
  }
  hint.hidden = false;
  hint.textContent = `Контекст: «${doc.file_name || doc.relative_path || "документ"}». Следующий вопрос — по этому документу.`;
}

function setAgentDocument(doc) {
  agentState.document = doc
    ? {
        file_name: doc.file_name || "",
        relative_path: doc.relative_path || "",
        absolute_path: doc.absolute_path || doc.path || "",
      }
    : null;
  updateAgentDocHint();
}

function pushAgentHistory(role, text) {
  if (!text) return;
  agentState.history.push({ role, content: text });
  if (agentState.history.length > 12) {
    agentState.history = agentState.history.slice(-12);
  }
}

async function callAgentApi(payload) {
  const res = await fetch("/api/agent/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      llm: agentLlm(),
      corpus: agentCorpus(),
      history: agentState.history,
      document: agentState.document,
      ...payload,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function looksLikeDocSearch(question) {
  const q = (question || "").toLowerCase();
  return /найд|найти|покаж|открой|документ|файл|регламент|приказ|акт\b|кс-?2|кс-?3/.test(q);
}

function agentCorpus() {
  return dashboardMeta?.agent?.corpus_default || "skru-2";
}

function agentLlm() {
  return "ollama";
}

function phaseLabel(phase) {
  const map = {
    reindexing: "Индексация архива",
    post_finalize: "Индексация завершена",
    ready_for_finalize: "Готово к финализации",
    reindex_complete_lock: "Re-index завершён",
    demo: "Демо",
  };
  return map[phase] || phase || "—";
}

function shortPathTail(path, maxLen = 72) {
  const text = String(path || "").replace(/\\/g, "/");
  if (!text) return "";
  if (text.length <= maxLen) return text;
  return "…" + text.slice(-(maxLen - 1));
}

async function refreshIndexProgress() {
  return;
}

function mountIndexProgressPoll() {
  return;
}

async function openDocFile(absolutePath) {
  if (!absolutePath) throw new Error("путь к файлу пуст");
  const res = await fetch("/api/doc/open", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ absolute_path: absolutePath }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  if (data.status && data.status !== "opened") {
    throw new Error(data.error || data.status || "файл не открыт");
  }
  return data;
}

async function openSynthTodo(groupId, fileName) {
  const res = await fetch("/api/synth/open", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ group_id: groupId, file: fileName || "" }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  if (data.status !== "opened") throw new Error(data.error || data.status || "не открыто");
  return data;
}

function showDocSearchDialog(items, query) {
  const dlg = byId("docSearchDialog");
  const list = byId("docSearchList");
  const hint = byId("docSearchHint");
  if (!dlg || !list) return;
  byId("docSearchTitle").textContent = items.length ? `Найдено: ${items.length}` : "Файлы не найдены";
  hint.textContent = query
    ? `Запрос: «${query}». Клик по строке откроет файл в приложении по умолчанию.`
    : "Уточните имя файла или слова из документа.";
  if (!items.length) {
    list.innerHTML = `<p class="muted">Ничего не найдено. Попробуйте другое имя или ключевые слова.</p>`;
  } else {
    list.innerHTML = items.map((item, idx) => `
      <button type="button" class="doc-search-item"
        data-doc-path="${encodeURIComponent(item.absolute_path || "")}"
        data-doc-rel="${encodeURIComponent(item.relative_path || "")}"
        data-doc-name="${encodeURIComponent(item.file_name || "")}"
        data-doc-idx="${idx}">
        <b>${escapeHtml(item.file_name || "Документ")}</b>
        <small>${escapeHtml(item.relative_path || "")}</small>
        ${item.snippet ? `<span>${escapeHtml(item.snippet)}</span>` : ""}
      </button>
    `).join("");
  }
  dlg.showModal();
}

async function searchAndShowDocuments(question) {
  const corpus = agentCorpus();
  const url = `/api/doc/resolve?q=${encodeURIComponent(question)}&corpus=${encodeURIComponent(corpus)}`;
  const res = await fetch(url);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  const items = (data.matches || []).map((item) => ({
    file_name: item.file_name,
    relative_path: item.relative_path,
    absolute_path: item.absolute_path,
    snippet: item.snippet || "",
    score: item.score || 0,
  }));
  showDocSearchDialog(items, question);
  return { query: question, total: items.length, items };
}

function collectFilesFromAsk(data) {
  const map = new Map();
  const add = (item) => {
    const path = item.absolute_path || item.path;
    const rel = item.relative_path || "";
    if (!path && !rel) return;
    const key = rel || path;
    if (!map.has(key)) {
      map.set(key, {
        file_name: item.file_name || rel.split(/[/\\]/).pop(),
        relative_path: rel,
        absolute_path: path,
        snippet: item.snippet || "",
        score: item.score || 0,
      });
    }
  };
  (data.matched_files || []).forEach(add);
  (data.citations || []).forEach(add);
  return [...map.values()];
}

async function transcribeAudio(blob) {
  const res = await fetch("/api/transcribe", {
    method: "POST",
    headers: { "Content-Type": blob.type || "audio/webm" },
    body: blob,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.hint || data.error || res.statusText);
  return (data.text || "").trim();
}

function pickAudioMime() {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/ogg"];
  for (const type of candidates) {
    if (window.MediaRecorder?.isTypeSupported(type)) return type;
  }
  return "";
}

const voiceInput = (() => {
  let recording = false;
  let mediaRecorder = null;
  let chunks = [];
  let stream = null;
  let busy = false;

  async function toggle(button, onText) {
    if (busy) return null;
    if (!navigator.mediaDevices || !window.MediaRecorder) {
      alert("Голосовой ввод недоступен в этом браузере.");
      return null;
    }
    if (recording) {
      if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
      recording = false;
      if (button) button.classList.remove("listening");
      return null;
    }
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
    } catch {
      alert("Разрешите доступ к микрофону.");
      return null;
    }
    return new Promise((resolve, reject) => {
      chunks = [];
      const mime = pickAudioMime();
      mediaRecorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
      mediaRecorder.ondataavailable = (event) => {
        if (event.data?.size) chunks.push(event.data);
      };
      mediaRecorder.onstop = async () => {
        if (stream) {
          stream.getTracks().forEach((track) => track.stop());
          stream = null;
        }
        if (button) button.classList.remove("listening");
        recording = false;
        const blob = new Blob(chunks, { type: mediaRecorder.mimeType || "audio/webm" });
        if (!blob.size) {
          resolve(null);
          return;
        }
        busy = true;
        try {
          const text = await transcribeAudio(blob);
          resolve(text || null);
        } catch (err) {
          reject(err);
        } finally {
          busy = false;
        }
      };
      mediaRecorder.start();
      recording = true;
      if (button) button.classList.add("listening");
      if (onText) onText("Говорите… (нажмите ещё раз — стоп)");
    });
  }

  return { toggle, get busy() { return busy; } };
})();

async function runVoiceInto(targetInput, micButton) {
  if (voiceInput.busy) return;
  try {
    const text = await voiceInput.toggle(micButton, (hint) => {
      if (targetInput?.placeholder) targetInput.dataset.voiceHint = hint;
    });
    if (text && targetInput) {
      targetInput.value = text;
      targetInput.focus();
      await handleAgentQuestion(text);
    }
  } catch (err) {
    alert(`Ошибка распознавания: ${err.message}`);
  }
}

async function handleAgentQuestion(question) {
  const q = (question || "").trim();
  if (!q) return;
  pushAgentHistory("user", q);
  addAgentMessage("user", q);
  if (looksLikeDocSearch(q) && !agentState.document) {
    try {
      const searching = "Ищу документы в архиве…";
      addAgentMessage("agent", searching);
      await speakAgent(searching);
      const data = await searchAndShowDocuments(q);
      const total = data.total || 0;
      const reply = total ? `Найдено файлов: ${total}. Выберите в списке.` : "Документы не найдены. Уточните запрос.";
      addAgentMessage("agent", reply);
      pushAgentHistory("assistant", reply);
      await speakAgent(reply);
      return;
    } catch (err) {
      const errText = `Ошибка поиска: ${err.message}`;
      addAgentMessage("agent", errText);
      await speakAgent(errText);
      return;
    }
  }
  await answerAgent(q);
}

async function resetAgentSession() {
  stopAgentSpeech();
  agentState.history = [];
  agentState.document = null;
  byId("agentChat").innerHTML = "";
  byId("agentQuestion").value = "";
  updateAgentDocHint();
}

async function openAiDialog(question = "") {
  byId("aiDialog").showModal();
  updateAgentCorpusHint();
  if (question) {
    await handleAgentQuestion(question);
  }
}

function addAgentMessage(role, text) {
  const label = role === "user" ? "Вы" : agentName();
  byId("agentChat").insertAdjacentHTML(
    "beforeend",
    `<div class="agent-message ${role}"><b>${escapeHtml(label)}</b><p>${escapeHtml(text)}</p></div>`
  );
  const chat = byId("agentChat");
  if (chat) chat.scrollTop = chat.scrollHeight;
}

async function answerAgent(question = "") {
  try {
    const data = await callAgentApi({ question });
    const answer = String(data.answer || "").slice(0, 1200);
    addAgentMessage("agent", answer);
    pushAgentHistory("assistant", answer);
    await speakAgent(answer, data.tts);
  } catch (err) {
    const fallback = `Не удалось получить ответ: ${err.message}`;
    addAgentMessage("agent", fallback);
    await speakAgent(fallback);
  }
}

function addTodoGroup() {
  const scope = byId("todoScope").value === "new" ? "all" : byId("todoScope").value;
  const id = `${scope}-${Date.now()}`;
  const firstTask = byId("todoFirstTask").value.trim() || "Новая задача";
  todoGroups.push({ id, title: byId("todoName").value.trim() || "Новый To-Do", scope, items: [{ title: firstTask, status: "Новая", priority: "medium", owner: "Евгений" }] });
  todoFiles[id] = [{ date: today(), file: `${id}-${today()}.docx`, text: firstTask }];
  byId("todoDialog").close();
  renderTodo();
  byId("kanbanTodoFilter").value = id;
  renderKanban();
}

function addObject() {
  const id = `object-${Date.now()}`;
  objects.push({ id, name: byId("newObjectName").value.trim() || "Новый объект", region: byId("newObjectRegion").value.trim() || "не указан", type: byId("newObjectType").value.trim() || "не указан", status: "новый" });
  initSelectors();
  byId("objectFilter").value = id;
  byId("objectDialog").close();
  renderDashboard();
  showObjectPage(id);
}

function bindEvents() {
  byId("objectToggle").addEventListener("click", () => byId("objectsPanel").classList.toggle("open"));
  byId("objectMenu").addEventListener("change", (event) => {
    const input = event.target.closest("[data-object-id]");
    if (!input) return;
    byId("objectFilter").value = input.dataset.objectId;
    byId("objectsPanel").classList.remove("open");
    renderDashboard();
    showObjectPage(input.dataset.objectId);
  });
  byId("expenseFrom").addEventListener("change", renderExpenses);
  byId("expenseTo").addEventListener("change", renderExpenses);
  byId("expensesDetailsBtn").addEventListener("click", () => showListPage("expenses"));
  byId("backToDashboard").addEventListener("click", showDashboard);
  byId("backFromObject").addEventListener("click", showDashboard);
  byId("contractsKpi").addEventListener("click", () => showListPage("contracts"));
  byId("overdueKpi").addEventListener("click", () => showListPage("overdue"));
  byId("risksKpi").addEventListener("click", () => showListPage("risks"));
  byId("debtorsKpi").addEventListener("click", () => showListPage("debtors"));
  byId("moneyKpi").addEventListener("click", () => byId("financePanel").scrollIntoView({ behavior: "smooth" }));
  byId("contractBreakdown").addEventListener("click", (event) => {
    const button = event.target.closest("[data-contract-filter]");
    if (!button) return;
    event.stopPropagation();
    showListPage("contracts", { filter: button.dataset.contractFilter });
  });
  byId("pageFilters").addEventListener("click", (event) => {
    const button = event.target.closest("[data-contract-page-filter]");
    if (button) renderContractsPage(button.dataset.contractPageFilter);
  });
  byId("pageFilters").addEventListener("input", (event) => {
    if (event.target.id !== "todoArchiveSearch") return;
    const query = event.target.value.toLowerCase();
    const group = todoGroups.find((item) => item.title === byId("listTitle").textContent) || todoGroups[0];
    const files = (todoFiles[group.id] || []).filter((file) => `${file.date} ${file.file} ${file.text}`.toLowerCase().includes(query));
    byId("todoArchiveResults").innerHTML = todoArchiveTable(files);
  });
  document.querySelectorAll("[data-open-page]").forEach((button) => button.addEventListener("click", (event) => { event.preventDefault(); showListPage(button.dataset.openPage); }));
  document.querySelector('[data-nav="dashboard"]').addEventListener("click", (event) => { event.preventDefault(); showDashboard(); });
  byId("addObjectSideBtn").addEventListener("click", () => byId("objectDialog").showModal());
  byId("saveObject").addEventListener("click", addObject);
  byId("quickAiSend").addEventListener("click", () => {
    const q = byId("quickAiQuery").value.trim();
    if (!q) { openAiDialog(); return; }
    openAiDialog(q);
  });
  const mic = byId("quickAiMic");
  if (mic) {
    mic.addEventListener("click", async () => {
      const input = byId("quickAiQuery");
      if (!byId("aiDialog").open) openAiDialog();
      await runVoiceInto(input, mic);
    });
  }
  const agentMic = byId("agentMic");
  if (agentMic) {
    agentMic.addEventListener("click", async () => {
      await runVoiceInto(byId("agentQuestion"), agentMic);
    });
  }
  const docSearchList = byId("docSearchList");
  if (docSearchList) {
    docSearchList.addEventListener("click", async (event) => {
      const btn = event.target.closest("[data-doc-path]");
      if (!btn) return;
      const path = decodeURIComponent(btn.dataset.docPath || "");
      if (!path) return;
      const doc = {
        absolute_path: path,
        relative_path: decodeURIComponent(btn.dataset.docRel || ""),
        file_name: decodeURIComponent(btn.dataset.docName || ""),
      };
      try {
        await openDocFile(path);
        setAgentDocument(doc);
        if (!byId("aiDialog").open) openAiDialog();
        const opened = `Документ «${doc.file_name || "файл"}» открыт. Следующий вопрос — по этому документу.`;
        addAgentMessage("agent", opened);
        pushAgentHistory("assistant", opened);
        await speakAgent(opened);
      } catch (err) {
        alert(`Не удалось открыть файл: ${err.message}`);
      }
    });
  }
  byId("navAssistant").addEventListener("click", (event) => { event.preventDefault(); openAiDialog(); });
  const mail = byId("navMail");
  if (mail) mail.addEventListener("click", (event) => { event.preventDefault(); openOutlook(); });
  const settings = byId("navSettings");
  if (settings) settings.addEventListener("click", (event) => { event.preventDefault(); openSettingsDialog(); });
  const agentReset = byId("agentReset");
  if (agentReset) {
    agentReset.addEventListener("click", () => resetAgentSession());
  }
  byId("sendAgentQuestion").addEventListener("click", async () => {
    const question = byId("agentQuestion").value.trim();
    if (!question) return;
    byId("agentQuestion").value = "";
    await handleAgentQuestion(question);
  });
  byId("todoGrid").addEventListener("click", async (event) => {
    const add = event.target.closest("#addTodoBtn");
    if (add) { byId("todoDialog").showModal(); return; }
    const card = event.target.closest("[data-todo-id]");
    if (!card) return;
    event.preventDefault();
    const id = card.dataset.todoId;
    const group = todoGroups.find((g) => g.id === id) || {};
    const latest = latestTodoFile(id);
    const path = decodeURIComponent(card.dataset.openPath || "") || group.xlsx_path || latest.absolute_path || "";
    await openDashboardDoc(path, {
      group_id: path ? undefined : id,
      file_name: group.xlsx_name || latest.file || decodeURIComponent(card.dataset.openName || ""),
      relative_path: latest.relative_path || decodeURIComponent(card.dataset.openRel || ""),
    });
  });
  const listView = byId("listView");
  if (listView) {
    listView.addEventListener("click", async (event) => {
      const row = event.target.closest("[data-open-path]");
      if (!row) return;
      event.preventDefault();
      const path = decodeURIComponent(row.dataset.openPath || "");
      const name = decodeURIComponent(row.dataset.openName || "");
      const todoId = row.dataset.todoId || "";
      await openDashboardDoc(path, {
        group_id: todoId || undefined,
        file_name: name,
        relative_path: decodeURIComponent(row.dataset.openRel || ""),
      });
    });
  }
  byId("saveTodo").addEventListener("click", addTodoGroup);
  byId("kanbanTodoFilter").addEventListener("change", renderKanban);
  byId("newsList").addEventListener("change", (event) => {
    const checkbox = event.target.closest("[data-news-check]");
    if (!checkbox) return;
    byId(`mail-${checkbox.dataset.newsCheck}`).classList.toggle("open", checkbox.checked);
  });
  byId("newsList").addEventListener("input", (event) => {
    const input = event.target.closest("[data-news-email]");
    if (!input) return;
    const item = news.find((n) => n.id === input.dataset.newsEmail);
    document.querySelector(`[data-news-send="${input.dataset.newsEmail}"]`).href = buildSingleNewsMailto(item, input.value.trim());
  });
}

function initCalculator() {
  const display = byId("calcDisplay");
  const clear = byId("calcClear");
  const back = byId("calcBack");
  const root = byId("calcWidget");
  if (!display || !clear || !root) return;

  let expr = "";

  const set = (v) => {
    display.value = v || "0";
  };

  const safeEval = (s) => {
    if (!s) return null;
    // allow only a small set of functions/constants for "инженерный" режим
    if (!/^[0-9+\-*/().,\sA-Za-z_]+$/.test(s)) return null;
    try {
      const normalized = s
        .replace(/,/g, ".")
        .replace(/\bpi\b/gi, "Math.PI")
        .replace(/\be\b/g, "Math.E")
        .replace(/\bsin\s*\(/gi, "Math.sin(")
        .replace(/\bcos\s*\(/gi, "Math.cos(")
        .replace(/\btan\s*\(/gi, "Math.tan(")
        .replace(/\bln\s*\(/gi, "Math.log(")
        .replace(/\blog\s*\(/gi, "Math.log10(")
        .replace(/\bsqrt\s*\(/gi, "Math.sqrt(")
        .replace(/\bpow\s*\(/gi, "Math.pow(");

      // disallow any remaining identifiers (besides Math.*)
      const withoutMath = normalized.replace(/Math\.(PI|E|sin|cos|tan|log|log10|sqrt|pow)\b/g, "");
      if (/[A-Za-z_]/.test(withoutMath)) return null;

      // eslint-disable-next-line no-new-func
      const fn = new Function(`return (${normalized})`);
      const out = fn();
      if (typeof out !== "number" || !Number.isFinite(out)) return null;
      return out;
    } catch {
      return null;
    }
  };

  const press = (tok) => {
    if (tok === "=") {
      const out = safeEval(expr);
      if (out === null) {
        set("Ошибка");
        expr = "";
        return;
      }
      expr = String(out);
      set(expr);
      return;
    }
    if (tok === "," || tok === ".") {
      expr += tok;
      set(expr);
      return;
    }
    if (tok === "(" || tok === ")") {
      expr += tok;
      set(expr);
      return;
    }
    if (tok === "pi" || tok === "e") {
      expr += tok;
      set(expr);
      return;
    }
    if (/^(sin|cos|tan|ln|log|sqrt|pow)\($/.test(tok)) {
      expr += tok;
      set(expr);
      return;
    }
    if (tok === ".") {
      expr += ".";
      set(expr);
      return;
    }
    if (/^[0-9]$/.test(tok)) {
      expr += tok;
      set(expr);
      return;
    }
    if (/^[+\-*/]$/.test(tok)) {
      expr = expr.trim();
      if (!expr) return;
      if (/[+\-*/]$/.test(expr)) expr = expr.slice(0, -1);
      expr += ` ${tok} `;
      set(expr);
      return;
    }
  };

  clear.addEventListener("click", () => {
    expr = "";
    set("0");
  });
  if (back) {
    back.addEventListener("click", () => {
      expr = expr.trimEnd();
      expr = expr.slice(0, -1);
      set(expr.trim() || "0");
    });
  }

  root.querySelectorAll("[data-calc]").forEach((btn) => {
    btn.addEventListener("click", () => press(btn.dataset.calc));
  });
}

mountSidebarCalendar();
initDirectorThemes();
bindEvents();
loadDashboardData()
  .then(() => {
    initSelectors();
    renderDashboard();
    mountSidebarCalendar();
    updateAgentCorpusHint();
    bootstrapKanboard();
    mountTodoKanboardSync();
    const tickClocks = mountTimezoneClocks();
    if (tickClocks) {
      tickClocks();
      setInterval(tickClocks, 1000);
    }
    initCalculator();
    mountIndexProgressPoll();
  })
  .catch((err) => {
    const el = byId("quickAiQuery");
    if (el) el.placeholder = "Ошибка загрузки: " + err.message;
  });
