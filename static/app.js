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
      const form = e.target?.closest?.('form[action^="/update/"]');
      if (!form) return;

      e.preventDefault();

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
        const progress = clampProgress(data?.progress);

        const row = form.closest("tr");
        if (!row) return;

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
