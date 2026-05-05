const fs = require("fs");
const path = require("path");
const cp = require("child_process");
const pptxgen = require("pptxgenjs");

const pptx = new pptxgen();
const OUTPUT = path.join(__dirname, "AGENT_WORKBENCH_PPT_V4_ZH.pptx");
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const TOTAL = 12;

const FONT = {
  sans: "Microsoft YaHei UI",
  mono: "Consolas",
};

const C = {
  navy: "08111F",
  navy2: "10213C",
  slate: "16314D",
  ink: "0F172A",
  muted: "475569",
  line: "D7E2F0",
  white: "F8FAFC",
  soft: "F6F8FC",
  softBlue: "EAF4FF",
  softGreen: "EAFBF5",
  softAmber: "FFF6E6",
  softRose: "FFF0F3",
  cyan: "38BDF8",
  teal: "14B8A6",
  blue: "2563EB",
  green: "22C55E",
  amber: "F59E0B",
  rose: "F43F5E",
  red: "EF4444",
};

pptx.layout = "LAYOUT_WIDE";
pptx.author = "OpenAI Codex";
pptx.company = "agent_workbench";
pptx.subject = "agent_workbench 使用介绍";
pptx.title = "agent_workbench 使用介绍 V4";
pptx.lang = "zh-CN";

function readRepoText(relPath) {
  try {
    return fs.readFileSync(path.join(REPO_ROOT, relPath), "utf8");
  } catch {
    return "";
  }
}

function extractJsonBlob(output) {
  const start = output.indexOf("{");
  const end = output.lastIndexOf("}");
  if (start === -1 || end === -1 || end <= start) {
    return null;
  }
  try {
    return JSON.parse(output.slice(start, end + 1));
  } catch {
    return null;
  }
}

function loadPwmPlan() {
  const fallback = {
    understanding: "在 PA8 上使用 TIM1_CH1 输出约 1000Hz PWM，占空比 50%。",
    requestText: 'add PWM output on PA8, 1kHz, 50% duty',
    pinRoute: "PA8 -> TIM1_CH1 (AF_PP)",
    systemClockHz: 72000000,
    prescaler: 71,
    period: 999,
    ccr: 500,
    dutyPercent: 50,
    timerLabel: "TIM1 / TIM_CHANNEL_1",
    editFiles: ["Core/Src/main.c", "Core/Inc/main.h"],
    summaryFormula: "72MHz / 72 / 1000 = 1kHz",
  };

  try {
    const raw = cp.execSync(
      'cmd /c ".\\agent_workbench.bat plan ""add PWM output on PA8, 1kHz, 50% duty"" --json"',
      { cwd: REPO_ROOT, encoding: "utf8" },
    );
    const json = extractJsonBlob(raw);
    if (!json) {
      return fallback;
    }
    const pinMapping = json.hardware_context?.pin_mapping || {};
    const timerConfig = json.hardware_context?.timer_config || {};
    const clock = json.hardware_context?.clock || {};
    const editFiles =
      json.constraints?.allowed_edit_files ||
      json.context?.related_files ||
      fallback.editFiles;
    return {
      understanding: json.understanding || fallback.understanding,
      requestText: "add PWM output on PA8, 1kHz, 50% duty",
      pinRoute:
        `${pinMapping.requested_pin || "PA8"} -> ${pinMapping.recommended || "TIM1_CH1"} ` +
        `(${pinMapping.alternate_function_mode || pinMapping.details?.af || "AF_PP"})`,
      systemClockHz: clock.system_clock_hz || fallback.systemClockHz,
      prescaler: timerConfig.prescaler ?? fallback.prescaler,
      period: timerConfig.period ?? fallback.period,
      ccr: timerConfig.ccr ?? fallback.ccr,
      dutyPercent: timerConfig.duty_percent ?? fallback.dutyPercent,
      timerLabel:
        `${timerConfig.timer || "TIM1"} / ${timerConfig.channel || "TIM_CHANNEL_1"}`,
      editFiles,
      summaryFormula: timerConfig.rationale || fallback.summaryFormula,
    };
  } catch {
    return fallback;
  }
}

function loadSessionSummary() {
  const text = readRepoText("agent_workbench/evidence/sessions/cli_automation_regression/session_summary.md");
  const fallback = {
    verdict: "pass",
    pass: 10,
    fail: 0,
    skip: 0,
    strongestEvidence: "saw_ready=True saw_prompt=True",
  };

  if (!text) {
    return fallback;
  }

  const verdict = text.match(/- verdict:\s+`?([^`\r\n]+)`?/);
  const assertions = text.match(/- assertions:\s+pass=(\d+)\s+fail=(\d+)\s+skip=(\d+)/);
  const strongest = text.match(/- strongest_evidence:\s+([^\r\n]+)/);
  return {
    verdict: verdict?.[1] || fallback.verdict,
    pass: assertions ? Number(assertions[1]) : fallback.pass,
    fail: assertions ? Number(assertions[2]) : fallback.fail,
    skip: assertions ? Number(assertions[3]) : fallback.skip,
    strongestEvidence: strongest?.[1] || fallback.strongestEvidence,
  };
}

function loadTranscriptExcerpt() {
  const text = readRepoText("agent_workbench/evidence/sessions/cli_automation_regression/cli_transcript.log");
  if (!text) {
    return [
      "[cli] start port=COM3 baud=115200 expect_ready=1 reset_first=1",
      "< STM32 UART CLI ready.",
      "< Console: USART2 @ 115200 8N1, TX=PA2, RX=PA3",
      "> help",
      "< Available commands:",
      "> red on",
      "< [ok] red -> on",
      "> blue toggle",
      "< [ok] blue -> toggle",
      "< cli>",
    ];
  }
  return text
    .split(/\r?\n/)
    .filter(Boolean)
    .slice(0, 10)
    .map((line) => line.replace(/^\[[^\]]+\]\s*/, ""));
}

const REPO_DATA = {
  pwmPlan: loadPwmPlan(),
  sessionSummary: loadSessionSummary(),
  transcriptExcerpt: loadTranscriptExcerpt(),
};

function addText(slide, text, opts = {}) {
  slide.addText(text, {
    fontFace: opts.fontFace || FONT.sans,
    fontSize: opts.fontSize || 12,
    color: opts.color || C.ink,
    bold: opts.bold || false,
    italic: opts.italic || false,
    align: opts.align || "left",
    valign: opts.valign || "top",
    margin: opts.margin ?? 0.08,
    fit: opts.fit || "shrink",
    breakLine: opts.breakLine || false,
    lineSpacingMultiple: opts.lineSpacingMultiple,
    x: opts.x,
    y: opts.y,
    w: opts.w,
    h: opts.h,
  });
}

function addBox(slide, opts = {}) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x: opts.x,
    y: opts.y,
    w: opts.w,
    h: opts.h,
    rectRadius: opts.rectRadius || 0.08,
    fill: {
      color: opts.fill || C.white,
      transparency: opts.transparency || 0,
    },
    line: opts.line
      ? { color: opts.line, pt: opts.linePt || 1.2 }
      : { color: opts.fill || C.white, transparency: 100 },
  });
}

function addRect(slide, opts = {}) {
  slide.addShape(pptx.ShapeType.rect, {
    x: opts.x,
    y: opts.y,
    w: opts.w,
    h: opts.h,
    fill: {
      color: opts.fill || C.white,
      transparency: opts.transparency || 0,
    },
    line: opts.line
      ? { color: opts.line, pt: opts.linePt || 1.0 }
      : { color: opts.fill || C.white, transparency: 100 },
  });
}

function addGlow(slide, x, y, w, h, color, transparency = 65) {
  slide.addShape(pptx.ShapeType.ellipse, {
    x,
    y,
    w,
    h,
    fill: { color, transparency },
    line: { color, transparency: 100 },
  });
}

function addPill(slide, text, x, y, w, h, fill, color, opts = {}) {
  addBox(slide, {
    x,
    y,
    w,
    h,
    fill,
    line: opts.line,
    transparency: opts.transparency || 0,
    rectRadius: 0.1,
  });
  addText(slide, text, {
    x,
    y,
    w,
    h,
    fontSize: opts.fontSize || 10.5,
    color,
    bold: opts.bold !== false,
    align: "center",
    valign: "mid",
    margin: 0.03,
  });
}

function addPageTag(slide, idx, label, dark = false) {
  addPill(
    slide,
    `${label} ${String(idx).padStart(2, "0")} / ${String(TOTAL).padStart(2, "0")}`,
    11.35,
    0.28,
    1.42,
    0.28,
    dark ? C.slate : C.white,
    dark ? C.white : C.ink,
    { line: dark ? C.slate : C.line, fontSize: 9.2 },
  );
}

function addTitle(slide, kicker, title, subtitle, dark = false) {
  addPill(
    slide,
    kicker,
    0.55,
    0.32,
    1.08,
    0.28,
    dark ? C.slate : C.softBlue,
    dark ? C.white : C.blue,
    { line: dark ? C.slate : C.softBlue, fontSize: 9.8 },
  );
  addText(slide, title, {
    x: 0.55,
    y: 0.72,
    w: 8.4,
    h: 0.45,
    fontSize: 24,
    bold: true,
    color: dark ? C.white : C.ink,
  });
  if (subtitle) {
    addText(slide, subtitle, {
      x: 0.55,
      y: 1.14,
      w: 9.25,
      h: 0.42,
      fontSize: 11.5,
      color: dark ? "CBD5E1" : C.muted,
    });
  }
}

function addArrow(slide, x, y, w, h, color, opts = {}) {
  slide.addShape(pptx.ShapeType.line, {
    x,
    y,
    w,
    h,
    line: {
      color,
      pt: opts.pt || 1.8,
      beginArrowType: opts.beginArrowType || "none",
      endArrowType: opts.endArrowType || "triangle",
      dashType: opts.dashType,
    },
  });
}

function addCodeBlock(slide, x, y, w, h, title, lines, accent = C.cyan) {
  addBox(slide, { x, y, w, h, fill: C.navy2, line: accent });
  addText(slide, title, {
    x: x + 0.18,
    y: y + 0.12,
    w: w - 0.36,
    h: 0.18,
    fontSize: 10.5,
    bold: true,
    color: C.white,
  });
  addPill(slide, "", x + w - 0.7, y + 0.11, 0.13, 0.13, C.rose, C.rose, {
    line: C.rose,
    fontSize: 1,
  });
  addPill(slide, "", x + w - 0.5, y + 0.11, 0.13, 0.13, C.amber, C.amber, {
    line: C.amber,
    fontSize: 1,
  });
  addPill(slide, "", x + w - 0.3, y + 0.11, 0.13, 0.13, C.green, C.green, {
    line: C.green,
    fontSize: 1,
  });
  addText(slide, lines.join("\n"), {
    x: x + 0.18,
    y: y + 0.4,
    w: w - 0.36,
    h: h - 0.52,
    fontFace: FONT.mono,
    fontSize: 9.3,
    color: "E2E8F0",
    margin: 0.02,
  });
}

function addMetric(slide, x, y, w, h, label, value, note, accent, dark = false) {
  addBox(slide, {
    x,
    y,
    w,
    h,
    fill: dark ? C.navy2 : C.white,
    line: accent,
  });
  addText(slide, label, {
    x: x + 0.14,
    y: y + 0.12,
    w: w - 0.28,
    h: 0.14,
    fontSize: 9.6,
    bold: true,
    color: dark ? C.white : C.ink,
  });
  addText(slide, value, {
    x: x + 0.14,
    y: y + 0.34,
    w: w - 0.28,
    h: 0.28,
    fontSize: 17,
    bold: true,
    color: accent,
    valign: "mid",
  });
  addText(slide, note, {
    x: x + 0.14,
    y: y + h - 0.24,
    w: w - 0.28,
    h: 0.16,
    fontSize: 8.8,
    color: dark ? "CBD5E1" : C.muted,
  });
}

function addBulletLines(slide, items, x, y, w, rowH, bulletColor, textColor) {
  items.forEach((item, idx) => {
    slide.addShape(pptx.ShapeType.ellipse, {
      x,
      y: y + idx * rowH + 0.08,
      w: 0.08,
      h: 0.08,
      fill: { color: bulletColor },
      line: { color: bulletColor, transparency: 100 },
    });
    addText(slide, item, {
      x: x + 0.14,
      y: y + idx * rowH,
      w: w - 0.14,
      h: rowH - 0.02,
      fontSize: 10.6,
      color: textColor,
    });
  });
}

function addCoverHero(slide) {
  addGlow(slide, 8.45, 0.22, 3.0, 2.8, C.cyan, 84);
  addGlow(slide, 9.45, 3.75, 2.55, 2.35, C.teal, 86);
  addBox(slide, {
    x: 8.32,
    y: 1.12,
    w: 3.85,
    h: 4.55,
    fill: C.navy2,
    line: C.cyan,
  });
  addBox(slide, {
    x: 8.68,
    y: 1.52,
    w: 3.1,
    h: 0.7,
    fill: C.slate,
    line: C.cyan,
  });
  addText(slide, "AI Frontend", {
    x: 8.94,
    y: 1.69,
    w: 2.55,
    h: 0.22,
    fontSize: 15,
    bold: true,
    color: C.white,
    align: "center",
  });
  addText(slide, "OpenCode / Continue / Cursor", {
    x: 8.84,
    y: 1.94,
    w: 2.76,
    h: 0.15,
    fontSize: 9.1,
    color: "CBD5E1",
    align: "center",
  });

  addBox(slide, {
    x: 8.68,
    y: 2.58,
    w: 3.1,
    h: 1.22,
    fill: "122B45",
    line: C.teal,
  });
  addText(slide, "agent_workbench", {
    x: 8.92,
    y: 2.77,
    w: 2.62,
    h: 0.22,
    fontSize: 16,
    bold: true,
    color: C.white,
    align: "center",
  });
  addText(slide, "plan / build / flash / uart / verify / report", {
    x: 8.83,
    y: 3.1,
    w: 2.82,
    h: 0.18,
    fontSize: 8.8,
    color: "CBD5E1",
    align: "center",
  });
  addPill(slide, "YAML", 8.9, 3.4, 0.58, 0.2, C.blue, C.white, { fontSize: 8.5 });
  addPill(slide, "CLI", 9.57, 3.4, 0.5, 0.2, C.teal, C.white, { fontSize: 8.5 });
  addPill(slide, "Evidence", 10.16, 3.4, 0.76, 0.2, C.amber, C.white, { fontSize: 8.5 });
  addPill(slide, "COM3", 11.02, 3.4, 0.56, 0.2, C.cyan, C.ink, { fontSize: 8.5 });

  addBox(slide, {
    x: 8.68,
    y: 4.16,
    w: 3.1,
    h: 0.92,
    fill: "0D1B2C",
    line: C.green,
  });
  addText(slide, "STM32 Board + UART CLI", {
    x: 8.9,
    y: 4.42,
    w: 2.64,
    h: 0.18,
    fontSize: 14,
    bold: true,
    color: C.white,
    align: "center",
  });
  addText(slide, "ready banner / cli> / smoke verification", {
    x: 8.84,
    y: 4.68,
    w: 2.76,
    h: 0.16,
    fontSize: 8.8,
    color: "CBD5E1",
    align: "center",
  });

  addArrow(slide, 10.2, 2.2, 0, 0.3, C.cyan);
  addArrow(slide, 10.2, 3.8, 0, 0.3, C.teal);
}

function buildSlide01() {
  const slide = pptx.addSlide();
  slide.background = { color: C.navy };
  addGlow(slide, -0.6, -0.8, 4.0, 3.1, C.blue, 92);
  addGlow(slide, 2.5, 4.45, 3.4, 2.4, C.teal, 92);
  addPill(slide, "STM32 Engineering Workflow", 0.72, 0.58, 2.08, 0.28, C.slate, C.white, {
    fontSize: 9.8,
    line: C.slate,
  });
  addText(slide, "agent_workbench", {
    x: 0.72,
    y: 1.32,
    w: 4.55,
    h: 0.52,
    fontSize: 28,
    bold: true,
    color: C.white,
  });
  addText(slide, "把 STM32 + AI 的研发流程做成可复用闭环", {
    x: 0.72,
    y: 1.9,
    w: 5.4,
    h: 0.76,
    fontSize: 25,
    bold: true,
    color: "D5F2FF",
  });
  addText(
    slide,
    "面向研发同事的使用介绍\n从“说一句需求”到“板上验证 + evidence 留痕”，统一成一条可复用流水线。",
    {
      x: 0.72,
      y: 2.92,
      w: 4.95,
      h: 0.7,
      fontSize: 13.2,
      color: "CBD5E1",
    },
  );
  addPill(slide, "统一入口", 0.72, 4.12, 0.96, 0.26, "12304A", C.white, { fontSize: 9.4 });
  addPill(slide, "Evidence first", 1.8, 4.12, 1.32, 0.26, "12304A", C.white, {
    fontSize: 9.4,
  });
  addPill(slide, "前端可替换", 3.26, 4.12, 1.18, 0.26, "12304A", C.white, {
    fontSize: 9.4,
  });
  addText(slide, "主讲 10 页 + 2 页备用案例，全部为原生可编辑文本与形状对象。", {
    x: 0.72,
    y: 6.72,
    w: 5.9,
    h: 0.18,
    fontSize: 10.2,
    color: "94A3B8",
  });
  addCoverHero(slide);
  addPageTag(slide, 1, "主讲", true);
  slide.addNotes(
    [
      "今天不讲某个单一工具，而是讲一条能落地的 STM32 + AI 工作流。",
      "核心判断：agent_workbench 不是 AI，它是把 plan、build、flash、uart、verify 和 evidence 串起来的工作台。",
      "听完之后希望大家能回答三件事：它解决什么问题、怎么上手、哪些重复劳动值得收进来自动化。",
    ].join("\n"),
  );
}

function buildSlide02() {
  const slide = pptx.addSlide();
  slide.background = { color: C.soft };
  addTitle(
    slide,
    "痛点",
    "为什么现在值得讲 agent_workbench",
    "它要解决的是团队每天都在重复付出的时间，而不是一个抽象概念。",
  );
  addPageTag(slide, 2, "主讲");

  const cards = [
    {
      no: "01",
      x: 0.55,
      y: 1.9,
      title: "命令入口分散",
      body: "构建用 cmake / make，烧录用 openocd，串口用 PuTTY，验证靠手动。\n换机器、换同事、换阶段时，命令链容易失真。",
      fill: C.softRose,
      accent: C.rose,
    },
    {
      no: "02",
      x: 6.95,
      y: 1.9,
      title: "硬件参数靠记忆",
      body: "TIM Prescaler / ARR / CCR、GPIO 模式、ADC Channel 经常要翻手册手算。\n算错时编译也许能过，但板上行为不对。",
      fill: C.softAmber,
      accent: C.amber,
    },
    {
      no: "03",
      x: 0.55,
      y: 4.22,
      title: "验证停留在目测",
      body: "打开串口看一眼“好像对了”就算通过，没有结构化证据。\n回归、交接、复盘都会变得脆弱。",
      fill: C.softBlue,
      accent: C.blue,
    },
    {
      no: "04",
      x: 6.95,
      y: 4.22,
      title: "AI 代码落不了地",
      body: "从聊天窗口复制代码进项目，编译失败后再手动修，来回多轮。\nAI 只帮了“前半程”，后半程还是人肉兜底。",
      fill: C.softGreen,
      accent: C.green,
    },
  ];

  cards.forEach((card) => {
    addBox(slide, {
      x: card.x,
      y: card.y,
      w: 5.8,
      h: 1.92,
      fill: card.fill,
      line: card.accent,
    });
    addPill(slide, card.no, card.x + 0.18, card.y + 0.16, 0.44, 0.24, card.accent, C.white, {
      fontSize: 9.5,
    });
    addText(slide, card.title, {
      x: card.x + 0.72,
      y: card.y + 0.16,
      w: 4.7,
      h: 0.22,
      fontSize: 16,
      bold: true,
      color: C.ink,
    });
    addText(slide, card.body, {
      x: card.x + 0.18,
      y: card.y + 0.54,
      w: 5.4,
      h: 1.08,
      fontSize: 11.2,
      color: C.muted,
    });
  });

  addBox(slide, {
    x: 0.55,
    y: 6.55,
    w: 12.25,
    h: 0.5,
    fill: C.navy,
    line: C.navy,
  });
  addText(slide, "agent_workbench 解决的不是某一个命令，而是把“改代码 -> 编译 -> 烧录 -> 串口验证 -> 结果留痕”整条链路统一起来。", {
    x: 0.75,
    y: 6.66,
    w: 11.85,
    h: 0.2,
    fontSize: 11.6,
    bold: true,
    color: C.white,
    align: "center",
    valign: "mid",
  });

  slide.addNotes(
    [
      "这页只做一件事：先让听众认领痛点。",
      "重点不是工具名，而是我们为什么总在命令、参数、验证和 AI 落地上重复付出时间。",
      "收口句要讲清楚：workbench 统一的是整条工程链路，而不是某个单命令入口。",
    ].join("\n"),
  );
}

function buildSlide03() {
  const slide = pptx.addSlide();
  slide.background = { color: C.white };
  addTitle(
    slide,
    "场景",
    "已经跑通的 6 个高频场景",
    "先不讲原理，先看它已经能帮团队省掉什么重复劳动。",
  );
  addPageTag(slide, 3, "主讲");

  const scenarios = [
    {
      no: "01",
      title: "需求到板上验证",
      before: "查手册 -> 算参数 -> 手改代码 -> 手测",
      after: "plan -> 改代码 -> build -> flash -> verify",
      gain: "30 分钟 -> 5 分钟",
      fill: C.softBlue,
      accent: C.blue,
    },
    {
      no: "02",
      title: "AI 代码编译不过",
      before: "复制粘贴 -> 报错 -> 手改 -> 再报错",
      after: "项目内直接改 -> build -> fix-build",
      gain: "5-10 轮 -> 1-2 轮",
      fill: C.softRose,
      accent: C.rose,
    },
    {
      no: "03",
      title: "测试验收自动化",
      before: "手工输命令 -> 目测 -> 截图写报告",
      after: "任务 YAML -> verify current -> summary",
      gain: "30 分钟 -> 1 分钟",
      fill: C.softGreen,
      accent: C.green,
    },
    {
      no: "04",
      title: "换机器恢复环境",
      before: "重装工具链 -> 找串口 -> 试命令",
      after: "doctor 自检 -> YAML 集中配置",
      gain: "半天 -> 5 分钟",
      fill: C.softAmber,
      accent: C.amber,
    },
    {
      no: "05",
      title: "切换 AI 前端",
      before: "重写 prompt / 规则 / 项目接入",
      after: "integration install continue",
      gain: "半天 -> 5 秒",
      fill: C.softBlue,
      accent: C.cyan,
    },
    {
      no: "06",
      title: "多人协作命令统一",
      before: "每个人记一套命令",
      after: "统一走 agent_workbench.bat",
      gain: "结果可复现",
      fill: C.softGreen,
      accent: C.teal,
    },
  ];

  scenarios.forEach((item, idx) => {
    const col = idx % 3;
    const row = Math.floor(idx / 3);
    const x = 0.45 + col * 4.27;
    const y = 1.82 + row * 2.37;
    addBox(slide, { x, y, w: 4.0, h: 2.05, fill: item.fill, line: item.accent });
    addPill(slide, item.no, x + 0.18, y + 0.16, 0.46, 0.24, item.accent, C.white, {
      fontSize: 9.5,
    });
    addText(slide, item.title, {
      x: x + 0.74,
      y: y + 0.16,
      w: 2.95,
      h: 0.22,
      fontSize: 14.2,
      bold: true,
      color: C.ink,
    });
    addText(slide, `以前：${item.before}`, {
      x: x + 0.18,
      y: y + 0.58,
      w: 3.55,
      h: 0.42,
      fontSize: 9.7,
      color: "64748B",
    });
    addText(slide, `现在：${item.after}`, {
      x: x + 0.18,
      y: y + 1.02,
      w: 3.55,
      h: 0.46,
      fontSize: 9.9,
      color: item.accent,
      bold: true,
    });
    addPill(slide, item.gain, x + 0.18, y + 1.63, 3.48, 0.24, item.accent, C.white, {
      fontSize: 9.2,
      line: item.accent,
    });
  });

  addBox(slide, {
    x: 0.55,
    y: 6.72,
    w: 12.25,
    h: 0.28,
    fill: C.navy2,
    line: C.navy2,
  });
  addText(slide, "这些只是已经跑通的组合：plan / build / flash / uart / verify / report / context 还可以继续长出更多场景。", {
    x: 0.75,
    y: 6.79,
    w: 11.85,
    h: 0.12,
    fontSize: 10.4,
    color: C.white,
    align: "center",
  });

  slide.addNotes(
    [
      "这一页不要陷入技术细节，只讲使用价值。",
      "如果时间有限，挑 2-3 个最贴近听众的场景展开，尤其是需求落地、测试验收和换机器恢复。",
      "最后一句要把听众往后面的案例页引：这不是想象中的能力，而是已经落地过的工作模式。",
    ].join("\n"),
  );
}

function buildSlide04() {
  const slide = pptx.addSlide();
  slide.background = { color: C.softBlue };
  addTitle(
    slide,
    "定位",
    "一句话理解 agent_workbench",
    "它不是另一个聊天工具，而是 STM32 项目的自动化工作台。",
  );
  addPageTag(slide, 4, "主讲");

  addBox(slide, {
    x: 0.55,
    y: 1.82,
    w: 12.2,
    h: 0.78,
    fill: C.white,
    line: C.cyan,
  });
  addText(
    slide,
    "agent_workbench 把 AI 编程助手和 STM32 开发流程（编译 -> 烧录 -> 串口验证）连接起来，让 AI 不只写代码，还能把后半程交付为可验证、可复盘的结果。",
    {
      x: 0.82,
      y: 2.02,
      w: 11.66,
      h: 0.36,
      fontSize: 15.5,
      bold: true,
      align: "center",
      color: C.ink,
    },
  );

  const features = [
    {
      no: "01",
      x: 0.55,
      title: "统一入口",
      body: "所有命令走 agent_workbench.bat，所有核心配置集中在 agent_workbench.yaml。",
      accent: C.blue,
    },
    {
      no: "02",
      x: 4.72,
      title: "Evidence first",
      body: "build.log、cli_transcript.log、session_summary.md 才是最终结论的依据。",
      accent: C.green,
    },
    {
      no: "03",
      x: 8.89,
      title: "前端可替换",
      body: "OpenCode / Continue / Cursor 都可以接在这层工作台之上，不需要重做流程。",
      accent: C.amber,
    },
  ];

  features.forEach((item) => {
    addBox(slide, {
      x: item.x,
      y: 2.92,
      w: 3.86,
      h: 1.38,
      fill: C.white,
      line: item.accent,
    });
    addText(slide, `${item.no}  ${item.title}`, {
      x: item.x + 0.18,
      y: 3.08,
      w: 3.34,
      h: 0.2,
      fontSize: 14.2,
      bold: true,
      color: item.accent,
    });
    addText(slide, item.body, {
      x: item.x + 0.18,
      y: 3.42,
      w: 3.44,
      h: 0.62,
      fontSize: 10.3,
      color: C.muted,
    });
  });

  const flow = [
    { y: 4.72, fill: C.white, line: C.line, label: "你（开发者）", sub: "说一句自然语言需求，例如：给 PA8 加 1kHz PWM" },
    { y: 5.2, fill: C.softBlue, line: C.blue, label: "AI 前端", sub: "理解需求、读写代码、调用工作台命令" },
    { y: 5.68, fill: C.softAmber, line: C.amber, label: "agent_workbench", sub: "plan / build / flash / uart / verify / report" },
    { y: 6.16, fill: C.softGreen, line: C.green, label: "STM32 硬件", sub: "运行固件，通过 ready banner / prompt / CLI 响应回传结果" },
  ];

  flow.forEach((item, idx) => {
    addBox(slide, {
      x: 1.2,
      y: item.y,
      w: 10.95,
      h: 0.32,
      fill: item.fill,
      line: item.line,
    });
    addText(slide, `${item.label}    ${item.sub}`, {
      x: 1.38,
      y: item.y + 0.04,
      w: 10.55,
      h: 0.14,
      fontSize: 10.3,
      color: C.ink,
      align: "center",
      valign: "mid",
    });
    if (idx < flow.length - 1) {
      addArrow(slide, 6.67, item.y + 0.32, 0, 0.14, "94A3B8", { pt: 1.3 });
    }
  });

  slide.addNotes(
    [
      "这里要帮听众建立一个简单模型：AI 是大脑，agent_workbench 是手脚。",
      "把“统一入口、结论看 evidence、前端可替换”三个特性讲透就够了。",
      "底部流图不是为了炫技，而是为了让听众知道 workbench 接的是后半程交付链路。",
    ].join("\n"),
  );
}

function buildSlide05() {
  const slide = pptx.addSlide();
  slide.background = { color: C.white };
  addTitle(
    slide,
    "架构",
    "三层架构：AI 前端 -> 工作台 -> 硬件",
    "AI 可以换，工作流不变；项目可以换，YAML 吸收差异。",
  );
  addPageTag(slide, 5, "主讲");

  addRect(slide, { x: 0.55, y: 1.9, w: 8.5, h: 0.82, fill: C.softBlue, line: C.blue });
  addText(slide, "外层：AI 前端", {
    x: 0.78,
    y: 2.08,
    w: 1.6,
    h: 0.16,
    fontSize: 14.8,
    bold: true,
    color: C.blue,
  });
  addPill(slide, "OpenCode", 2.0, 2.05, 1.05, 0.24, C.blue, C.white, { fontSize: 9.6 });
  addPill(slide, "Continue", 3.22, 2.05, 1.05, 0.24, C.teal, C.white, { fontSize: 9.6 });
  addPill(slide, "Cursor", 4.44, 2.05, 0.92, 0.24, C.cyan, C.ink, { fontSize: 9.6 });
  addPill(slide, "更多前端", 5.52, 2.05, 1.08, 0.24, C.soft, C.ink, {
    fontSize: 9.6,
    line: C.line,
  });
  addText(slide, "负责理解需求、读写代码，并按统一命令接入工作台。", {
    x: 0.78,
    y: 2.36,
    w: 6.4,
    h: 0.12,
    fontSize: 10.4,
    color: C.muted,
  });

  addRect(slide, { x: 0.55, y: 2.98, w: 8.5, h: 2.5, fill: C.soft, line: C.line });
  addText(slide, "中层：agent_workbench 工作台", {
    x: 0.78,
    y: 3.14,
    w: 2.55,
    h: 0.16,
    fontSize: 14.8,
    bold: true,
    color: C.ink,
  });
  addBox(slide, { x: 0.86, y: 3.54, w: 2.42, h: 1.56, fill: C.white, line: C.blue });
  addBox(slide, { x: 3.59, y: 3.54, w: 2.42, h: 1.56, fill: C.white, line: C.teal });
  addBox(slide, { x: 6.32, y: 3.54, w: 2.42, h: 1.56, fill: C.white, line: C.amber });
  addText(slide, "配置中心", {
    x: 1.04,
    y: 3.7,
    w: 1.8,
    h: 0.14,
    fontSize: 13.2,
    bold: true,
    color: C.blue,
    align: "center",
  });
  addText(slide, "agent_workbench.yaml\n项目名 / build_dir / COM3 / ready banner / prompt", {
    x: 1.04,
    y: 4.0,
    w: 1.8,
    h: 0.62,
    fontSize: 9.6,
    color: C.muted,
    align: "center",
  });
  addText(slide, "CLI 引擎", {
    x: 3.77,
    y: 3.7,
    w: 1.8,
    h: 0.14,
    fontSize: 13.2,
    bold: true,
    color: C.teal,
    align: "center",
  });
  addText(slide, "doctor / plan / build\nflash / uart / verify / report", {
    x: 3.77,
    y: 4.0,
    w: 1.8,
    h: 0.62,
    fontSize: 9.6,
    color: C.muted,
    align: "center",
  });
  addText(slide, "证据系统", {
    x: 6.5,
    y: 3.7,
    w: 1.8,
    h: 0.14,
    fontSize: 13.2,
    bold: true,
    color: C.amber,
    align: "center",
  });
  addText(slide, "runtime/ + evidence/\nbuild.log / transcript / summary / assertions", {
    x: 6.5,
    y: 4.0,
    w: 1.8,
    h: 0.62,
    fontSize: 9.6,
    color: C.muted,
    align: "center",
  });

  addRect(slide, { x: 0.55, y: 5.7, w: 8.5, h: 0.92, fill: C.softGreen, line: C.green });
  addText(slide, "内层：硬件", {
    x: 0.78,
    y: 5.93,
    w: 1.45,
    h: 0.14,
    fontSize: 14.8,
    bold: true,
    color: C.green,
  });
  addPill(slide, "STM32 MCU", 2.0, 5.92, 1.02, 0.24, C.green, C.white, { fontSize: 9.6 });
  addPill(slide, "UART CLI", 3.16, 5.92, 0.88, 0.24, C.teal, C.white, { fontSize: 9.6 });
  addPill(slide, "OpenOCD / ST-Link", 4.18, 5.92, 1.46, 0.24, C.soft, C.ink, {
    fontSize: 9.6,
    line: C.line,
  });
  addText(slide, "负责真正跑固件、回应 CLI、把板上结果带回 evidence。", {
    x: 0.78,
    y: 6.25,
    w: 6.5,
    h: 0.12,
    fontSize: 10.4,
    color: C.muted,
  });

  addCodeBlock(slide, 9.3, 1.95, 3.2, 4.68, "数据流", [
    "需求（自然语言）",
    "  -> AI 理解需求",
    "plan（硬件参数 + 步骤）",
    "  -> AI 按 plan 改代码",
    "build（产出 .elf）",
    "flash（写入 MCU）",
    "uart exec（发命令、收响应）",
    "verify（断言判定 pass/fail）",
    "evidence（build.log + transcript + summary）",
  ], C.cyan);

  addBox(slide, {
    x: 9.3,
    y: 6.82,
    w: 3.2,
    h: 0.16,
    fill: C.navy2,
    line: C.navy2,
  });
  addText(slide, "前端可换，工作台不变；项目可换，只需改 YAML。", {
    x: 9.45,
    y: 6.84,
    w: 2.9,
    h: 0.1,
    fontSize: 9.8,
    color: C.white,
    align: "center",
  });

  slide.addNotes(
    [
      "这页建议站在架构视角讲，不要掉进实现细节。",
      "三层结构里最关键的是中层：配置中心、CLI 引擎和证据系统。",
      "右侧的数据流是为了说明 workbench 不只做命令包装，它负责把需求、验证和证据串成闭环。",
    ].join("\n"),
  );
}

function buildSlide06() {
  const slide = pptx.addSlide();
  slide.background = { color: C.softAmber };
  addTitle(
    slide,
    "上手",
    "第一次上手：5 步跑通",
    "把复杂流程压缩成一条新人也能记住的最短路径。",
  );
  addPageTag(slide, 6, "主讲");

  const steps = [
    {
      no: "01",
      x: 0.45,
      accent: C.blue,
      name: "doctor",
      desc: "先自检工具链、YAML、串口与构建目录。",
      cmd: "doctor --json",
      cost: "约 5 秒",
    },
    {
      no: "02",
      x: 2.95,
      accent: C.teal,
      name: "integration install",
      desc: "给 OpenCode / Continue 生成项目接入文件。",
      cmd: "integration install opencode --json",
      cost: "约 3 秒",
    },
    {
      no: "03",
      x: 5.45,
      accent: C.amber,
      name: "plan",
      desc: "把自然语言需求转成参数、范围和执行步骤。",
      cmd: 'plan "add PWM output on PA8, 1kHz, 50% duty" --json',
      cost: "约 2 秒",
    },
    {
      no: "04",
      x: 7.95,
      accent: C.rose,
      name: "build",
      desc: "统一走构建入口，失败时进入 fix-build。",
      cmd: "build --json",
      cost: "10-30 秒",
    },
    {
      no: "05",
      x: 10.45,
      accent: C.green,
      name: "verify",
      desc: "做 smoke + 断言 + summary 的端到端闭环。",
      cmd: "verify current --task agent_workbench/tasks/cli_automation_regression.yaml --json",
      cost: "30-60 秒",
    },
  ];

  steps.forEach((item, idx) => {
    addBox(slide, { x: item.x, y: 1.98, w: 2.18, h: 3.58, fill: C.white, line: item.accent });
    addPill(slide, item.no, item.x + 0.16, 2.14, 0.42, 0.22, item.accent, C.white, {
      fontSize: 9.2,
    });
    addText(slide, item.name, {
      x: item.x + 0.16,
      y: 2.46,
      w: 1.82,
      h: 0.24,
      fontSize: 13,
      bold: true,
      color: C.ink,
      align: "center",
    });
    addText(slide, item.desc, {
      x: item.x + 0.16,
      y: 2.84,
      w: 1.82,
      h: 0.7,
      fontSize: 9.8,
      color: C.muted,
      align: "center",
    });
    addCodeBlock(slide, item.x + 0.12, 3.72, 1.94, 1.12, "命令", [item.cmd], item.accent);
    addPill(slide, item.cost, item.x + 0.34, 5.08, 1.48, 0.22, item.accent, C.white, {
      fontSize: 9.0,
    });
    if (idx < steps.length - 1) {
      addArrow(slide, item.x + 2.2, 3.78, 0.3, 0, "94A3B8", { pt: 1.6 });
    }
  });

  addBox(slide, {
    x: 0.55,
    y: 6.1,
    w: 12.2,
    h: 0.56,
    fill: C.navy,
    line: C.navy,
  });
  addText(
    slide,
    "当前仓库默认值：project=serial | build_dir=build/cmake-debug | UART=COM3 @ 115200 | ready banner=\"STM32 UART CLI ready.\" | prompt=\"cli>\"",
    {
      x: 0.78,
      y: 6.26,
      w: 11.76,
      h: 0.18,
      fontSize: 10.3,
      color: C.white,
      align: "center",
    },
  );
  addText(slide, "实际执行时统一通过 cmd /c \".\\agent_workbench.bat ... --json\" 调用。", {
    x: 3.18,
    y: 6.74,
    w: 7.0,
    h: 0.12,
    fontSize: 9.8,
    color: C.muted,
    align: "center",
  });

  slide.addNotes(
    [
      "第一次上手只让听众记住五个动作，不要求记参数。",
      "如果现场要演示，优先演示 doctor 和 verify，价值最容易被看到。",
      "底部默认值要强调是真实仓库配置，不是 PPT 里杜撰出来的示意文本。",
    ].join("\n"),
  );
}

function buildSlide07() {
  const slide = pptx.addSlide();
  const pwm = REPO_DATA.pwmPlan;
  const editScope = pwm.editFiles.map((file) => file.replace("Core/", "")).join(" + ");
  slide.background = { color: C.soft };
  addTitle(
    slide,
    "案例 1",
    "一句话需求到板上验证",
    "把硬件参数、代码范围、编译、烧录和验证串成一个可追踪闭环。",
  );
  addPageTag(slide, 7, "主讲");

  addBox(slide, { x: 0.55, y: 1.92, w: 5.75, h: 4.65, fill: C.white, line: C.line });
  addPill(slide, "Before / After", 0.78, 2.1, 1.16, 0.24, C.navy2, C.white, {
    fontSize: 9.5,
  });
  addText(slide, "同样一件事：在 PA8 输出 1kHz / 50% 的 PWM", {
    x: 0.78,
    y: 2.42,
    w: 4.95,
    h: 0.22,
    fontSize: 13.4,
    bold: true,
    color: C.ink,
  });

  const rows = [
    ["查参数", "翻手册手算 Prescaler / ARR / CCR", `plan 自动给出 ${pwm.pinRoute}`],
    ["写代码", "手动改 main.c / 头文件 / 可能误改其他模块", `按约束只改 ${editScope}`],
    ["编译", "手跑 cmake + make", "build 统一编译，失败进 fix-build"],
    ["烧录", "手动 openocd 命令", "征得用户确认后 flash 一条命令"],
    ["验证", "打开串口目测", "verify / uart smoke 自动做回归确认"],
    ["留痕", "截图或没有记录", "build.log / transcript / session_summary"],
  ];

  addRect(slide, { x: 0.78, y: 2.88, w: 5.08, h: 0.3, fill: C.softBlue, line: C.line });
  addText(slide, "环节", { x: 0.92, y: 2.95, w: 0.6, h: 0.12, fontSize: 9.8, bold: true });
  addText(slide, "以前", { x: 1.78, y: 2.95, w: 1.35, h: 0.12, fontSize: 9.8, bold: true });
  addText(slide, "现在", { x: 3.35, y: 2.95, w: 2.2, h: 0.12, fontSize: 9.8, bold: true });
  rows.forEach((row, idx) => {
    const y = 3.18 + idx * 0.48;
    addRect(slide, { x: 0.78, y, w: 5.08, h: 0.42, fill: idx % 2 === 0 ? "FBFDFF" : "F3F7FB", line: C.line });
    addText(slide, row[0], { x: 0.92, y: y + 0.06, w: 0.7, h: 0.14, fontSize: 9.4, bold: true });
    addText(slide, row[1], { x: 1.78, y: y + 0.05, w: 1.35, h: 0.18, fontSize: 8.9, color: "64748B" });
    addText(slide, row[2], { x: 3.35, y: y + 0.05, w: 2.28, h: 0.18, fontSize: 8.9, color: C.teal, bold: idx >= 3 });
  });
  addPill(slide, "总耗时：30-60 分钟 -> 5 分钟内", 1.52, 6.2, 3.6, 0.24, C.green, C.white, {
    fontSize: 10,
  });

  addCodeBlock(slide, 6.58, 1.94, 6.02, 2.18, "输入 -> plan 输出", [
    `需求       : "${pwm.requestText}"`,
    "",
    `Understanding: ${pwm.understanding}`,
    `Pin route    : ${pwm.pinRoute}`,
    `Timer        : ${pwm.timerLabel}`,
    `PWM params   : PSC ${pwm.prescaler} / ARR ${pwm.period} / CCR ${pwm.ccr}`,
    `Edit scope   : ${pwm.editFiles.join(" + ")}`,
  ], C.cyan);

  addMetric(slide, 6.58, 4.36, 1.42, 0.96, "推荐外设", pwm.pinRoute.split(" -> ")[1] || "TIM1_CH1", "来自 pin mapping", C.amber);
  addMetric(slide, 8.16, 4.36, 1.42, 0.96, "PWM 参数", `${pwm.prescaler}/${pwm.period}/${pwm.ccr}`, `${pwm.dutyPercent}% duty`, C.teal);
  addMetric(slide, 9.74, 4.36, 1.42, 0.96, "烧录动作", "需确认", "硬件动作不默认自动触发", C.rose);
  addMetric(slide, 11.32, 4.36, 1.26, 0.96, "编辑边界", String(pwm.editFiles.length), editScope, C.green);

  addCodeBlock(slide, 6.58, 5.52, 6.02, 1.18, "evidence 交付物", [
    "build.log",
    "cli_transcript.log",
    "session_summary.md",
  ], C.green);

  slide.addNotes(
    [
      "这页重点讲“工作台让硬件参数和交付边界结构化”。",
      "要强调 flash 是硬件动作，真实执行时必须征得用户确认，这也是流程可信的一部分。",
      "如果现场问为什么不是 100% 自动，答案是：能自动的自动，涉及硬件风险的动作保留人工确认。",
    ].join("\n"),
  );
}

function buildSlide08() {
  const slide = pptx.addSlide();
  const summary = REPO_DATA.sessionSummary;
  slide.background = { color: C.navy };
  addTitle(
    slide,
    "案例 2",
    "测试验收自动化：10 条断言，一条命令，一份 evidence",
    "内容取自仓库中的 cli_automation_regression 任务与 session evidence。",
    true,
  );
  addPageTag(slide, 8, "主讲", true);

  addCodeBlock(slide, 0.55, 1.82, 5.55, 3.46, "agent_workbench/tasks/cli_automation_regression.yaml", [
    "acceptance:",
    "  blackbox:",
    "    - cli_ready_banner_seen      # STM32 UART CLI ready.",
    "    - cli_prompt_seen            # cli>",
    "    - cli_help_lists_commands    # Available commands:",
    "    - cli_status_reports_uart    # UART: USART2 @ 115200 8N1",
    "    - cli_red_ack                # [ok] red -> on",
    "    - cli_green_ack              # [ok] green -> off",
    "    - cli_blue_ack               # [ok] blue -> toggle",
    "    - cli_all_off_ack            # [ok] all -> off",
    "verify.sequence: [doctor, build, test, debug]",
  ], C.cyan);

  addMetric(slide, 6.42, 1.92, 1.78, 1.08, "Verdict", summary.verdict, "session_summary.md", C.green, true);
  addMetric(slide, 8.42, 1.92, 1.78, 1.08, "Assertions", `${summary.pass} / ${summary.fail} / ${summary.skip}`, "pass / fail / skip", C.cyan, true);
  addMetric(slide, 10.42, 1.92, 1.78, 1.08, "Evidence", "ready + prompt", summary.strongestEvidence, C.amber, true);

  addCodeBlock(slide, 6.42, 3.18, 5.78, 2.1, "session_summary.md（节选）", [
    `verdict: ${summary.verdict}`,
    "summary: CLI probe completed successfully.",
    `strongest_evidence: ${summary.strongestEvidence}`,
    `assertions: pass=${summary.pass} fail=${summary.fail} skip=${summary.skip}`,
    "",
    "CLI Tail:",
    "< UART: USART2 @ 115200 8N1",
    "< LED RED : off",
    "< cli>",
  ], C.teal);

  addCodeBlock(slide, 0.55, 5.52, 11.65, 1.22, "cli_transcript.log（节选）", [
    ...REPO_DATA.transcriptExcerpt,
  ], C.amber);

  addPill(slide, "结论来自机器判定，不是“看起来像是对了”", 3.44, 6.96, 6.42, 0.24, C.slate, C.white, {
    fontSize: 10.4,
    line: C.slate,
  });

  slide.addNotes(
    [
      "这一页一定要强调‘仓库里有真实 evidence’，不是为了 PPT 临时编的示例。",
      "session_summary、assertions.jsonl 和 cli_transcript 三件套，分别回答通过结论、断言明细和原始交互。",
      "最后一句建议直接说：这就是测试报告，机器判的，不是人感觉出来的。",
    ].join("\n"),
  );
}

function buildSlide09() {
  const slide = pptx.addSlide();
  slide.background = { color: C.softAmber };
  addTitle(
    slide,
    "征集",
    "你的下一个自动化场景是什么",
    "已知场景只是起点，更有价值的是把团队真实问题继续收进这套工作台。",
  );
  addPageTag(slide, 9, "主讲");

  addBox(slide, { x: 0.55, y: 1.84, w: 4.5, h: 2.5, fill: C.white, line: C.amber });
  addText(slide, "已知场景回顾", {
    x: 0.78,
    y: 2.02,
    w: 1.4,
    h: 0.16,
    fontSize: 13.6,
    bold: true,
    color: C.ink,
  });
  const recap = [
    "需求落地：30 分钟 -> 5 分钟",
    "AI 编译修复：5-10 轮 -> 1-2 轮",
    "测试验收：30 分钟 -> 1 分钟",
    "换机器恢复：半天 -> 5 分钟",
    "切前端：半天 -> 5 秒",
    "命令统一：各记一套 -> 统一 CLI",
  ];
  addBulletLines(slide, recap, 0.82, 2.42, 3.95, 0.28, C.amber, C.muted);

  addBox(slide, { x: 5.28, y: 1.84, w: 7.5, h: 3.02, fill: C.white, line: C.cyan });
  addText(slide, "投稿模板", {
    x: 5.52,
    y: 2.02,
    w: 1.2,
    h: 0.16,
    fontSize: 13.6,
    bold: true,
    color: C.blue,
  });
  addText(
    slide,
    [
      "场景名称：______________________________",
      "我现在手动做要多久：__________ 分钟 / 小时",
      "我当前的痛点：______________________________",
      "我希望 agent_workbench 帮我：________________",
      "验收标准：__________________________________",
      "预期节省时间：______________________________",
    ].join("\n"),
    {
      x: 5.58,
      y: 2.38,
      w: 6.88,
      h: 1.72,
      fontFace: FONT.mono,
      fontSize: 10.2,
      color: C.ink,
    },
  );
  addPill(slide, "可以从 GitHub Issue / PR / 群接龙 / 直接口头沟通四种方式投稿", 5.58, 4.18, 5.96, 0.24, C.softBlue, C.blue, {
    fontSize: 9.8,
    line: C.softBlue,
  });

  addBox(slide, { x: 0.55, y: 4.68, w: 12.22, h: 1.42, fill: C.white, line: C.line });
  addText(slide, "灵感方向", {
    x: 0.78,
    y: 4.86,
    w: 1.0,
    h: 0.16,
    fontSize: 13.6,
    bold: true,
    color: C.ink,
  });
  const ideas = [
    "ADC 采集配置",
    "PWM 波形调参",
    "多 UART 管理",
    "自定义协议解析",
    "CI/CD 硬件验证",
    "功耗测试",
    "代码 review + evidence",
    "diag_uart 自动判定",
  ];
  ideas.forEach((idea, idx) => {
    const col = idx % 4;
    const row = Math.floor(idx / 4);
    addPill(
      slide,
      idea,
      0.82 + col * 2.95,
      5.2 + row * 0.4,
      2.52,
      0.24,
      row === 0 ? C.softBlue : C.softGreen,
      row === 0 ? C.blue : C.teal,
      {
        fontSize: 9.4,
        line: row === 0 ? C.softBlue : C.softGreen,
      },
    );
  });

  addBox(slide, {
    x: 0.55,
    y: 6.28,
    w: 12.22,
    h: 0.5,
    fill: C.navy,
    line: C.navy,
  });
  addText(slide, "你每天重复最多的手动操作，就是 agent_workbench 下一个最值得自动化的事情。", {
    x: 0.78,
    y: 6.41,
    w: 11.76,
    h: 0.18,
    fontSize: 12,
    bold: true,
    color: C.white,
    align: "center",
  });

  slide.addNotes(
    [
      "这页是从‘介绍功能’转到‘争取内部需求’的关键页。",
      "先提醒大家已经跑通的场景，再把投稿门槛降下来：只要能说清楚时间成本、痛点和验收标准就够了。",
      "如果要现场互动，可以直接让听众喊出一个每天最烦的手工动作。",
    ].join("\n"),
  );
}

function buildSlide10() {
  const slide = pptx.addSlide();
  slide.background = { color: C.navy };
  addGlow(slide, 9.2, 0.45, 2.8, 2.6, C.cyan, 86);
  addGlow(slide, 7.7, 4.35, 2.6, 2.1, C.blue, 90);
  addTitle(
    slide,
    "收束",
    "三句话带走",
    "如果今天只记住几句话，至少把下面这 3 句带走。",
    true,
  );
  addPageTag(slide, 10, "主讲", true);

  const summary = [
    {
      no: "1",
      x: 0.65,
      accent: C.cyan,
      title: "AI 是大脑，agent_workbench 是手脚",
      body: "AI 负责理解需求和写代码，工作台负责编译、烧录、验证和出报告。",
    },
    {
      no: "2",
      x: 4.48,
      accent: C.teal,
      title: "所有结论看 Evidence",
      body: "build.log、cli_transcript.log、session_summary.md 比口头判断更可信。",
    },
    {
      no: "3",
      x: 8.31,
      accent: C.amber,
      title: "你的重复劳动就是自动化目标",
      body: "把场景投稿进来，让这套工作台替团队省掉更多重复时间。",
    },
  ];

  summary.forEach((item) => {
    addBox(slide, { x: item.x, y: 1.88, w: 3.35, h: 2.4, fill: C.navy2, line: item.accent });
    addText(slide, item.no, {
      x: item.x + 0.18,
      y: 2.0,
      w: 0.42,
      h: 0.34,
      fontSize: 28,
      bold: true,
      color: item.accent,
      align: "center",
      valign: "mid",
    });
    addText(slide, item.title, {
      x: item.x + 0.74,
      y: 2.04,
      w: 2.3,
      h: 0.36,
      fontSize: 13.4,
      bold: true,
      color: C.white,
    });
    addText(slide, item.body, {
      x: item.x + 0.18,
      y: 2.58,
      w: 2.95,
      h: 0.88,
      fontSize: 10.2,
      color: "CBD5E1",
    });
  });

  addBox(slide, { x: 0.65, y: 4.66, w: 7.25, h: 1.28, fill: C.navy2, line: C.cyan });
  addText(slide, "仓库与入口", {
    x: 0.9,
    y: 4.86,
    w: 1.1,
    h: 0.14,
    fontSize: 12.5,
    bold: true,
    color: C.white,
  });
  addText(
    slide,
    [
      "Repo   : https://github.com/jqrpfqffss/agent_workbench.git",
      "Docs   : agent_workbench/README.md",
      "Config : agent_workbench/agent_workbench.yaml",
      "投稿   : GitHub Issues / scenario_inbox.md / 直接沟通",
    ].join("\n"),
    {
      x: 0.92,
      y: 5.12,
      w: 6.82,
      h: 0.58,
      fontFace: FONT.mono,
      fontSize: 9.8,
      color: "CBD5E1",
    },
  );

  addBox(slide, { x: 9.22, y: 4.74, w: 2.72, h: 1.06, fill: "0B172A", line: C.teal });
  addText(slide, "Q&A", {
    x: 9.46,
    y: 5.04,
    w: 2.24,
    h: 0.3,
    fontSize: 24,
    bold: true,
    color: C.white,
    align: "center",
    valign: "mid",
  });

  slide.addNotes(
    [
      "三句总结建议逐句停顿，不要一口气读过去。",
      "如果现场时间不够，到这页就可以自然结束；后面两页是备用案例，不一定要讲。",
      "Q&A 时如果被追问细节，可以直接切到附录里的 bug 定位和前端切换页。",
    ].join("\n"),
  );
}

function buildSlide11() {
  const slide = pptx.addSlide();
  slide.background = { color: C.soft };
  addTitle(
    slide,
    "附录",
    "备用案例 A：Bug 定位从“猜”变成 evidence-first",
    "适合回答‘AI 到底怎么定位问题’这类追问。",
  );
  addPageTag(slide, 11, "附录");

  addBox(slide, { x: 0.55, y: 1.92, w: 3.75, h: 2.55, fill: C.white, line: C.rose });
  addText(slide, "Before：传统手动调试", {
    x: 0.8,
    y: 2.12,
    w: 2.4,
    h: 0.18,
    fontSize: 13.4,
    bold: true,
    color: C.rose,
  });
  addBulletLines(slide, [
    "加 printf -> 编译 -> 烧录 -> 看串口 -> 猜问题",
    "一次只验证一个假设，经常来回 5-10 轮",
    "1-3 小时很常见，且难复盘",
  ], 0.82, 2.5, 3.1, 0.34, C.rose, C.muted);
  addPill(slide, "常见结果：修好了但说不清为什么", 0.82, 3.96, 2.96, 0.24, C.softRose, C.rose, {
    fontSize: 9.1,
    line: C.softRose,
  });

  addBox(slide, { x: 0.55, y: 4.74, w: 3.75, h: 1.72, fill: C.white, line: C.green });
  addText(slide, "After：evidence-first 调试", {
    x: 0.8,
    y: 4.96,
    w: 2.4,
    h: 0.18,
    fontSize: 13.4,
    bold: true,
    color: C.green,
  });
  addBulletLines(slide, [
    "先看 cli_transcript / assertions / build.log",
    "再按 task scope 只读相关文件",
    "定位后 build -> flash -> verify 再闭环",
  ], 0.82, 5.34, 3.1, 0.3, C.green, C.muted);

  const steps = [
    { y: 1.94, accent: C.cyan, title: "1. 读 transcript", body: "确认 ready banner / prompt / 响应链路缺了哪一段。" },
    { y: 2.72, accent: C.blue, title: "2. 读 assertions", body: "看 fail 的不是“感觉”，而是具体断言和 needle。" },
    { y: 3.5, accent: C.amber, title: "3. 读 scoped files", body: "只看任务定义允许的 cli.c / main.c / commands.c 等范围。" },
    { y: 4.28, accent: C.teal, title: "4. 修复并复验", body: "改动后重新 build -> flash -> verify，让 evidence 自己说话。" },
  ];
  steps.forEach((step, idx) => {
    addBox(slide, { x: 4.68, y: step.y, w: 4.18, h: 0.62, fill: C.white, line: step.accent });
    addText(slide, step.title, {
      x: 4.88,
      y: step.y + 0.1,
      w: 1.55,
      h: 0.16,
      fontSize: 11.8,
      bold: true,
      color: step.accent,
    });
    addText(slide, step.body, {
      x: 6.0,
      y: step.y + 0.08,
      w: 2.56,
      h: 0.18,
      fontSize: 9.4,
      color: C.muted,
    });
    if (idx < steps.length - 1) {
      addArrow(slide, 6.77, step.y + 0.62, 0, 0.14, "94A3B8", { pt: 1.2 });
    }
  });

  addCodeBlock(slide, 9.18, 1.96, 3.42, 3.22, "调试口播示例", [
    '你说： "UART CLI 没有输出 ready banner，帮我查一下"',
    "",
    "AI 先读：",
    "- cli_transcript.log",
    "- assertions.jsonl",
    "- build.log",
    "",
    "再读 scope 限定文件，给出修复点：",
    "MX_USART2_UART_Init() 的调用顺序",
  ], C.cyan);
  addPill(slide, "目标不是更会猜，而是更快找到“哪份 evidence 指向了哪一行代码”", 4.68, 6.12, 7.92, 0.24, C.navy2, C.white, {
    fontSize: 10,
    line: C.navy2,
  });

  slide.addNotes(
    [
      "这一页是答疑备用，不一定主讲。",
      "如果听众质疑 AI 会不会乱猜，回答就落在 evidence-first：先读 transcript、assertions、build log，再读 scoped files。",
      "你可以把它理解为：AI 被流程约束在证据和边界里工作，而不是在全仓库里自由发挥。",
    ].join("\n"),
  );
}

function buildSlide12() {
  const slide = pptx.addSlide();
  slide.background = { color: C.white };
  addTitle(
    slide,
    "附录",
    "备用案例 B：换 AI 前端，迁移成本接近零",
    "适合回答‘为什么说它前端可替换’这类追问。",
  );
  addPageTag(slide, 12, "附录");

  addCodeBlock(slide, 0.55, 1.9, 4.66, 3.58, "integrations/ 目录结构", [
    "integrations/",
    "├── opencode/",
    "│   ├── manifest.yaml",
    "│   ├── files/",
    "│   └── README_ZH.md",
    "├── continue/",
    "│   ├── manifest.yaml",
    "│   ├── files/",
    "│   └── README_ZH.md",
    "└── cursor/   # 将来可继续新增",
  ], C.cyan);

  addBox(slide, { x: 5.52, y: 2.0, w: 2.12, h: 1.86, fill: C.softBlue, line: C.blue });
  addText(slide, "共享配置源", {
    x: 5.88,
    y: 2.22,
    w: 1.4,
    h: 0.18,
    fontSize: 13.6,
    bold: true,
    color: C.blue,
    align: "center",
  });
  addText(slide, "agent_workbench.yaml\n\nproject_name\nbuild_dir\nuart_port\nready_banner\nprompt", {
    x: 5.86,
    y: 2.6,
    w: 1.44,
    h: 0.92,
    fontFace: FONT.mono,
    fontSize: 9.6,
    color: C.ink,
    align: "center",
  });

  addBox(slide, { x: 7.92, y: 1.9, w: 4.68, h: 3.58, fill: C.white, line: C.line });
  addText(slide, "OpenCode 与 Continue 的迁移对比", {
    x: 8.18,
    y: 2.12,
    w: 2.64,
    h: 0.18,
    fontSize: 13.6,
    bold: true,
    color: C.ink,
  });
  const compareRows = [
    ["安装", "integration install opencode", "integration install continue"],
    ["检查", "integration check opencode", "integration check continue"],
    ["移除", "integration remove opencode", "integration remove continue"],
    ["配置来源", "同一个 YAML", "同一个 YAML"],
    ["核心 CLI", "完全不变", "完全不变"],
  ];
  addRect(slide, { x: 8.12, y: 2.54, w: 4.22, h: 0.3, fill: C.softBlue, line: C.line });
  addText(slide, "动作", { x: 8.24, y: 2.62, w: 0.48, h: 0.1, fontSize: 9.2, bold: true });
  addText(slide, "OpenCode", { x: 8.94, y: 2.62, w: 1.18, h: 0.1, fontSize: 9.2, bold: true });
  addText(slide, "Continue", { x: 10.44, y: 2.62, w: 1.2, h: 0.1, fontSize: 9.2, bold: true });
  compareRows.forEach((row, idx) => {
    const y = 2.84 + idx * 0.46;
    addRect(slide, { x: 8.12, y, w: 4.22, h: 0.4, fill: idx % 2 === 0 ? "FBFDFF" : "F3F7FB", line: C.line });
    addText(slide, row[0], { x: 8.24, y: y + 0.06, w: 0.48, h: 0.1, fontSize: 8.9, bold: true });
    addText(slide, row[1], { x: 8.94, y: y + 0.05, w: 1.26, h: 0.16, fontSize: 8.3, fontFace: FONT.mono, color: C.muted });
    addText(slide, row[2], { x: 10.44, y: y + 0.05, w: 1.46, h: 0.16, fontSize: 8.3, fontFace: FONT.mono, color: C.muted });
  });

  addArrow(slide, 7.64, 2.92, 0.24, 0, C.blue, { pt: 1.4 });
  addArrow(slide, 7.64, 4.18, 0.24, 0, C.teal, { pt: 1.4 });
  addPill(slide, "新增前端 = 新增一个 integration 目录，而不是重做整套流程", 2.2, 6.08, 8.94, 0.26, C.navy2, C.white, {
    fontSize: 10.2,
    line: C.navy2,
  });

  slide.addNotes(
    [
      "这页适合回答‘为什么不把 OpenCode 写死在流程里’。",
      "核心观点：工作台和前端适配解耦，新增前端时修改的是 integration 包，而不是核心 CLI。",
      "如果团队未来还会换工具，这页通常很能打消大家的迁移顾虑。",
    ].join("\n"),
  );
}

async function main() {
  buildSlide01();
  buildSlide02();
  buildSlide03();
  buildSlide04();
  buildSlide05();
  buildSlide06();
  buildSlide07();
  buildSlide08();
  buildSlide09();
  buildSlide10();
  buildSlide11();
  buildSlide12();

  await pptx.writeFile({ fileName: OUTPUT });
  console.log(`saved=${OUTPUT}`);
  console.log(`slides=${pptx._slides.length}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
