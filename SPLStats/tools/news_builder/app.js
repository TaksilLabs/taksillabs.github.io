const REGION_TAGS = ["East", "Central", "West"];

    let articles = [];
    let teams = [];
    let matches = [];
    let currentArticleId = "";
    let pendingLinkSelection = {
      start: 0,
      end: 0,
      text: "",
      type: "player"
    };

    const els = {
      articleSearch: document.querySelector("#articleSearch"),
      articleList: document.querySelector("#articleList"),
      newButton: document.querySelector("#newButton"),
      saveButton: document.querySelector("#saveButton"),
      reloadButton: document.querySelector("#reloadButton"),
      statusInput: document.querySelector("#statusInput"),
      publishedAtInput: document.querySelector("#publishedAtInput"),
      titleInput: document.querySelector("#titleInput"),
      subtitleInput: document.querySelector("#subtitleInput"),
      authorInput: document.querySelector("#authorInput"),
      heroImageInput: document.querySelector("#heroImageInput"),
      regionTags: document.querySelector("#regionTags"),
      customTagsInput: document.querySelector("#customTagsInput"),
      relatedTeamsInput: document.querySelector("#relatedTeamsInput"),
      relatedMatchesInput: document.querySelector("#relatedMatchesInput"),
      relatedPlayersInput: document.querySelector("#relatedPlayersInput"),
      relatedFranchisesInput: document.querySelector("#relatedFranchisesInput"),
      bodyInput: document.querySelector("#bodyInput"),
      statusText: document.querySelector("#statusText"),
      previewTags: document.querySelector("#previewTags"),
      previewTitle: document.querySelector("#previewTitle"),
      previewSubtitle: document.querySelector("#previewSubtitle"),
      previewByline: document.querySelector("#previewByline"),
      previewBody: document.querySelector("#previewBody"),
      previewRelated: document.querySelector("#previewRelated"),
      linkModalBackdrop: document.querySelector("#linkModalBackdrop"),
      linkModalClose: document.querySelector("#linkModalClose"),
      linkModalCancel: document.querySelector("#linkModalCancel"),
      linkModalInsert: document.querySelector("#linkModalInsert"),
      linkIdInput: document.querySelector("#linkIdInput"),
      linkLabelInput: document.querySelector("#linkLabelInput"),
      linkPreviewToken: document.querySelector("#linkPreviewToken"),
      linkTypeButtons: [...document.querySelectorAll("[data-link-type]")]
    };

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }

    function cleanText(value) {
      return String(value || "").trim();
    }

    function splitCsv(value) {
      return cleanText(value)
        .split(",")
        .map(item => item.trim())
        .filter(Boolean);
    }

    function todayIso() {
      return new Date().toISOString().slice(0, 10);
    }

    function slugify(text) {
      return cleanText(text)
        .toLowerCase()
        .replace(/['’]/g, "")
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/-+/g, "-")
        .replace(/^-|-$/g, "") || "untitled-article";
    }

    async function loadBootstrap() {
      const response = await fetch("/api/bootstrap");

      if (!response.ok) {
        throw new Error("Could not load news builder data.");
      }

      const data = await response.json();

      articles = data.articles || [];
      teams = data.teams || [];
      matches = data.matches || [];

      renderRegionTags();
      renderEntityPickers();
      renderArticleList();

      if (articles.length) {
        await loadArticle(articles[0].id);
      } else {
        newArticle();
      }

      setStatus("Loaded news builder data.", "good");
    }

    function renderRegionTags() {
      els.regionTags.innerHTML = REGION_TAGS.map(region => `
        <label class="check-pill">
          <input type="checkbox" value="${region}">
          ${region}
        </label>
      `).join("");

      els.regionTags.querySelectorAll("input").forEach(input => {
        input.addEventListener("change", updatePreview);
      });
    }

    function renderEntityPickers() {
      els.relatedTeamsInput.innerHTML = teams.map(team => `
        <option value="${escapeHtml(team.team_id)}">
          ${escapeHtml(team.team_display_name)}
        </option>
      `).join("");

      els.relatedMatchesInput.innerHTML = matches.map(match => `
        <option value="${escapeHtml(match.match_id)}">
          ${escapeHtml(match.schedule_id || match.match_id)} ·
          ${escapeHtml(match.home_team)} ${escapeHtml(match.score)} ${escapeHtml(match.away_team)}
        </option>
      `).join("");
    }

    function renderArticleList() {
      const query = cleanText(els.articleSearch.value).toLowerCase();

      els.articleList.innerHTML = "";

      const filtered = articles.filter(article => {
        const haystack = [
          article.title,
          article.subtitle,
          article.author,
          article.status,
          ...(article.tags || []),
          ...(article.region_tags || [])
        ].join(" ").toLowerCase();

        return !query || haystack.includes(query);
      });

      if (!filtered.length) {
        els.articleList.innerHTML = `<p class="note">No articles found.</p>`;
        return;
      }

      filtered.forEach(article => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `article-button ${article.id === currentArticleId ? "active" : ""}`;
        button.innerHTML = `
          <strong>${escapeHtml(article.title || "Untitled Article")}</strong>
          <span>${escapeHtml(article.status || "draft")} · ${escapeHtml(article.published_at || "No date")}</span>
        `;

        button.addEventListener("click", () => {
          loadArticle(article.id);
        });

        els.articleList.appendChild(button);
      });
    }

    async function loadArticle(id) {
      const response = await fetch(`/api/article?id=${encodeURIComponent(id)}`);

      if (!response.ok) {
        throw new Error("Could not load article.");
      }

      const article = await response.json();
      currentArticleId = article.id;

      fillForm(article);
      renderArticleList();
      updatePreview();
      setStatus(`Loaded ${article.title}.`, "good");
    }

    function fillForm(article) {
      els.statusInput.value = article.status || "draft";
      els.publishedAtInput.value = article.published_at || todayIso();
      els.titleInput.value = article.title || "";
      els.subtitleInput.value = article.subtitle || "";
      els.authorInput.value = article.author || "SPL Media Team";
      els.heroImageInput.value = article.hero_image || "";

      const regionTags = new Set(article.region_tags || []);

      els.regionTags.querySelectorAll("input").forEach(input => {
        input.checked = regionTags.has(input.value);
      });

      const customTags = (article.tags || [])
        .filter(tag => !REGION_TAGS.includes(tag));

      els.customTagsInput.value = customTags.join(", ");

      setMultiSelectValues(els.relatedTeamsInput, article.related_teams || []);
      setMultiSelectValues(els.relatedMatchesInput, article.related_matches || []);

      els.relatedPlayersInput.value = (article.related_players || []).join(", ");
      els.relatedFranchisesInput.value = (article.related_franchises || []).join(", ");

      els.bodyInput.value = blocksToText(article.body || []);
    }

    function setMultiSelectValues(select, values) {
      const set = new Set(values);

      [...select.options].forEach(option => {
        option.selected = set.has(option.value);
      });
    }

    function getMultiSelectValues(select) {
      return [...select.selectedOptions].map(option => option.value);
    }

    function blocksToText(blocks) {
      return blocks.map(block => {
        if (block.type === "heading") {
          return `## ${block.text || ""}`;
        }

        if (block.type === "quote") {
          const lines = [`“${block.text || ""}”`];

          if (block.credit) {
            lines.push(`- ${block.credit}`);
          }

          if (block.color) {
            lines.push(`color: ${normalizeQuoteColor(block.color)}`);
          }

          return lines.join("\n");
        }

        return block.text || "";
      }).join("\n\n");
    }

    function parseBlocks(text) {
      const chunks = cleanText(text)
        .split(/\n\s*\n/g)
        .map(chunk => chunk.trim())
        .filter(Boolean);

      const blocks = [];

      for (let i = 0; i < chunks.length; i += 1) {
        const chunk = chunks[i];

        if (chunk.startsWith("## ")) {
          blocks.push({
            type: "heading",
            text: chunk.slice(3).trim()
          });
          continue;
        }

        const quoteBlock = parseQuoteChunk(chunk);

        if (quoteBlock) {
          blocks.push(quoteBlock);
          continue;
        }

        blocks.push({
          type: "paragraph",
          text: chunk
        });
      }

      return blocks;
    }

    function parseQuoteChunk(chunk) {
      const lines = chunk
        .split(/\n/g)
        .map(line => line.trim())
        .filter(Boolean);

      if (!lines.length) {
        return null;
      }

      let quoteText = "";
      let credit = "";
      let color = "#ffd166";

      const firstLine = lines[0];

      // Style 1:
      // > Quote text
      if (firstLine.startsWith("> ")) {
        quoteText = firstLine.slice(2).trim();

        lines.slice(1).forEach(line => {
          const parsed = parseQuoteMetaLine(line);

          if (parsed.type === "credit") credit = parsed.value;
          if (parsed.type === "color") color = parsed.value;
          if (parsed.type === "text") quoteText += `\n${parsed.value}`;
        });

        return {
          type: "quote",
          text: quoteText.trim(),
          credit,
          color: normalizeQuoteColor(color)
        };
      }

      // Style 2:
      // “Quote text.”
      // - Credit
      // color: #ffd166
      const smartQuoteMatch = firstLine.match(/^[“"]([\s\S]*?)[”"]\s*(?:color:\s*(#[0-9a-fA-F]{3,6}))?\s*$/);

      if (smartQuoteMatch) {
        quoteText = smartQuoteMatch[1].trim();

        if (smartQuoteMatch[2]) {
          color = smartQuoteMatch[2];
        }

        lines.slice(1).forEach(line => {
          const parsed = parseQuoteMetaLine(line);

          if (parsed.type === "credit") credit = parsed.value;
          if (parsed.type === "color") color = parsed.value;
          if (parsed.type === "text") quoteText += `\n${parsed.value}`;
        });

        return {
          type: "quote",
          text: quoteText.trim(),
          credit,
          color: normalizeQuoteColor(color)
        };
      }

      return null;
    }

    function parseQuoteMetaLine(line) {
      const cleanLine = cleanText(line);

      if (
        cleanLine.startsWith("-- ")
        || cleanLine.startsWith("- ")
        || cleanLine.startsWith("— ")
      ) {
        return {
          type: "credit",
          value: cleanLine
            .replace(/^--\s*/, "")
            .replace(/^-\s*/, "")
            .replace(/^—\s*/, "")
            .trim()
        };
      }

      if (cleanLine.toLowerCase().startsWith("color:")) {
        return {
          type: "color",
          value: cleanLine.split(":").slice(1).join(":").trim()
        };
      }

      return {
        type: "text",
        value: cleanLine
      };
    }

    function getSelectedRegionTags() {
      return [...els.regionTags.querySelectorAll("input:checked")]
        .map(input => input.value);
    }

    function buildArticleFromForm() {
      const title = cleanText(els.titleInput.value) || "Untitled Article";
      const id = currentArticleId || slugify(title);

      const regionTags = getSelectedRegionTags();
      const customTags = splitCsv(els.customTagsInput.value);
      const allTags = [...new Set([...regionTags, ...customTags])];

      return {
        id,
        status: els.statusInput.value || "draft",
        title,
        subtitle: cleanText(els.subtitleInput.value),
        author: cleanText(els.authorInput.value) || "SPL Media Team",
        published_at: els.publishedAtInput.value || todayIso(),
        hero_image: cleanText(els.heroImageInput.value),

        tags: allTags,
        region_tags: regionTags,

        related_players: splitCsv(els.relatedPlayersInput.value),
        related_teams: getMultiSelectValues(els.relatedTeamsInput),
        related_franchises: splitCsv(els.relatedFranchisesInput.value),
        related_matches: getMultiSelectValues(els.relatedMatchesInput),

        body: parseBlocks(els.bodyInput.value)
      };
    }

    function newArticle() {
      currentArticleId = "";

      fillForm({
        id: "",
        status: "draft",
        title: "",
        subtitle: "",
        author: "SPL Media Team",
        published_at: todayIso(),
        hero_image: "",
        tags: [],
        region_tags: [],
        related_players: [],
        related_teams: [],
        related_franchises: [],
        related_matches: [],
        body: []
      });

      renderArticleList();
      updatePreview();
      setStatus("Started new article.", "");
    }

    async function saveArticle() {
      const article = buildArticleFromForm();

      const response = await fetch("/api/article", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(article)
      });

      const result = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(result.error || "Save failed.");
      }

      currentArticleId = article.id;
      articles = result.articles || articles;

      renderArticleList();
      setStatus(`Saved ${article.title}.`, "good");
    }

    function getTeamById(teamId) {
      return teams.find(team => team.team_id === teamId);
    }

    function getMatchById(matchId) {
      return matches.find(match => match.match_id === matchId);
    }

    function getInlineEntityLabel(type, id, customLabel = "") {
      if (customLabel) {
        return customLabel;
      }

      if (type === "team") {
        const team = getTeamById(id);

        return team?.team_display_name || id;
      }

      if (type === "match") {
        const match = getMatchById(id);

        if (!match) {
          return id;
        }

        if (match.schedule_id) {
          return match.schedule_id;
        }

        return `${match.home_team} vs ${match.away_team}`;
      }

      return id;
    }

    function getInlineEntityHref(type, id) {
      if (type === "team") {
        return `team.html?id=${encodeURIComponent(id)}`;
      }

      if (type === "player") {
        return `player.html?id=${encodeURIComponent(id)}`;
      }

      if (type === "franchise") {
        return `franchise.html?id=${encodeURIComponent(id)}`;
      }

      if (type === "match") {
        return `match.html?id=${encodeURIComponent(id)}`;
      }

      return "#";
    }

    function renderInlineText(text) {
      const source = String(text || "");
      const tokenPattern = /\[\[(team|player|franchise|match):([^|\]]+)(?:\|([^\]]+))?\]\]/g;

      let output = "";
      let lastIndex = 0;
      let match;

      while ((match = tokenPattern.exec(source)) !== null) {
        const [fullToken, type, rawId, rawLabel] = match;

        output += escapeHtml(source.slice(lastIndex, match.index));

        const id = cleanText(rawId);
        const label = getInlineEntityLabel(type, id, cleanText(rawLabel));
        const href = getInlineEntityHref(type, id);

        output += `
          <a
            class="preview-inline-link ${type}"
            href="${escapeHtml(href)}"
            title="${escapeHtml(type)}: ${escapeHtml(id)}"
          >
            ${escapeHtml(label)}
          </a>
        `;

        lastIndex = match.index + fullToken.length;
      }

      output += escapeHtml(source.slice(lastIndex));

      return output;
    }

    function normalizeEntityId(value) {
        return cleanText(value)
            .toLowerCase()
            .replace(/['’]/g, "")
            .replace(/&/g, "and")
            .replace(/[^a-z0-9]+/g, "_")
            .replace(/_+/g, "_")
            .replace(/^_|_$/g, "");
    }

    function normalizeQuoteColor(value) {
      const text = cleanText(value);

      if (/^#[0-9a-fA-F]{3}$/.test(text)) {
        return "#" + text.slice(1).split("").map(char => char + char).join("");
      }

      if (/^#[0-9a-fA-F]{6}$/.test(text)) {
        return text;
      }

      return "#ffd166";
    }

    function updatePreview() {
      const article = buildArticleFromForm();

      els.previewTags.innerHTML = article.tags.map(tag => `
        <span class="tag">${escapeHtml(tag)}</span>
      `).join("");

      els.previewTitle.textContent = article.title || "Untitled Article";
      els.previewSubtitle.textContent = article.subtitle || "";
      els.previewByline.textContent = `${article.author} · ${article.published_at || "No date"} · ${article.status}`;

      els.previewBody.innerHTML = article.body.map(block => {
        if (block.type === "heading") {
          return `<h4>${escapeHtml(block.text)}</h4>`;
        }

        if (block.type === "quote") {
          const quoteColor = normalizeQuoteColor(block.color || "#ffd166");

          return `
            <div
              class="preview-quote"
              style="--quote-color: ${escapeHtml(quoteColor)};"
            >
              <p>${renderInlineText(block.text || "")}</p>
              ${
                block.credit
                  ? `<cite>- ${renderInlineText(block.credit)}</cite>`
                  : ""
              }
            </div>
          `;
        }

        return `<p>${renderInlineText(block.text)}</p>`;
      }).join("");

      const related = [];

      article.related_teams.forEach(teamId => {
        const team = getTeamById(teamId);

        related.push(`
          <div class="related-card">
            <strong>${escapeHtml(team?.team_display_name || teamId)}</strong>
            <span>Related Team</span>
          </div>
        `);
      });

      article.related_matches.forEach(matchId => {
        const match = getMatchById(matchId);

        related.push(`
          <div class="related-card">
            <strong>
              ${escapeHtml(match ? `${match.home_team} ${match.score} ${match.away_team}` : matchId)}
            </strong>
            <span>Related Match</span>
          </div>
        `);
      });

      article.related_players.forEach(playerId => {
        related.push(`
          <div class="related-card">
            <strong>${escapeHtml(playerId)}</strong>
            <span>Related Player</span>
          </div>
        `);
      });

      article.related_franchises.forEach(franchiseId => {
        related.push(`
          <div class="related-card">
            <strong>${escapeHtml(franchiseId)}</strong>
            <span>Related Franchise</span>
          </div>
        `);
      });

      els.previewRelated.innerHTML = related.join("");
    }

    function setStatus(message, type = "") {
      els.statusText.textContent = message;
      els.statusText.className = `status ${type}`;
    }

    function getSelectedBodyText() {
      const textarea = els.bodyInput;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const text = textarea.value.slice(start, end);

      return {
        start,
        end,
        text
      };
    }

    function setActiveLinkType(type) {
      pendingLinkSelection.type = type;

      els.linkTypeButtons.forEach(button => {
        button.classList.toggle("active", button.dataset.linkType === type);
      });

      updateLinkTokenPreview();
    }

    function buildLinkToken() {
        const type = pendingLinkSelection.type || "player";

        const rawId = cleanText(els.linkIdInput.value);
        const rawLabel = cleanText(els.linkLabelInput.value);

        const id = normalizeEntityId(rawId || rawLabel);
        const label = rawLabel || rawId;

        if (!id && !label) {
            return `[[${type}:id|text]]`;
        }

        if (!label) {
            return `[[${type}:${id}]]`;
        }

        return `[[${type}:${id}|${label}]]`;
    }

    function updateLinkTokenPreview() {
      els.linkPreviewToken.textContent = buildLinkToken();
    }

    function openLinkModal() {
      const selection = getSelectedBodyText();

      pendingLinkSelection = {
        start: selection.start,
        end: selection.end,
        text: selection.text,
        type: pendingLinkSelection.type || "player"
      };

        els.linkLabelInput.value = selection.text || "";
        els.linkIdInput.value = selection.text || "";

      setActiveLinkType(pendingLinkSelection.type || "player");
      updateLinkTokenPreview();

      els.linkModalBackdrop.hidden = false;

      setTimeout(() => {
        els.linkIdInput.focus();
        els.linkIdInput.select();
      }, 0);
    }

    function closeLinkModal() {
      els.linkModalBackdrop.hidden = true;
      els.bodyInput.focus();
    }

    function insertLinkToken() {
      const token = buildLinkToken();

      const currentValue = els.bodyInput.value;
      const start = pendingLinkSelection.start;
      const end = pendingLinkSelection.end;

      els.bodyInput.value =
        currentValue.slice(0, start)
        + token
        + currentValue.slice(end);

      const nextCursorPosition = start + token.length;

      els.bodyInput.focus();
      els.bodyInput.setSelectionRange(nextCursorPosition, nextCursorPosition);

      closeLinkModal();
      updatePreview();
    }

    function bindEvents() {
      els.articleSearch.addEventListener("input", renderArticleList);
      els.newButton.addEventListener("click", newArticle);

      els.reloadButton.addEventListener("click", () => {
        if (!confirm("Reload article data from disk? Unsaved changes will be lost.")) {
          return;
        }

        loadBootstrap().catch(error => {
          console.error(error);
          setStatus(error.message, "bad");
          alert(error.message);
        });
      });

      els.saveButton.addEventListener("click", async () => {
        try {
          await saveArticle();
        } catch (error) {
          console.error(error);
          setStatus(error.message, "bad");
          alert(error.message);
        }
      });

      els.bodyInput.addEventListener("keydown", event => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
          event.preventDefault();
          openLinkModal();
        }
      });

      els.linkTypeButtons.forEach(button => {
        button.addEventListener("click", () => {
          setActiveLinkType(button.dataset.linkType);
        });
      });

      els.linkIdInput.addEventListener("input", updateLinkTokenPreview);
      els.linkLabelInput.addEventListener("input", updateLinkTokenPreview);

      els.linkModalClose.addEventListener("click", closeLinkModal);
      els.linkModalCancel.addEventListener("click", closeLinkModal);
      els.linkModalInsert.addEventListener("click", insertLinkToken);

      els.linkModalBackdrop.addEventListener("click", event => {
        if (event.target === els.linkModalBackdrop) {
          closeLinkModal();
        }
      });

      document.addEventListener("keydown", event => {
        if (event.key === "Escape" && !els.linkModalBackdrop.hidden) {
          closeLinkModal();
        }

        if (event.key === "Enter" && !els.linkModalBackdrop.hidden) {
          event.preventDefault();
          insertLinkToken();
        }
      });

      [
        els.statusInput,
        els.publishedAtInput,
        els.titleInput,
        els.subtitleInput,
        els.authorInput,
        els.heroImageInput,
        els.customTagsInput,
        els.relatedTeamsInput,
        els.relatedMatchesInput,
        els.relatedPlayersInput,
        els.relatedFranchisesInput,
        els.bodyInput
      ].forEach(input => {
        input.addEventListener("input", updatePreview);
        input.addEventListener("change", updatePreview);
      });
    }

    bindEvents();

    loadBootstrap().catch(error => {
      console.error(error);
      setStatus(error.message, "bad");
      alert(error.message);
    });