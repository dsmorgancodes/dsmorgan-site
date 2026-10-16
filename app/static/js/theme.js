(() => {
  const themes = ["light", "dark"];
  const colors = { light: "#fdf6e3", dark: "#2d353b" };
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
    const toggle = document.querySelector(".theme-toggle");
    if (toggle) {
      const label = `Switch to Everforest ${theme === "light" ? "Dark" : "Light"}`;
      toggle.setAttribute("aria-label", label);
      toggle.setAttribute("title", label);
      toggle.setAttribute("aria-pressed", String(theme === "dark"));
    }
  }
  apply(chosen || "light");
  document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector(".theme-toggle");
    toggle.hidden = false;
    apply(document.documentElement.dataset.theme);
    toggle.addEventListener("click", () => {
      chosen = document.documentElement.dataset.theme === "light" ? "dark" : "light";
      apply(chosen);
      try {
        localStorage.setItem("dsmorgan-theme", chosen);
      } catch (error) {
        console.warn("Theme preference could not be saved.", error);
      }
    });
    window.addEventListener("storage", (event) => {
      if (event.key !== "dsmorgan-theme" && event.key !== null) return;
      chosen = themes.includes(event.newValue) ? event.newValue : null;
      apply(chosen || "light");
    });
  });
})();
