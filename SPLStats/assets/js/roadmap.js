async function fetchRoadmap() {
  const response = await fetch("data/roadmap.json");

  if (!response.ok) {
    throw new Error(`Could not load roadmap.json: ${response.status}`);
  }

  return await response.json();
}

function formatDate(dateText) {
  if (!dateText) return "";

  const date = new Date(`${dateText}T00:00:00`);

  if (Number.isNaN(date.getTime())) {
    return dateText;
  }

  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric"
  });
}

function sortRoadmapItems(items, status) {
  const copied = [...items];

  if (status === "finished") {
    copied.sort((a, b) => {
      const dateA = new Date(`${a.date_completed || "1900-01-01"}T00:00:00`);
      const dateB = new Date(`${b.date_completed || "1900-01-01"}T00:00:00`);

      return dateB - dateA;
    });

    return copied;
  }

  copied.sort((a, b) => {
    const orderA = Number(a.order || 9999);
    const orderB = Number(b.order || 9999);

    if (orderA !== orderB) {
      return orderA - orderB;
    }

    return String(a.title || "").localeCompare(String(b.title || ""));
  });

  return copied;
}

function renderRoadmapCard(item, status) {
  const completedDate = formatDate(item.date_completed);

  return `
    <article class="roadmap-card roadmap-card-${status}">
      <div class="roadmap-card-top">
        ${
          status === "finished"
            ? `<span class="roadmap-date">${completedDate || "Completed"}</span>`
            : `<span class="roadmap-order">#${item.order || "—"}</span>`
        }
      </div>

      <h3>${item.title}</h3>

      ${
        item.description
          ? `<p>${item.description}</p>`
          : ""
      }
    </article>
  `;
}

function renderColumn(containerId, items, status) {
  const container = document.querySelector(containerId);

  if (!container) return;

  const sorted = sortRoadmapItems(items, status);

  if (!sorted.length) {
    container.innerHTML = `
      <div class="roadmap-empty">
        Nothing listed yet.
      </div>
    `;

    return;
  }

  container.innerHTML = sorted
    .map(item => renderRoadmapCard(item, status))
    .join("");
}

async function loadRoadmap() {
  try {
    const roadmap = await fetchRoadmap();

    const finished = roadmap.filter(item => item.status === "finished");
    const working = roadmap.filter(item => item.status === "working");
    const planned = roadmap.filter(item => item.status === "planned");

    renderColumn("#roadmapFinished", finished, "finished");
    renderColumn("#roadmapWorking", working, "working");
    renderColumn("#roadmapPlanned", planned, "planned");

  } catch (error) {
    console.error(error);

    document.querySelector("#roadmapFinished").innerHTML = "Could not load roadmap.";
    document.querySelector("#roadmapWorking").innerHTML = "Could not load roadmap.";
    document.querySelector("#roadmapPlanned").innerHTML = "Could not load roadmap.";
  }
}

loadRoadmap();