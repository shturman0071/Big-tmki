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
const calendarMonthNames = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];
const contractFilterName = { attention: "Договоры требуют внимания", active: "Активные договоры", approval: "Договоры на согласовании", expiring: "Договоры: остался 1 месяц до окончания" };
let calendarDate = new Date(2026, 4, 1);

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

function renderCalendar() {
  const year = calendarDate.getFullYear();
  const month = calendarDate.getMonth();
  const first = new Date(year, month, 1);
  const startOffset = (first.getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < startOffset; i += 1) cells.push(`<span class="muted"></span>`);
  for (let day = 1; day <= daysInMonth; day += 1) {
    const hasEvent = [5, 12, 18, 22, 26].includes(day);
    cells.push(`<button class="${hasEvent ? "has-event" : ""}" type="button">${day}</button>`);
  }
  byId("calendarTitle").textContent = `${calendarMonthNames[month]} ${year}`;
  byId("calendarGrid").innerHTML = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"].map((d) => `<b>${d}</b>`).join("") + cells.join("");
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
  byId("aiBrief").textContent = briefs[scope] || briefs.all;

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
  byId("todoGrid").innerHTML = rows.map((group) => `
    <button class="todo-card" type="button" data-todo-id="${group.id}">
      <b>${group.title}</b><span>${group.items.length} задачи · ${latestTodoFile(group.id).file}</span>
      <ul>${group.items.slice(0, 3).map((item) => `<li>${item.title}</li>`).join("")}</ul>
    </button>`).join("") + `<button class="todo-card add-todo" id="addTodoBtn" type="button"><strong>+</strong><span>Добавить дела</span></button>`;
  renderKanbanFilter();
}

function latestTodoFile(id) {
  if (!todoFiles[id]) todoFiles[id] = [{ date: today(), file: `${id}-${today()}.docx`, text: "Автоматически созданный файл To-Do" }];
  return todoFiles[id][0];
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
  byId("pageFilters").innerHTML = Object.entries(contractFilterName).map(([key, label]) => `<button class="filter-chip ${key === filter ? "active" : ""}" type="button" data-contract-page-filter="${key}">${label}</button>`).join("");
  byId("pageTableWrap").innerHTML = table(["Договор", "Контрагент", "Объект", "Статус", "Окончание", "Сумма", "Факт", "Ожидание", "Риск"], rows.map((row) => [row.name, row.counterparty, row.object, row.status, formatDate(row.end), `${row.amount} млн`, `${row.actual} млн`, `${row.expected} млн`, badge(row.risk)]));
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
  byId("pageFilters").innerHTML = `<label class="archive-search">Поиск по дате или слову <input id="todoArchiveSearch" placeholder="например: 2026-05-22 или договор"></label>`;
  byId("pageTableWrap").innerHTML = `<div class="latest-file"><h2>Последний сохраненный файл</h2><strong>${latest.file}</strong><p>Дата: ${latest.date}</p><p>${latest.text}</p></div>`;
  byId("pageExtra").innerHTML = `<section class="litigation"><h2>Предыдущие файлы</h2><div id="todoArchiveResults">${todoArchiveTable(files)}</div></section>`;
}

function todoArchiveTable(files) {
  return table(["Дата", "Файл", "Содержание"], files.map((row) => [row.date, row.file, row.text]));
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

function openAiDialog(question = "") {
  byId("agentChat").innerHTML = `<div class="agent-message agent"><b>ИИ-агент</b><p>${briefs[currentScope()] || briefs.all}</p></div>`;
  byId("aiDialog").showModal();
  if (question) {
    addAgentMessage("user", question);
    answerAgent("custom", question);
  }
}

function addAgentMessage(role, text) {
  byId("agentChat").insertAdjacentHTML("beforeend", `<div class="agent-message ${role}"><b>${role === "user" ? "Вы" : "ИИ-агент"}</b><p>${text}</p></div>`);
}

async function answerAgent(type, question = "") {
  const c = scoped(contracts);
  const debt = total(scoped(debtors), "overdue");
  const answers = {
    summary: `Сводка: договоры ${total(c, "amount")} млн ₽, дебиторка ${debt} млн ₽, рисков ${scoped(risks).length}, просрочек ${scoped(overdueItems).length}.`,
    risks: "Главные риски: договоры на согласовании, отправка оборудования, документы поставщиков и платежные задержки.",
    money: `Финансы: факт ${total(c, "actual")} млн ₽, ожидание ${total(c, "expected")} млн ₽, расходы отображены третьим столбцом.`,
    news: "Новости: мониторинг РФ/РК/ЕС по трудовому праву, санкциям, налогам, финансам и шахтостроению."
  };
  if (question && dashboardMeta?.agent) {
    try {
      const corpus = dashboardMeta.agent.corpus_default || "test_docs";
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, llm: "stub", corpus }),
      });
      const data = await res.json();
      if (res.ok && data.answer) {
        addAgentMessage("agent", String(data.answer).slice(0, 600));
        return;
      }
    } catch {
      /* fallback ниже */
    }
  }
  addAgentMessage("agent", question ? `По вопросу «${question}»: сначала проверьте дебиторку, расходы, просрочки и новости по санкционному/налоговому контуру.` : answers[type]);
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
  byId("prevMonth").addEventListener("click", () => { calendarDate.setMonth(calendarDate.getMonth() - 1); renderCalendar(); });
  byId("nextMonth").addEventListener("click", () => { calendarDate.setMonth(calendarDate.getMonth() + 1); renderCalendar(); });
  byId("prevYear").addEventListener("click", () => { calendarDate.setFullYear(calendarDate.getFullYear() - 1); renderCalendar(); });
  byId("nextYear").addEventListener("click", () => { calendarDate.setFullYear(calendarDate.getFullYear() + 1); renderCalendar(); });
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
  byId("quickAiSend").addEventListener("click", () => openAiDialog(byId("quickAiQuery").value.trim()));
  byId("navAssistant").addEventListener("click", (event) => { event.preventDefault(); openAiDialog(); });
  document.querySelectorAll("[data-agent-prompt]").forEach((button) => button.addEventListener("click", () => answerAgent(button.dataset.agentPrompt)));
  byId("sendAgentQuestion").addEventListener("click", () => {
    const question = byId("agentQuestion").value.trim();
    if (!question) return;
    addAgentMessage("user", question);
    byId("agentQuestion").value = "";
    answerAgent("custom", question);
  });
  byId("todoGrid").addEventListener("click", (event) => {
    const add = event.target.closest("#addTodoBtn");
    if (add) { byId("todoDialog").showModal(); return; }
    const card = event.target.closest("[data-todo-id]");
    if (!card) return;
    showListPage("todoArchive", { todoId: card.dataset.todoId });
  });
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

renderCalendar();
bindEvents();
loadDashboardData()
  .then(() => {
    initSelectors();
    renderDashboard();
  })
  .catch((err) => {
    byId("aiBrief").textContent = "Ошибка загрузки: " + err.message;
  });
