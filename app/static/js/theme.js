(() => {
  const themes = ["rose-pine", "moon", "dawn"];
  const colors = { "rose-pine": "#191724", moon: "#232136", dawn: "#faf4ed" };
  const system = window.matchMedia("(prefers-color-scheme: light)");
  let saved = null;
  try {
    saved = localStorage.getItem("dsmorgan-theme");
  } catch (error) {
    console.warn("Theme preference storage is unavailable.", error);
  }
  let chosen = themes.includes(saved) ? saved : null;
  function apply(theme) {
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]').content = colors[theme];
    document.querySelectorAll('input[name="theme"]').forEach((input) => {
      input.checked = input.value === theme;
    });
  }
  apply(chosen || (system.matches ? "dawn" : "rose-pine"));
  system.addEventListener("change", () => {
    if (!chosen) apply(system.matches ? "dawn" : "rose-pine");
  });
  document.addEventListener("DOMContentLoaded", () => {
    const picker = document.querySelector(".theme-picker");
    picker.hidden = false;
    apply(document.documentElement.dataset.theme);
    picker.addEventListener("change", (event) => {
      if (!themes.includes(event.target.value)) return;
      chosen = event.target.value;
      apply(chosen);
      try {
        localStorage.setItem("dsmorgan-theme", chosen);
      } catch (error) {
        console.warn("Theme preference could not be saved.", error);
      }
    });
    document.addEventListener("click", (event) => {
      if (!picker.contains(event.target)) picker.open = false;
    });
    picker.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        picker.open = false;
        picker.querySelector("summary").focus();
      }
    });
    window.addEventListener("storage", (event) => {
      if (event.key !== "dsmorgan-theme" && event.key !== null) return;
      chosen = themes.includes(event.newValue) ? event.newValue : null;
      apply(chosen || (system.matches ? "dawn" : "rose-pine"));
    });
  });
})();
