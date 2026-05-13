const DailyTodo = (() => {
  function clampProgress(progress) {
    const n = Number.parseInt(String(progress ?? "0"), 10);
    if (!Number.isFinite(n)) return 0;
    return Math.max(0, Math.min(100, n));
  }

  function applyProgressBars() {
    document.querySelectorAll(".progress-fill[data-progress]").forEach((el) => {
      const value = clampProgress(el.dataset.progress);
      el.style.width = `${value}%`;
    });
  }

  function closestTaskView(el) {
    if (!el) return null;
    const row = el.closest("tr");
    if (row) return row.querySelector("[data-task-view]");
    return null;
  }

  function startEdit(taskView) {
    if (!taskView) return;
    taskView.classList.add("editing");
    const titleInput = taskView.querySelector('input[name="title"]');
    if (titleInput) titleInput.focus();
  }

  function cancelEdit(taskView) {
    if (!taskView) return;
    taskView.classList.remove("editing");
  }

  function init() {
    applyProgressBars();

    document.addEventListener("submit", async (e) => {
      const form = e.target?.closest?.("form");
      if (!form) return;

      const action = form.getAttribute("action") || "";
      const isAjax =
        action === "/add" ||
        action.startsWith("/update/") ||
        action.startsWith("/done/") ||
        action.startsWith("/delete/") ||
        action.startsWith("/edit/");

      if (!isAjax) return;

      e.preventDefault();

      const row = form.closest("tr");

      try {
        const res = await fetch(form.action, {
          method: "POST",
          headers: { Accept: "application/json" },
          body: new FormData(form),
        });

        if (!res.ok) {
          form.submit();
          return;
        }

        const data = await res.json();

        // If the server included updated stats, apply them to the stat cards
        if (data && data.stats) {
          try {
            const s = data.stats;
            const totalEl = document.getElementById('stat-total');
            const doneEl = document.getElementById('stat-done');
            const avgEl = document.getElementById('stat-avg');
            if (totalEl) totalEl.textContent = String(s.total_count || 0);
            if (doneEl) doneEl.textContent = String(s.done_count || 0);
            if (avgEl) avgEl.textContent = `${Number(s.avg_progress || 0).toFixed(1)}%`;
          } catch (_e) {
            // ignore UI update errors
          }
        }

        // /add
        if (action === "/add") {
          const task = data?.task;
          if (!task) return;

          const tbody = document.querySelector("table tbody");
          if (!tbody) return;

          const noteHtml = (task.note || "").trim()
            ? `<div class="note" data-note-text>${escapeHtml(task.note)}</div>`
            : `<div class="note" data-note-text style="display:none"></div>`;

          const statusHtml =
            Number(task.progress) === 100
              ? `<span data-status-label class="done-label">✅ تمام شده</span>`
              : `<span data-status-label class="doing-label">در حال انجام</span>`;

          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td class="edit-col">
              <button class="icon-btn" type="button" data-start-edit data-task-id="${task.id}" title="ویرایش" aria-label="ویرایش">✎</button>
            </td>
            <td class="title-col">
              <div class="task-view" data-task-view data-task-id="${task.id}">
                <div class="task-view-mode">
                  <div data-title-text>${escapeHtml(task.title)}</div>
                  ${noteHtml}
                </div>
                <div class="task-edit-mode">
                  <form method="post" action="/edit/${task.id}">
                    <input type="hidden" name="date" value="${escapeAttr(data.selected_date || task.jalali_date)}">
                    <input type="text" name="title" value="${escapeAttr(task.title)}" required>
                    <br>
                    <textarea name="note" placeholder="توضیحات">${escapeHtml(task.note || "")}</textarea>
                    <br>
                    <button type="submit">ذخیره</button>
                    <button type="button" data-cancel-edit>انصراف</button>
                  </form>
                </div>
              </div>
            </td>
            <td class="date-col"><span class="ltr">${escapeHtml(task.jalali_date)}</span></td>
            <td>
              <span class="ltr" data-progress-text>${Number(task.progress) || 0}%</span>
              <div class="progress-bar">
                <div class="progress-fill" data-progress="${Number(task.progress) || 0}"></div>
              </div>
            </td>
            <td class="status-col">${statusHtml}</td>
            <td class="actions-col">
              <div class="actions">
                <form class="inline-form" method="post" action="/update/${task.id}">
                  <input type="hidden" name="date" value="${escapeAttr(data.selected_date || task.jalali_date)}">
                  <input type="number" name="progress" min="0" max="100" value="${Number(task.progress) || 0}" style="width: 70px;">
                  <button class="icon-btn" type="submit" title="ثبت درصد" aria-label="ثبت درصد">✓</button>
                </form>
                <form class="inline-form" method="post" action="/done/${task.id}">
                  <input type="hidden" name="date" value="${escapeAttr(data.selected_date || task.jalali_date)}">
                  <button class="done" type="submit">Done</button>
                </form>
                <form class="inline-form" method="post" action="/delete/${task.id}" onsubmit="return confirm('این کار حذف شود؟');">
                  <input type="hidden" name="date" value="${escapeAttr(data.selected_date || task.jalali_date)}">
                  <button class="delete" type="submit">حذف</button>
                </form>
              </div>
            </td>
          `;
          tbody.prepend(tr);
          applyProgressBars();

          const titleInput = form.querySelector('input[name="title"]');
          const noteTextarea = form.querySelector('textarea[name="note"]');
          const progressInput = form.querySelector('input[name="progress"]');
          if (titleInput) titleInput.value = "";
          if (noteTextarea) noteTextarea.value = "";
          if (progressInput) progressInput.value = "0";
          return;
        }

        // Row-based actions
        if (!row) return;

        // /update & /done
        if (action.startsWith("/update/") || action.startsWith("/done/")) {
          const progress = clampProgress(data?.progress);

          const progressInput = row.querySelector('form[action^="/update/"] input[name="progress"]');
          if (progressInput) progressInput.value = String(progress);

          const progressText = row.querySelector("[data-progress-text]");
          if (progressText) progressText.textContent = `${progress}%`;

          const progressFill = row.querySelector(".progress-fill[data-progress]");
          if (progressFill) {
            progressFill.dataset.progress = String(progress);
            progressFill.style.width = `${progress}%`;
          }

          const statusLabel = row.querySelector("[data-status-label]");
          if (statusLabel) {
            if (progress === 100) {
              statusLabel.classList.remove("doing-label");
              statusLabel.classList.add("done-label");
              statusLabel.textContent = "✅ تمام شده";
            } else {
              statusLabel.classList.remove("done-label");
              statusLabel.classList.add("doing-label");
              statusLabel.textContent = "در حال انجام";
            }
          }

          return;
        }

        // /delete
        if (action.startsWith("/delete/")) {
          row.remove();
          return;
        }

        // /edit
        if (action.startsWith("/edit/")) {
          const task = data?.task;
          if (!task) return;

          const taskView = row.querySelector("[data-task-view]");
          if (!taskView) return;

          const titleText = taskView.querySelector("[data-title-text]");
          if (titleText) titleText.textContent = task.title;

          const noteText = taskView.querySelector("[data-note-text]");
          if (noteText) {
            noteText.textContent = task.note || "";
            noteText.style.display = (task.note || "").trim() ? "" : "none";
          }

          cancelEdit(taskView);
        }
      } catch (_err) {
        form.submit();
      }
    });

    document.addEventListener("click", (e) => {
      const startBtn = e.target.closest("[data-start-edit]");
      if (startBtn) {
        const taskView = closestTaskView(startBtn);
        startEdit(taskView);
        return;
      }

      const cancelBtn = e.target.closest("[data-cancel-edit]");
      if (cancelBtn) {
        const taskView = closestTaskView(cancelBtn);
        cancelEdit(taskView);
      }
    });
  }

  return { init };
})();

window.DailyTodo = DailyTodo;

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttr(text) {
  return escapeHtml(text).replaceAll("\n", " ");
}
