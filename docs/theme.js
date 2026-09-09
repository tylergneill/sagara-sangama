/* Theme toggle. The choice persists in localStorage and is applied by an
   inline <head> script before first paint so there is no flash; this file
   only handles the button.

   Three modes, cycled in order: light -> dark -> wave -> light. Light is the
   default a first-time visitor gets, regardless of prefers-color-scheme --
   unlike the Atlases, this page picks its own opening face rather than
   deferring to the system. Wave is dark's cerulean cousin with a drifting
   band of scrollwork behind the page (see the wave-mode section of
   styles.css). */

const SUN_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>`;
const MOON_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z"/></svg>`;
/* Two crests of a swell, echoing the sweep the mode is named for. */
const WAVE_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8c2.5-3 5.5-3 8 0s5.5 3 8 0M2 16c2.5-3 5.5-3 8 0s5.5 3 8 0"/></svg>`;

/* The cycle, and what each step is called. Order is deliberate: light opens,
   the two ordinary modes stay adjacent so light/dark is one press from either,
   and wave sits at the end of the round before returning to the default. */
const THEMES = ["light", "dark", "wave"];

const NEXT_LABEL = {
  light: { icon: MOON_ICON, name: "Dark" },
  dark:  { icon: WAVE_ICON, name: "Wave" },
  wave:  { icon: SUN_ICON,  name: "Light" },
};

function currentTheme() {
  const t = document.documentElement.getAttribute("data-theme");
  // Anything unrecognised (a stale localStorage value, say) falls back to
  // light, which is both the default and what the bare :root now paints.
  return THEMES.includes(t) ? t : "light";
}

function updateThemeToggleLabel() {
  const btn = document.getElementById("themeToggle");
  if (!btn) return;
  // Label the destination, not the current state.
  const next = NEXT_LABEL[currentTheme()];
  btn.innerHTML = `${next.icon}<span class="toggle-label">${next.name}</span>`;
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("themeToggle");
  if (!btn) return;
  updateThemeToggleLabel();
  btn.addEventListener("click", () => {
    const next = THEMES[(THEMES.indexOf(currentTheme()) + 1) % THEMES.length];
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    updateThemeToggleLabel();
  });
});
