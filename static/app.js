const selectedFiles = [];

const dropArea = document.querySelector("#drop-area");
const fileInput = document.querySelector("#file-input");
const fileList = document.querySelector("#file-list");
const uploadStage = document.querySelector("#upload-stage");
const analysisStage = document.querySelector("#analysis-stage");
const reviewStage = document.querySelector("#review-stage");

function renderFiles() {
  fileList.innerHTML = "";
  selectedFiles.forEach((file, index) => {
    const row = document.createElement("div");
    row.className = "file-row";

    const name = document.createElement("span");
    name.textContent = `${file.name} — ${Math.max(1, Math.round(file.size / 1024))} KB`;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "حذف";
    remove.addEventListener("click", () => {
      selectedFiles.splice(index, 1);
      renderFiles();
    });

    row.append(name, remove);
    fileList.append(row);
  });
}

function addFiles(files) {
  for (const file of files) {
    if (!file.name.toLowerCase().endsWith(".jsonl.zst")) continue;
    if (!selectedFiles.some(item => item.name === file.name && item.size === file.size)) {
      selectedFiles.push(file);
    }
  }
  renderFiles();
}

document.querySelector("#browse-button").addEventListener("click", async () => {
  try {
    const response = await fetch("/api/select-files", { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "خطا در باز کردن انتخابگر فایل");

    for (const item of data.files || []) {
      const bytes = atob(item.data);
      const buffer = new Uint8Array(bytes.length);
      for (let i = 0; i < bytes.length; i++) buffer[i] = bytes.charCodeAt(i);
      const file = new File([buffer], item.name, { type: "application/zstd" });
      if (!selectedFiles.some(existing => existing.name === file.name && existing.size === file.size)) {
        selectedFiles.push(file);
      }
    }
    renderFiles();
  } catch (error) {
    alert(error.message);
  }
});

fileInput.addEventListener("change", () => addFiles(fileInput.files));

dropArea.addEventListener("dragover", event => {
  event.preventDefault();
  dropArea.classList.add("dragging");
});

dropArea.addEventListener("dragleave", () => dropArea.classList.remove("dragging"));
dropArea.addEventListener("drop", event => {
  event.preventEvent?.();
  event.preventDefault();
  dropArea.classList.remove("dragging");
  addFiles(event.dataTransfer.files);
});

function setStep(activeStep) {
  document.querySelectorAll(".stepper .step").forEach((step, index) => {
    const number = index + 1;
    step.classList.toggle("active", number === activeStep);
    step.classList.toggle("complete", number < activeStep);
  });
}

function showStage(stage) {
  [uploadStage, analysisStage, reviewStage].forEach(item => item.classList.add("hidden"));
  stage.classList.remove("hidden");
}

function showError(element, message) {
  element.textContent = message;
  element.classList.remove("hidden");
}

document.querySelector("#analyze-button").addEventListener("click", async () => {
  if (!selectedFiles.length) {
    alert("حداقل یک فایل انتخاب کنید.");
    return;
  }

  const startDate = document.querySelector("#start-date").dataset.gregorian;
  const endDate = document.querySelector("#end-date").dataset.gregorian;
  if (!startDate || !endDate || startDate > endDate) {
    alert("بازه زمانی معتبر انتخاب کنید.");
    return;
  }

  setStep(2);
  showStage(analysisStage);
  document.querySelector("#status-text").textContent = "در حال پردازش فایل‌ها و ارسال اطلاعات استخراج‌شده برای تحلیل...";
  const analysisErrors = document.querySelector("#analysis-errors");
  analysisErrors.classList.add("hidden");

  const form = new FormData();
  selectedFiles.forEach(file => form.append("files", file));
  form.append("start_date", startDate);
  form.append("end_date", endDate);

  try {
    const response = await fetch("/api/analyze", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "خطا در تحلیل فایل‌ها");

    document.querySelector("#report-title").value = data.title;
    document.querySelector("#uploaded-count").textContent = `فایل‌های معتبر: ${data.uploaded_sessions}`;
    document.querySelector("#analyzed-count").textContent = `جلسات در بازه: ${data.analyzed_sessions}`;
    document.querySelector("#conversation-count").textContent = `پیام‌های تحلیل‌شده: ${data.conversation_count}`;

    renderTasks(data.tasks || []);

    if (data.errors?.length) {
      showError(analysisErrors, data.errors.join("\n"));
    }

    setStep(3);
    showStage(reviewStage);
  } catch (error) {
    showError(analysisErrors, error.message);
  }
});

function moveTask(index, offset) {
  const tasks = [...document.querySelectorAll(".task-row textarea")];
  const target = index + offset;
  if (target < 0 || target >= tasks.length) return;

  const values = tasks.map(task => task.value);
  [values[index], values[target]] = [values[target], values[index]];
  renderTasks(values);
}

function renderTasks(tasks) {
  const list = document.querySelector("#task-list");
  list.innerHTML = "";

  tasks.forEach((task, index) => {
    const row = document.createElement("div");
    row.className = "task-row";

    const up = document.createElement("button");
    up.type = "button";
    up.className = "move";
    up.textContent = "▲";
    up.addEventListener("click", () => moveTask(index, -1));

    const down = document.createElement("button");
    down.type = "button";
    down.className = "move";
    down.textContent = "▼";
    down.addEventListener("click", () => moveTask(index, 1));

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "remove-task";
    remove.textContent = "×";
    remove.title = "حذف فعالیت";
    remove.addEventListener("click", () => {
      row.remove();
    });

    const textarea = document.createElement("textarea");
    textarea.value = task;

    row.append(up, down, remove, textarea);
    list.append(row);
  });
}

document.querySelector("#add-task").addEventListener("click", () => {
  const row = document.createElement("div");
  row.className = "task-row";

  const up = document.createElement("button");
  up.type = "button";
  up.className = "move";
  up.textContent = "▲";

  const down = document.createElement("button");
  down.type = "button";
  down.className = "move";
  down.textContent = "▼";

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "remove-task";
  remove.textContent = "×";
  remove.title = "حذف فعالیت";
  remove.addEventListener("click", () => row.remove());

  const textarea = document.createElement("textarea");
  textarea.placeholder = "متن فعالیت انجام‌شده";

  row.append(up, down, remove, textarea);
  document.querySelector("#task-list").append(row);

  const rows = [...document.querySelectorAll(".task-row")];
  const index = rows.length - 1;
  up.addEventListener("click", () => moveTask(index, -1));
  down.addEventListener("click", () => moveTask(index, 1));
  textarea.focus();
});

document.querySelector("#export-button").addEventListener("click", async () => {
  const title = document.querySelector("#report-title").value.trim();
  const tasks = [...document.querySelectorAll(".task-row textarea")]
    .map(item => item.value.trim())
    .filter(Boolean);
  const error = document.querySelector("#review-errors");
  error.classList.add("hidden");

  if (!title) {
    showError(error, "عنوان گزارش نمی‌تواند خالی باشد");
    return;
  }

  try {
    const response = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, tasks }),
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "خطا در ایجاد فایل Word");
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename=([^;]+)/);
    const filename = match ? decodeURIComponent(match[1].replaceAll('"', "")) : `${title}.docx`;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (exportError) {
    showError(error, exportError.message);
  }
});

const PERSIAN_MONTHS = [
  "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
  "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
];

function persianDigits(value) {
  return String(value).replace(/\d/g, digit => "۰۱۲۳۴۵۶۷۸۹"[Number(digit)]);
}

async function setupPersianDate(containerId) {
  const container = document.querySelector(`#${containerId}`);
  const daySelect = container.querySelector(".jalali-day");
  const monthSelect = container.querySelector(".jalali-month");
  const yearSelect = container.querySelector(".jalali-year");

  const todayResponse = await fetch("/api/persian-today");
  const today = await todayResponse.json();
  const current = today.persian;

  for (let year = current.year - 5; year <= current.year + 5; year++) {
    const option = document.createElement("option");
    option.value = year;
    option.textContent = persianDigits(year);
    yearSelect.append(option);
  }

  PERSIAN_MONTHS.forEach((name, index) => {
    const option = document.createElement("option");
    option.value = index + 1;
    option.textContent = name;
    monthSelect.append(option);
  });

  yearSelect.value = current.year;
  monthSelect.value = current.month;

  async function updateDate() {
    const year = Number(yearSelect.value);
    const month = Number(monthSelect.value);
    const previousDay = Number(daySelect.value) || current.day;
    daySelect.innerHTML = "";

    let length = month <= 6 ? 31 : month <= 11 ? 30 : 29;
    if (month === 12) {
      const leapCheck = await fetch("/api/persian-to-gregorian", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: `${year}-12-30` })
      });
      if (leapCheck.ok) length = 30;
    }

    for (let day = 1; day <= length; day++) {
      const option = document.createElement("option");
      option.value = day;
      option.textContent = persianDigits(day);
      daySelect.append(option);
    }
    daySelect.value = Math.min(previousDay, length);

    const conversion = await fetch("/api/persian-to-gregorian", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value: `${year}-${month}-${daySelect.value}` })
    });
    if (conversion.ok) {
      const result = await conversion.json();
      container.dataset.gregorian = result.gregorian;
    }
  }

  yearSelect.addEventListener("change", updateDate);
  monthSelect.addEventListener("change", updateDate);
  daySelect.addEventListener("change", updateDate);
  await updateDate();
}

setupPersianDate("start-date");
setupPersianDate("end-date");
