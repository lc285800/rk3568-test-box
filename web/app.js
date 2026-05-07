const statusDot = document.querySelector("#status-dot");
const statusText = document.querySelector("#status-text");
const summary = document.querySelector("#summary");
const systemInfo = document.querySelector("#system-info");
const resources = document.querySelector("#resources");
const log = document.querySelector("#log");
const taskResult = document.querySelector("#task-result");
const gpioResult = document.querySelector("#gpio-result");

const resourceLabels = {
  gpiochips: "GPIO",
  i2c_buses: "I2C",
  serial_ports: "串口",
  can_interfaces: "CAN",
  pwm_chips: "PWM",
  adc_channels: "ADC",
};

function setStatus(kind, text) {
  statusDot.className = `dot dot-${kind}`;
  statusText.textContent = text;
}

function appendLog(message, payload = null) {
  const line = `[${new Date().toLocaleTimeString()}] ${message}`;
  log.textContent += payload ? `${line} ${JSON.stringify(payload)}\n` : `${line}\n`;
  log.scrollTop = log.scrollHeight;
}

async function getJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }
  return response.json();
}

function renderSystem(info) {
  const rows = [
    ["主机名", info.hostname],
    ["内核", info.kernel],
    ["系统", info.os],
    ["架构", info.arch],
    ["CPU", info.cpu],
    ["内存", info.memory_total],
    ["网络", (info.network || []).join(" | ")],
  ];
  systemInfo.innerHTML = rows
    .map(([key, value]) => `<dt>${key}</dt><dd>${escapeHtml(value || "-")}</dd>`)
    .join("");
}

function renderResources(data) {
  resources.innerHTML = Object.entries(resourceLabels)
    .map(([key, label]) => {
      const values = data[key] || [];
      const chips = values.length
        ? values.map((item) => `<code>${escapeHtml(item)}</code>`).join("")
        : "<span class=\"empty\">未发现</span>";
      return `<div class="resource"><strong>${label}</strong>${chips}</div>`;
    })
    .join("");
}

async function refresh() {
  try {
    const [health, system, resourceData] = await Promise.all([
      getJson("/api/health"),
      getJson("/api/system"),
      getJson("/api/resources"),
    ]);
    setStatus("ok", `${health.status} · ${health.mode}`);
    summary.textContent = `${system.hostname} · ${system.kernel} · ${resourceData.mode}`;
    renderSystem(system);
    renderResources(resourceData);
    appendLog("刷新完成");
  } catch (error) {
    setStatus("bad", "离线");
    summary.textContent = "无法连接 Board Agent";
    appendLog("刷新失败", { error: error.message });
  }
}

function connectEvents() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/events`);

  socket.addEventListener("open", () => appendLog("WebSocket 已连接"));
  socket.addEventListener("message", (event) => {
    try {
      const data = JSON.parse(event.data);
      appendLog(data.type, data.payload);
    } catch {
      appendLog(event.data);
    }
  });
  socket.addEventListener("close", () => {
    appendLog("WebSocket 已断开，3 秒后重连");
    window.setTimeout(connectEvents, 3000);
  });
}

document.querySelector("#refresh").addEventListener("click", refresh);
document.querySelector("#clear-log").addEventListener("click", () => {
  log.textContent = "";
});

document.querySelector("#task-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  let params = {};
  try {
    params = JSON.parse(form.get("params") || "{}");
  } catch {
    taskResult.textContent = "参数 JSON 格式错误";
    return;
  }

  const body = {
    interface: form.get("interface"),
    action: form.get("action"),
    params,
    dry_run: form.get("dry_run") === "on",
    confirm: false,
  };

  try {
    const response = await fetch("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    taskResult.textContent = `任务 ${data.id}: ${data.message}`;
    appendLog("任务已提交", data);
  } catch (error) {
    taskResult.textContent = "任务提交失败";
    appendLog("任务提交失败", { error: error.message });
  }
});

document.querySelectorAll("[data-gpio-action]").forEach((button) => {
  button.addEventListener("click", async () => {
    const form = document.querySelector("#gpio-form");
    const data = new FormData(form);
    const action = button.dataset.gpioAction;
    const params = {
      chip: data.get("chip"),
      line: Number(data.get("line")),
    };
    if (action === "write") {
      params.value = Number(data.get("value"));
      params.duration_ms = Number(data.get("duration_ms"));
    }

    const body = {
      interface: "gpio",
      action,
      params,
      dry_run: data.get("dry_run") === "on",
      confirm: data.get("confirm") === "on",
    };

    try {
      const response = await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const created = await response.json();
      appendLog("GPIO 任务已提交", created);
      gpioResult.textContent = JSON.stringify(created, null, 2);
      window.setTimeout(() => loadTask(created.id, gpioResult), 500);
    } catch (error) {
      gpioResult.textContent = `GPIO 任务失败: ${error.message}`;
      appendLog("GPIO 任务失败", { error: error.message });
    }
  });
});

async function loadTask(id, target) {
  try {
    const task = await getJson(`/api/tasks/${id}`);
    target.textContent = JSON.stringify(task, null, 2);
    if (task.status === "queued" || task.status === "running") {
      window.setTimeout(() => loadTask(id, target), 500);
    }
  } catch (error) {
    target.textContent = `读取任务失败: ${error.message}`;
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

refresh();
connectEvents();
