/**
 * Store Editor & 2,381-Character Catalog Controller for MLPMP Full Suite.
 * Ported from MLPStoreSuite2 architecture.
 * Provides instant town filtering, search filtering, batch selection presets,
 * and direct RAM synchronization.
 */

(function () {
  "use strict";

  // Catalog State
  let catalogPonies = [];
  let selectedPonyIds = new Set();
  let currentTownFilter = "ALL";
  let currentStatusFilter = "ALL";
  let searchQuery = "";
  let currentPage = 1;
  const pageSize = 60;
  let liveCurrentZone = 0; // default Ponyville
  let isCatalogLoaded = false;

  // Escape helper for safe HTML interpolation
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Global Image Error Handler (fallback SVG if portrait fails to load)
  window.handlePortraitError = function (img) {
    if (!img) return;
    img.style.display = "none";
    if (img.parentElement) {
      const fallback = img.parentElement.querySelector(".pony-portrait-fallback");
      if (fallback) fallback.style.display = "block";
    }
  };

  // DOM Elements
  const elCatalogGrid = document.getElementById("catalog-grid");
  const elCatalogSearchInput = document.getElementById("catalog-search-input");
  const elBtnClearSearch = document.getElementById("btn-clear-search");
  const elCatalogSummary = document.getElementById("catalog-selection-summary");
  const elBtnRescanRam = document.getElementById("btn-rescan-ram");

  const elBtnSelectSearch = document.getElementById("btn-select-search");
  const elBtnSelectSearchCount = document.getElementById("btn-select-search-count");
  const elBtnSelectAll = document.getElementById("btn-select-all");
  const elBtnSelectNone = document.getElementById("btn-select-none");
  const elBtnSelectCurrentTown = document.getElementById("btn-select-current-town");
  const elBtnInvertSelection = document.getElementById("btn-invert-selection");
  const elBtnApplySelection = document.getElementById("btn-apply-selection");
  const elBtnApplyCount = document.getElementById("btn-apply-count");

  const elTownTabs = document.querySelectorAll(".town-tab");
  const elStatusTabs = document.querySelectorAll(".status-tab");

  const elCountZoneAll = document.getElementById("count-zone-all");
  const elCountZone0 = document.getElementById("count-zone-0");
  const elCountZone1 = document.getElementById("count-zone-1");
  const elCountZone2 = document.getElementById("count-zone-2");
  const elCountZone4 = document.getElementById("count-zone-4");
  const elCountZone6 = document.getElementById("count-zone-6");

  const elCountStatusEnabled = document.getElementById("count-status-enabled");
  const elCountStatusDisabled = document.getElementById("count-status-disabled");

  const elShowingCount = document.getElementById("showing-count");
  const elMatchingCount = document.getElementById("matching-count");
  const elActiveStoreCount = document.getElementById("active-store-count");
  const elPaginationControls = document.getElementById("pagination-controls");

  const elBtnApplyHooks = document.getElementById("btn-apply-store-hooks");
  const elBtnRevertHooks = document.getElementById("btn-revert-store-hooks");
  const elStoreHooksBadge = document.getElementById("store-hooks-badge");

  function getTownBadgeClass(zoneId) {
    switch (zoneId) {
      case 0: return "town-ponyville";
      case 1: return "town-canterlot";
      case 2: return "town-saa";
      case 4: return "town-crystal";
      case 6: return "town-kluge";
      case 3: return "town-everfree";
      default: return "town-ponyville";
    }
  }

  function updateStatusCounters() {
    if (elCountStatusEnabled) elCountStatusEnabled.textContent = selectedPonyIds.size;
    if (elCountStatusDisabled) {
      elCountStatusDisabled.textContent = Math.max(0, catalogPonies.length - selectedPonyIds.size);
    }
  }

  function updateSearchSelectionButton(filtered) {
    if (!elBtnSelectSearch) return;

    if (!searchQuery || filtered.length === 0) {
      elBtnSelectSearch.style.display = "none";
      return;
    }

    elBtnSelectSearch.style.display = "inline-flex";
    const allMatchingSelected = filtered.every(p => selectedPonyIds.has(p.id));

    if (allMatchingSelected) {
      elBtnSelectSearch.classList.add("deselect-mode");
      elBtnSelectSearch.innerHTML = `DESELECT SEARCH (<span id="btn-select-search-count">${filtered.length}</span>)`;
    } else {
      elBtnSelectSearch.classList.remove("deselect-mode");
      elBtnSelectSearch.innerHTML = `SELECT SEARCH (<span id="btn-select-search-count">${filtered.length}</span>)`;
    }
  }

  function getFilteredPonies() {
    let list = catalogPonies;

    // 1. Filter by town tab
    if (currentTownFilter !== "ALL") {
      const targetZone = parseInt(currentTownFilter, 10);
      list = list.filter(p => p.primary_zone === targetZone || (p.zones && p.zones.includes(targetZone)));
    }

    // 2. Filter by status tab (ALL, ENABLED, DISABLED)
    if (currentStatusFilter === "ENABLED") {
      list = list.filter(p => selectedPonyIds.has(p.id));
    } else if (currentStatusFilter === "DISABLED") {
      list = list.filter(p => !selectedPonyIds.has(p.id));
    }

    // 3. Filter by search text
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      list = list.filter(p => p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q));
    }

    return list;
  }

  function renderCatalog() {
    if (!elCatalogGrid) return;

    updateStatusCounters();
    const filtered = getFilteredPonies();
    updateSearchSelectionButton(filtered);

    const totalMatching = filtered.length;
    const totalPages = Math.max(1, Math.ceil(totalMatching / pageSize));

    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = Math.min(startIdx + pageSize, totalMatching);
    const pageItems = filtered.slice(startIdx, endIdx);

    // Update summary badges
    if (elCatalogSummary) {
      elCatalogSummary.textContent = `SELECTED: ${selectedPonyIds.size.toLocaleString()} / ${catalogPonies.length.toLocaleString()} PONIES`;
    }
    if (elBtnApplyCount) {
      elBtnApplyCount.textContent = selectedPonyIds.size.toLocaleString();
    }
    if (elShowingCount) elShowingCount.textContent = pageItems.length;
    if (elMatchingCount) elMatchingCount.textContent = totalMatching;
    if (elActiveStoreCount) {
      const activeInFilter = filtered.filter(p => selectedPonyIds.has(p.id)).length;
      elActiveStoreCount.textContent = activeInFilter;
    }

    if (pageItems.length === 0) {
      elCatalogGrid.innerHTML = `<div class="catalog-loading">No ponies match the selected town, status, or search query.</div>`;
      renderPagination(0, 0);
      return;
    }

    const cardsHtml = pageItems.map(p => {
      const isSelected = selectedPonyIds.has(p.id);
      const townClass = getTownBadgeClass(p.primary_zone);
      const priceClass = p.currency === "Bits" ? "price-bits" : "price-gems";
      const cardClass = isSelected ? "selected" : "deselected";
      const portraitSrc = p.local_portrait || `/assets/portraits/${encodeURIComponent(p.id)}.png`;

      return `
        <div class="pony-card ${cardClass}" data-id="${escapeHtml(p.id)}">
          <div class="pony-portrait-wrap">
            <img class="pony-portrait" 
                 src="${escapeHtml(portraitSrc)}" 
                 alt="${escapeHtml(p.name)}" 
                 loading="lazy"
                 onerror="handlePortraitError(this)">
            <svg class="pony-portrait-fallback" viewBox="0 0 24 24"><path d="M19.5 7.05L16.2 3.75C15.8 3.35 15.2 3.1 14.6 3.1H9.4C8.8 3.1 8.2 3.35 7.8 3.75L4.5 7.05C4.1 7.45 3.85 8.05 3.85 8.65V15.35C3.85 15.95 4.1 16.55 4.5 16.95L7.8 20.25C8.2 20.65 8.8 20.9 9.4 20.9H14.6C15.2 20.9 15.8 20.65 16.2 20.25L19.5 16.95C19.9 16.55 20.15 15.95 20.15 15.35V8.65C20.15 8.05 19.9 7.45 19.5 7.05ZM12 17.5C9.5 17.5 7.5 15.5 7.5 13C7.5 10.5 9.5 8.5 12 8.5C14.5 8.5 16.5 10.5 16.5 13C16.5 15.5 14.5 17.5 12 17.5Z"/></svg>
          </div>
          <div class="pony-info">
            <div class="pony-name" title="${escapeHtml(p.name)}">${escapeHtml(p.name)}</div>
            <div class="pony-id-code" title="${escapeHtml(p.id)}">${escapeHtml(p.id)}</div>
            <div class="pony-meta-row">
              <span class="town-badge ${townClass}">${escapeHtml(p.zone_name)}</span>
              <span class="price-badge ${priceClass}">${p.price} ${p.currency}</span>
            </div>
          </div>
          <div class="pony-checkbox-wrap">
            <input type="checkbox" class="pony-checkbox" ${isSelected ? "checked" : ""} data-id="${escapeHtml(p.id)}" tabindex="-1">
          </div>
        </div>
      `;
    }).join("");

    elCatalogGrid.innerHTML = cardsHtml;
    renderPagination(currentPage, totalPages);
  }

  function renderPagination(page, totalPages) {
    if (!elPaginationControls) return;
    if (totalPages <= 1) {
      elPaginationControls.innerHTML = "";
      return;
    }

    elPaginationControls.innerHTML = `
      <button type="button" class="pagination-btn" id="btn-prev-page" ${page <= 1 ? "disabled" : ""}>&lt; PREV</button>
      <span class="page-indicator">PAGE ${page} / ${totalPages}</span>
      <button type="button" class="pagination-btn" id="btn-next-page" ${page >= totalPages ? "disabled" : ""}>NEXT &gt;</button>
    `;

    const btnPrev = document.getElementById("btn-prev-page");
    const btnNext = document.getElementById("btn-next-page");

    if (btnPrev) {
      btnPrev.addEventListener("click", () => {
        if (currentPage > 1) {
          currentPage--;
          renderCatalog();
          if (elCatalogGrid.parentElement) elCatalogGrid.parentElement.scrollTop = 0;
        }
      });
    }

    if (btnNext) {
      btnNext.addEventListener("click", () => {
        if (currentPage < totalPages) {
          currentPage++;
          renderCatalog();
          if (elCatalogGrid.parentElement) elCatalogGrid.parentElement.scrollTop = 0;
        }
      });
    }
  }

  async function fetchCatalog(refreshRam = false) {
    try {
      if (elCatalogGrid && (!catalogPonies || catalogPonies.length === 0)) {
        elCatalogGrid.innerHTML = `<div class="catalog-loading">Loading 2,381 ponies from local database...</div>`;
      }
      const url = refreshRam ? "/api/catalog?refresh=1" : "/api/catalog";
      const data = await window.api.get(url);

      catalogPonies = data.ponies || [];

      // Initialize selection from live b125 states
      selectedPonyIds.clear();
      catalogPonies.forEach(p => {
        if (p.active_in_store !== false && p.b125 !== 0) {
          selectedPonyIds.add(p.id);
        }
      });

      // Update zone summary badges
      const summary = data.zones_summary || {};
      if (elCountZoneAll) elCountZoneAll.textContent = catalogPonies.length;
      if (elCountZone0) elCountZone0.textContent = summary["Ponyville"] || 0;
      if (elCountZone1) elCountZone1.textContent = summary["Canterlot"] || 0;
      if (elCountZone2) elCountZone2.textContent = summary["Sweet Apple Acres"] || 0;
      if (elCountZone4) elCountZone4.textContent = summary["Crystal Empire"] || 0;
      if (elCountZone6) elCountZone6.textContent = summary["Klugetown"] || 0;

      updateStatusCounters();
      isCatalogLoaded = true;
      renderCatalog();
    } catch (err) {
      if (elCatalogGrid) {
        elCatalogGrid.innerHTML = `<div class="catalog-loading" style="color: var(--accent-red);">Failed to load pony catalog: ${escapeHtml(err.message)}</div>`;
      }
    }
  }

  // Event: Whole-Card & Checkbox Click Handling
  if (elCatalogGrid) {
    elCatalogGrid.addEventListener("click", (e) => {
      const card = e.target.closest(".pony-card");
      if (!card) return;

      const ponyId = card.dataset.id;
      if (!ponyId) return;

      const checkbox = card.querySelector(".pony-checkbox");
      const isCurrentlySelected = selectedPonyIds.has(ponyId);

      if (isCurrentlySelected) {
        selectedPonyIds.delete(ponyId);
        card.classList.remove("selected");
        card.classList.add("deselected");
        if (checkbox) checkbox.checked = false;
        if (currentStatusFilter === "ENABLED") {
          card.style.display = "none";
        }
      } else {
        selectedPonyIds.add(ponyId);
        card.classList.remove("deselected");
        card.classList.add("selected");
        if (checkbox) checkbox.checked = true;
        if (currentStatusFilter === "DISABLED") {
          card.style.display = "none";
        }
      }

      updateStatusCounters();
      if (elCatalogSummary) {
        elCatalogSummary.textContent = `SELECTED: ${selectedPonyIds.size.toLocaleString()} / ${catalogPonies.length.toLocaleString()} PONIES`;
      }
      if (elBtnApplyCount) {
        elBtnApplyCount.textContent = selectedPonyIds.size.toLocaleString();
      }

      const filtered = getFilteredPonies();
      updateSearchSelectionButton(filtered);
      if (elActiveStoreCount) {
        elActiveStoreCount.textContent = filtered.filter(p => selectedPonyIds.has(p.id)).length;
      }
    });
  }

  // Event: Town Tabs
  elTownTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      elTownTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentTownFilter = tab.dataset.zone;
      currentPage = 1;
      renderCatalog();
    });
  });

  // Event: Status Tabs
  elStatusTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      elStatusTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentStatusFilter = tab.dataset.status;
      currentPage = 1;
      renderCatalog();
    });
  });

  // Event: Search Input
  if (elCatalogSearchInput) {
    let searchDebounce = null;
    elCatalogSearchInput.addEventListener("input", () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        searchQuery = elCatalogSearchInput.value.trim();
        currentPage = 1;
        renderCatalog();
      }, 100);
    });
  }

  if (elBtnClearSearch) {
    elBtnClearSearch.addEventListener("click", () => {
      if (elCatalogSearchInput) elCatalogSearchInput.value = "";
      searchQuery = "";
      currentPage = 1;
      renderCatalog();
    });
  }

  // Event: Select Search (Selects all ponies matching the user's active search filter!)
  if (elBtnSelectSearch) {
    elBtnSelectSearch.addEventListener("click", () => {
      const filtered = getFilteredPonies();
      const allMatchingSelected = filtered.length > 0 && filtered.every(p => selectedPonyIds.has(p.id));
      if (allMatchingSelected) {
        filtered.forEach(p => selectedPonyIds.delete(p.id));
      } else {
        filtered.forEach(p => selectedPonyIds.add(p.id));
      }
      renderCatalog();
    });
  }

  // Event: Select All
  if (elBtnSelectAll) {
    elBtnSelectAll.addEventListener("click", () => {
      catalogPonies.forEach(p => selectedPonyIds.add(p.id));
      renderCatalog();
    });
  }

  // Event: Clear All
  if (elBtnSelectNone) {
    elBtnSelectNone.addEventListener("click", () => {
      selectedPonyIds.clear();
      renderCatalog();
    });
  }

  // Event: Current Town Only
  if (elBtnSelectCurrentTown) {
    elBtnSelectCurrentTown.addEventListener("click", () => {
      selectedPonyIds.clear();
      catalogPonies.forEach(p => {
        if (p.primary_zone === liveCurrentZone || (p.zones && p.zones.includes(liveCurrentZone))) {
          selectedPonyIds.add(p.id);
        }
      });
      renderCatalog();
    });
  }

  // Event: Invert Selection
  if (elBtnInvertSelection) {
    elBtnInvertSelection.addEventListener("click", () => {
      const filtered = getFilteredPonies();
      filtered.forEach(p => {
        if (selectedPonyIds.has(p.id)) {
          selectedPonyIds.delete(p.id);
        } else {
          selectedPonyIds.add(p.id);
        }
      });
      renderCatalog();
    });
  }

  // Event: Apply Selection to Store RAM
  if (elBtnApplySelection) {
    elBtnApplySelection.addEventListener("click", async () => {
      elBtnApplySelection.disabled = true;
      const originalText = elBtnApplySelection.innerHTML;
      elBtnApplySelection.textContent = "WRITING TO IN-GAME RAM...";

      try {
        const selectedArr = Array.from(selectedPonyIds);
        const res = await window.api.post("/api/catalog/apply", { selected_ids: selectedArr });
        window.toast.success(`Applied ${res.selected_count} ponies to in-game store shelf!`);
        elBtnApplySelection.textContent = `APPLIED ${res.selected_count} PONIES TO RAM!`;

        setTimeout(() => {
          elBtnApplySelection.disabled = false;
          elBtnApplySelection.innerHTML = originalText;
          if (elBtnApplyCount) elBtnApplyCount.textContent = selectedPonyIds.size.toLocaleString();
        }, 1500);
      } catch (err) {
        window.toast.error("Failed to apply store selection: " + err.message);
        elBtnApplySelection.disabled = false;
        elBtnApplySelection.innerHTML = originalText;
      }
    });
  }

  // Event: Re-scan from RAM
  if (elBtnRescanRam) {
    elBtnRescanRam.addEventListener("click", async () => {
      elBtnRescanRam.disabled = true;
      elBtnRescanRam.textContent = "SCANNING RAM...";
      try {
        await window.api.post("/api/catalog/rescan");
        await fetchCatalog(true);
        window.toast.success("Successfully re-scanned catalog database directly from live RAM.");
      } catch (err) {
        window.toast.error("Failed to rescan RAM: " + err.message);
      } finally {
        elBtnRescanRam.disabled = false;
        elBtnRescanRam.textContent = "RE-SCAN FROM RAM";
      }
    });
  }

  // Event: Store Code Hooks (Apply / Revert)
  if (elBtnApplyHooks) {
    elBtnApplyHooks.addEventListener("click", async () => {
      elBtnApplyHooks.disabled = true;
      try {
        const res = await window.api.post("/api/store/hooks", { action: "apply" });
        if (res.success) {
          window.toast.success(res.message);
          if (elStoreHooksBadge) {
            elStoreHooksBadge.textContent = "8/8 HOOKS ACTIVE";
            elStoreHooksBadge.className = "meta-pill status-attached";
          }
        } else {
          window.toast.error(res.message || "Failed applying store hooks.");
        }
      } catch (err) {
        window.toast.error("Hook application failed: " + err.message);
      } finally {
        elBtnApplyHooks.disabled = false;
      }
    });
  }

  if (elBtnRevertHooks) {
    elBtnRevertHooks.addEventListener("click", async () => {
      elBtnRevertHooks.disabled = true;
      try {
        const res = await window.api.post("/api/store/hooks", { action: "revert" });
        if (res.success) {
          window.toast.info(res.message);
          if (elStoreHooksBadge) {
            elStoreHooksBadge.textContent = "0/8 HOOKS ACTIVE";
            elStoreHooksBadge.className = "meta-pill status-detached";
          }
        } else {
          window.toast.error(res.message || "Failed reverting store hooks.");
        }
      } catch (err) {
        window.toast.error("Hook revert failed: " + err.message);
      } finally {
        elBtnRevertHooks.disabled = false;
      }
    });
  }

  // Tab change listener to auto-load catalog when Store tab is selected
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      if (btn.dataset.tab === "tab-store" && !isCatalogLoaded) {
        fetchCatalog();
      }
    });
  });

  // Export controller on window for cross-module access
  window.storeController = {
    fetchCatalog,
    renderCatalog,
    getLoaded: () => isCatalogLoaded,
  };

  // Auto-fetch on startup
  fetchCatalog();

})();
