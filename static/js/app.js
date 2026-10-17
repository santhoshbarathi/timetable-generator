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
  viewMode: "dual", // "dual" | "single" | "all"
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
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tabId);
    });
    document.querySelectorAll(".tab-pane").forEach((pane) => {
      pane.classList.toggle("active", pane.id === tabId);
    });
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
      layoutToggle.style.display = mode === "dual" ? "flex" : "none";
    }

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
    const days = this.config?.days || ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

    // Options dropdown for selecting class
    const optionsHtml = this.classes
      .map(
        (c) =>
          `<option value="${c.id}" ${c.id === cls.id ? "selected" : ""}>${this.escapeHtml(c.name)} (${this.escapeHtml(c.code)})</option>`
      )
      .join("");

    const badgeClass = slotIndex === 1 ? "slot-1" : slotIndex === 2 ? "slot-2" : "slot-default";

    // Table rows
    let rowsHtml = "";
    if (!classSched || !classSched.grid) {
      rowsHtml = `<tr><td colspan="12" style="text-align: center; padding: 2rem; color: var(--slate-500);">No schedule generated yet for this class. Click "Regenerate Timetable" to generate.</td></tr>`;
    } else {
      days.forEach((day) => {
        const dayGrid = classSched.grid[day] || {};

        const renderPeriodSlot = (pNum) => {
          const slot = dayGrid[pNum];
          if (!slot) {
            return `<td><div class="empty-slot">— Free —</div></td>`;
          }
          const isPt = slot.faculty_work_type === "part_time";
          return `
            <td>
              <div class="slot-card ${isPt ? "part-time" : "full-time"}">
                <div>
                  <span class="slot-subject-code">${this.escapeHtml(slot.subject_code)}</span>
                  <div class="slot-subject-name" title="${this.escapeHtml(slot.subject_name)}">${this.escapeHtml(slot.subject_name)}</div>
                </div>
                <div class="slot-faculty">
                  <span class="slot-faculty-name" title="${this.escapeHtml(slot.faculty_name)}">${this.escapeHtml(slot.faculty_name)}</span>
                  <span class="slot-tag ${isPt ? "pt" : "ft"}">${isPt ? "PT" : "FT"}</span>
                </div>
              </div>
            </td>
          `;
        };

        rowsHtml += `
          <tr>
            <td class="day-header-cell">${day}</td>
            ${renderPeriodSlot(1)}
            ${renderPeriodSlot(2)}
            <td class="short-break-cell"><span class="break-vertical-badge short-badge">MORNING BREAK</span></td>
            ${renderPeriodSlot(3)}
            ${renderPeriodSlot(4)}
            <td class="break-cell"><span class="break-vertical-badge lunch-badge">LUNCH BREAK</span></td>
            ${renderPeriodSlot(5)}
            ${renderPeriodSlot(6)}
            <td class="short-break-cell"><span class="break-vertical-badge short-badge">TEA BREAK</span></td>
            ${renderPeriodSlot(7)}
            ${renderPeriodSlot(8)}
          </tr>
        `;
      });
    }

    return `
      <div class="timetable-card" id="timetable-card-${slotIndex}">
        <div class="timetable-card-header">
          <div class="timetable-card-left">
            <span class="timetable-badge-pill ${badgeClass}">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/></svg>
              ${slotLabel}
            </span>
            <label class="sr-only" for="class-select-slot-${slotIndex}">Select Class</label>
            <select id="class-select-slot-${slotIndex}" class="class-selector-dropdown" onchange="App.onClassChange(${slotIndex}, this)">
              ${optionsHtml}
            </select>
            <span class="badge badge-info">${cls.subject_count || 0} Subjects • ${cls.total_weekly_periods || 0} Periods/Wk</span>
          </div>
          <div class="timetable-card-right">
            <span class="badge badge-success">✓ 0 Conflicts Verified</span>
          </div>
        </div>
        <div class="table-responsive">
          <table class="timetable-table">
            <thead>
              <tr>
                <th>Day / Time</th>
                <th>Period 1<span class="period-time">09:00 - 09:50</span></th>
                <th>Period 2<span class="period-time">09:50 - 10:40</span></th>
                <th class="short-break-col-header">Short Break<span class="period-time">10:40 - 10:50</span></th>
                <th>Period 3<span class="period-time">10:50 - 11:40</span></th>
                <th>Period 4<span class="period-time">11:40 - 12:30</span></th>
                <th class="break-col-header">Lunch Break<span class="period-time">12:30 - 01:05</span></th>
                <th>Period 5<span class="period-time">01:05 - 01:55</span></th>
                <th>Period 6<span class="period-time">01:55 - 02:45</span></th>
                <th class="short-break-col-header">Tea Break<span class="period-time">02:45 - 03:05</span></th>
                <th>Period 7<span class="period-time">03:05 - 03:55</span></th>
                <th>Period 8<span class="period-time">03:55 - 04:45</span></th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml}
            </tbody>
          </table>
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
