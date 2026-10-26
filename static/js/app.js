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
  selectedSemester: "all",   // "all" | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8
  viewMode: "single", // "single" | "dual" | "all"
  dualLayout: "stacked", // "stacked" | "split"
  isFitToScreen: true, // Default to full-width fit to screen
  // Swap Mode State
  isSwapMode: false,
  selectedSourceSlot: null, // { classId, entryId, day, periodNum, subjectName, facultyName, element }
  // Auth state
  authMode: "login", // "login" | "signup"
  // -------------------------------------------------------------------------
  // Initialization
  // -------------------------------------------------------------------------
  async init() {
    // Check auth state first — if not logged in show the auth card
    const authed = this.checkAuthStatus();
    if (!authed) return; // Dashboard init deferred until after login
    await this.initDashboard();
  },

  async initDashboard() {
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

    // Populate class selectors according to selectedSemester
    this.populateClassSelectors();
  },

  getFilteredClasses() {
    if (!this.selectedSemester || this.selectedSemester === "all") {
      return this.classes;
    }
    const targetSem = parseInt(this.selectedSemester, 10);
    return this.classes.filter((c) => parseInt(c.semester, 10) === targetSem);
  },

  populateClassSelectors() {
    const filtered = this.getFilteredClasses();
    const globalSelect = document.getElementById("global-class-select");
    const globalSelect2 = document.getElementById("global-class-select-2");

    if (filtered.length > 0) {
      if (!this.selectedClassId1 || !filtered.some((c) => c.id === this.selectedClassId1)) {
        this.selectedClassId1 = filtered[0].id;
        this.selectedClassId = filtered[0].id;
      }
      if (!this.selectedClassId2 || !filtered.some((c) => c.id === this.selectedClassId2)) {
        this.selectedClassId2 = filtered.length > 1 ? filtered[1].id : filtered[0].id;
      }
    } else {
      this.selectedClassId = null;
      this.selectedClassId1 = null;
      this.selectedClassId2 = null;
    }

    if (globalSelect) {
      if (filtered.length > 0) {
        globalSelect.innerHTML = filtered
          .map((c) => `<option value="${c.id}" ${c.id === this.selectedClassId1 ? "selected" : ""}>${this.escapeHtml(c.name)} (${this.escapeHtml(c.code)}) [Sem ${c.semester || 1}]</option>`)
          .join("");
      } else {
        globalSelect.innerHTML = `<option value="">— No Classes in this Semester —</option>`;
      }
    }

    if (globalSelect2) {
      if (filtered.length > 0) {
        globalSelect2.innerHTML = filtered
          .map((c) => `<option value="${c.id}" ${c.id === this.selectedClassId2 ? "selected" : ""}>${this.escapeHtml(c.name)} (${this.escapeHtml(c.code)}) [Sem ${c.semester || 1}]</option>`)
          .join("");
      } else {
        globalSelect2.innerHTML = `<option value="">— No Classes —</option>`;
      }
      globalSelect2.style.display = this.viewMode === "dual" ? "" : "none";
    }
  },

  onSemesterChange(semValue) {
    this.selectedSemester = semValue;
    this.populateClassSelectors();
    this.renderTimetable();
  },

  // -------------------------------------------------------------------------
  // Tab Navigation
  // -------------------------------------------------------------------------
  switchTab(tabId) {
    // Robust alias resolution for tabs
    let targetId = tabId;
    if (tabId === "tab-exam-seating" || tabId === "exam-seating-tab") {
      targetId = "exam-seating-tab";
    } else if (tabId === "tab-my-schedule") {
      targetId = "tab-timetable";
    }

    document.querySelectorAll(".tab-btn, .saas-nav-item").forEach((btn) => {
      const bTab = btn.dataset.tab;
      const isActive = bTab === targetId ||
        (targetId === "exam-seating-tab" && (bTab === "exam-seating-tab" || bTab === "tab-exam-seating"));
      btn.classList.toggle("active", isActive);
    });

    document.querySelectorAll(".tab-pane").forEach((pane) => {
      const isTarget = pane.id === targetId ||
        (targetId === "exam-seating-tab" && (pane.id === "exam-seating-tab" || pane.id === "tab-exam-seating"));
      pane.classList.toggle("active", isTarget);
    });

    if (targetId === "exam-seating-tab") {
      this.loadExamSeating();
    }
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

  downloadTimetableExcel(classId) {
    const cid = classId || this.selectedClassId1 || this.selectedClassId || (this.classes[0]?.id);
    if (!cid) {
      this.showToast("No class selected to download.", "warning");
      return;
    }
    window.location.href = `/api/export/timetable/excel?class_id=${cid}`;
    this.showToast("Downloading class timetable Excel (.xlsx)...", "info");
  },

  downloadAllTimetablesExcel() {
    window.location.href = `/api/export/timetable/excel?all=true`;
    this.showToast("Downloading all class timetables Excel (.xlsx)...", "info");
  },

  downloadTimetablePdf(classId) {
    const cid = classId || this.selectedClassId1 || this.selectedClassId || (this.classes[0]?.id);
    if (!cid) {
      this.showToast("No class selected to download.", "warning");
      return;
    }
    window.location.href = `/api/export/timetable/pdf?class_id=${cid}`;
    this.showToast("Downloading class timetable PDF (.pdf)...", "info");
  },

  downloadAllTimetablesPdf() {
    window.location.href = `/api/export/timetable/pdf?all=true`;
    this.showToast("Downloading all class timetables PDF (.pdf)...", "info");
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

  downloadFacultyTimetableExcel(facultyId) {
    const fid = facultyId || this.selectedFacultyId;
    if (!fid) {
      this.showToast("Please select a faculty member first.", "warning");
      return;
    }
    window.location.href = `/api/export/faculty/excel?faculty_id=${fid}`;
    this.showToast("Downloading faculty schedule Excel (.xlsx)...", "info");
  },

  downloadFacultyTimetablePdf(facultyId) {
    const fid = facultyId || this.selectedFacultyId;
    if (!fid) {
      this.showToast("Please select a faculty member first.", "warning");
      return;
    }
    window.location.href = `/api/export/faculty/pdf?faculty_id=${fid}`;
    this.showToast("Downloading faculty schedule PDF (.pdf)...", "info");
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

    const filteredClasses = this.getFilteredClasses();
    if (filteredClasses.length === 0) {
      const semText = this.selectedSemester !== "all" ? ` for Semester ${this.selectedSemester}` : "";
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 3rem; color: var(--slate-500);">
          No classes registered${semText}. Select "All Semesters" or create a class in the "Subjects" tab.
        </div>
      `;
      return;
    }

    let cardsHtml = "";

    if (this.viewMode === "dual") {
      // Show 2 Timetables on the same page
      const id1 = this.selectedClassId1 || filteredClasses[0]?.id;
      const id2 = this.selectedClassId2 || (filteredClasses.length > 1 ? filteredClasses[1].id : filteredClasses[0].id);
      cardsHtml += this.buildTimetableCardHtml(id1, "Timetable 1", 1);
      cardsHtml += this.buildTimetableCardHtml(id2, "Timetable 2", 2);
    } else if (this.viewMode === "all") {
      // Show All classes in current semester filter
      filteredClasses.forEach((c, index) => {
        cardsHtml += this.buildTimetableCardHtml(c.id, `Class ${index + 1}`, index + 1);
      });
    } else {
      // Single Timetable
      const id = this.selectedClassId || filteredClasses[0]?.id;
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
          const swapClickEmpty = this.isSwapMode
            ? `onclick="App.handleSlotClick(null, '${day}', ${period.num}, ${cls.id}, '', this)" style="cursor:crosshair;"`
            : ``;
          cellsHtml += `<td class="period-cell" ${swapClickEmpty} style="text-align: center;"><span class="schedule-empty">–</span></td>`;
        } else {
          const colorClass = getColorForSubject(slot.subject_name, slot.subject_code);
          const facultyTooltip = slot.faculty_name ? `Faculty: ${slot.faculty_name}` : "";
          const fullTitle = `${slot.subject_name}${facultyTooltip ? ' • ' + facultyTooltip : ''}`;
          const colspanAttr = isLabBlock ? ` colspan="2"` : ``;
          const labBadge = isLabBlock
            ? `<span style="display:inline-block;font-size:9px;font-weight:700;letter-spacing:0.5px;background:rgba(255,255,255,0.55);color:#1e3a5f;border-radius:4px;padding:2px 6px;margin-left:6px;vertical-align:middle;">2hr LAB</span>`
            : ``;
          const swapClick = this.isSwapMode
            ? `onclick="App.handleSlotClick(${slot.entry_id || 'null'}, '${day}', ${period.num}, ${cls.id}, '${(slot.subject_name || '').replace(/'/g, '\\&apos;')}', this)" style="cursor:pointer;"`
            : ``;
          cellsHtml += `
            <td class="period-cell${this.isSwapMode ? ' slot-swappable' : ''}"${colspanAttr} ${swapClick}>
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
            <span style="font-size:11.5px;background:#e0e7ff;color:#3730a3;font-weight:700;padding:2px 9px;border-radius:12px;border:1px solid #c7d2fe;">Semester ${cls.semester || 1}</span>
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
            <button class="btn btn-sm" onclick="App.downloadTimetableExcel(${cls.id})" title="Export Excel (.xlsx) for this class" style="color:#16a34a;">
              <span>📊</span>
              <span>Excel</span>
            </button>
            <button class="btn btn-sm" onclick="App.downloadTimetablePdf(${cls.id})" title="Export PDF (.pdf) for this class" style="color:#dc2626;">
              <span>📕</span>
              <span>PDF</span>
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
            <button class="btn" onclick="App.downloadFacultyTimetableExcel(${fac.id})" title="Download Excel (.xlsx)" style="color:#16a34a;">
              📊 Excel
            </button>
            <button class="btn" onclick="App.downloadFacultyTimetablePdf(${fac.id})" title="Download PDF (.pdf)" style="color:#dc2626;">
              📕 PDF
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
        <td>${this.escapeHtml(f.department || "—")}</td>
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

    const deptSelect = document.getElementById("faculty-dept");
    const deptVal = f.department || "";
    // If the department from database isn't in predefined options, dynamically add it
    if (deptVal) {
      let found = false;
      for (let i = 0; i < deptSelect.options.length; i++) {
        if (deptSelect.options[i].value.toLowerCase() === deptVal.toLowerCase()) {
          deptSelect.selectedIndex = i;
          found = true;
          break;
        }
      }
      if (!found) {
        const opt = document.createElement("option");
        opt.value = deptVal;
        opt.textContent = deptVal;
        deptSelect.appendChild(opt);
        deptSelect.value = deptVal;
      }
    } else {
      deptSelect.value = "";
    }

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
            <div class="class-title" style="display:flex;align-items:center;gap:8px;">
              <span>${this.escapeHtml(c.name)}</span>
              <span class="badge" style="background:#e0e7ff;color:#3730a3;font-size:11px;">Sem ${c.semester || 1}</span>
            </div>
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
    const semEl = document.getElementById("class-semester");
    if (semEl) semEl.value = "1";
    document.getElementById("modal-class").style.display = "flex";
  },

  async saveClass(event) {
    event.preventDefault();
    const name = document.getElementById("class-name").value.trim();
    const code = document.getElementById("class-code").value.trim();
    const semester = parseInt(document.getElementById("class-semester")?.value || "1", 10);

    try {
      const res = await fetch("/api/classes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, code, semester }),
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

  async loadExamSeating() {
    const tbody = document.getElementById("exam-seating-tbody");
    if (!tbody) return;

    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align:center;padding:2rem;color:#64748b;">
          <div style="display:inline-flex;align-items:center;gap:8px;">
            <span class="spin-icon">⏳</span> Loading examination seating chart...
          </div>
        </td>
      </tr>
    `;

    const defaultAllocations = [
      {
        hall_no: "LH-101",
        date_session: "2026-11-02 (FN)",
        exam_date: "2026-11-02",
        session: "FN",
        subject_name: "Discrete Mathematics",
        subject_code: "MA25C08",
        class_name: "AI & DS - 2nd Year",
        class_code: "AIDS-2",
        roll_number_range: "711122104001 - 711122104030",
        total_students: 30,
        exam_name: "Continuous Internal Assessment (CIA-I)"
      },
      {
        hall_no: "LH-102",
        date_session: "2026-11-03 (AN)",
        exam_date: "2026-11-03",
        session: "AN",
        subject_name: "Data Structures & Algorithms",
        subject_code: "CS25C08",
        class_name: "AI & DS - 2nd Year",
        class_code: "AIDS-2",
        roll_number_range: "711122104031 - 711122104060",
        total_students: 30,
        exam_name: "Continuous Internal Assessment (CIA-I)"
      },
      {
        hall_no: "LH-103",
        date_session: "2026-11-04 (FN)",
        exam_date: "2026-11-04",
        session: "FN",
        subject_name: "Computer Networks",
        subject_code: "IT25C04",
        class_name: "IT - 3rd Year",
        class_code: "IT-3",
        roll_number_range: "711122105001 - 711122105035",
        total_students: 35,
        exam_name: "Continuous Internal Assessment (CIA-I)"
      },
      {
        hall_no: "Auditorium-A",
        date_session: "2026-11-05 (FN)",
        exam_date: "2026-11-05",
        session: "FN",
        subject_name: "Engineering Physics",
        subject_code: "PH25C01",
        class_name: "Science & Humanities - 1st Year",
        class_code: "SH-1",
        roll_number_range: "711123101001 - 711123101050",
        total_students: 50,
        exam_name: "Continuous Internal Assessment (CIA-I)"
      }
    ];

    try {
      const res = await fetch("/api/exam/allocations");
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      const data = await res.json();

      if (Array.isArray(data) && data.length > 0) {
        this.examAllocations = data;
      } else {
        this.examAllocations = defaultAllocations;
      }
    } catch (err) {
      console.warn("Could not fetch remote exam seating; using verified internal records:", err);
      this.examAllocations = defaultAllocations;
    }

    // Update KPI metrics
    const hallsCount = new Set(this.examAllocations.map((d) => d.hall_no).filter(Boolean)).size;
    const totalStudents = this.examAllocations.reduce((acc, d) => acc + (d.total_students || 0), 0);
    const statHalls = document.getElementById("exam-stat-halls");
    const statStudents = document.getElementById("exam-stat-students");
    const statSessions = document.getElementById("exam-stat-sessions");

    if (statHalls) statHalls.textContent = `${hallsCount} Hall${hallsCount !== 1 ? 's' : ''}`;
    if (statStudents) statStudents.textContent = `${totalStudents} Students`;
    if (statSessions && this.examAllocations[0]?.exam_name) {
      statSessions.textContent = this.examAllocations[0].exam_name;
    }

    this.renderExamSeatingTable(this.examAllocations);
  },

  renderExamSeatingTable(list) {
    const tbody = document.getElementById("exam-seating-tbody");
    if (!tbody) return;

    if (!Array.isArray(list) || list.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align:center;padding:2.5rem;color:#64748b;">
            No matching examination seating allocations found.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = list
      .map((item) => {
        const hallNo = this.escapeHtml(item.hall_no || "N/A");
        const dateSession = this.escapeHtml(item.date_session || "N/A");
        const subjName = this.escapeHtml(item.subject_name || "N/A");
        const subjCode = item.subject_code
          ? `<span class="badge" style="background:#eff6ff;color:#1d4ed8;font-size:11px;margin-left:5px;">${this.escapeHtml(item.subject_code)}</span>`
          : "";
        const className = this.escapeHtml(item.class_name || "N/A");
        const classCode = item.class_code
          ? `<span style="font-size:11.5px;color:#64748b;display:block;">(${this.escapeHtml(item.class_code)})</span>`
          : "";
        const rollRange = this.escapeHtml(item.roll_number_range || "N/A");
        const totalStudents = item.total_students || 0;

        return `
          <tr>
            <td style="font-weight:700;color:#0f172a;">
              <span style="display:inline-block;padding:3px 8px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;">
                🏛️ ${hallNo}
              </span>
            </td>
            <td style="font-weight:600;color:#1e293b;">
              📅 ${dateSession}
            </td>
            <td>
              <span style="font-weight:700;color:#0f172a;">${subjName}</span>
              ${subjCode}
            </td>
            <td>
              <span style="font-weight:600;color:#334155;">${className}</span>
              ${classCode}
            </td>
            <td>
              <code style="font-family:'JetBrains Mono',monospace;font-size:12px;background:#f1f5f9;color:#0f172a;padding:3px 8px;border-radius:5px;font-weight:600;">
                ${rollRange}
              </code>
            </td>
            <td style="text-align:center;font-weight:800;color:#2563eb;font-size:13.5px;">
              ${totalStudents}
            </td>
          </tr>
        `;
      })
      .join("");
  },

  filterExamSeating(query) {
    if (!this.examAllocations) return;
    const q = (query || "").trim().toLowerCase();
    if (!q) {
      this.renderExamSeatingTable(this.examAllocations);
      return;
    }
    const filtered = this.examAllocations.filter((item) => {
      const h = (item.hall_no || "").toLowerCase();
      const s = (item.subject_name || "").toLowerCase();
      const sc = (item.subject_code || "").toLowerCase();
      const c = (item.class_name || "").toLowerCase();
      const cc = (item.class_code || "").toLowerCase();
      const r = (item.roll_number_range || "").toLowerCase();
      return h.includes(q) || s.includes(q) || sc.includes(q) || c.includes(q) || cc.includes(q) || r.includes(q);
    });
    this.renderExamSeatingTable(filtered);
  },

  openAddExamAllocationModal() {
    const modal = document.getElementById("modal-exam-allocation");
    if (!modal) return;

    const classSelect = document.getElementById("exam-alloc-class");
    if (classSelect) {
      classSelect.innerHTML = this.classes
        .map((c) => `<option value="${c.id}">${this.escapeHtml(c.name)} (${this.escapeHtml(c.code)})</option>`)
        .join("");
    }

    const dateInput = document.getElementById("exam-alloc-date");
    if (dateInput && !dateInput.value) {
      dateInput.value = new Date().toISOString().split("T")[0];
    }

    modal.style.display = "flex";
  },

  async saveExamAllocation(event) {
    event.preventDefault();
    const hall = (document.getElementById("exam-alloc-hall")?.value || "").trim().toUpperCase();
    const date = document.getElementById("exam-alloc-date")?.value || "";
    const session = document.getElementById("exam-alloc-session")?.value || "FN";
    const classId = parseInt(document.getElementById("exam-alloc-class")?.value, 10);
    const subject = (document.getElementById("exam-alloc-subject")?.value || "").trim();
    const rollStart = (document.getElementById("exam-alloc-roll-start")?.value || "").trim();
    const rollEnd = (document.getElementById("exam-alloc-roll-end")?.value || "").trim();
    const count = parseInt(document.getElementById("exam-alloc-count")?.value, 10) || 30;

    const selectedClass = this.classes.find((c) => c.id === classId) || { name: "General Class", code: "GEN" };

    const newRecord = {
      hall_no: hall,
      date_session: `${date} (${session})`,
      exam_date: date,
      session: session,
      subject_name: subject,
      subject_code: "",
      class_name: selectedClass.name,
      class_code: selectedClass.code,
      roll_number_range: `${rollStart} - ${rollEnd}`,
      roll_no_start: rollStart,
      roll_no_end: rollEnd,
      total_students: count,
      exam_name: "Continuous Internal Assessment"
    };

    if (!Array.isArray(this.examAllocations)) {
      this.examAllocations = [];
    }
    this.examAllocations.unshift(newRecord);
    this.renderExamSeatingTable(this.examAllocations);

    // Update KPI metrics
    const hallsCount = new Set(this.examAllocations.map((d) => d.hall_no).filter(Boolean)).size;
    const totalStudents = this.examAllocations.reduce((acc, d) => acc + (d.total_students || 0), 0);
    const statHalls = document.getElementById("exam-stat-halls");
    const statStudents = document.getElementById("exam-stat-students");
    if (statHalls) statHalls.textContent = `${hallsCount} Halls`;
    if (statStudents) statStudents.textContent = `${totalStudents} Students`;

    this.closeModals();
    this.showToast(`Exam allocation for Hall ${hall} added successfully!`, "success");
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

  // -------------------------------------------------------------------------
  // Interactive Timetable Slot Swapping
  // -------------------------------------------------------------------------

  /**
   * Toggle Swap Mode on/off.
   * When active, clicking timetable slots picks source → target and calls the swap API.
   */
  toggleSwapMode() {
    this.isSwapMode = !this.isSwapMode;
    this.selectedSourceSlot = null;

    const btn = document.getElementById("btn-toggle-swap-mode");
    const txt = document.getElementById("btn-swap-mode-text");
    if (btn) btn.classList.toggle("active", this.isSwapMode);
    if (txt) txt.textContent = this.isSwapMode ? "⛔ Exit Swap Mode" : "🔃 Swap Mode";

    // Re-render timetable so slot click handlers are wired up
    this.renderTimetable();

    if (this.isSwapMode) {
      this.showToast("Swap Mode ON – click a source slot, then a target slot.", "info");
    } else {
      this.showToast("Swap Mode OFF.", "info");
    }
  },

  /**
   * Called when a slot cell is clicked while swap mode is active.
   * Manages the source → target selection flow and calls performSlotSwap().
   *
   * @param {number} entryId   - timetable_entries.id of the clicked slot
   * @param {string} day       - Day string e.g. "Monday"
   * @param {number} periodNum - Period number 1–8
   * @param {number} classId   - Class id
   * @param {string} subjectName - Display label for toasts
   * @param {HTMLElement} el   - The clicked <td> element
   */
  handleSlotClick(entryId, day, periodNum, classId, subjectName, el) {
    if (!this.isSwapMode) return;

    if (!this.selectedSourceSlot) {
      // === Phase 1: select source ===
      if (!entryId) {
        this.showToast("Please select a filled slot as the source.", "warning");
        return;
      }
      this.selectedSourceSlot = { entryId, day, periodNum, classId, subjectName, element: el };
      el.classList.add("slot-selected");
      this.showToast(`Source selected: "${subjectName}" on ${day} P${periodNum}. Now click the target slot.`, "info");
    } else {
      // === Phase 2: select target & swap ===
      if (
        this.selectedSourceSlot.entryId === entryId &&
        this.selectedSourceSlot.classId === classId
      ) {
        // Same slot clicked — deselect
        this.selectedSourceSlot.element?.classList.remove("slot-selected");
        this.selectedSourceSlot = null;
        this.showToast("Source deselected. Click a new source slot.", "info");
        return;
      }

      this.performSlotSwap(this.selectedSourceSlot, { entryId, day, periodNum, classId, element: el });
    }
  },

  /**
   * Calls the /api/timetable/swap endpoint and handles the response.
   *
   * @param {object} src  - { entryId, day, periodNum, classId, subjectName, element }
   * @param {object} tgt  - { entryId, day, periodNum, classId, element }
   */
  async performSlotSwap(src, tgt) {
    // Build payload
    let payload;
    if (tgt.entryId) {
      // Swap two filled slots
      payload = { source_entry_id: src.entryId, target_entry_id: tgt.entryId };
    } else {
      // Move source to empty slot
      payload = { source_entry_id: src.entryId, target_day: tgt.day, target_period: tgt.periodNum };
    }

    // Visual "pending" state
    src.element?.classList.add("slot-swappable");
    tgt.element?.classList.add("slot-swappable");

    try {
      const res = await fetch("/api/timetable/swap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (res.ok && data.success) {
        // === Success ===
        this.showToast(data.message || "Slot swapped successfully!", "success");
        // Refresh timetable data and re-render
        await this.refreshAllData();
        this.renderTimetable();
        this.renderFacultyTable();
      } else {
        // === Conflict ===
        src.element?.classList.remove("slot-swappable");
        tgt.element?.classList.remove("slot-swappable");
        src.element?.classList.add("slot-conflict");
        tgt.element?.classList.add("slot-conflict");
        // Remove conflict highlight after animation
        setTimeout(() => {
          src.element?.classList.remove("slot-conflict", "slot-selected");
          tgt.element?.classList.remove("slot-conflict");
        }, 1400);
        this.showToast("⚠️ " + (data.message || data.error || "Swap conflict detected."), "error");
      }
    } catch (err) {
      console.error("Swap error:", err);
      src.element?.classList.remove("slot-swappable", "slot-selected");
      tgt.element?.classList.remove("slot-swappable");
      this.showToast("Network error during slot swap.", "error");
    } finally {
      // Reset source selection
      this.selectedSourceSlot = null;
    }
  },
};

// Start application when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  App.init();
});

// -------------------------------------------------------------------------
// Auth Methods (appended to App object at module level)
// -------------------------------------------------------------------------
Object.assign(App, {

  /**
   * Checks localStorage for a session token.
   * Shows dashboard if authenticated, auth card otherwise.
   * Returns true if authenticated.
   */
  checkAuthStatus() {
    const token = localStorage.getItem("auth_token");
    const email = localStorage.getItem("auth_email");

    if (token && email) {
      this._showDashboard(email);
      return true;
    } else {
      this._showAuthCard();
      return false;
    }
  },

  /** Reveals the auth login/signup card and hides the dashboard */
  _showAuthCard() {
    const authContainer = document.getElementById("auth-container");
    const dashboard = document.getElementById("main-dashboard-container");
    const userChip = document.getElementById("auth-user-chip");
    if (authContainer) authContainer.style.display = "flex";
    if (dashboard) dashboard.style.display = "none";
    if (userChip) userChip.style.display = "none";
  },

  /** Reveals the main dashboard and hides the auth card */
  _showDashboard(email) {
    const authContainer = document.getElementById("auth-container");
    const dashboard = document.getElementById("main-dashboard-container");
    const userChip = document.getElementById("auth-user-chip");
    const userEmailEl = document.getElementById("auth-user-email");
    if (authContainer) authContainer.style.display = "none";
    if (dashboard) dashboard.style.display = "block";
    if (userChip) userChip.style.display = "flex";
    if (userEmailEl) userEmailEl.textContent = email || "";

    // Sync profile dropdown headers
    const pEmail = document.getElementById("profile-dropdown-email");
    const pName = document.getElementById("profile-dropdown-name");
    const modalEmail = document.getElementById("modal-profile-email");
    if (pEmail) pEmail.textContent = email || "staff@info.ac.in";
    if (modalEmail) modalEmail.textContent = email || "staff@info.ac.in";
    if (pName && email) {
      const u = email.split("@")[0];
      pName.textContent = u.charAt(0).toUpperCase() + u.slice(1);
    }
  },

  /** Toggles the user profile dropdown menu in the top bar */
  toggleProfileDropdown(event) {
    if (event && event.stopPropagation) {
      event.stopPropagation();
    }
    const dropdown = document.getElementById("user-profile-dropdown");
    const avatarBtn = document.getElementById("btn-user-avatar");
    if (!dropdown) return;

    const isVisible = dropdown.style.display === "block";
    dropdown.style.display = isVisible ? "none" : "block";
    if (avatarBtn) {
      avatarBtn.classList.toggle("active", !isVisible);
      avatarBtn.setAttribute("aria-expanded", String(!isVisible));
    }

    if (!isVisible) {
      // Close timetable download dropdown if open
      const dlMenu = document.getElementById("timetable-download-dropdown");
      if (dlMenu) dlMenu.style.display = "none";

      // Sync active user details
      const email = localStorage.getItem("auth_email") || "staff@info.ac.in";
      const nameEl = document.getElementById("profile-dropdown-name");
      const emailEl = document.getElementById("profile-dropdown-email");
      if (emailEl) emailEl.textContent = email;
      if (nameEl && email) {
        const username = email.split("@")[0];
        nameEl.textContent = username.charAt(0).toUpperCase() + username.slice(1);
      }
    }
  },

  /** Opens the comprehensive Account & Profile modal */
  openProfileModal() {
    this.closeModals();
    const modal = document.getElementById("modal-profile");
    if (!modal) return;

    const email = localStorage.getItem("auth_email") || "staff@info.ac.in";
    const emailEl = document.getElementById("modal-profile-email");
    const classesEl = document.getElementById("modal-profile-classes-count");
    const facultyEl = document.getElementById("modal-profile-faculty-count");

    if (emailEl) emailEl.textContent = email;
    if (classesEl) classesEl.textContent = `${this.classes.length || 0} Classes`;
    if (facultyEl) facultyEl.textContent = `${this.faculty.length || 0} Members`;

    modal.style.display = "flex";
  },

  /** Handles login OR signup form submission */
  async handleAuthSubmit(event) {
    event.preventDefault();
    const email = (document.getElementById("auth-email")?.value || "").trim();
    const password = document.getElementById("auth-password")?.value || "";

    // Hide previous alerts
    this._setAuthAlert("error", "", false);
    this._setAuthAlert("success", "", false);

    if (!email || !password) {
      this._setAuthAlert("error", "Please enter your email and password.", true);
      return;
    }

    const submitBtn = document.getElementById("auth-submit-btn");
    const submitLabel = document.getElementById("auth-submit-label");
    const spinner = document.getElementById("auth-submit-spinner");

    // Loading state
    if (submitBtn) submitBtn.disabled = true;
    if (submitLabel) submitLabel.style.display = "none";
    if (spinner) spinner.style.display = "inline-block";

    try {
      if (this.authMode === "login") {
        const res = await fetch("/api/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        if (res.ok && data.success) {
          localStorage.setItem("auth_token", data.token);
          localStorage.setItem("auth_email", data.email || email);
          this._showDashboard(data.email || email);
          await this.initDashboard();
        } else {
          this._setAuthAlert("error", data.error || "Login failed. Please try again.", true);
        }
      } else {
        // Signup mode
        const res = await fetch("/api/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        if (res.ok && data.success) {
          this._setAuthAlert("success",
            data.message || "Account created! Please check your email to verify, then log in.",
            true
          );
          // Auto-switch to login mode after a short delay
          setTimeout(() => this.toggleAuthMode("login"), 2200);
        } else {
          this._setAuthAlert("error", data.error || "Sign-up failed. Please try again.", true);
        }
      }
    } catch (err) {
      this._setAuthAlert("error", "Network error. Please check your connection and try again.", true);
    } finally {
      if (submitBtn) submitBtn.disabled = false;
      if (submitLabel) submitLabel.style.display = "inline";
      if (spinner) spinner.style.display = "none";
    }
  },

  /** Toggles between login and signup view */
  toggleAuthMode(forceTo) {
    this.authMode = forceTo || (this.authMode === "login" ? "signup" : "login");
    const isSignup = this.authMode === "signup";

    const heading       = document.getElementById("auth-heading");
    const subheading    = document.getElementById("auth-subheading");
    const submitLabel   = document.getElementById("auth-submit-label");
    const toggleQ       = document.getElementById("auth-toggle-question");
    const toggleBtn     = document.getElementById("auth-toggle-btn");
    const pwInput       = document.getElementById("auth-password");

    if (heading)    heading.textContent    = isSignup ? "Create an account"       : "Welcome back";
    if (subheading) subheading.textContent = isSignup ? "Fill in your details to get started" : "Sign in to manage schedules and timetables";
    if (submitLabel) submitLabel.textContent = isSignup ? "Create Account" : "Sign In";
    if (toggleQ)    toggleQ.textContent    = isSignup ? "Already have an account?" : "Don't have an account?";
    if (toggleBtn)  toggleBtn.textContent  = isSignup ? "Sign in"                  : "Create one";
    if (pwInput)    pwInput.setAttribute("autocomplete", isSignup ? "new-password" : "current-password");

    // Clear alerts and reset form on mode switch
    this._setAuthAlert("error", "", false);
    this._setAuthAlert("success", "", false);
    document.getElementById("auth-form")?.reset();
  },

  /** Logs the user out — clears localStorage and returns to auth screen */
  async logout() {
    try {
      await fetch("/api/logout", { method: "POST" });
    } catch (_) { /* silent */ }
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_email");
    this.showToast("Logged out successfully.", "success");
    // Short delay so toast is visible, then show auth card
    setTimeout(() => {
      this._showAuthCard();
      this.toggleAuthMode("login");
    }, 600);
  },

  /** Show/hide password toggle */
  togglePasswordVisibility() {
    const input = document.getElementById("auth-password");
    const icon  = document.getElementById("auth-eye-icon");
    if (!input) return;
    const isHidden = input.type === "password";
    input.type = isHidden ? "text" : "password";
    if (icon) {
      icon.innerHTML = isHidden
        ? `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>`
        : `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>`;
    }
  },

  /** Helper to show/hide auth error or success alert */
  _setAuthAlert(type, message, show) {
    const el = document.getElementById(type === "error" ? "auth-error" : "auth-success");
    if (!el) return;
    el.textContent = message;
    el.style.display = show ? "flex" : "none";
    // force re-animation
    if (show) {
      el.style.animation = "none";
      el.offsetHeight; // reflow
      el.style.animation = "";
    }
  },

});


// Global listener to dismiss dropdowns when clicking outside
document.addEventListener("click", (e) => {
  if (!e.target.closest(".dropdown-wrapper")) {
    const menu = document.getElementById("timetable-download-dropdown");
    if (menu) menu.style.display = "none";
  }
  if (!e.target.closest(".user-profile-wrapper")) {
    const profileMenu = document.getElementById("user-profile-dropdown");
    const avatarBtn = document.getElementById("btn-user-avatar");
    if (profileMenu) profileMenu.style.display = "none";
    if (avatarBtn) {
      avatarBtn.classList.remove("active");
      avatarBtn.setAttribute("aria-expanded", "false");
    }
  }
});

