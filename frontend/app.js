let API_BASE = "http://localhost:5000";
let token = localStorage.getItem("todo_token") || "";
let username = localStorage.getItem("todo_user") || "";
let page = 1;
let pagination = { pages: 1, has_next: false, has_prev: false };
let expandedTaskId = null;
const taskDetailCache = {};

const authSection = document.getElementById("authSection");
const appSection = document.getElementById("appSection");
const messagePanel = document.getElementById("messagePanel");
const apiChip = document.getElementById("apiChip");
const userChip = document.getElementById("userChip");
const logoutBtn = document.getElementById("logoutBtn");
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const showRegisterBtn = document.getElementById("showRegisterBtn");
const showLoginBtn = document.getElementById("showLoginBtn");
const tasksContainer = document.getElementById("tasksContainer");
const pageInfo = document.getElementById("pageInfo");
const prevPageBtn = document.getElementById("prevPageBtn");
const nextPageBtn = document.getElementById("nextPageBtn");

function showMessage(text, type = "ok") {
  messagePanel.textContent = text;
  messagePanel.className = `alert ${type}`;
  setTimeout(() => {
    messagePanel.className = "alert";
  }, 2600);
}

function normalizeBase(url) {
  return (url || "").trim().replace(/\/+$/, "");
}

function updateApiChip() {
  apiChip.innerHTML = `<span class="dot"></span>API: ${API_BASE}`;
}

async function resolveApiBase() {
  const queryApi = new URLSearchParams(window.location.search).get("api");
  const storedApi = localStorage.getItem("todo_api_base");
  const candidates = [...new Set([
    normalizeBase(queryApi),
    normalizeBase(storedApi),
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://192.168.59.100:30080"
  ].filter(Boolean))];

  for (const candidate of candidates) {
    try {
      const response = await fetch(`${candidate}/health`);
      if (response.ok) {
        API_BASE = candidate;
        localStorage.setItem("todo_api_base", API_BASE);
        updateApiChip();
        return;
      }
    } catch (_) {
      // Try next.
    }
  }

  API_BASE = candidates[0] || "http://localhost:5000";
  updateApiChip();
}

function escapeHtml(value) {
  return (value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function authHeaders(extra = {}) {
  const headers = { ...extra };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function api(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const headers = authHeaders(options.headers || {});
  if (!isFormData && options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const contentType = response.headers.get("Content-Type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) throw new Error(payload.error || payload.message || "Request failed");
  return payload;
}

function setSession(newToken, user) {
  token = newToken;
  username = user;
  localStorage.setItem("todo_token", token);
  localStorage.setItem("todo_user", username);
  applyAuthUI();
}

function clearSession() {
  token = "";
  username = "";
  localStorage.removeItem("todo_token");
  localStorage.removeItem("todo_user");
  expandedTaskId = null;
  Object.keys(taskDetailCache).forEach((k) => delete taskDetailCache[k]);
  applyAuthUI();
}

function resetUiState() {
  page = 1;
  pagination = { pages: 1, has_next: false, has_prev: false };
  expandedTaskId = null;
  Object.keys(taskDetailCache).forEach((k) => delete taskDetailCache[k]);

  tasksContainer.innerHTML = "";
  pageInfo.textContent = "Page 1";
  messagePanel.className = "alert";
  messagePanel.textContent = "";

  loginForm.reset();
  registerForm.reset();
  document.getElementById("taskForm").reset();

  registerForm.classList.add("hidden");
  loginForm.classList.remove("hidden");
}

function applyAuthUI() {
  if (token) {
    authSection.classList.add("hidden");
    appSection.classList.remove("hidden");
    logoutBtn.classList.remove("hidden");
    userChip.innerHTML = `<span class="dot"></span>Signed in: ${username}`;
  } else {
    authSection.classList.remove("hidden");
    appSection.classList.add("hidden");
    logoutBtn.classList.add("hidden");
    userChip.innerHTML = `<span class="dot"></span>Not signed in`;
    registerForm.classList.add("hidden");
    loginForm.classList.remove("hidden");
  }
}

function getFilters() {
  return {
    search: document.getElementById("searchInput").value.trim(),
    status: document.getElementById("filterStatus").value,
    priority: document.getElementById("filterPriority").value,
    sort_by: document.getElementById("sortBy").value,
    sort_order: document.getElementById("sortOrder").value,
    per_page: document.getElementById("perPage").value
  };
}

async function loadTasks() {
  const f = getFilters();
  const params = new URLSearchParams({
    page: String(page),
    per_page: f.per_page,
    sort_by: f.sort_by,
    sort_order: f.sort_order
  });
  if (f.search) params.set("search", f.search);
  if (f.status) params.set("status", f.status);
  if (f.priority) params.set("priority", f.priority);

  const data = await api(`/tasks?${params.toString()}`);
  pagination = data.pagination;
  renderTasks(data.items || []);
  updatePagination();
}

function updatePagination() {
  pageInfo.textContent = `Page ${pagination.page || page} of ${Math.max(1, pagination.pages || 1)}`;
  prevPageBtn.disabled = !pagination.has_prev;
  nextPageBtn.disabled = !pagination.has_next;
}

function renderTasks(tasks) {
  if (!tasks.length) {
    tasksContainer.innerHTML = "<p class='muted'>No tasks found for this filter set.</p>";
    return;
  }

  tasksContainer.innerHTML = tasks.map((task, index) => {
    const isOpen = expandedTaskId === task.id;
    const detail = taskDetailCache[task.id];
    const comments = detail?.comments || [];
    const attachments = detail?.attachments || [];

    return `
      <article class="task-card" data-task-id="${task.id}" style="--i:${index}">
        <h3>${escapeHtml(task.title)}</h3>
        <p class="muted">${escapeHtml(task.description || "No description")}</p>
        <div class="task-meta">
          <span class="pill status-${escapeHtml(task.status)}">Status: ${escapeHtml(task.status)}</span>
          <span class="pill priority-${escapeHtml(task.priority)}">Priority: ${escapeHtml(task.priority)}</span>
          <span class="pill">Due: ${task.due_date ? escapeHtml(task.due_date) : "none"}</span>
          <span class="pill">Comments: ${task.comments_count}</span>
          <span class="pill">Files: ${task.attachments_count}</span>
        </div>
        <div class="row two">
          <select data-field="status">${["todo", "in-progress", "done"].map((v) =>
            `<option value="${v}" ${task.status === v ? "selected" : ""}>${v}</option>`).join("")}</select>
          <select data-field="priority">${["low", "medium", "high"].map((v) =>
            `<option value="${v}" ${task.priority === v ? "selected" : ""}>${v}</option>`).join("")}</select>
        </div>
        <div class="tiny-actions">
          <button data-action="save-meta" class="btn-secondary" type="button">Save</button>
          <button data-action="toggle-detail" class="btn-muted" type="button">${isOpen ? "Hide Details" : "Show Details"}</button>
          <button data-action="delete-task" class="btn-danger" type="button">Delete</button>
        </div>
        ${isOpen ? `
          <div class="detail">
            <h3>Comments</h3>
            ${(comments.length ? comments.map((c) => `<p class="muted">- ${escapeHtml(c.content)}</p>`).join("")
              : "<p class='muted'>No comments yet.</p>")}
            <div class="inline">
              <input data-role="comment-input" type="text" placeholder="Add comment" />
              <button data-action="add-comment" class="btn-primary" type="button">Post</button>
            </div>
            <h3>Attachments</h3>
            ${(attachments.length ? attachments.map((a) => `
              <div class="attachment-row">
                <span class="muted">${escapeHtml(a.original_name)} (${Math.ceil(a.size / 1024)} KB)</span>
                <div class="tiny-actions">
                  <button data-action="download-attachment" data-attachment-id="${a.id}" class="btn-muted" type="button">Download</button>
                  <button data-action="delete-attachment" data-attachment-id="${a.id}" class="btn-danger" type="button">Delete</button>
                </div>
              </div>
            `).join("") : "<p class='muted'>No files uploaded.</p>")}
            <div class="inline upload-zone">
              <input data-role="file-input" type="file" />
              <button data-action="upload-attachment" class="btn-primary" type="button">Upload</button>
            </div>
          </div>
        ` : ""}
      </article>
    `;
  }).join("");
}

async function loadTaskDetails(taskId) {
  const detail = await api(`/tasks/${taskId}`);
  taskDetailCache[taskId] = detail;
  await loadTasks();
}

async function handleLogin(event) {
  event.preventDefault();
  try {
    const loginData = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username: document.getElementById("loginUsername").value.trim(),
        password: document.getElementById("loginPassword").value
      })
    });
    setSession(loginData.access_token, loginData.user.username);
    showMessage("Logged in");
    page = 1;
    await loadTasks();
  } catch (error) {
    showMessage(error.message, "err");
  }
}

async function handleRegister(event) {
  event.preventDefault();
  try {
    await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        username: document.getElementById("registerUsername").value.trim(),
        password: document.getElementById("registerPassword").value
      })
    });
    showMessage("Registration successful. You can now log in.");
  } catch (error) {
    showMessage(error.message, "err");
  }
}

async function handleCreateTask(event) {
  event.preventDefault();
  try {
    await api("/tasks", {
      method: "POST",
      body: JSON.stringify({
        title: document.getElementById("titleInput").value.trim(),
        description: document.getElementById("descriptionInput").value.trim(),
        status: document.getElementById("statusInput").value,
        priority: document.getElementById("priorityInput").value,
        due_date: document.getElementById("dueInput").value || null
      })
    });
    event.target.reset();
    showMessage("Task created");
    page = 1;
    await loadTasks();
  } catch (error) {
    showMessage(error.message, "err");
  }
}

async function downloadAttachment(attachmentId) {
  const response = await fetch(`${API_BASE}/attachments/${attachmentId}/download`, {
    headers: authHeaders()
  });
  if (!response.ok) throw new Error("Unable to download attachment");
  const blob = await response.blob();
  const contentDisposition = response.headers.get("Content-Disposition") || "";
  const fallbackName = `attachment-${attachmentId}`;
  const fileNameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
  const fileName = fileNameMatch ? fileNameMatch[1] : fallbackName;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

loginForm.addEventListener("submit", handleLogin);
registerForm.addEventListener("submit", handleRegister);
document.getElementById("taskForm").addEventListener("submit", handleCreateTask);
document.getElementById("applyFiltersBtn").addEventListener("click", async () => {
  page = 1;
  await loadTasks();
});

prevPageBtn.addEventListener("click", async () => {
  if (pagination.has_prev) {
    page -= 1;
    await loadTasks();
  }
});
nextPageBtn.addEventListener("click", async () => {
  if (pagination.has_next) {
    page += 1;
    await loadTasks();
  }
});
logoutBtn.addEventListener("click", () => {
  clearSession();
  resetUiState();
  window.location.reload();
});

showRegisterBtn.addEventListener("click", () => {
  loginForm.classList.add("hidden");
  registerForm.classList.remove("hidden");
});

showLoginBtn.addEventListener("click", () => {
  registerForm.classList.add("hidden");
  loginForm.classList.remove("hidden");
});

tasksContainer.addEventListener("click", async (event) => {
  const action = event.target.dataset.action;
  if (!action) return;
  const card = event.target.closest(".task-card");
  if (!card) return;
  const taskId = Number(card.dataset.taskId);

  try {
    if (action === "delete-task") {
      await api(`/tasks/${taskId}`, { method: "DELETE" });
      delete taskDetailCache[taskId];
      if (expandedTaskId === taskId) expandedTaskId = null;
      showMessage("Task deleted");
      await loadTasks();
    }
    if (action === "save-meta") {
      const status = card.querySelector('[data-field="status"]').value;
      const priority = card.querySelector('[data-field="priority"]').value;
      await api(`/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify({ status, priority }) });
      showMessage("Task updated");
      await loadTasks();
    }
    if (action === "toggle-detail") {
      if (expandedTaskId === taskId) {
        expandedTaskId = null;
        await loadTasks();
      } else {
        expandedTaskId = taskId;
        await loadTaskDetails(taskId);
      }
    }
    if (action === "add-comment") {
      const input = card.querySelector('[data-role="comment-input"]');
      const content = input.value.trim();
      if (!content) return;
      await api(`/tasks/${taskId}/comments`, { method: "POST", body: JSON.stringify({ content }) });
      input.value = "";
      showMessage("Comment added");
      await loadTaskDetails(taskId);
    }
    if (action === "upload-attachment") {
      const fileInput = card.querySelector('[data-role="file-input"]');
      if (!fileInput.files.length) {
        showMessage("Choose a file first", "err");
        return;
      }
      const formData = new FormData();
      formData.append("file", fileInput.files[0]);
      await api(`/tasks/${taskId}/attachments`, { method: "POST", body: formData });
      fileInput.value = "";
      showMessage("Attachment uploaded");
      await loadTaskDetails(taskId);
    }
    if (action === "delete-attachment") {
      const attachmentId = Number(event.target.dataset.attachmentId);
      await api(`/attachments/${attachmentId}`, { method: "DELETE" });
      showMessage("Attachment deleted");
      await loadTaskDetails(taskId);
    }
    if (action === "download-attachment") {
      const attachmentId = Number(event.target.dataset.attachmentId);
      await downloadAttachment(attachmentId);
    }
  } catch (error) {
    showMessage(error.message, "err");
  }
});

(async function bootstrap() {
  await resolveApiBase();
  applyAuthUI();
  if (!token) return;
  try {
    await loadTasks();
  } catch (error) {
    clearSession();
    showMessage("Session expired. Please sign in again.", "err");
  }
})();
