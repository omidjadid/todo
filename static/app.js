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
