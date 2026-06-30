// This is used to hide the unused divisions on the division page. It also relies on the consts in divsion.js .

(() => {
  const DIVISIONS_SEASON_ID = "summer_2026";

  const DIVISIONS_DATA_PATHS = {
    divisionSummary: `data/live_season/${DIVISIONS_SEASON_ID}/regular_season/division_summary.json`
  };

  function cleanDivisionText(value) {
    return String(value || "").trim();
  }

  function normalizeDivisionKey(value) {
    return cleanDivisionText(value)
      .toLowerCase()
      .replace(/&/g, "and")
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "");
  }

  async function fetchJsonOrFallback(url, fallback) {
    try {
      const response = await fetch(url);

      if (!response.ok) {
        return fallback;
      }

      return await response.json();
    } catch (error) {
      console.warn(`Could not load ${url}`, error);
      return fallback;
    }
  }

  function getActiveDivisionKeys(summary) {
    const divisions = Array.isArray(summary?.divisions)
      ? summary.divisions
      : [];

    return new Set(
      divisions
        .filter(division => Number(division.team_count || 0) > 0)
        .map(division => normalizeDivisionKey(division.division))
    );
  }

  function hideInactiveDivisionElements(activeDivisionKeys) {
    document.querySelectorAll("[data-division]").forEach(element => {
      const divisionKey = normalizeDivisionKey(element.dataset.division);

      if (!divisionKey) return;

      element.hidden = !activeDivisionKeys.has(divisionKey);
    });
  }

  async function loadDivisionVisibility() {
    const summary = await fetchJsonOrFallback(
      DIVISIONS_DATA_PATHS.divisionSummary,
      { divisions: [] }
    );

    const activeDivisionKeys = getActiveDivisionKeys(summary);

    hideInactiveDivisionElements(activeDivisionKeys);
  }

  loadDivisionVisibility();
})();