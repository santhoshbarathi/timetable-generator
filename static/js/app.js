/**
 * Intelligent Department Timetable Scheduler - Client Application Logic
 * Vanilla JavaScript (ES6+), zero external library dependencies.
 */

const App = {
  // Cached State
  config: null,
  classes: [],
  faculty: [],
  subjects: [],
  timetableData: null,
  selectedClassId: null,
  selectedClassId1: null,
  selectedClassId2: null,
  selectedFacultyId: null,   // for Faculty Timetable tab
  viewMode: "single", // "single" | "dual" | "all"
  dualLayout: "stacked", // "stacked" | "split"
  isFitToScreen: true, // Default to full-width fit to screen
  // -------------------------------------------------------------------------
  // Initialization
  // -------------------------------------------------------------------------
  async init() {
    try {
      await this.loadConfig();
      await this.refreshAllData();

      // Load fit to screen preference (default to true)
      const savedFit = localStorage.getItem("timetable_fit_to_screen");
      const shouldFit = savedFit !== null ? savedFit === "true" : true;
      this.setFitToScreen(shouldFit);

      this.renderTimetable();
      this.renderFacultyTable();
        this.populateFacultyTimetableDropdown();
      this.renderClassesAndSubjects();
    } catch (err) {
      console.error("Initialization error:", err);
      this.showToast("Failed to initialize scheduler data.", "error");
    }
  },

  async loadConfig() {
    const res = await fetch("/api/config");
    this.config = await res.json();
  },

  async refreshAllData() {
    const [classesRes, facultyRes, subjectsRes, timetableRes] = await Promise.all([
      fetch("/api/classes").then((r) => r.json()),
      fetch("/api/faculty").then((r) => r.json()),
      fetch("/api/subjects").then((r) => r.json()),
      fetch("/api/timetable").then((r) => r.json()),
    ]);

    this.classes = classesRes;
    this.faculty = facultyRes;
    this.subjects = subjectsRes;
    this.timetableData = timetableRes;

    // Update faculty tab badge counter
    const facCountEl = document.getElementById("faculty-tab-count");
    if (facCountEl) facCountEl.textContent = this.faculty.length;

    // Populate global class selectors in header (selector 1 and 2)
    const globalSelect = document.getElementById("global-class-select");
    if (globalSelect && this.classes.length > 0) {
      globalSelect.innerHTML = this.classes
        .map((c) => `<option value="${c.id}" ${c.id === this.selectedClassId1 ? "selected" : ""}>${this.escapeHtml(c.name)} (${this.escapeHtml(c.code)})</option>`)
        .join("");
    }
    const globalSelect2 = document.getElementById("global-class-select-2");
    if (globalSelect2 && this.classes.length > 0) {
      globalSelect2.innerHTML = this.classes
        .map((c) => `<option value="${c.id}" ${c.id === this.selectedClassId2 ? "selected" : ""}>${this.escapeHtml(c.name)} (${this.escapeHtml(c.code)})</option>`)
        .join("");
      // Show selector-2 only in dual mode
      globalSelect2.style.display = this.viewMode === "dual" ? "" : "none";
    }

    // Default selected classes for single and dual timetable views
    if (this.classes.length > 0) {
      if (!this.selectedClassId1 || !this.classes.some((c) => c.id === this.selectedClassId1)) {
        this.selectedClassId1 = this.classes[0].id;
      }
      if (!this.selectedClassId2 || !this.classes.some((c) => c.id === this.selectedClassId2)) {
        this.selectedClassId2 = this.classes.length > 1 ? this.classes[1].id : this.classes[0].id;
      }
      if (!this.selectedClassId || !this.classes.some((c) => c.id === this.selectedClassId)) {
        this.selectedClassId = this.classes[0].id;
      }
    } else {
      this.selectedClassId = null;
      this.selectedClassId1 = null;
      this.selectedClassId2 = null;
    }
  },

  // -------------------------------------------------------------------------
  // Tab Navigation
  // -------------------------------------------------------------------------
  switchTab(tabId) {
    document.querySelectorAll(".tab-btn, .saas-nav-item").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabId);
    });
    document.querySelectorAll(".tab-pane").forEach((pane) => {
      pane.classList.toggle("active", pane.id === tabId);
    });
  },

  openModal(modalId) {
    if (modalId === "modal-subject") {
      this.openAddSubjectModal();
    } else if (modalId === "modal-faculty") {
      this.openAddFacultyModal();
    } else if (modalId === "modal-class") {
      this.openAddClassModal();
    } else {
      const el = document.getElementById(modalId);
      if (el) el.style.display = "flex";
    }
  },

  // -------------------------------------------------------------------------
  // Download & Printing Export Handlers
  // -------------------------------------------------------------------------
  toggleDownloadDropdown(evt) {
    if (evt && evt.stopPropagation) evt.stopPropagation();
    const menu = document.getElementById("timetable-download-dropdown");
    if (!menu) return;
    if (typeof evt === "boolean") {
      menu.style.display = evt ? "block" : "none";
    } else {
      menu.style.display = menu.style.display === "none" || !menu.style.display ? "block" : "none";
    }
  },

  downloadTimetableCsv(classId) {
    const cid = classId || this.selectedClassId1 || this.selectedClassId || (this.classes[0]?.id);
    if (!cid) {
      this.showToast("No class selected to download.", "warning");
      return;
    }
    const targetUrl = `/api/export/timetable/csv?class_id=${cid}`;
    window.location.href = targetUrl;
    this.showToast("Downloading class timetable CSV...", "info");
  },

  downloadAllTimetablesCsv() {
    window.location.href = `/api/export/timetable/csv?all=true`;
    this.showToast("Downloading all class timetables CSV...", "info");
  },

  downloadFacultyTimetableCsv(facultyId) {
    const fid = facultyId || this.selectedFacultyId;
    if (!fid) {
      this.showToast("Please select a faculty member first.", "warning");
      return;
    }
    window.location.href = `/api/export/faculty/csv?faculty_id=${fid}`;
    this.showToast("Downloading faculty schedule CSV...", "info");
  },

  downloadTimetableJson() {
    if (!this.timetableData) {
      this.showToast("No timetable data to export.", "warning");
      return;
    }
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.timetableData, null, 2));
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `Department_Timetable_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(dlAnchor);
    dlAnchor.click();
    dlAnchor.remove();
    this.showToast("Timetable JSON exported successfully!", "success");
  },

  printTimetable() {
    window.print();
  },

  printSingleTimetable(classId) {
    const prevMode = this.viewMode;
    const prevId = this.selectedClassId;
    this.selectedClassId = classId;
    this.selectedClassId1 = classId;
    this.viewMode = "single";
    this.renderTimetable();
    setTimeout(() => {
      window.print();
      setTimeout(() => {
        this.viewMode = prevMode;
        this.selectedClassId = prevId;
        this.renderTimetable();
      }, 500);
    }, 100);
  },

  printFacultyTimetable() {
    if (!this.selectedFacultyId) {
      this.showToast("Please select a faculty member first.", "warning");
      return;
    }
    window.print();
  },

  // -------------------------------------------------------------------------
  // Timetable Matrix & Multi-View Rendering
  // -------------------------------------------------------------------------
  setViewMode(mode) {
    this.viewMode = mode;
    document.getElementById("btn-view-dual")?.classList.toggle("active", mode === "dual");
    document.getElementById("btn-view-single")?.classList.toggle("active", mode === "single");
    document.getElementById("btn-view-all")?.classList.toggle("active", mode === "all");

    const layoutToggle = document.getElementById("dual-layout-toggle");
    if (layoutToggle) {
      layoutToggle.style.display = mode === "dual" ? "inline-flex" : "none";
    }

    // Show/hide second class selector wrapper
    const sel2Wrapper = document.getElementById("dual-select-wrapper");
    if (sel2Wrapper) {
      sel2Wrapper.style.display = mode === "dual" ? "inline-flex" : "none";
    }
    const sel2 = document.getElementById("global-class-select-2");
    if (sel2) sel2.style.display = mode === "dual" ? "" : "none";

    this.renderTimetable();
  },

  setDualLayout(layout) {
    this.dualLayout = layout;
    document.getElementById("btn-layout-stacked")?.classList.toggle("active", layout === "stacked");
    document.getElementById("btn-layout-split")?.classList.toggle("active", layout === "split");

    this.renderTimetable();
  },

  toggleFitToScreen() {
    this.setFitToScreen(!this.isFitToScreen);
  },

  setFitToScreen(enabled) {
    this.isFitToScreen = enabled;
    localStorage.setItem("timetable_fit_to_screen", enabled ? "true" : "false");
    document.body.classList.toggle("fit-to-screen", enabled);

    const btn = document.getElementById("btn-toggle-fit");
    const textEl = document.getElementById("btn-fit-text");
    if (btn) btn.classList.toggle("active", enabled);
    if (textEl) textEl.textContent = enabled ? "Standard Width" : "Fit to Screen";
  },

  onClassChange(slotIndex, selectEl) {
    const classId = parseInt(selectEl.value, 10);
    if (slotIndex === 1) {
      this.selectedClassId1 = classId;
      this.selectedClassId = classId;
    } else if (slotIndex === 2) {
      this.selectedClassId2 = classId;
    } else {
      this.selectedClassId = classId;
    }
    this.renderTimetable();
  },

  populateClassDropdown() {
    // Retained for backward compatibility
  },

  onClassSelectChange() {
    // Retained for backward compatibility
  },

  updateClassBadge() {
    // Retained for backward compatibility
  },

  renderTimetable() {
    const container = document.getElementById("timetables-container");
    if (!container) return;

    // Apply layout class
    container.className = `timetables-container ${this.viewMode === "dual" && this.dualLayout === "split" ? "layout-split" : "layout-stacked"}`;

    if (this.classes.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 3rem; color: var(--slate-500);">
          No classes registered yet. Create classes in the "Classes & Subjects" tab.
        </div>
      `;
      return;
    }

    let cardsHtml = "";

    if (this.viewMode === "dual") {
      // Show 2 Timetables on the same page
      const id1 = this.selectedClassId1 || this.classes[0]?.id;
      const id2 = this.selectedClassId2 || (this.classes.length > 1 ? this.classes[1].id : this.classes[0].id);
      cardsHtml += this.buildTimetableCardHtml(id1, "Timetable 1", 1);
      cardsHtml += this.buildTimetableCardHtml(id2, "Timetable 2", 2);
    } else if (this.viewMode === "all") {
      // Show All classes
      this.classes.forEach((c, index) => {
        cardsHtml += this.buildTimetableCardHtml(c.id, `Class ${index + 1}`, index + 1);
      });
    } else {
      // Single Timetable
      const id = this.selectedClassId || this.classes[0]?.id;
      cardsHtml += this.buildTimetableCardHtml(id, "Timetable", 1);
    }

    container.innerHTML = cardsHtml;
  },

  buildTimetableCardHtml(classId, slotLabel, slotIndex) {
    const cls = this.classes.find((c) => c.id === classId) || this.classes[0];
    if (!cls) return "";

    const classSched = this.timetableData?.schedules_by_class?.[cls.id];
    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

    // Update global class select if needed
    const globalSelect = document.getElementById("global-class-select");
    if (globalSelect && globalSelect.children.length === 0 && this.classes.length > 0) {
      globalSelect.innerHTML = this.classes
        .map((c) => `<option value="${c.id}" ${c.id === cls.id ? "selected" : ""}>${this.escapeHtml(c.name)} (${this.escapeHtml(c.code)})</option>`)
        .join("");
    }

    const getColorForSubject = (name, code) => {
      const n = (name || "").toLowerCase();
      const c = (code || "").toLowerCase();
      if (n.includes("operating") || c.includes("os")) return "pill-blue";
      if (n.includes("discrete") || c.includes("dm")) return "pill-yellow";
      if (n.includes("exploratory") || n.includes("eda") || c.includes("eda")) return "pill-purple";
      if (n.includes("java") || c.includes("java")) return "pill-lavender";
      if (n.includes("data structure") || c.includes("ds")) return "pill-blue-alt";

      const colorClasses = [
        "pill-blue",
        "pill-yellow",
        "pill-purple",
        "pill-lavender",
        "pill-blue-alt",
        "pill-green",
        "pill-pink",
        "pill-teal",
        "pill-peach"
      ];
      let hash = 0;
      const str = name || code || "";
      for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
      }
      return colorClasses[Math.abs(hash) % colorClasses.length];
    };

    // Build periods dynamically from config.py via API (incorporating Morning Break, Lunch Break, and Tea Break)
    const _pt = this.timetableData?.period_timings || {};
    const _bt = this.timetableData?.break_timings  || {};
    const _sb1 = _bt.short_break_1 || {};
    const _lunch = _bt.lunch_break || {};
    const _sb2 = _bt.short_break_2 || {};

    const _sb1After = _sb1.after_period || 2;
    const _sb1Time  = (_sb1.start || "10:40") + " – " + (_sb1.end || "10:50");
    const _lunchAfter = _lunch.after_period || 4;
    const _lunchTime  = (_lunch.start || "12:30") + " – " + (_lunch.end || "13:05");
    const _sb2After = _sb2.after_period || 6;
    const _sb2Time  = (_sb2.start || "14:45") + " – " + (_sb2.end || "15:05");

    const periods = (() => {
      const nums = Object.keys(_pt).map(Number).sort((a, b) => a - b);
      const arr = [];
      for (const num of nums) {
        if (num === _sb1After + 1) {
          arr.push({ isBreak: true, label: "Morning Break", time: _sb1Time, breakType: "short" });
        }
        if (num === _lunchAfter + 1) {
          arr.push({ isBreak: true, label: "Lunch Break", time: _lunchTime, breakType: "lunch" });
        }
        if (num === _sb2After + 1) {
          arr.push({ isBreak: true, label: "Tea Break", time: _sb2Time, breakType: "short" });
        }
        const t = _pt[num];
        const label = t.label || (t.start + " – " + t.end);
        arr.push({ num, time: label });
      }
      return arr;
    })();

    let rowsHtml = "";

    // Days running vertically down the left side
    days.forEach((day, dayIdx) => {
      const dayGrid = classSched?.grid?.[day] || {};
      let cellsHtml = "";

      // Time slots running horizontally across
      const skipPeriods = new Set();
      periods.forEach((period, pidx) => {
        if (period.isBreak) {
          // Render unified break column on the first day spanning all days
          if (dayIdx === 0) {
            const pillClass = period.breakType === "lunch" ? "pill-lunch" : "pill-break";
            const cellClass = period.breakType === "lunch" ? "lunch-cell unified-break-cell" : "break-cell unified-break-cell";
            cellsHtml += `
              <td class="${cellClass}" rowspan="${days.length}">
                <div class="${pillClass}">
                  <span class="break-vertical-text">${period.label}</span>
                </div>
              </td>
            `;
          }
          // On other days (Tuesday-Friday), the break cell is occupied by the rowspan
          return;
        }

        if (skipPeriods.has(period.num)) {
          // Merged into previous colspan=2 lab cell
          return;
        }

        const slot = dayGrid[period.num];

        // Detect lab block: next consecutive period has same subject_id
        let isLabBlock = false;
        if (slot && slot.subject_id) {
          const nextPeriod = periods[pidx + 1];
          if (nextPeriod && !nextPeriod.isBreak) {
            const nextSlot = dayGrid[nextPeriod.num];
            if (nextSlot && nextSlot.subject_id === slot.subject_id) {
              isLabBlock = true;
              skipPeriods.add(nextPeriod.num);
            }
          }
        }

        if (!slot) {
          cellsHtml += `<td class="period-cell" style="text-align: center;"><span class="schedule-empty">–</span></td>`;
        } else {
          const colorClass = getColorForSubject(slot.subject_name, slot.subject_code);
          const facultyTooltip = slot.faculty_name ? `Faculty: ${slot.faculty_name}` : "";
          const fullTitle = `${slot.subject_name}${facultyTooltip ? ' • ' + facultyTooltip : ''}`;
          const colspanAttr = isLabBlock ? ` colspan="2"` : ``;
          const labBadge = isLabBlock
            ? `<span style="display:inline-block;font-size:9px;font-weight:700;letter-spacing:0.5px;background:rgba(255,255,255,0.55);color:#1e3a5f;border-radius:4px;padding:2px 6px;margin-left:6px;vertical-align:middle;">2hr LAB</span>`
            : ``;
          cellsHtml += `
            <td class="period-cell"${colspanAttr}>
              <div class="schedule-pill ${colorClass}">
                <div class="pill-subject" title="${this.escapeHtml(fullTitle)}">${this.escapeHtml(slot.subject_name)}${labBadge}</div>
              </div>
            </td>
          `;
        }
      });

      rowsHtml += `
        <tr>
          <td class="saas-day-cell">${day}</td>
          ${cellsHtml}
        </tr>
      `;
    });

    // Subjects in this class for the print legend
    const classSubjects = (this.subjects || []).filter((s) => s.class_id === cls.id);
    const legendRows = classSubjects.map((s) => {
      const facName = s.faculty_name || "Dynamic Pool";
      return `<tr>
        <td style="font-weight:700;">${this.escapeHtml(s.code)}</td>
        <td>${this.escapeHtml(s.name)}</td>
        <td>${this.escapeHtml(facName)}</td>
        <td style="text-align:center;">${s.periods_per_week} hrs/wk</td>
      </tr>`;
    }).join("");

    return `
      <div class="saas-table-card">
        <!-- Printable Institution Header (Only rendered when printing) -->
        <div class="print-only-banner">
          <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:1.5px solid #0f172a;padding-bottom:5px;margin-bottom:6px;">
            <div style="display:flex;align-items:center;gap:10px;">
              <img src="/static/images/info-logo.png" style="height:36px;width:auto;" alt="INFO Logo">
              <div>
                <div style="font-size:12pt;font-weight:800;letter-spacing:0.3px;color:#0f172a;line-height:1.1;">INFO INSTITUTE OF ENGINEERING</div>
                <div style="font-size:6.5pt;color:#334155;font-weight:600;line-height:1.1;">(An Autonomous Institution | Approved by AICTE, New Delhi | Affiliated to Anna University, Chennai)</div>
                <div style="font-size:7.5pt;color:#1e3a8a;font-weight:700;margin-top:1px;">DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING</div>
              </div>
            </div>
            <div style="display:flex;gap:6px;align-items:center;">
              <img src="/static/images/logo-anna-university.png" style="height:30px;width:auto;" alt="Anna Univ">
              <img src="/static/images/logo-aicte.png" style="height:30px;width:auto;" alt="AICTE">
              <img src="/static/images/logo-naac.png" style="height:30px;width:auto;" alt="NAAC">
            </div>
          </div>
        </div>

        <!-- Card Top Bar with Title, Badges, and Per-Card Print & Download CSV Buttons -->
        <div class="timetable-card-top">
          <div class="timetable-card-title-group">
            <span class="timetable-card-title">${this.escapeHtml(cls.name)}</span>
            <span class="timetable-card-code">${this.escapeHtml(cls.code)}</span>
            <span class="timetable-card-meta">40 Periods · Full-Week Active</span>
            ${slotLabel && this.viewMode === "dual" ? `<span style="font-size:11px;background:#f1f5f9;color:#475569;font-weight:700;padding:2px 8px;border-radius:4px;">${this.escapeHtml(slotLabel)}</span>` : ""}
          </div>
          <div class="timetable-card-actions">
            <button class="btn btn-sm" onclick="App.printSingleTimetable(${cls.id})" title="Print this class timetable">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6 9 6 2 18 2 18 9"></polyline>
                <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
                <rect x="6" y="14" width="12" height="8"></rect>
              </svg>
              <span>Print</span>
            </button>
            <button class="btn btn-sm" onclick="App.downloadTimetableCsv(${cls.id})" title="Export CSV for this class">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              <span>CSV</span>
            </button>
          </div>
        </div>

        <div class="table-scroll-wrapper">
          <table class="saas-schedule-table">
            <thead>
              <tr>
                <th style="padding-left: 10px; text-align: left;">Day / Time</th>
                ${periods.map(p => p.isBreak
                  ? `<th class="${p.breakType === 'lunch' ? 'lunch-col-header' : 'short-break-col-header'}">
                      <div style="font-size:11px;font-weight:700;color:${p.breakType === 'lunch' ? '#b45309' : '#475569'};line-height:1.2;">${p.label}</div>
                      <div style="font-size:9.5px;font-weight:500;color:#64748b;margin-top:2px;line-height:1.1;">${p.time}</div>
                    </th>`
                  : `<th>
                      <div style="font-size:12px;font-weight:800;color:#0f172a;line-height:1.2;">Period ${p.num}</div>
                      <div style="font-size:9.5px;font-weight:500;color:#64748b;margin-top:2px;line-height:1.1;">${p.time}</div>
                    </th>`
                ).join("")}
              </tr>
            </thead>
            <tbody>
              ${rowsHtml}
            </tbody>
          </table>
        </div>

        <!-- Course & Faculty Allocation Legend (Visible on Print) -->
        <div class="print-legend-section">
          <div style="font-weight:700;margin-bottom:3px;color:#0f172a;">Course & Faculty Allocation:</div>
          <table>
            <thead>
              <tr style="background:#f1f5f9;font-weight:700;">
                <th style="width:12%;">Code</th>
                <th style="width:48%;">Subject Title</th>
                <th style="width:28%;">Faculty In-Charge</th>
                <th style="width:12%;text-align:center;">Hours / Week</th>
              </tr>
            </thead>
            <tbody>
              ${legendRows || '<tr><td colspan="4" style="text-align:center;">No subjects allocated.</td></tr>'}
            </tbody>
          </table>
        </div>

        <!-- Formal University Signatures Block (Visible on Print) -->
        <div class="print-signatures">
          <div>Class Advisor / Tutor</div>
          <div>Time Table Coordinator</div>
          <div>Head of Department (HOD)</div>
          <div>Principal</div>
        </div>
      </div>
    `;
  },

  // -------------------------------------------------------------------------
  // Timetable Regeneration
  // -------------------------------------------------------------------------
  async regenerateTimetable() {
    const btn = document.getElementById("btn-quick-regenerate");
    const icon = btn?.querySelector(".spin-icon");
    if (icon) icon.classList.add("spinning");

    try {
      const res = await fetch("/api/timetable/regenerate", { method: "POST" });
      const data = await res.json();

      if (res.ok && data.success) {
        this.showToast(data.message || "Timetable generated with 0 conflicts!", "success");
        await this.refreshAllData();
        this.renderTimetable();
        this.renderFacultyTable();
        this.renderClassesAndSubjects();
      } else {
        const errMsg = data.error || "Unable to generate timetable with current constraints.";
        this.showToast(errMsg, "error");
      }
    } catch (err) {
      console.error("Regeneration error:", err);
      this.showToast("Server communication error during timetable generation.", "error");
    } finally {
      if (icon) icon.classList.remove("spinning");
    }
  },

  // -------------------------------------------------------------------------
  // Faculty Management
  // -------------------------------------------------------------------------


  // -------------------------------------------------------------------------
  // Faculty Timetable Tab
  // -------------------------------------------------------------------------

  /** Populate the faculty dropdown and render if one is already selected. */
  populateFacultyTimetableDropdown() {
    const sel = document.getElementById("faculty-timetable-select");
    if (!sel) return;
    const prev = this.selectedFacultyId;
    sel.innerHTML = '<option value="">— Select Faculty —</option>';
    this.faculty.forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f.id;
      const wtype = f.work_type === "part_time" ? "Part-Time" : "Full-Time";
      opt.textContent = `${f.name} (${wtype} · ${f.department})`;
      if (f.id === prev) opt.selected = true;
      sel.appendChild(opt);
    });
  },

  onFacultyTimetableChange(selectEl) {
    const id = parseInt(selectEl.value, 10) || null;
    this.selectedFacultyId = id;
    this.renderFacultyTimetable();
  },

  async renderFacultyTimetable() {
    this.populateFacultyTimetableDropdown();
    const container = document.getElementById("faculty-timetable-container");
    const infoBar   = document.getElementById("faculty-timetable-info");
    const infoText  = document.getElementById("faculty-timetable-info-text");
    if (!container) return;

    if (!this.selectedFacultyId) {
      container.innerHTML = `
        <div class="card" style="text-align:center;padding:3rem;color:var(--slate-500,#64748b);">
          Select a faculty member above to view their weekly timetable.
        </div>`;
      if (infoBar) infoBar.style.display = "none";
      return;
    }

    try {
      const res  = await fetch(`/api/timetable/faculty/${this.selectedFacultyId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const fac  = data.faculty;
      const grid = data.grid;

      // Show part-time info bar
      if (infoBar && infoText) {
        const isPt = fac.work_type === "part_time";
        infoBar.style.display = isPt ? "block" : "none";
        infoText.textContent  = `Part-time faculty · Periods 1–4 only (09:00–12:30) · ${fac.assigned_periods} / ${fac.weekly_period_limit} periods assigned this week`;
      }

      container.innerHTML = this.buildFacultyTimetableHtml(fac, grid);
    } catch (err) {
      console.error("Faculty timetable fetch error:", err);
      container.innerHTML = `
        <div class="card" style="text-align:center;padding:2rem;color:#ef4444;">
          Failed to load faculty timetable. Please try again.
        </div>`;
    }
  },

  buildFacultyTimetableHtml(fac, grid) {
    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

    const getColorForSubject = (name, code) => {
      const n = (name || "").toLowerCase();
      const c = (code || "").toLowerCase();
      if (n.includes("operating") || c.includes("os"))      return "pill-blue";
      if (n.includes("discrete")  || c.includes("dm"))      return "pill-yellow";
      if (n.includes("exploratory") || n.includes("eda") || c.includes("eda")) return "pill-purple";
      if (n.includes("java")      || c.includes("java"))    return "pill-lavender";
      if (n.includes("data structure") || c.includes("ds")) return "pill-blue-alt";
      const palette = ["pill-blue","pill-yellow","pill-purple","pill-lavender","pill-blue-alt","pill-green","pill-pink","pill-teal","pill-peach"];
      let hash = 0;
      const str = name || code || "";
      for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
      return palette[Math.abs(hash) % palette.length];
    };

    // Build periods dynamically from config.py via API (with all 3 breaks)
    const _pt = this.timetableData?.period_timings || {};
    const _bt = this.timetableData?.break_timings  || {};
    const _sb1 = _bt.short_break_1 || {};
    const _lunch = _bt.lunch_break || {};
    const _sb2 = _bt.short_break_2 || {};

    const _sb1After = _sb1.after_period || 2;
    const _sb1Time  = (_sb1.start || "10:40") + " – " + (_sb1.end || "10:50");
    const _lunchAfter = _lunch.after_period || 4;
    const _lunchTime  = (_lunch.start || "12:30") + " – " + (_lunch.end || "13:05");
    const _sb2After = _sb2.after_period || 6;
    const _sb2Time  = (_sb2.start || "14:45") + " – " + (_sb2.end || "15:05");

    const periods = (() => {
      const nums = Object.keys(_pt).map(Number).sort((a, b) => a - b);
      const arr = [];
      for (const num of nums) {
        if (num === _sb1After + 1) {
          arr.push({ isBreak: true, label: "Morning Break", time: _sb1Time, breakType: "short" });
        }
        if (num === _lunchAfter + 1) {
          arr.push({ isBreak: true, label: "Lunch Break", time: _lunchTime, breakType: "lunch" });
        }
        if (num === _sb2After + 1) {
          arr.push({ isBreak: true, label: "Tea Break", time: _sb2Time, breakType: "short" });
        }
        const t = _pt[num];
        const label = t.label || (t.start + " – " + t.end);
        arr.push({ num, time: label });
      }
      return arr;
    })();

    // Header row
    let theadHtml = `<tr>
      <th style="padding-left:20px;text-align:left;">Day / Time</th>`;
    periods.forEach((p) => {
      if (p.isBreak) {
        theadHtml += `<th class="${p.breakType === 'lunch' ? 'lunch-col-header' : 'short-break-col-header'}">
          <div style="font-size:11px;font-weight:700;color:${p.breakType === 'lunch' ? '#b45309' : '#475569'};line-height:1.2;">${p.label}</div>
          <div style="font-size:9.5px;font-weight:500;color:#64748b;margin-top:2px;line-height:1.1;">${p.time}</div>
        </th>`;
      } else {
        theadHtml += `<th>
          <div style="font-size:12px;font-weight:800;color:#0f172a;line-height:1.2;">Period ${p.num}</div>
          <div style="font-size:9.5px;font-weight:500;color:#64748b;margin-top:2px;line-height:1.1;">${p.time}</div>
        </th>`;
      }
    });
    theadHtml += `</tr>`;

    // Body rows – one per day
    let tbodyHtml = "";
    const skipPeriods = new Set();

    days.forEach((day, dayIdx) => {
      const dayGrid = grid[day] || {};
      skipPeriods.clear();
      let cellsHtml = "";

      periods.forEach((period, pidx) => {
        if (period.isBreak) {
          if (dayIdx === 0) {
            const pillClass = period.breakType === "lunch" ? "pill-lunch" : "pill-break";
            const cellClass = period.breakType === "lunch" ? "lunch-cell unified-break-cell" : "break-cell unified-break-cell";
            cellsHtml += `
              <td class="${cellClass}" rowspan="${days.length}">
                <div class="${pillClass}">
                  <span class="break-vertical-text">${period.label}</span>
                </div>
              </td>
            `;
          }
          return;
        }
        if (skipPeriods.has(period.num)) return;

        const slot = dayGrid[period.num];

        // Lab merge detection
        let isLabBlock = false;
        if (slot && slot.subject_id) {
          const nextP = periods[pidx + 1];
          if (nextP && !nextP.isBreak) {
            const nextSlot = dayGrid[nextP.num];
            if (nextSlot && nextSlot.subject_id === slot.subject_id) {
              isLabBlock = true;
              skipPeriods.add(nextP.num);
            }
          }
        }

        if (!slot) {
          cellsHtml += `<td class="period-cell" style="text-align:center;"><span class="schedule-empty">–</span></td>`;
        } else {
          const colorClass  = getColorForSubject(slot.subject_name, slot.subject_code);
          const classLabel  = slot.class_name ? this.escapeHtml(slot.class_name) : "";
          const colspanAttr = isLabBlock ? ` colspan="2"` : "";
          const labBadge    = isLabBlock
            ? `<span style="display:inline-block;font-size:9px;font-weight:700;background:rgba(255,255,255,0.45);color:#1e3a5f;border-radius:4px;padding:1px 5px;margin-left:5px;vertical-align:middle;">2hr LAB</span>`
            : "";
          cellsHtml += `
            <td class="period-cell"${colspanAttr}>
              <div class="schedule-pill ${colorClass}">
                <div class="pill-subject" title="${this.escapeHtml(slot.subject_name)}">${this.escapeHtml(slot.subject_name)}${labBadge}</div>
                <div class="pill-sub" title="${classLabel}">${classLabel}</div>
              </div>
            </td>`;
        }
      });

      tbodyHtml += `<tr><td class="saas-day-cell">${day}</td>${cellsHtml}</tr>`;
    });

    const isPt       = fac.work_type === "part_time";
    const workLabel  = isPt ? "Part-Time · Periods 1–4" : "Full-Time · All Periods";
    const badgeColor = isPt ? "#fef3c7;color:#92400e" : "#dcfce7;color:#166534";

    return `
      <div class="saas-table-card">
        <!-- Printable Institution Header (Only rendered when printing) -->
        <div class="print-only-banner">
          <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:1.5px solid #0f172a;padding-bottom:5px;margin-bottom:6px;">
            <div style="display:flex;align-items:center;gap:10px;">
              <img src="/static/images/info-logo.png" style="height:36px;width:auto;" alt="INFO Logo">
              <div>
                <div style="font-size:12pt;font-weight:800;letter-spacing:0.3px;color:#0f172a;line-height:1.1;">INFO INSTITUTE OF ENGINEERING</div>
                <div style="font-size:6.5pt;color:#334155;font-weight:600;line-height:1.1;">(An Autonomous Institution | Approved by AICTE, New Delhi | Affiliated to Anna University, Chennai)</div>
                <div style="font-size:7.5pt;color:#1e3a8a;font-weight:700;margin-top:1px;">DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING</div>
              </div>
            </div>
            <div style="display:flex;gap:6px;align-items:center;">
              <img src="/static/images/logo-anna-university.png" style="height:30px;width:auto;" alt="Anna Univ">
              <img src="/static/images/logo-aicte.png" style="height:30px;width:auto;" alt="AICTE">
              <img src="/static/images/logo-naac.png" style="height:30px;width:auto;" alt="NAAC">
            </div>
          </div>
        </div>

        <!-- Faculty Card Top Header with Actions -->
        <div class="timetable-card-top">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:34px;height:34px;border-radius:50%;background:#eff6ff;display:flex;align-items:center;justify-content:center;font-size:16px;">👤</div>
            <div>
              <div style="font-weight:800;font-size:14.5px;color:#0f172a;">${this.escapeHtml(fac.name)}</div>
              <div style="font-size:11.5px;color:#64748b;">${this.escapeHtml(fac.department || "")}</div>
            </div>
          </div>
          <span style="font-size:11.5px;font-weight:600;background:${badgeColor};padding:3px 10px;border-radius:16px;">
            ${workLabel}
          </span>
          <span style="font-size:11.5px;color:#64748b;font-weight:500;">
            ${fac.assigned_periods} / ${fac.weekly_period_limit} periods/wk
          </span>
          <div class="timetable-card-actions" style="margin-left:auto;">
            <button class="btn" onclick="App.printFacultyTimetable()" title="Print Faculty Timetable">
              🖨️ Print
            </button>
            <button class="btn" onclick="App.downloadFacultyTimetableCsv(${fac.id})" title="Download CSV">
              📥 CSV
            </button>
          </div>
        </div>

        <div class="table-scroll-wrapper">
          <table class="saas-schedule-table">
            <thead>${theadHtml}</thead>
            <tbody>${tbodyHtml}</tbody>
          </table>
        </div>

        <!-- Faculty Signatures on Print -->
        <div class="print-signatures">
          <div>Faculty Signature</div>
          <div>Time Table Coordinator</div>
          <div>Head of Department (HOD)</div>
          <div>Principal</div>
        </div>
      </div>`;
  },

  renderFacultyTable() {
    const tbody = document.getElementById("faculty-table-body");
    if (!tbody) return;

    tbody.innerHTML = "";
    if (this.faculty.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--slate-500);">No faculty members registered. Add instructors above.</td></tr>`;
      return;
    }

    this.faculty.forEach((f) => {
      const isPt = f.work_type === "part_time";
      const windowStr = isPt ? "09:00 AM - 12:30 PM (Periods 1–4)" : "09:00 AM - 04:45 PM (Periods 1–8)";
      const assigned = f.assigned_periods || 0;
      const limit = f.weekly_period_limit || (isPt ? 12 : 40);
      const pct = Math.min(100, Math.round((assigned / limit) * 100));

      let barClass = "";
      if (pct >= 100) barClass = "full";
      else if (pct >= 80) barClass = "warning";

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${this.escapeHtml(f.name)}</strong></td>
        <td>${this.escapeHtml(f.department)}</td>
        <td>
          <span class="badge ${isPt ? "badge-pt" : "badge-ft"}">
            ${isPt ? "Part-Time" : "Full-Time"}
          </span>
        </td>
        <td style="font-size: 0.82rem; font-family: var(--font-mono);">${windowStr}</td>
        <td>
          <div style="font-weight: 600;">${assigned} / ${limit} periods/wk</div>
          <div class="progress-track">
            <div class="progress-fill ${barClass}" style="width: ${pct}%;"></div>
          </div>
        </td>
        <td>
          <span style="font-size: 0.8rem; font-weight: 600; color: ${assigned > 0 ? "var(--success)" : "var(--slate-400)"};">
            ${assigned > 0 ? "● Assigned" : "○ Available"}
          </span>
        </td>
        <td class="text-right">
          <div class="btn-group" style="justify-content: flex-end;">
            <button class="btn btn-outline btn-sm" onclick="App.openEditFacultyModal(${f.id})">Edit</button>
            <button class="btn btn-danger-outline btn-sm" onclick="App.deleteFaculty(${f.id})">Delete</button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  },

  openAddFacultyModal() {
    document.getElementById("modal-faculty-title").textContent = "Add Faculty Member";
    document.getElementById("faculty-id").value = "";
    document.getElementById("faculty-name").value = "";
    document.getElementById("faculty-dept").value = "";
    document.getElementById("faculty-work-type").value = "full_time";
    document.getElementById("faculty-weekly-limit").value = 40;
    this.onFacultyWorkTypeChange();
    document.getElementById("modal-faculty").style.display = "flex";
  },

  openEditFacultyModal(id) {
    const f = this.faculty.find((item) => item.id === id);
    if (!f) return;

    document.getElementById("modal-faculty-title").textContent = "Edit Faculty Member";
    document.getElementById("faculty-id").value = f.id;
    document.getElementById("faculty-name").value = f.name;
    document.getElementById("faculty-dept").value = f.department;
    document.getElementById("faculty-work-type").value = f.work_type;
    document.getElementById("faculty-weekly-limit").value = f.weekly_period_limit;
    this.onFacultyWorkTypeChange();
    document.getElementById("modal-faculty").style.display = "flex";
  },

  onFacultyWorkTypeChange() {
    const wtype = document.getElementById("faculty-work-type").value;
    const limitInput = document.getElementById("faculty-weekly-limit");
    const help = document.getElementById("faculty-limit-help");

    if (wtype === "part_time") {
      help.textContent = "(Fixed Half-Day Window: 09:00 - 12:30. Default: 12 periods/wk)";
      if (!document.getElementById("faculty-id").value) {
        limitInput.value = 12;
      }
    } else {
      help.textContent = "(Full-Day Window: 09:00 - 16:45. Default: 40 periods/wk, max 8/day)";
      if (!document.getElementById("faculty-id").value) {
        limitInput.value = 40;
      }
    }
  },

  async saveFaculty(event) {
    event.preventDefault();
    const id = document.getElementById("faculty-id").value;
    const name = document.getElementById("faculty-name").value.trim();
    const department = document.getElementById("faculty-dept").value.trim();
    const work_type = document.getElementById("faculty-work-type").value;
    const weekly_period_limit = parseInt(document.getElementById("faculty-weekly-limit").value, 10);

    const payload = { name, department, work_type, weekly_period_limit };
    const url = id ? `/api/faculty/${id}` : "/api/faculty";
    const method = id ? "PUT" : "POST";

    try {
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (res.ok) {
        this.closeModals();
        this.showToast(data.message, "success");
        if (data.regeneration && !data.regeneration.success) {
          this.showToast(data.regeneration.message, "warning");
        }
        await this.refreshAllData();
        this.renderFacultyTable();
        this.renderTimetable();
        this.renderClassesAndSubjects();
      } else {
        this.showToast(data.error || "Failed to save faculty.", "error");
      }
    } catch (err) {
      console.error(err);
      this.showToast("Network error while saving faculty.", "error");
    }
  },

  async deleteFaculty(id) {
    const f = this.faculty.find((item) => item.id === id);
    if (!f) return;
    if (!confirm(`Are you sure you want to delete faculty member '${f.name}'?\nTimetable will automatically adjust.`)) {
      return;
    }

    try {
      const res = await fetch(`/api/faculty/${id}`, { method: "DELETE" });
      const data = await res.json();
      if (res.ok) {
        this.showToast(data.message, "success");
        await this.refreshAllData();
        this.renderFacultyTable();
        this.renderTimetable();
        this.renderClassesAndSubjects();
      } else {
        this.showToast(data.error || "Failed to delete faculty.", "error");
      }
    } catch (err) {
      console.error(err);
      this.showToast("Network error while deleting faculty.", "error");
    }
  },

  // -------------------------------------------------------------------------
  // Classes & Subjects Management
  // -------------------------------------------------------------------------
  renderClassesAndSubjects() {
    const container = document.getElementById("classes-list-container");
    if (!container) return;

    container.innerHTML = "";
    if (this.classes.length === 0) {
      container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--slate-500);">No classes found. Click "New Class" to add one.</div>`;
      return;
    }

    this.classes.forEach((c) => {
      const classSubjects = this.subjects.filter((s) => s.class_id === c.id);
      const totalPeriods = classSubjects.reduce((acc, s) => acc + s.periods_per_week, 0);

      const card = document.createElement("div");
      card.className = "class-card";

      let subjectsHtml = "";
      if (classSubjects.length === 0) {
        subjectsHtml = `<div style="text-align: center; padding: 1rem; color: var(--slate-400); font-style: italic;">No subjects assigned yet.</div>`;
      } else {
        subjectsHtml = classSubjects
          .map((s) => {
            const fac = s.faculty_name
              ? `${s.faculty_name} (${s.faculty_work_type === "part_time" ? "PT" : "FT"})`
              : "Dynamic Faculty Pool";
            return `
              <div class="subject-item">
                <div class="subject-item-left">
                  <span class="subject-item-name">${this.escapeHtml(s.name)} [${this.escapeHtml(s.code)}]</span>
                  <span class="subject-item-meta">${fac}</span>
                </div>
                <div class="subject-item-right">
                  <span class="badge badge-info">${s.periods_per_week} p/wk</span>
                  <button class="btn btn-outline btn-sm" onclick="App.openEditSubjectModal(${s.id})">Edit</button>
                  <button class="btn btn-danger-outline btn-sm" onclick="App.deleteSubject(${s.id})">×</button>
                </div>
              </div>
            `;
          })
          .join("");
      }

      card.innerHTML = `
        <div class="class-card-header">
          <div>
            <div class="class-title">${this.escapeHtml(c.name)}</div>
            <div class="text-muted" style="font-size: 0.8rem;">${totalPeriods} / 40 periods filled per week</div>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="class-code">${this.escapeHtml(c.code)}</span>
            <button class="btn btn-danger-outline btn-sm" title="Delete Class" onclick="App.deleteClass(${c.id})">🗑️</button>
          </div>
        </div>
        <div style="flex: 1;">
          ${subjectsHtml}
        </div>
      `;
      container.appendChild(card);
    });
  },

  openAddClassModal() {
    document.getElementById("class-name").value = "";
    document.getElementById("class-code").value = "";
    document.getElementById("modal-class").style.display = "flex";
  },

  async saveClass(event) {
    event.preventDefault();
    const name = document.getElementById("class-name").value.trim();
    const code = document.getElementById("class-code").value.trim();

    try {
      const res = await fetch("/api/classes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, code }),
      });
      const data = await res.json();
      if (res.ok) {
        this.closeModals();
        this.showToast(data.message, "success");
        await this.refreshAllData();
        this.populateClassDropdown();
        this.renderClassesAndSubjects();
        this.renderTimetable();
      } else {
        this.showToast(data.error || "Failed to create class.", "error");
      }
    } catch (err) {
      console.error(err);
      this.showToast("Network error while creating class.", "error");
    }
  },

  async deleteClass(id) {
    const c = this.classes.find((item) => item.id === id);
    if (!c) return;
    if (!confirm(`Are you sure you want to delete class '${c.name}'?\nAll its subjects and schedule entries will be removed.`)) {
      return;
    }

    try {
      const res = await fetch(`/api/classes/${id}`, { method: "DELETE" });
      const data = await res.json();
      if (res.ok) {
        this.showToast(data.message, "success");
        await this.refreshAllData();
        this.populateClassDropdown();
        this.renderClassesAndSubjects();
        this.renderTimetable();
      } else {
        this.showToast(data.error || "Failed to delete class.", "error");
      }
    } catch (err) {
      console.error(err);
      this.showToast("Network error while deleting class.", "error");
    }
  },

  openAddSubjectModal() {
    document.getElementById("modal-subject-title").textContent = "Add Subject";
    document.getElementById("subject-id").value = "";
    document.getElementById("subject-name").value = "";
    document.getElementById("subject-code").value = "";
    document.getElementById("subject-periods-per-week").value = "4";

    this.populateSubjectModalOptions();
    if (this.selectedClassId) {
      document.getElementById("subject-class-id").value = this.selectedClassId;
    }
    document.getElementById("modal-subject").style.display = "flex";
  },

  openEditSubjectModal(id) {
    const s = this.subjects.find((item) => item.id === id);
    if (!s) return;

    document.getElementById("modal-subject-title").textContent = "Edit Subject";
    document.getElementById("subject-id").value = s.id;
    document.getElementById("subject-name").value = s.name;
    document.getElementById("subject-code").value = s.code;
    document.getElementById("subject-periods-per-week").value = s.periods_per_week;

    this.populateSubjectModalOptions();
    document.getElementById("subject-class-id").value = s.class_id;
    document.getElementById("subject-faculty-id").value = s.faculty_id || "";

    document.getElementById("modal-subject").style.display = "flex";
  },

  populateSubjectModalOptions() {
    const classSelect = document.getElementById("subject-class-id");
    classSelect.innerHTML = "";
    this.classes.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = `${c.name} (${c.code})`;
      classSelect.appendChild(opt);
    });

    const facSelect = document.getElementById("subject-faculty-id");
    facSelect.innerHTML = `<option value="">-- Dynamic Pool Assignment (Any eligible faculty) --</option>`;
    this.faculty.forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f.id;
      const wtype = f.work_type === "part_time" ? "Part-Time" : "Full-Time";
      opt.textContent = `${f.name} (${wtype} • ${f.department})`;
      facSelect.appendChild(opt);
    });
  },

  async saveSubject(event) {
    event.preventDefault();
    const id = document.getElementById("subject-id").value;
    const class_id = parseInt(document.getElementById("subject-class-id").value, 10);
    const name = document.getElementById("subject-name").value.trim();
    const code = document.getElementById("subject-code").value.trim();
    const periods_per_week = parseInt(document.getElementById("subject-periods-per-week").value, 10);
    const faculty_id = document.getElementById("subject-faculty-id").value || null;

    const payload = { class_id, name, code, periods_per_week, faculty_id };
    const url = id ? `/api/subjects/${id}` : "/api/subjects";
    const method = id ? "PUT" : "POST";

    try {
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok) {
        this.closeModals();
        this.showToast(data.message, "success");
        if (data.regeneration && !data.regeneration.success) {
          this.showToast(data.regeneration.message, "warning");
        }
        await this.refreshAllData();
        this.renderClassesAndSubjects();
        this.renderTimetable();
        this.renderFacultyTable();
      } else {
        this.showToast(data.error || "Failed to save subject.", "error");
      }
    } catch (err) {
      console.error(err);
      this.showToast("Network error while saving subject.", "error");
    }
  },

  async deleteSubject(id) {
    const s = this.subjects.find((item) => item.id === id);
    if (!s) return;
    if (!confirm(`Are you sure you want to delete subject '${s.name}'? Timetable will adjust.`)) {
      return;
    }

    try {
      const res = await fetch(`/api/subjects/${id}`, { method: "DELETE" });
      const data = await res.json();
      if (res.ok) {
        this.showToast(data.message, "success");
        await this.refreshAllData();
        this.renderClassesAndSubjects();
        this.renderTimetable();
        this.renderFacultyTable();
      } else {
        this.showToast(data.error || "Failed to delete subject.", "error");
      }
    } catch (err) {
      console.error(err);
      this.showToast("Network error while deleting subject.", "error");
    }
  },

  // -------------------------------------------------------------------------
  // Modals & UI Utilities
  // -------------------------------------------------------------------------
  closeModals() {
    document.querySelectorAll(".modal-overlay").forEach((m) => (m.style.display = "none"));
  },

  showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    let icon = "ℹ️";
    if (type === "success") icon = "✓";
    else if (type === "error") icon = "✕";
    else if (type === "warning") icon = "⚠️";

    toast.innerHTML = `
      <span style="font-weight: 800; font-size: 1rem;">${icon}</span>
      <div style="flex: 1;">${this.escapeHtml(message)}</div>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.transition = "opacity 0.3s ease, transform 0.3s ease";
      toast.style.opacity = "0";
      toast.style.transform = "translateX(50px)";
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  },

  escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },
};

// Start application when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  App.init();
});


// Global listener to dismiss dropdowns when clicking outside
document.addEventListener("click", (e) => {
  if (!e.target.closest(".dropdown-wrapper")) {
    const menu = document.getElementById("timetable-download-dropdown");
    if (menu) menu.style.display = "none";
  }
});
