/**
 * Main WebGUI State Coordinator & Event Dispatcher for MLPMP Full Suite.
 * Coordinates real-time state polling, mechanic execution, version mismatch handling,
 * and safe process termination.
 */

class SuiteApp {
  constructor() {
    this.isAttached = false;
    this.mismatchOverridden = false;
    this.pollTimer = null;
    this.activeTab = 'tab-profile';
    this.levelTableData = [];
    this.lastLevelEditTime = 0;

    this.initElements();
    this.initEventListeners();
    this.initTabs();
    this.loadLevelTable();
    this.startPolling();
  }

  initElements() {
    this.elStatusBadge = document.getElementById('status-badge');
    this.elPid = document.getElementById('meta-pid');
    this.elBtnAttach = document.getElementById('btn-attach');
    this.elBtnDetach = document.getElementById('btn-detach');
    this.elBtnClose = document.getElementById('btn-close-suite');
    this.elBtnLogs = document.getElementById('btn-open-logs');

    // Mismatch Banner & Override
    this.elMismatchBanner = document.getElementById('mismatch-banner');
    this.elMismatchDetected = document.getElementById('mismatch-detected-version');
    this.elMismatchExpected = document.getElementById('mismatch-expected-version');
    this.elBtnOverride = document.getElementById('btn-mismatch-override');
  }

  initTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');
        if (!targetTab || targetTab === this.activeTab) return;

        tabButtons.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');

        document.querySelectorAll('.tab-panel').forEach((panel) => {
          panel.classList.remove('active');
        });

        const activePanel = document.getElementById(targetTab);
        if (activePanel) {
          activePanel.classList.add('active');
          this.activeTab = targetTab;
        }

        if (targetTab === 'tab-store' && window.storeController) {
          window.storeController.fetchCatalog();
        }
      });
    });
  }

  initEventListeners() {
    // Process Attach / Detach
    this.elBtnAttach?.addEventListener('click', () => this.attachProcess());
    this.elBtnDetach?.addEventListener('click', () => this.detachProcess());

    // Safe Exit (Red X Close)
    this.elBtnClose?.addEventListener('click', () => this.closeSuite());

    // Debug Console Modal
    this.elBtnLogs?.addEventListener('click', () => window.logViewer.open());
    document.getElementById('btn-close-modal')?.addEventListener('click', () => window.logViewer.close());
    document.getElementById('btn-select-logs')?.addEventListener('click', () => window.logViewer.selectAll());
    document.getElementById('btn-save-logs')?.addEventListener('click', () => window.logViewer.saveToFile());
    document.getElementById('btn-clear-logs')?.addEventListener('click', () => window.logViewer.clear());

    // Version Mismatch Override
    this.elBtnOverride?.addEventListener('click', async () => {
      this.mismatchOverridden = true;
      if (this.elMismatchBanner) {
        this.elMismatchBanner.classList.remove('show');
      }
      this.updateControlsLockState();
      try {
        await window.api.post('/api/version/override', { override_version: true });
      } catch (e) {
        console.warn('Failed notifying backend of version override:', e);
      }
      window.toast.warn('Version safety override active. Controls unlocked.');
    });

    // =========================================================================
    // Tab 1: Profile Editor Bindings
    // =========================================================================

    // 1. Level & XP (Decoupled: Apply Level & Apply XP)
    document.getElementById('input-level')?.addEventListener('input', () => {
      this.lastLevelEditTime = Date.now();
    });
    document.getElementById('input-xp')?.addEventListener('input', () => {
      this.lastLevelEditTime = Date.now();
    });

    document.getElementById('btn-apply-level')?.addEventListener('click', async () => {
      const level = parseInt(document.getElementById('input-level')?.value) || 1;
      const res = await window.api.post('/api/mechanic/level', {
        action: 'set_level',
        level: level,
      });
      if (res.success) {
        window.toast.success(res.message);
        if (res.state) {
          const xpInp = document.getElementById('input-xp');
          if (xpInp) xpInp.value = res.state.xp;
          const lvlBadge = document.getElementById('level-badge-display');
          if (lvlBadge) lvlBadge.textContent = `Lvl ${res.state.level} (${res.state.xp_percentage}%)`;
        }
      } else {
        window.toast.error(res.message);
      }
    });

    document.getElementById('btn-apply-xp')?.addEventListener('click', async () => {
      const xp = parseInt(document.getElementById('input-xp')?.value) || 0;
      const res = await window.api.post('/api/mechanic/level', {
        action: 'set_xp',
        xp: xp,
      });
      if (res.success) {
        window.toast.success(res.message);
        if (res.state) {
          const lvlInp = document.getElementById('input-level');
          if (lvlInp) lvlInp.value = res.state.level;
          const lvlBadge = document.getElementById('level-badge-display');
          if (lvlBadge) lvlBadge.textContent = `Lvl ${res.state.level} (${res.state.xp_percentage}%)`;
        }
      } else {
        window.toast.error(res.message);
      }
    });

    // Level Table Dropdown Toggle & Filter
    const toggleBtn = document.getElementById('btn-toggle-xp-dropdown');
    const dropdownContent = document.getElementById('xp-dropdown-content');
    const chevron = document.getElementById('xp-chevron');
    toggleBtn?.addEventListener('click', () => {
      const isHidden = dropdownContent.style.display === 'none';
      dropdownContent.style.display = isHidden ? 'block' : 'none';
      chevron?.classList.toggle('open', isHidden);
      if (isHidden && (!this.levelTableData || !this.levelTableData.length)) {
        this.loadLevelTable();
      }
    });

    document.getElementById('xp-table-filter')?.addEventListener('input', (e) => {
      const q = e.target.value.trim().toLowerCase();
      this.filterLevelTable(q);
    });

    document.getElementById('xp-reference-body')?.addEventListener('click', async (e) => {
      const btn = e.target.closest('.xp-quick-set-btn');
      if (!btn) return;
      const lvl = parseInt(btn.dataset.level);
      const xp = parseInt(btn.dataset.xp);

      if (document.getElementById('input-level')) document.getElementById('input-level').value = lvl;
      if (document.getElementById('input-xp')) document.getElementById('input-xp').value = xp;
      this.lastLevelEditTime = Date.now();

      if (!this.isAttached) {
        window.toast.info(`Selected Level ${lvl} (${Number(xp).toLocaleString()} XP). Attach Suite to write to RAM.`);
        return;
      }

      // Automatically apply level and synchronized XP to game RAM immediately
      try {
        const res = await window.api.post('/api/mechanic/level', {
          action: 'set_level',
          level: lvl,
        });
        if (res.success) {
          window.toast.success(res.message);
          if (res.state) {
            const lvlInp = document.getElementById('input-level');
            if (lvlInp) lvlInp.value = res.state.level;
            const xpInp = document.getElementById('input-xp');
            if (xpInp) xpInp.value = res.state.xp;
            const lvlBadge = document.getElementById('level-badge-display');
            if (lvlBadge) lvlBadge.textContent = `Lvl ${res.state.level} (${res.state.xp_percentage}%)`;
          }
        } else {
          window.toast.error(res.message);
        }
      } catch (err) {
        console.error(err);
        window.toast.error('Failed to apply level to game RAM.');
      }
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
      const dropdownSection = document.getElementById('xp-dropdown-section');
      if (dropdownSection && !dropdownSection.contains(e.target)) {
        const dropdownContent = document.getElementById('xp-dropdown-content');
        const chevron = document.getElementById('xp-chevron');
        if (dropdownContent && dropdownContent.style.display !== 'none') {
          dropdownContent.style.display = 'none';
          chevron?.classList.remove('open');
        }
      }
    });

    // 2. Currencies & Shards
    document.getElementById('btn-apply-currencies')?.addEventListener('click', async () => {
      const payload = {
        bits: parseInt(document.getElementById('input-bits')?.value) || 0,
        gems: parseInt(document.getElementById('input-gems')?.value) || 0,
        hearts: parseInt(document.getElementById('input-hearts')?.value) || 0,
        friendship_hearts: parseInt(document.getElementById('input-friendship-hearts')?.value) || 0,
        shards: {
          loyalty: parseInt(document.getElementById('input-shard-loyalty')?.value) || 0,
          kindness: parseInt(document.getElementById('input-shard-kindness')?.value) || 0,
          honesty: parseInt(document.getElementById('input-shard-honesty')?.value) || 0,
          generosity: parseInt(document.getElementById('input-shard-generosity')?.value) || 0,
          laughter: parseInt(document.getElementById('input-shard-laughter')?.value) || 0,
          magic: parseInt(document.getElementById('input-shard-magic')?.value) || 0,
        },
      };

      const res = await window.api.post('/api/mechanic/currency', payload);
      if (res.success) window.toast.success(res.message);
    });

    document.getElementById('btn-max-currencies')?.addEventListener('click', () => {
      document.getElementById('input-bits').value = 999999999;
      document.getElementById('input-gems').value = 999999;
      document.getElementById('input-hearts').value = 99999;
      document.getElementById('input-friendship-hearts').value = 99999;
      ['loyalty', 'kindness', 'honesty', 'generosity', 'laughter', 'magic'].forEach((s) => {
        const el = document.getElementById(`input-shard-${s}`);
        if (el) el.value = 9999;
      });
      window.toast.info('Populated maximum safe currency values. Click Apply to write.');
    });

    // 3. Profile Customizations (743 Items)
    document.getElementById('btn-unlock-customizations')?.addEventListener('click', async () => {
      const res = await window.api.post('/api/mechanic/profile', { unlock: true });
      if (res.success) window.toast.success(res.message);
    });
    document.getElementById('btn-lock-customizations')?.addEventListener('click', async () => {
      const res = await window.api.post('/api/mechanic/profile', { unlock: false });
      if (res.success) window.toast.info(res.message);
    });

    // 4. Pony Editor: Costumes/Sets & Crafting Materials
    document.getElementById('btn-toggle-costumes')?.addEventListener('click', async () => {
      const isCurrentlyUnlocked = document.getElementById('costumes-status-badge')?.dataset.unlocked === 'true';
      const targetState = !isCurrentlyUnlocked;
      const res = await window.api.post('/api/mechanic/costumes', { unlock_costumes: targetState });
      if (res.success) window.toast.success(res.message);
    });

    document.getElementById('btn-apply-materials')?.addEventListener('click', async () => {
      const payload = {
        materials: {
          pins: parseInt(document.getElementById('input-mat-pins')?.value) || 0,
          buttons: parseInt(document.getElementById('input-mat-buttons')?.value) || 0,
          twine: parseInt(document.getElementById('input-mat-twine')?.value) || 0,
          ribbons: parseInt(document.getElementById('input-mat-ribbons')?.value) || 0,
          bows: parseInt(document.getElementById('input-mat-bows')?.value) || 0,
        },
      };
      const res = await window.api.post('/api/mechanic/costumes', payload);
      if (res.success) window.toast.success(res.message);
    });

    document.getElementById('btn-max-materials')?.addEventListener('click', () => {
      ['pins', 'buttons', 'twine', 'ribbons', 'bows'].forEach((m) => {
        const el = document.getElementById(`input-mat-${m}`);
        if (el) el.value = 9999;
      });
      window.toast.info('Populated 9,999 for all crafting materials.');
    });

    // 5. Group Quests Keys (Decoupled)
    document.getElementById('btn-apply-gq-keys')?.addEventListener('click', async () => {
      const keys = parseInt(document.getElementById('input-gq-keys')?.value) || 0;
      const res = await window.api.post('/api/mechanic/group_quests', { keys: keys });
      if (res.success) window.toast.success(res.message);
    });

    // 6. Active Boosters
    document.getElementById('btn-apply-boosters')?.addEventListener('click', async () => {
      const payload = {
        xp_time: parseFloat(document.getElementById('input-booster-xp-time')?.value) || 0,
        bits_time: parseFloat(document.getElementById('input-booster-bits-time')?.value) || 0,
        xp_mult: parseFloat(document.getElementById('input-booster-xp-mult')?.value) || 1.0,
        bits_mult: parseFloat(document.getElementById('input-booster-bits-mult')?.value) || 1.0,
      };
      const res = await window.api.post('/api/mechanic/boosters', payload);
      if (res.success) window.toast.success(res.message);
    });

    document.getElementById('btn-preset-boosters')?.addEventListener('click', () => {
      document.getElementById('input-booster-xp-time').value = 86400;
      document.getElementById('input-booster-bits-time').value = 86400;
      document.getElementById('input-booster-xp-mult').value = 2.0;
      document.getElementById('input-booster-bits-mult').value = 2.0;
      window.toast.info('Populated 24-hour (86,400s) 2.0x Boosters.');
    });

    // 7. Find a Pair Minigame
    document.getElementById('btn-apply-pair-timer')?.addEventListener('click', async () => {
      const t = parseFloat(document.getElementById('input-pair-timer')?.value) || 999;
      const res = await window.api.post('/api/mechanic/find_a_pair', { timer: t });
      if (res.success) window.toast.success(res.message);
    });

    document.getElementById('checkbox-freeze-pair-timer')?.addEventListener('change', async (e) => {
      const freeze = e.target.checked;
      const t = parseFloat(document.getElementById('input-pair-timer')?.value) || 999;
      const res = await window.api.post('/api/mechanic/find_a_pair', { timer_freeze: freeze, timer: t });
      if (res.success) window.toast.info(res.message);
    });

    document.getElementById('btn-apply-pair-multiplier')?.addEventListener('click', async () => {
      const m = parseInt(document.getElementById('input-pair-multiplier')?.value) || 10;
      const mode = document.getElementById('select-pair-mult-mode')?.value || 'freeze';
      const res = await window.api.post('/api/mechanic/find_a_pair', { multiplier: m, multiplier_mode: mode });
      if (res.success) window.toast.success(res.message);
    });

    document.getElementById('checkbox-freeze-pair-multiplier')?.addEventListener('change', async (e) => {
      const freeze = e.target.checked;
      const m = parseInt(document.getElementById('input-pair-multiplier')?.value) || 10;
      const mode = document.getElementById('select-pair-mult-mode')?.value || 'freeze';
      const res = await window.api.post('/api/mechanic/find_a_pair', {
        multiplier_freeze: freeze,
        multiplier: m,
        multiplier_mode: mode,
      });
      if (res.success) window.toast.info(res.message);
    });

    // 8. Ferris Wheel Reset
    document.getElementById('btn-reset-ferris-wheel')?.addEventListener('click', async () => {
      const res = await window.api.post('/api/mechanic/ferris_wheel', {});
      if (res.success) window.toast.success(res.message);
    });

    // =========================================================================
    // Tab 2: Fortune Shop & Store Tweaks Bindings
    // =========================================================================
    document.getElementById('btn-refresh-fortune-shop')?.addEventListener('click', async () => {
      const res = await window.api.post('/api/mechanic/fortune_shop', {
        cost: 0,
        force_rare: true,
      });
      if (res.success) window.toast.success(res.message);
    });
  }

  async attachProcess() {
    try {
      const res = await window.api.post('/api/attach');
      if (res.success) {
        window.toast.success(res.message);
        this.pollState();
      } else {
        window.toast.error(res.message);
      }
    } catch (e) {
      console.error(e);
    }
  }

  async detachProcess() {
    try {
      const res = await window.api.post('/api/detach');
      window.toast.info(res.message);
      this.pollState();
    } catch (e) {
      console.error(e);
    }
  }

  async closeSuite() {
    const ok = confirm('Terminate Suite process and detach from game RAM?');
    if (!ok) return;

    try {
      const res = await window.api.post('/api/shutdown');
      document.body.innerHTML = `
        <div style="min-height: 100vh; display: flex; align-items: center; justify-content: center; background-color: #141517; color: #f3f4f6; font-family: sans-serif; text-align: center; padding: 24px;">
          <div style="background-color: #202227; border: 1px solid #2d3139; border-radius: 8px; padding: 32px 40px; max-width: 500px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.6);">
            <div style="font-size: 16px; font-weight: 700; text-transform: uppercase; color: #34d399; margin-bottom: 12px;">Suite Safely Detached & Terminated</div>
            <p style="font-size: 13px; color: #9ca3af; line-height: 1.6; margin-bottom: 20px;">
              ${res.message || 'All memory hooks and handles have been safely cleaned up.'}
            </p>
            <div style="font-size: 12px; font-weight: 600; color: #6b7280; text-transform: uppercase;">You may now safely close this browser tab.</div>
          </div>
        </div>
      `;
    } catch (e) {
      window.toast.error('Failed to contact server for shutdown.');
    }
  }

  startPolling() {
    this.pollState();
    this.pollTimer = setInterval(() => this.pollState(), 2500);
  }

  async pollState() {
    try {
      const data = await window.api.get('/api/state');
      this.renderState(data);
    } catch (e) {
      // Connection lost or not ready
    }
  }

  renderState(data) {
    const status = data.status || {};
    this.isAttached = !!status.attached;

    // Header Status Pill
    if (this.elStatusBadge) {
      if (this.isAttached) {
        this.elStatusBadge.className = 'meta-pill status-attached';
        this.elStatusBadge.textContent = 'ATTACHED';
      } else {
        this.elStatusBadge.className = 'meta-pill status-detached';
        this.elStatusBadge.textContent = 'DETACHED';
      }
    }

    // PID
    if (this.elPid) {
      this.elPid.textContent = status.pid ? `PID ${status.pid}` : 'PID ---';
    }

    // Attach/Detach Buttons
    if (this.elBtnAttach) this.elBtnAttach.disabled = this.isAttached;
    if (this.elBtnDetach) this.elBtnDetach.disabled = !this.isAttached;

    // Version Mismatch Check
    const verInfo = status.version_info || {};
    if (this.isAttached && !verInfo.is_match && !this.mismatchOverridden) {
      if (this.elMismatchBanner) this.elMismatchBanner.classList.add('show');
      if (this.elMismatchDetected) this.elMismatchDetected.textContent = verInfo.detected_version || 'Unknown';
      if (this.elMismatchExpected) this.elMismatchExpected.textContent = verInfo.expected_version || 'v11.4.1a';
    } else {
      if (this.elMismatchBanner) this.elMismatchBanner.classList.remove('show');
    }

    this.updateControlsLockState(verInfo);

    if (!this.isAttached) return;

    // Only update form fields if user is NOT currently focusing or recently modified them
    const activeEl = document.activeElement;
    const now = Date.now();
    const recentlyEditedLevel = this.lastLevelEditTime && (now - this.lastLevelEditTime < 3500);

    // 1. Level & XP
    if (data.level && data.level.available) {
      const lvlInp = document.getElementById('input-level');
      if (lvlInp && activeEl !== lvlInp && !recentlyEditedLevel) lvlInp.value = data.level.level;

      const xpInp = document.getElementById('input-xp');
      if (xpInp && activeEl !== xpInp && !recentlyEditedLevel) xpInp.value = data.level.xp;

      const lvlBadge = document.getElementById('level-badge-display');
      if (lvlBadge) lvlBadge.textContent = `Lvl ${data.level.level} (${data.level.xp_percentage}%)`;
    }

    // 2. Currencies
    if (data.currency && data.currency.available) {
      const c = data.currency.currencies || {};
      const s = data.currency.shards || {};

      const map = {
        'input-bits': c.bits,
        'input-gems': c.gems,
        'input-hearts': c.hearts,
        'input-friendship-hearts': c.friendship_hearts,
        'input-shard-loyalty': s.loyalty,
        'input-shard-kindness': s.kindness,
        'input-shard-honesty': s.honesty,
        'input-shard-generosity': s.generosity,
        'input-shard-laughter': s.laughter,
        'input-shard-magic': s.magic,
      };

      for (const [id, val] of Object.entries(map)) {
        const inp = document.getElementById(id);
        if (inp && activeEl !== inp && val !== undefined) {
          inp.value = val;
        }
      }
    }

    // 3. Profile Customizations
    if (data.profile && data.profile.available) {
      const pBadge = document.getElementById('profile-status-badge');
      if (pBadge) {
        if (data.profile.unlocked) {
          pBadge.textContent = 'ALL 743 UNLOCKED';
          pBadge.className = 'meta-pill status-attached';
        } else {
          pBadge.textContent = `${data.profile.hooks_active}/${data.profile.hooks_total} HOOKS`;
          pBadge.className = 'meta-pill status-detached';
        }
      }
    }

    // 4. Costumes & Materials
    if (data.costumes && data.costumes.available) {
      const cUnlock = data.costumes.unlock_state || {};
      const cBadge = document.getElementById('costumes-status-badge');
      const cBtn = document.getElementById('btn-toggle-costumes');
      if (cBadge) {
        cBadge.dataset.unlocked = cUnlock.all_unlocked ? 'true' : 'false';
        if (cUnlock.all_unlocked) {
          cBadge.textContent = 'UNLOCKED';
          cBadge.className = 'meta-pill status-attached';
          if (cBtn) cBtn.textContent = 'Lock Costumes (Vanilla)';
        } else {
          cBadge.textContent = 'LOCKED';
          cBadge.className = 'meta-pill status-detached';
          if (cBtn) cBtn.textContent = 'Unlock All Costumes (Sets)';
        }
      }

      const mats = data.costumes.materials || {};
      ['pins', 'buttons', 'twine', 'ribbons', 'bows'].forEach((m) => {
        const inp = document.getElementById(`input-mat-${m}`);
        if (inp && activeEl !== inp && mats[m] !== undefined) {
          inp.value = mats[m];
        }
      });
    }

    // 5. Group Quests Keys
    if (data.group_quests && data.group_quests.available) {
      const gqInp = document.getElementById('input-gq-keys');
      if (gqInp && activeEl !== gqInp && data.group_quests.keys !== undefined) {
        gqInp.value = data.group_quests.keys;
      }
    }

    // 6. Boosters
    if (data.boosters && data.boosters.available) {
      const b = data.boosters;
      const bMap = {
        'input-booster-xp-time': b.xp_time,
        'input-booster-bits-time': b.bits_time,
        'input-booster-xp-mult': b.xp_mult,
        'input-booster-bits-mult': b.bits_mult,
      };
      for (const [id, val] of Object.entries(bMap)) {
        const inp = document.getElementById(id);
        if (inp && activeEl !== inp && val !== undefined) {
          inp.value = val;
        }
      }
    }

    // 7. Find a Pair
    if (data.find_a_pair) {
      const pair = data.find_a_pair;
      const statusBadge = document.getElementById('pair-status-badge');
      if (statusBadge) {
        statusBadge.textContent = pair.game_active ? 'MINIGAME ACTIVE' : 'WAITING FOR GAME';
        statusBadge.className = pair.game_active ? 'meta-pill status-attached' : 'meta-pill';
      }

      const chkTimerFreeze = document.getElementById('checkbox-freeze-pair-timer');
      if (chkTimerFreeze) chkTimerFreeze.checked = !!pair.timer_freeze;

      const chkMultFreeze = document.getElementById('checkbox-freeze-pair-multiplier');
      if (chkMultFreeze) chkMultFreeze.checked = !!pair.multiplier_freeze;

      const timerInp = document.getElementById('input-pair-timer');
      if (timerInp && activeEl !== timerInp && pair.timer !== undefined && !pair.timer_freeze) {
        timerInp.value = pair.timer;
      }

      const multInp = document.getElementById('input-pair-multiplier');
      if (multInp && activeEl !== multInp && pair.multiplier !== undefined && !pair.multiplier_freeze) {
        multInp.value = pair.multiplier;
      }

      const multMode = document.getElementById('select-pair-mult-mode');
      if (multMode && pair.multiplier_mode) {
        multMode.value = pair.multiplier_mode;
      }
    }

    // 8. Ferris Wheel
    if (data.ferris_wheel) {
      const fw = data.ferris_wheel;
      const fwBadge = document.getElementById('ferris-status-badge');
      if (fwBadge) {
        if (fw.ready) {
          fwBadge.textContent = 'FREE SPIN READY';
          fwBadge.className = 'meta-pill status-attached';
        } else {
          fwBadge.textContent = `COOLDOWN: ${fw.remaining}s`;
          fwBadge.className = 'meta-pill status-detached';
        }
      }
    }

    // 9. Fortune Shop
    if (data.fortune_shop) {
      const fs = data.fortune_shop;
      const rcBadge = document.getElementById('fortune-rc-badge');
      if (rcBadge) {
        rcBadge.textContent = fs.royal_club_active ? 'ROYAL CLUB ACTIVE' : 'STANDARD';
        rcBadge.className = fs.royal_club_active ? 'meta-pill status-attached' : 'meta-pill';
      }
    }

    // 10. Store Hooks Badge
    if (data.store && data.store.patches) {
      const p = data.store.patches;
      const hooksBadge = document.getElementById('store-hooks-badge');
      if (hooksBadge) {
        hooksBadge.textContent = `${p.active_count || 0}/${p.total_count || 8} HOOKS ACTIVE`;
        hooksBadge.className = (p.active_count === p.total_count && p.total_count > 0) ? 'meta-pill status-attached' : 'meta-pill status-detached';
      }
    }
  }

  async loadLevelTable() {
    try {
      const res = await window.api.get('/api/level/table');
      if (res && res.success && Array.isArray(res.table)) {
        this.levelTableData = res.table;
        this.renderLevelTable(this.levelTableData);
      }
    } catch (e) {
      console.warn('Failed loading level table:', e);
    }
  }

  renderLevelTable(records) {
    const tbody = document.getElementById('xp-reference-body');
    if (!tbody) return;
    if (!records || !records.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#888; padding:12px;">No matching levels found</td></tr>';
      return;
    }
    const html = records.map(r => `
      <tr>
        <td style="font-weight:700; color:#60a5fa;">${r.level}</td>
        <td>${Number(r.req_xp).toLocaleString()}</td>
        <td>${Number(r.reward_bits || 0).toLocaleString()}</td>
        <td>${Number(r.reward_gems || 0).toLocaleString()}</td>
        <td>
          <button type="button" class="xp-quick-set-btn" data-level="${r.level}" data-xp="${r.req_xp}">Set</button>
        </td>
      </tr>
    `).join('');
    tbody.innerHTML = html;
  }

  filterLevelTable(query) {
    if (!this.levelTableData) return;
    if (!query) {
      this.renderLevelTable(this.levelTableData);
      return;
    }
    const filtered = this.levelTableData.filter(r => String(r.level).includes(query));
    this.renderLevelTable(filtered);
  }

  updateControlsLockState(verInfo = {}) {
    const isLocked = !this.isAttached || (!verInfo.is_match && !this.mismatchOverridden);
    const actionButtons = document.querySelectorAll(
      '.main-wrapper button:not(#btn-mismatch-override):not(.tab-btn), .main-wrapper input, .main-wrapper select'
    );
    actionButtons.forEach((el) => {
      // Keep search, tabs, presets, and checkboxes in catalog browsing interactive offline
      if (el.closest('.catalog-section') && el.id !== 'btn-apply-selection' && el.id !== 'btn-rescan-ram') return;
      // Keep level table reference dropdown and search interactive offline
      if (el.closest('.xp-dropdown-section')) return;
      el.disabled = isLocked;
    });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.app = new SuiteApp();
});
