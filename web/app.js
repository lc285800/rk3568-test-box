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
      params.value = Number(button.dataset.gpioValue);
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
      renderTaskResult(created, gpioResult);
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
    renderTaskResult(task, target);
    if (task.status === "queued" || task.status === "running") {
      window.setTimeout(() => loadTask(id, target), 500);
    }
  } catch (error) {
    target.textContent = `读取任务失败: ${error.message}`;
  }
}

function renderTaskResult(task, target) {
  if (!task || !task.request) {
    target.classList.add("result-empty");
    target.textContent = task?.message || "任务已提交";
    return;
  }

  target.classList.remove("result-empty");
  if (task.request.interface === "gpio") {
    target.innerHTML = renderGpioTask(task);
    return;
  }
  target.textContent = JSON.stringify(task, null, 2);
}

function renderGpioTask(task) {
  const request = task.request || {};
  const params = request.params || {};
  const result = task.result || {};
  const actionText = {
    info: "GPIO 信息",
    read: "GPIO 读取",
    write: "GPIO 输出",
  }[request.action] || request.action || "-";
  const modeText = request.dry_run ? "Dry run" : result.simulated ? "模拟" : "真实硬件";
  const statusText = task.status || "-";

  const summary = `
    <div class="result-summary">
      <span class="result-pill">${escapeHtml(statusText)}</span>
      <span>${escapeHtml(actionText)}</span>
      <span>任务 ${escapeHtml(task.id || "-")}</span>
      <span>${escapeHtml(modeText)}</span>
    </div>
  `;

  if (task.status === "queued" || task.status === "running") {
    return `<div class="result-card">${summary}<p class="hint">${escapeHtml(task.message || "任务执行中")}</p></div>`;
  }

  if (task.status === "failed" || task.status === "rejected") {
    return `<div class="result-card">${summary}<p class="hint">${escapeHtml(task.message || "任务失败")}</p></div>`;
  }

  if (request.action === "info") {
    return `
      <div class="result-card">
        ${summary}
        ${renderResultKv([
          ["芯片", result.chip || params.chip || "-"],
          ["来源", result.simulated ? "模拟数据" : "板卡实测"],
        ])}
        ${renderGpioInfo(result.text || "")}
      </div>
    `;
  }

  if (request.action === "read") {
    const values = result.values || {};
    return `
      <div class="result-card">
        ${summary}
        ${renderResultKv([
          ["芯片", result.chip || params.chip || "-"],
          ["Line", Object.keys(values).join(", ") || params.line || "-"],
          ["读取值", Object.values(values).join(", ") || "-"],
          ["来源", result.simulated ? "模拟数据" : "板卡实测"],
        ])}
      </div>
    `;
  }

  if (request.action === "write") {
    return `
      <div class="result-card">
        ${summary}
        ${renderResultKv([
          ["芯片", result.chip || params.chip || "-"],
          ["Line", result.line ?? params.line ?? "-"],
          ["输出值", result.value ?? params.value ?? "-"],
          ["状态", result.mode === "held" ? "持续保持" : "已提交"],
          ["来源", result.simulated ? "Dry run / 模拟" : "板卡实测"],
        ])}
      </div>
    `;
  }

  return `<div class="result-card">${summary}<pre class="raw-output">${escapeHtml(JSON.stringify(result, null, 2))}</pre></div>`;
}

function renderResultKv(rows) {
  return `
    <dl class="result-kv">
      ${rows
        .map(
          ([key, value]) => `
            <div>
              <dt>${escapeHtml(key)}</dt>
              <dd>${escapeHtml(value)}</dd>
            </div>
          `
        )
        .join("")}
    </dl>
  `;
}

function renderGpioInfo(text) {
  const lines = parseGpioInfo(text);
  if (!lines.length) {
    return `<pre class="raw-output">${escapeHtml(text || "没有返回 GPIO 信息")}</pre>`;
  }
  return `
    <table class="gpio-lines">
      <thead>
        <tr>
          <th>Line</th>
          <th>名称</th>
          <th>占用</th>
          <th>方向</th>
          <th>电平逻辑</th>
        </tr>
      </thead>
      <tbody>
        ${lines
          .map(
            (line) => `
              <tr>
                <td>${escapeHtml(line.line)}</td>
                <td>${escapeHtml(line.name)}</td>
                <td>${escapeHtml(line.consumer)}</td>
                <td>${escapeHtml(line.direction)}</td>
                <td>${escapeHtml(line.active)}</td>
              </tr>
            `
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function parseGpioInfo(text) {
  return String(text || "")
    .split("\n")
    .map((line) => {
      const match = line.match(/line\s+(\d+):\s+(.+)/);
      if (!match) {
        return null;
      }
      const tokens = match[2].match(/"[^"]*"|\S+/g) || [];
      return {
        line: match[1],
        name: cleanGpioToken(tokens[0]) || "-",
        consumer: cleanGpioToken(tokens[1]) || "-",
        direction: cleanGpioToken(tokens[2]) || "-",
        active: cleanGpioToken(tokens[3]) || "-",
      };
    })
    .filter(Boolean);
}

function cleanGpioToken(value) {
  return String(value || "").replace(/^"|"$/g, "");
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
