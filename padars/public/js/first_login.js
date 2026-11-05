(() => {
  if (window.location.pathname !== "/login") return;
  const addLink = () => {
    const actions = document.querySelector(".page-card-actions");
    if (!actions || document.getElementById("padars-first-login")) return;
    const link = document.createElement("a");
    link.id = "padars-first-login";
    link.href = "/student-activation";
    link.textContent = typeof __ === "function" ? __("Student first login") : "Student first login";
    actions.appendChild(link);
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", addLink);
  else addLink();
})();
