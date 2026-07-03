// --- 表示モード設定 ---
const VIEW_MODE_KEY = "viewMode";
const DEFAULT_VIEW_MODE = "card";
let viewMode = localStorage.getItem(VIEW_MODE_KEY) || DEFAULT_VIEW_MODE;

// --- グラフカラー設定 ---
const DEFAULT_GRAPH_COLOR = "rgba(120, 120, 120, 0.8)";
const GRAPH_COLOR_KEY = "graphColor";
let graphColor = localStorage.getItem(GRAPH_COLOR_KEY) || DEFAULT_GRAPH_COLOR;

// --- グラフ表示/非表示 状態管理 ---
const GRAPH_VISIBILITY_KEY = "graphVisibility";

const GRAPH_IDS = [
  "country-chart",
  "country-view-chart",
  "view-chart",
  "engagement-chart",
  "category-chart",
  "category-view-chart",
  "category-revenue-chart",
  "tag-chart",
  "title-word-chart",
  "weekday-chart",
  "hour-chart",
  "correlation-chart",
];

function loadGraphVisibility() {
  try {
    return JSON.parse(localStorage.getItem(GRAPH_VISIBILITY_KEY)) || {};
  } catch {
    return {};
  }
}

function saveGraphVisibility(state) {
  localStorage.setItem(GRAPH_VISIBILITY_KEY, JSON.stringify(state));
}

function getGraphVisible(id) {
  const state = loadGraphVisibility();
  return state[id] !== false;
}

function resetGraphVisibility() {
  localStorage.removeItem(GRAPH_VISIBILITY_KEY);
}

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function rgbaToHex(rgba) {
  const m = rgba.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!m) return "#787878";
  return "#" + [m[1], m[2], m[3]].map((v) => Number(v).toString(16).padStart(2, "0")).join("");
}

const form = document.getElementById("search-form");
const queryInput = document.getElementById("query");
const maxResultsInput = document.getElementById("max-results");
const durationFilterInput = document.getElementById("duration-filter");
const publishedAfterInput = document.getElementById("published-after");
const categoryFilterInput = document.getElementById("category-filter");
const engagementFilterInput = document.getElementById("engagement-filter");
const viewCountFilterInput = document.getElementById("view-count-filter");
const languageFilterInput = document.getElementById("language-filter");
const regionFilterInput = document.getElementById("region-filter");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const exportCsvBtn = document.getElementById("export-csv-btn");
const exportXlsxBtn = document.getElementById("export-xlsx-btn");
const categoryChartCanvas = document.getElementById("category-chart");
const videoPreviewModal = document.getElementById("video-preview-modal");
const videoModalClose = document.getElementById("video-modal-close");
const videoModalPlayer = document.getElementById("video-modal-player");
const videoModalTitle = document.getElementById("video-modal-title");
const videoModalLink = document.getElementById("video-modal-link");

// --- クォータ表示 ---
async function fetchQuota() {
  try {
    const res = await fetch("/api/quota");
    if (!res.ok) return;
    const data = await res.json();
    const used = data.used || 0;
    const limit = data.limit || 10000;
    const pct = Math.min(100, (used / limit) * 100);
    const label = document.getElementById("quota-label");
    const fill = document.getElementById("quota-bar-fill");
    if (!label || !fill) return;
    label.textContent = `API: ${new Intl.NumberFormat("ja-JP").format(used)} / ${new Intl.NumberFormat("ja-JP").format(limit)}`;
    fill.style.width = pct + "%";
    // 色クラスの切り替え
    fill.classList.remove("warn", "danger");
    label.classList.remove("warn", "danger");
    if (pct >= 95) {
      fill.classList.add("danger");
      label.classList.add("danger");
    } else if (pct >= 80) {
      fill.classList.add("warn");
      label.classList.add("warn");
    }
  } catch (_) {
    // サイレント失敗
  }
}

// ページ読み込み時に1回取得
fetchQuota();

const viewChartCanvas = document.getElementById("view-chart");
const engagementChartCanvas = document.getElementById("engagement-chart");
const tagChartCanvas = document.getElementById("tag-chart");
const countryChartCanvas = document.getElementById("country-chart");
const hourChartCanvas = document.getElementById("hour-chart");
const countryViewChartCanvas = document.getElementById("country-view-chart");
const categoryViewChartCanvas = document.getElementById("category-view-chart");
const categoryRevenueChartCanvas = document.getElementById("category-revenue-chart");
const weekdayChartCanvas = document.getElementById("weekday-chart");
const titleWordChartCanvas = document.getElementById("title-word-chart");
const correlationChartCanvas = document.getElementById("correlation-chart");
const channelModal = document.getElementById("channel-modal");

// --- テーマ管理 ---
const THEME_KEY = "yt_theme";
const themeToggleBtn = document.getElementById("theme-toggle-btn");

function getSystemTheme() {
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function applyTheme(theme) {
  const logo = document.querySelector(".title-logo");
  if (theme === "light") {
    document.documentElement.setAttribute("data-theme", "light");
    themeToggleBtn.textContent = "☀️";
    themeToggleBtn.title = "ダークモードに切替";
    if (logo) logo.src = "/static/logo-vidscope-light.svg";
  } else {
    document.documentElement.removeAttribute("data-theme");
    themeToggleBtn.textContent = "🌙";
    themeToggleBtn.title = "ライトモードに切替";
    if (logo) logo.src = "/static/logo-vidscope.svg";
  }
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved) {
    applyTheme(saved);
  } else {
    applyTheme(getSystemTheme());
  }
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  const next = current === "light" ? "dark" : "light";
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
  // チャートを再描画してテーマを反映
  if (compareMode && comparisonData.length) {
    renderComparisonSummary(comparisonData);
    renderComparisonCharts(comparisonData);
  } else if (latestItems.length) {
    const filtered = applyEngagementFilter(latestItems);
    renderTrendCharts(filtered);
  }
}

initTheme();
themeToggleBtn.addEventListener("click", toggleTheme);

// system preferenceの変化を検知（LocalStorageに保存済みの場合は無視）
window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", (e) => {
  if (!localStorage.getItem(THEME_KEY)) {
    applyTheme(e.matches ? "light" : "dark");
  }
});

// --- グラフ表示/非表示 UI制御 ---
function updateToggleAllBtn() {
  const allVisible = GRAPH_IDS.every((id) => getGraphVisible(id));
  const btn = document.getElementById("graph-toggle-all-btn");
  if (btn) btn.textContent = allVisible ? "全グラフ非表示" : "全グラフ表示";
}

function applyGraphVisibility() {
  GRAPH_IDS.forEach((id) => {
    const card = document.querySelector(`.trend-card[data-graph-id="${id}"]`);
    const btn = document.querySelector(`.graph-toggle-btn[data-graph-id="${id}"]`);
    if (!card || !btn) return;
    const visible = getGraphVisible(id);
    card.classList.toggle("is-hidden", !visible);
    btn.textContent = visible ? "非表示" : "表示";
    btn.classList.toggle("is-hidden", !visible);
  });
  updateToggleAllBtn();
}

// 個別トグルボタン
document.querySelectorAll(".graph-toggle-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const id = btn.dataset.graphId;
    const state = loadGraphVisibility();
    state[id] = !getGraphVisible(id);
    saveGraphVisibility(state);
    applyGraphVisibility();
  });
});

// 一括切替ボタン
const graphToggleAllBtn = document.getElementById("graph-toggle-all-btn");
if (graphToggleAllBtn) {
  graphToggleAllBtn.addEventListener("click", () => {
    const allVisible = GRAPH_IDS.every((id) => getGraphVisible(id));
    const state = {};
    GRAPH_IDS.forEach((id) => {
      state[id] = !allVisible;
    });
    saveGraphVisibility(state);
    applyGraphVisibility();
  });
}

// リセットボタン
const graphResetBtn = document.getElementById("graph-reset-btn");
if (graphResetBtn) {
  graphResetBtn.addEventListener("click", () => {
    resetGraphVisibility();
    applyGraphVisibility();
  });
}

// 初期状態を反映
applyGraphVisibility();

let latestItems = [];
let listSortState = { key: null, asc: false };
let compareMode = false;
let comparisonData = []; // [{keyword, color, items}, ...]

const COMPARE_COLORS = [
  { solid: "rgba(255, 60, 60, 0.8)",   light: "rgba(255, 60, 60, 0.3)",   label: "#ff3c3c" },
  { solid: "rgba(62, 166, 255, 0.8)",  light: "rgba(62, 166, 255, 0.3)",  label: "#3ea6ff" },
  { solid: "rgba(76, 219, 138, 0.8)",  light: "rgba(76, 219, 138, 0.3)",  label: "#4cdb8a" },
];
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (videoPreviewModal && videoPreviewModal.style.display === "flex") {
      videoModalPlayer.innerHTML = "";
      videoPreviewModal.style.display = "none";
      document.body.style.overflow = "";
    }
    if (channelModal && channelModal.style.display === "flex") {
      channelModal.style.display = "none";
    }
  }
});
let chartFilter = { tag: null, viewRange: null, engRange: null, country: null, weekday: null, hour: null, titleWord: null };
let charts = {
  category: null,
  tag: null,
  view: null,
  engagement: null,
  country: null,
  hour: null,
  countryView: null,
  categoryView: null,
  categoryRevenue: null,
  weekday: null,
  titleWord: null,
  correlation: null,
};

// --- CPM / 推定収益 ---
const CPM_KEY = "yt_cpm";
const CPM_DEFAULT = 100;
const CPM_GENRE_KEY_PREFIX = "yt_cpm_genre_";

const GENRE_CPM_DEFAULTS = {
  "1": 50,    // 映画・アニメ
  "2": 50,    // 自動車・乗り物
  "10": 200,  // 音楽
  "15": 200,  // ペット・動物
  "17": 50,   // スポーツ
  "19": 50,   // 旅行・イベント
  "20": 200,  // ゲーム
  "22": 150,  // 人物・ブログ
  "23": 50,   // コメディ
  "24": 50,   // エンタメ
  "25": 50,   // ニュース・政治
  "26": 200,  // ハウツー・スタイル
  "27": 200,  // 教育
  "28": 1000, // 科学・テクノロジー
  "29": 1000, // 非営利・社会活動
  "short": 10, // ショート動画
};

function loadCpm() {
  const v = Number(localStorage.getItem(CPM_KEY));
  return (v >= 1 && v <= 1000) ? v : CPM_DEFAULT;
}

function saveCpm(value) {
  localStorage.setItem(CPM_KEY, String(value));
}

function loadGenreCpm(categoryId) {
  const id = String(categoryId || "");
  const stored = localStorage.getItem(CPM_GENRE_KEY_PREFIX + id);
  if (stored !== null) {
    const v = Number(stored);
    if (v >= 1) return v;
  }
  return GENRE_CPM_DEFAULTS[id] !== undefined ? GENRE_CPM_DEFAULTS[id] : loadCpm();
}

function saveGenreCpm(categoryId, value) {
  localStorage.setItem(CPM_GENRE_KEY_PREFIX + String(categoryId), String(value));
}

function resetAllGenreCpm() {
  Object.keys(GENRE_CPM_DEFAULTS).forEach((id) => {
    localStorage.removeItem(CPM_GENRE_KEY_PREFIX + id);
  });
}

function formatRevenue(viewCount, cpm) {
  const revenue = Math.round((viewCount * cpm) / 1000);
  if (revenue >= 100000000) {
    return `¥${(revenue / 100000000).toFixed(1).replace(/\.0$/, "")}億`;
  }
  if (revenue >= 10000) {
    return `¥${(revenue / 10000).toFixed(1).replace(/\.0$/, "")}万`;
  }
  return `¥${new Intl.NumberFormat("ja-JP").format(revenue)}`;
}

const CATEGORY_MAP = {
  "1": "映画・アニメ", "2": "自動車・乗り物", "10": "音楽",
  "15": "ペット・動物", "17": "スポーツ", "19": "旅行・イベント",
  "20": "ゲーム", "22": "人物・ブログ", "23": "コメディ",
  "24": "エンタメ", "25": "ニュース・政治", "26": "ハウツー・スタイル",
  "27": "教育", "28": "科学・テクノロジー", "29": "非営利・社会活動"
};

const CATEGORY_NAME_TO_ID = Object.fromEntries(
  Object.entries(CATEGORY_MAP).map(([id, name]) => [name, id])
);

function fmt(num) {
  return new Intl.NumberFormat("ja-JP").format(num || 0);
}

function csvEscape(value) {
  const s = String(value ?? "");
  if (/[",\n]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

function buildCsvRows(items) {
  const header = [
    "タイトル",
    "チャンネル名",
    "再生回数",
    "いいね数",
    "コメント数",
    "登録者数",
    "エンゲージメント率",
    "動画の長さ(秒)",
    "公開日",
    "ジャンル",
    "タグ",
    "動画URL",
  ];
  const rows = items.map((item) => {
    const categoryName = CATEGORY_MAP[item.category_id] || "不明";
    return [
      item.title || "",
      item.channel_title || "",
      item.view_count || 0,
      item.like_count || 0,
      item.comment_count || 0,
      item.subscriber_count || 0,
      (Number(item.engagement_rate || 0) * 100).toFixed(2) + "%",
      item.duration_seconds || 0,
      item.published_at || "",
      categoryName,
      (item.tags || []).join("|"),
      item.video_url || "",
    ];
  });
  return [header, ...rows].map((line) => line.map(csvEscape).join(",")).join("\n");
}

function exportCsv(items) {
  if (!items.length) {
    statusEl.textContent = "エクスポート対象がありません。先に検索してください。";
    return;
  }
  const csv = buildCsvRows(items);
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const timestamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  const filename = `youtube_research_${timestamp}.csv`;
  const blob = new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  statusEl.textContent = `${items.length}件をCSVエクスポートしました`;
}

function exportXlsx(items) {
  if (!items.length) {
    statusEl.textContent = "エクスポート対象がありません。先に検索してください。";
    return;
  }
  const header = [
    "タイトル", "チャンネル名", "再生回数", "いいね数", "コメント数",
    "登録者数", "エンゲージメント率", "動画の長さ(秒)", "公開日", "ジャンル", "タグ", "動画URL",
  ];
  const rows = items.map((item) => [
    item.title || "",
    item.channel_title || "",
    item.view_count || 0,
    item.like_count || 0,
    item.comment_count || 0,
    item.subscriber_count || 0,
    Number(item.engagement_rate || 0) * 100,
    item.duration_seconds || 0,
    item.published_at || "",
    CATEGORY_MAP[item.category_id] || "不明",
    (item.tags || []).join("|"),
    item.video_url || "",
  ]);
  const ws = XLSX.utils.aoa_to_sheet([header, ...rows]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "検索結果");
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const timestamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  XLSX.writeFile(wb, `youtube_research_${timestamp}.xlsx`);
  statusEl.textContent = `${items.length}件をExcelエクスポートしました`;
}

function formatViewCount(n) {
  if (n >= 100000000) return (n / 100000000).toFixed(1).replace(/\.0$/, "") + "億";
  if (n >= 10000) return (n / 10000).toFixed(1).replace(/\.0$/, "") + "万";
  if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, "") + "千";
  return String(n);
}

function createViewHistogram(values) {
  if (!values.length) return { labels: [], counts: [], ranges: [] };
  // 固定の区間で分類
  const bins = [
    { label: "0-1千", min: 0, max: 1000 },
    { label: "1千-1万", min: 1000, max: 10000 },
    { label: "1万-10万", min: 10000, max: 100000 },
    { label: "10万-50万", min: 100000, max: 500000 },
    { label: "50万-100万", min: 500000, max: 1000000 },
    { label: "100万-500万", min: 1000000, max: 5000000 },
    { label: "500万-1000万", min: 5000000, max: 10000000 },
    { label: "1000万-1億", min: 10000000, max: 100000000 },
    { label: "1億以上", min: 100000000, max: Infinity },
  ];
  const counts = bins.map(() => 0);
  values.forEach((v) => {
    for (let i = 0; i < bins.length; i++) {
      if (v >= bins[i].min && v < bins[i].max) { counts[i]++; break; }
      if (i === bins.length - 1 && v >= bins[i].min) { counts[i]++; }
    }
  });
  // 値が0の区間を除外（先頭・末尾のみ）
  let start = 0, end = bins.length - 1;
  while (start < end && counts[start] === 0) start++;
  while (end > start && counts[end] === 0) end--;
  return {
    labels: bins.slice(start, end + 1).map((b) => b.label),
    counts: counts.slice(start, end + 1),
    ranges: bins.slice(start, end + 1).map((b) => `${b.min}-${b.max === Infinity ? 999999999999 : b.max}`),
  };
}

function createHistogram(values, binCount = 8) {
  if (!values.length) return { labels: [], counts: [] };
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    return { labels: [`${min}`], counts: [values.length] };
  }
  const width = (max - min) / binCount;
  const counts = new Array(binCount).fill(0);
  values.forEach((v) => {
    const idx = Math.min(Math.floor((v - min) / width), binCount - 1);
    counts[idx] += 1;
  });
  const labels = counts.map((_, i) => {
    const start = min + i * width;
    const end = start + width;
    return `${Math.round(start)}-${Math.round(end)}`;
  });
  return { labels, counts };
}

function destroyCharts() {
  Object.keys(charts).forEach((key) => {
    if (charts[key]) {
      charts[key].destroy();
      charts[key] = null;
    }
  });
}

function chartOptions(titleX, titleY, indexAxis = "x") {
  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  const textColor = isLight ? "#111111" : "#f1f1f1";
  const gridColor = isLight ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.08)";
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis,
    plugins: {
      legend: { display: false, labels: { color: textColor } },
    },
    scales: {
      x: {
        ticks: { color: textColor },
        grid: { color: gridColor },
        title: { display: true, text: titleX, color: textColor },
      },
      y: {
        ticks: { color: textColor },
        grid: { color: gridColor },
        title: { display: true, text: titleY, color: textColor },
      },
    },
    datasets: {
      bar: {
        barPercentage: 0.6,
        categoryPercentage: 0.8,
      },
    },
  };
}

function renderTrendCharts(items) {
  if (typeof Chart === "undefined") return;
  destroyCharts();

  const categoryCounts = {};
  items.forEach((item) => {
    const key = CATEGORY_MAP[item.category_id] || "不明";
    categoryCounts[key] = (categoryCounts[key] || 0) + 1;
  });
  const categoryLabels = Object.keys(categoryCounts).sort((a, b) => categoryCounts[b] - categoryCounts[a]);
  const categoryValues = categoryLabels.map((k) => categoryCounts[k]);

  charts.category = new Chart(categoryChartCanvas, {
    type: "bar",
    data: {
      labels: categoryLabels,
      datasets: [{
        data: categoryValues,
        backgroundColor: graphColor,
      }],
    },
    options: {
      ...chartOptions("件数", "カテゴリ", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clickedCategory = categoryLabels[index];
          const categoryId = CATEGORY_NAME_TO_ID[clickedCategory];
          if (categoryId) {
            categoryFilterInput.value = categoryId;
            runSearch(new Event("submit"));
          }
        }
      },
    },
  });

  // 頻出タグ TOP15
  const tagCounts = {};
  items.forEach((item) => {
    (item.tags || []).forEach((tag) => {
      const t = tag.toLowerCase().trim();
      if (t) tagCounts[t] = (tagCounts[t] || 0) + 1;
    });
  });
  const sortedTags = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);
  const tagLabels = sortedTags.map(([tag]) => tag);
  const tagValues = sortedTags.map(([, count]) => count);

  charts.tag = new Chart(tagChartCanvas, {
    type: "bar",
    data: {
      labels: tagLabels,
      datasets: [{
        data: tagValues,
        backgroundColor: graphColor,
      }],
    },
    options: {
      ...chartOptions("件数", "タグ", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clickedTag = tagLabels[index];
          chartFilter.tag = chartFilter.tag === clickedTag ? null : clickedTag;
          rerenderWithEngagementFilter();
        }
      },
    },
  });

  // 再生回数分布（単位自動切り替え）
  const viewValues = items.map((i) => Number(i.view_count || 0));
  const viewMax = Math.max(...viewValues, 0);
  const viewUnit = viewMax >= 100000000 ? 100000000 : 10000;
  const viewUnitLabel = viewMax >= 100000000 ? "億" : "万";
  const viewHist = createHistogram(viewValues.map((v) => v / viewUnit), 8);
  // ラベルを単位表記に
  viewHist.labels = viewHist.labels.map((l) => {
    const [a, b] = l.split("-");
    const val = Number(b);
    return `~${viewMax >= 100000000 ? val.toFixed(1) : Math.round(val)}${viewUnitLabel}`;
  });
  viewHist.labels.reverse();
  viewHist.counts.reverse();
  // フィルター用に元の値のレンジを保持
  const viewRangesRaw = createHistogram(viewValues, 8);
  charts.view = new Chart(viewChartCanvas, {
    type: "bar",
    data: {
      labels: viewHist.labels,
      datasets: [{
        data: viewHist.counts,
        backgroundColor: graphColor,
      }],
    },
    options: {
      ...chartOptions("件数", "再生回数レンジ", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const label = viewRangesRaw.labels[index];
          chartFilter.viewRange = chartFilter.viewRange === label ? null : label;
          rerenderWithEngagementFilter();
        }
      },
    },
  });

  const engHist = createHistogram(items.map((i) => Number(i.engagement_rate || 0)), 7);
  const engLabelsRaw = [...engHist.labels];
  engHist.labels = engHist.labels.map((l) => {
    const [a, b] = l.split("-");
    return `~${Number(b).toFixed(1)}%`;
  });
  engHist.labels.reverse();
  engHist.counts.reverse();
  charts.engagement = new Chart(engagementChartCanvas, {
    type: "bar",
    data: {
      labels: engHist.labels,
      datasets: [{
        data: engHist.counts,
        backgroundColor: graphColor,
      }],
    },
    options: {
      ...chartOptions("件数", "エンゲージメント率レンジ", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const label = engLabelsRaw[index];
          chartFilter.engRange = chartFilter.engRange === label ? null : label;
          rerenderWithEngagementFilter();
        }
      },
    },
  });

  // 国別分布（言語から推定）
  const LANG_TO_COUNTRY = {
    "ja": "日本", "en": "英語圏", "ko": "韓国", "zh": "中国",
    "es": "スペイン語圏", "pt": "ポルトガル語圏", "hi": "インド",
    "fr": "フランス語圏", "de": "ドイツ語圏", "ar": "アラビア語圏",
    "ru": "ロシア", "id": "インドネシア", "th": "タイ", "vi": "ベトナム",
  };
  const countryCounts = {};
  items.forEach((item) => {
    const lang = (item.default_audio_language || item.default_language || "").toLowerCase().split("-")[0];
    const country = LANG_TO_COUNTRY[lang] || (lang ? lang.toUpperCase() : "不明");
    countryCounts[country] = (countryCounts[country] || 0) + 1;
  });
  const countryLabels = Object.keys(countryCounts).sort((a, b) => countryCounts[b] - countryCounts[a]);
  const countryValues = countryLabels.map((k) => countryCounts[k]);

  charts.country = new Chart(countryChartCanvas, {
    type: "bar",
    data: {
      labels: countryLabels,
      datasets: [{
        data: countryValues,
        backgroundColor: graphColor,
      }],
    },
    options: {
      ...chartOptions("件数", "国・言語", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clicked = countryLabels[index];
          chartFilter.country = chartFilter.country === clicked ? null : clicked;
          rerenderWithEngagementFilter();
        }
      },
    },
  });

  // 投稿時間帯分布（0〜23時）
  const hourCounts = new Array(24).fill(0);
  items.forEach((item) => {
    if (item.published_at) {
      const hour = new Date(item.published_at).getHours();
      hourCounts[hour]++;
    }
  });
  const hourLabels = Array.from({ length: 24 }, (_, i) => `${i}時`).reverse();
  hourCounts.reverse();

  const isLightTheme = document.documentElement.getAttribute("data-theme") === "light";
  const tc = isLightTheme ? "#111111" : "#f1f1f1";
  const gc = isLightTheme ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.08)";
  charts.hour = new Chart(hourChartCanvas, {
    type: "bar",
    data: {
      labels: hourLabels,
      datasets: [{
        data: hourCounts,
        backgroundColor: graphColor,
      }],
    },
    options: {
      ...chartOptions("件数", "時間帯", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          // hourLabels はreverse()されているので実際の時間に変換
          const hourNum = 23 - index;
          chartFilter.hour = chartFilter.hour === hourNum ? null : hourNum;
          rerenderWithEngagementFilter();
        }
      },
      scales: {
        x: {
          ticks: { color: tc },
          grid: { color: gc },
          title: { display: true, text: "件数", color: tc },
        },
        y: {
          ticks: {
            color: tc,
            callback: function(value, index) {
              return index % 2 === 0 ? this.getLabelForValue(value) : '';
            }
          },
          grid: { color: gc },
          title: { display: true, text: "時間帯", color: tc },
        },
      },
    },
  });

  // --- 国別再生回数分布 ---
  const LANG_TO_COUNTRY2 = {
    "ja": "日本", "en": "英語圏", "ko": "韓国", "zh": "中国",
    "es": "スペイン語圏", "pt": "ポルトガル語圏", "hi": "インド",
    "fr": "フランス語圏", "de": "ドイツ語圏", "ar": "アラビア語圏",
    "ru": "ロシア", "id": "インドネシア", "th": "タイ", "vi": "ベトナム",
  };
  const countryViewMap = {};
  items.forEach((item) => {
    const lang = (item.default_audio_language || item.default_language || "").toLowerCase().split("-")[0];
    const country = LANG_TO_COUNTRY2[lang] || (lang ? lang.toUpperCase() : "不明");
    countryViewMap[country] = (countryViewMap[country] || 0) + Number(item.view_count || 0);
  });
  const countryViewLabels = Object.keys(countryViewMap).sort((a, b) => countryViewMap[b] - countryViewMap[a]);
  const countryViewValues = countryViewLabels.map((k) => Math.round(countryViewMap[k] / 10000));

  charts.countryView = new Chart(countryViewChartCanvas, {
    type: "bar",
    data: {
      labels: countryViewLabels,
      datasets: [{
        data: countryViewValues,
        backgroundColor: graphColor,
      }],
    },
    options: {
      ...chartOptions("再生回数合計（万回）", "国・言語", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clicked = countryViewLabels[index];
          chartFilter.country = chartFilter.country === clicked ? null : clicked;
          rerenderWithEngagementFilter();
        }
      },
    },
  });

  // --- カテゴリ別再生回数分布 ---
  const categoryViewMap = {};
  items.forEach((item) => {
    const key = CATEGORY_MAP[item.category_id] || "不明";
    categoryViewMap[key] = (categoryViewMap[key] || 0) + Number(item.view_count || 0);
  });
  const categoryViewLabels = Object.keys(categoryViewMap).sort((a, b) => categoryViewMap[b] - categoryViewMap[a]);
  const categoryViewValues = categoryViewLabels.map((k) => Math.round(categoryViewMap[k] / 10000));

  charts.categoryView = new Chart(categoryViewChartCanvas, {
    type: "bar",
    data: {
      labels: categoryViewLabels,
      datasets: [{
        data: categoryViewValues,
        backgroundColor: graphColor,
      }],
    },
    options: {
      ...chartOptions("再生回数合計（万回）", "カテゴリ", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clickedCategory = categoryViewLabels[index];
          const categoryId = CATEGORY_NAME_TO_ID[clickedCategory];
          if (categoryId) {
            categoryFilterInput.value = categoryId;
            runSearch(new Event("submit"));
          }
        }
      },
    },
  });

  // --- カテゴリ別推定収益 ---
  const categoryRevenueMap = {};
  items.forEach((item) => {
    const key = CATEGORY_MAP[item.category_id] || "不明";
    const isShort = (item.duration_seconds || 0) <= 180;
    const cpm = isShort ? loadGenreCpm("short") : loadGenreCpm(item.category_id);
    const revenue = Math.round((Number(item.view_count || 0) * cpm) / 1000);
    categoryRevenueMap[key] = (categoryRevenueMap[key] || 0) + revenue;
  });
  const categoryRevenueLabels = Object.keys(categoryRevenueMap).sort((a, b) => categoryRevenueMap[b] - categoryRevenueMap[a]);
  const categoryRevenueValues = categoryRevenueLabels.map((k) => Math.round(categoryRevenueMap[k] / 1000));

  charts.categoryRevenue = new Chart(categoryRevenueChartCanvas, {
    type: "bar",
    data: {
      labels: categoryRevenueLabels,
      datasets: [{
        data: categoryRevenueValues,
        backgroundColor: graphColor,
      }],
    },
    options: {
      ...chartOptions("推定収益合計（千円）", "カテゴリ", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clickedCategory = categoryRevenueLabels[index];
          const categoryId = CATEGORY_NAME_TO_ID[clickedCategory];
          if (categoryId) {
            categoryFilterInput.value = categoryId;
            runSearch(new Event("submit"));
          }
        }
      },
    },
  });

  // --- 曜日別投稿動画数 ---
  const weekdayCounts = new Array(7).fill(0);
  items.forEach((item) => {
    if (item.published_at) {
      const day = new Date(item.published_at).getDay();
      weekdayCounts[day]++;
    }
  });
  const weekdayLabels = ["日", "月", "火", "水", "木", "金", "土"].reverse();
  weekdayCounts.reverse();

  charts.weekday = new Chart(weekdayChartCanvas, {
    type: "bar",
    data: {
      labels: weekdayLabels,
      datasets: [{
        data: weekdayCounts,
        backgroundColor: graphColor,
      }],
    },
    options: {
      ...chartOptions("件数", "曜日", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          // weekdayLabels はreverse()されているので実際の曜日番号に変換
          const dayNum = 6 - index;
          chartFilter.weekday = chartFilter.weekday === dayNum ? null : dayNum;
          rerenderWithEngagementFilter();
        }
      },
    },
  });

  // --- タイトル頻出ワード TOP15 ---
  const TITLE_STOPWORDS = new Set([
    "の","と","は","を","に","が","で","から","まで","より","や","へ","も","です","ます",
    "する","こと","ある","いる","なる","れる","よう","これ","それ","あれ","ここ","そこ","あそこ",
    "この","その","あの",
    "the","a","an","is","are","was","were","be","been","being","have","has","had",
    "do","does","did","will","would","could","should","may","might","must","shall","can",
    "need","dare","ought","used","to","of","in","for","on","with","at","by","from","as",
    "into","through","during","before","after","above","below","between","under","again",
    "further","then","once","here","there","when","where","why","how","all","each","few",
    "more","most","other","some","such","no","nor","not","only","own","same","so","than",
    "too","very","just","and","but","if","or","because","until","while","what","which",
    "who","whom","whose","this","that","these","those","am","you","your","i","my","me",
    "we","our","us","they","their","them","he","him","his","she","her","it","its"
  ]);
  const titleWordCounts = {};
  items.forEach((item) => {
    const words = (item.title || "")
      .split(/[\s\u3000\u00a0]+/)
      .map((w) => w.replace(/[「」【】『』（）()[\]{}《》〈〉、。,.!?！？・:：;；\-_~～|｜]/g, "").toLowerCase())
      .filter((w) => w.length >= 2 && !/^\d+$/.test(w) && !TITLE_STOPWORDS.has(w));
    words.forEach((w) => { titleWordCounts[w] = (titleWordCounts[w] || 0) + 1; });
  });
  const sortedTitleWords = Object.entries(titleWordCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);
  const titleWordLabels = sortedTitleWords.map(([w]) => w);
  const titleWordValues = sortedTitleWords.map(([, c]) => c);

  charts.titleWord = new Chart(titleWordChartCanvas, {
    type: "bar",
    data: {
      labels: titleWordLabels,
      datasets: [{
        data: titleWordValues,
        backgroundColor: graphColor,
      }],
    },
    options: {
      ...chartOptions("件数", "ワード", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clickedWord = titleWordLabels[index];
          chartFilter.titleWord = chartFilter.titleWord === clickedWord ? null : clickedWord;
          rerenderWithEngagementFilter();
        }
      },
    },
  });

  // --- 動画の長さと再生回数の相関（散布図） ---
  const isLightCorr = document.documentElement.getAttribute("data-theme") === "light";
  const tcCorr = isLightCorr ? "#111111" : "#f1f1f1";
  const gcCorr = isLightCorr ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.08)";
  const corrViewMax = Math.max(...items.map((i) => Number(i.view_count || 0)), 0);
  const corrViewUnit = corrViewMax >= 100000000 ? 100000000 : 10000;
  const corrViewUnitLabel = corrViewMax >= 100000000 ? "億" : "万";
  const correlationData = items.map((item) => ({
    x: Math.round((item.duration_seconds || 0) / 60),
    y: Math.round((item.view_count || 0) / corrViewUnit),
    title: item.title || "",
    videoId: (item.video_url || "").replace("https://www.youtube.com/watch?v=", ""),
  }));
  charts.correlation = new Chart(correlationChartCanvas, {
    type: "scatter",
    data: {
      datasets: [{
        data: correlationData,
        backgroundColor: graphColor,
        pointRadius: 5,
        pointHoverRadius: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick: function(event, elements) {
        if (elements.length > 0) {
          const idx = elements[0].index;
          const dataPoint = correlationData[idx];
          if (dataPoint.videoId) {
            openVideoPreview(dataPoint.videoId, dataPoint.title, `https://www.youtube.com/watch?v=${dataPoint.videoId}`);
          }
        }
      },
      onHover: function(event, elements) {
        event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              const raw = context.raw;
              return [`タイトル: ${raw.title}`, `長さ: ${raw.x}分`, `再生回数: ${corrViewMax >= 100000000 ? raw.y.toFixed(1) : raw.y}`];
            },
          },
        },
      },
      scales: {
        x: {
          ticks: { color: tcCorr },
          grid: { color: gcCorr },
          title: { display: true, text: "動画の長さ（分）", color: tcCorr },
        },
        y: {
          ticks: { color: tcCorr, callback: function(value) { return value.toFixed(1) + corrViewUnitLabel; } },
          grid: { color: gcCorr },
          title: { display: true, text: "再生回数", color: tcCorr },
        },
      },
    },
  });
  applyGraphVisibility();
}

function applyListSort(items) {
  const { key, asc } = listSortState;
  if (!key) return items;
  const sorted = [...items];
  sorted.sort((a, b) => {
    let va, vb;
    if (key === 'revenue') {
      const isShortA = (a.duration_seconds || 0) <= 180;
      const isShortB = (b.duration_seconds || 0) <= 180;
      va = (a.view_count || 0) * (isShortA ? loadGenreCpm('short') : loadGenreCpm(a.category_id)) / 1000;
      vb = (b.view_count || 0) * (isShortB ? loadGenreCpm('short') : loadGenreCpm(b.category_id)) / 1000;
    } else if (key === 'published_at') {
      va = new Date(a.published_at).getTime();
      vb = new Date(b.published_at).getTime();
    } else {
      va = a[key] || 0;
      vb = b[key] || 0;
    }
    if (va < vb) return asc ? -1 : 1;
    if (va > vb) return asc ? 1 : -1;
    return 0;
  });
  return sorted;
}

function renderTop10Results(items) {
  const top10El = document.getElementById("top10-results");
  const top10Header = document.getElementById("top10-header");
  if (!top10El || !top10Header) return;

  const top10 = items.slice(0, 10);
  if (!top10.length) {
    top10El.style.display = "none";
    top10Header.style.display = "none";
    return;
  }

  top10Header.style.display = "";
  top10El.style.display = "flex";

  const scrollBtn = document.getElementById("scroll-to-results-btn");
  if (scrollBtn && !scrollBtn._scrollListenerAdded) {
    scrollBtn.addEventListener("click", () => {
      const target = document.querySelector(".results-header");
      if (target) target.scrollIntoView({ behavior: "smooth" });
    });
    scrollBtn._scrollListenerAdded = true;
  }

  top10El.innerHTML = top10.map((item, index) => {
    const videoId = (item.video_url || "").replace("https://www.youtube.com/watch?v=", "");
    return `
      <article class="top10-card">
        <div class="top10-rank">${index + 1}</div>
        <div class="top10-thumb-wrap thumb-play-btn" data-video-id="${videoId}" data-title="${item.title.replace(/"/g, '&quot;')}" data-video-url="${item.video_url}" role="button" tabindex="0" aria-label="動画をプレビュー">
          <img src="${item.thumbnail_url}" alt="${item.title}" loading="lazy" />
          <span class="play-icon-overlay top10-play-icon" aria-hidden="true">&#9654;</span>
        </div>
        <div class="top10-meta">
          <a class="top10-title-text" href="${item.video_url}" target="_blank" rel="noopener noreferrer">${item.title}</a>
          <div class="top10-channel">${item.channel_title}</div>
          <div class="top10-views">${formatViewCount(item.view_count)}</div>
        </div>
      </article>
    `;
  }).join("");

  top10El.querySelectorAll(".thumb-play-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      openVideoPreview(btn.dataset.videoId, btn.dataset.title, btn.dataset.videoUrl);
    });
    btn.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openVideoPreview(btn.dataset.videoId, btn.dataset.title, btn.dataset.videoUrl);
      }
    });
  });
}

function renderResults(items) {
  renderTop10Results(items);
  if (viewMode === "list") {
    renderListResults(applyListSort(items));
  } else {
    renderCardResults(items);
  }
}

function renderListResults(items) {
  const resultsEl = document.getElementById("results");
  if (!items.length) {
    resultsEl.innerHTML = "<p>結果がありませんでした。</p>";
    return;
  }

  const rows = items.map((item) => {
    const published = new Date(item.published_at).toLocaleDateString("ja-JP");
    const engagementRate = Number(item.engagement_rate || 0);
    const isFav = isFavorite(item.video_url);
    const videoId = (item.video_url || "").replace("https://www.youtube.com/watch?v=", "");
    const isShort = (item.duration_seconds || 0) <= 180;
    const cpm = isShort ? loadGenreCpm("short") : loadGenreCpm(item.category_id);
    const revenueStr = formatRevenue(Number(item.view_count || 0), cpm);
    const categoryName = CATEGORY_MAP[item.category_id] || "不明";
    return `
      <tr class="list-row" data-video-id="${videoId}" data-title="${item.title.replace(/"/g, '&quot;')}" data-video-url="${item.video_url}">
        <td class="list-col-thumb">
          <div class="list-thumb-wrap thumb-play-btn" data-video-id="${videoId}" data-title="${item.title.replace(/"/g, '&quot;')}" data-video-url="${item.video_url}" role="button" tabindex="0" aria-label="動画をプレビュー">
            <img src="${item.thumbnail_url}" alt="${item.title}" loading="lazy" width="80" height="45" />
            <span class="play-icon-overlay list-play-icon" aria-hidden="true">&#9654;</span>
          </div>
        </td>
        <td class="list-col-title">
          <a class="title list-title" href="${item.video_url}" target="_blank" rel="noopener noreferrer">${item.title}</a>
        </td>
        <td class="list-col-channel">
          <button class="channel-link" data-channel-id="${item.channel_id || ""}">${item.channel_title}</button>
        </td>
        <td class="list-col-genre">${categoryName}</td>
        <td class="list-col-subs">${formatViewCount(item.subscriber_count)}</td>
        <td class="list-col-views">${formatViewCount(item.view_count)}</td>
        <td class="list-col-eng">${engagementRate.toFixed(1)}%</td>
        <td class="list-col-duration">${item.duration_seconds ? Math.floor(item.duration_seconds/60) + '分' + (item.duration_seconds%60) + '秒' : '-'}</td>
        <td class="list-col-date">${published}</td>
        <td class="list-col-revenue"><span class="revenue-badge">${revenueStr}</span></td>
      </tr>
    `;
  }).join("");

  const sortKey = listSortState.key;
  const sortAsc = listSortState.asc;
  function thSort(key, label, cls) {
    const isActive = sortKey === key;
    const dirClass = isActive ? (sortAsc ? ' sort-asc' : ' sort-desc') : '';
    return `<th class="${cls} sortable${dirClass}" data-sort-key="${key}">${label}</th>`;
  }

  resultsEl.innerHTML = `
    <div class="list-table-wrap">
      <table class="list-table">
        <thead>
          <tr>
            <th class="list-col-thumb">サムネイル</th>
            <th class="list-col-title">タイトル</th>
            <th class="list-col-channel">チャンネル</th>
            <th class="list-col-genre">ジャンル</th>
            ${thSort('subscriber_count', '登録者数', 'list-col-subs')}
            ${thSort('view_count', '再生回数', 'list-col-views')}
            ${thSort('engagement_rate', 'ENG率', 'list-col-eng')}
            ${thSort('duration_seconds', '長さ', 'list-col-duration')}
            ${thSort('published_at', '公開日', 'list-col-date')}
            ${thSort('revenue', '推定収益', 'list-col-revenue')}
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;

  resultsEl.querySelectorAll("th.sortable").forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.dataset.sortKey;
      if (listSortState.key === key) {
        listSortState.asc = !listSortState.asc;
      } else {
        listSortState.key = key;
        listSortState.asc = false;
      }
      rerenderWithEngagementFilter();
    });
  });

  resultsEl.querySelectorAll(".fav-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const videoId = btn.dataset.videoId;
      const item = latestItems.find((i) => (i.video_url || "").includes(videoId));
      if (item) toggleFavorite(item);
      const isFav = isFavorite(`https://www.youtube.com/watch?v=${videoId}`);
      btn.textContent = isFav ? "★" : "☆";
      btn.title = isFav ? "お気に入りを解除" : "お気に入りに追加";
      btn.classList.toggle("fav-btn--active", isFav);
      renderFavorites();
    });
  });

  resultsEl.querySelectorAll(".thumb-play-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      openVideoPreview(btn.dataset.videoId, btn.dataset.title, btn.dataset.videoUrl);
    });
    btn.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openVideoPreview(btn.dataset.videoId, btn.dataset.title, btn.dataset.videoUrl);
      }
    });
  });

  resultsEl.querySelectorAll(".channel-link").forEach((btn) => {
    btn.addEventListener("click", () => {
      const channelId = btn.dataset.channelId;
      if (channelId) openChannelModal(channelId);
    });
  });
}

function renderCardResults(items) {
  const resultsEl = document.getElementById("results");
  if (!items.length) {
    resultsEl.innerHTML = "<p>結果がありませんでした。</p>";
    return;
  }

  resultsEl.innerHTML = items
    .map((item) => {
      const tags = (item.tags || []).slice(0, 8).join(", ");
      const published = new Date(item.published_at).toLocaleString("ja-JP");
      const engagementRate = Number(item.engagement_rate || 0);
      const categoryName = CATEGORY_MAP[item.category_id] || "不明";
      const isFav = isFavorite(item.video_url);
      const videoId = (item.video_url || "").replace("https://www.youtube.com/watch?v=", "");
      // ショート動画（3分以下）はショートCPM、それ以外はジャンル別CPM
      const isShort = (item.duration_seconds || 0) <= 180;
      const cpm = isShort ? loadGenreCpm("short") : loadGenreCpm(item.category_id);
      const revenueStr = formatRevenue(Number(item.view_count || 0), cpm);
      return `
        <article class="card">
          <div class="card-thumb-wrap">
            <div class="thumb-play-btn" data-video-id="${videoId}" data-title="${item.title.replace(/"/g, '&quot;')}" data-video-url="${item.video_url}" role="button" tabindex="0" aria-label="動画をプレビュー">
              <img src="${item.thumbnail_url}" alt="${item.title}" loading="lazy" width="320" height="180" />
              <span class="play-icon-overlay" aria-hidden="true">&#9654;</span>
            </div>
            <button class="fav-btn${isFav ? " fav-btn--active" : ""}" data-video-id="${videoId}" title="${isFav ? "お気に入りを解除" : "お気に入りに追加"}">${isFav ? "★" : "☆"}</button>
          </div>
          <div class="meta">
            <a class="title" href="${item.video_url}" target="_blank" rel="noopener noreferrer">${item.title}</a>
            <div><button class="channel-link" data-channel-id="${item.channel_id || ""}">${item.channel_title}</button> / 公開日: ${published} / ジャンル: ${categoryName}</div>
            <div class="stats">
              再生回数: ${formatViewCount(item.view_count)} ・ いいね: ${fmt(item.like_count)} ・ コメント: ${fmt(item.comment_count)}
              <span class="revenue-badge" title="推定収益（参考値）: 再生回数 × CPM(${cpm}円) ÷ 1000">推定収益: ${revenueStr}<span class="revenue-note">※参考値</span></span>
            </div>
            <div class="stats">
              登録者数: ${fmt(item.subscriber_count)} ・ エンゲージメント率: ${engagementRate.toFixed(1)}% ・ 長さ: ${Math.floor((item.duration_seconds||0)/60)}分${(item.duration_seconds||0)%60}秒
            </div>
            <div class="description">${(item.description || "").slice(0, 40)}${(item.description || "").length > 40 ? "…" : ""}</div>
            <div class="tags">${tags ? `タグ: ${tags}` : "タグなし"}</div>
          </div>
        </article>
      `;
    })
    .join("");

  resultsEl.querySelectorAll(".fav-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const videoId = btn.dataset.videoId;
      const item = latestItems.find((i) => (i.video_url || "").includes(videoId));
      if (item) toggleFavorite(item);
      // Re-render just this button
      const isFav = isFavorite(`https://www.youtube.com/watch?v=${videoId}`);
      btn.textContent = isFav ? "★" : "☆";
      btn.title = isFav ? "お気に入りを解除" : "お気に入りに追加";
      btn.classList.toggle("fav-btn--active", isFav);
      renderFavorites();
    });
  });

  resultsEl.querySelectorAll(".thumb-play-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      openVideoPreview(btn.dataset.videoId, btn.dataset.title, btn.dataset.videoUrl);
    });
    btn.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openVideoPreview(btn.dataset.videoId, btn.dataset.title, btn.dataset.videoUrl);
      }
    });
  });

  resultsEl.querySelectorAll(".channel-link").forEach((btn) => {
    btn.addEventListener("click", () => {
      const channelId = btn.dataset.channelId;
      if (channelId) openChannelModal(channelId);
    });
  });
}

function applyEngagementFilter(items) {
  const filter = engagementFilterInput.value;
  const durationFilter = durationFilterInput.value;
  const viewCountMin = Number(viewCountFilterInput.value || 0) * 10000;

  let filtered = items;

  // 再生回数フィルター
  if (viewCountMin > 0) {
    filtered = filtered.filter((item) => (item.view_count || 0) >= viewCountMin);
  }

  // 言語フィルター（動画のdefault_audio_languageで判定、未設定は文字種フォールバック）
  const lang = languageFilterInput.value;
  if (lang !== "all") {
    filtered = filtered.filter((item) => {
      const audioLang = (item.default_audio_language || "").toLowerCase();
      const defLang = (item.default_language || "").toLowerCase();
      // 動画に言語情報が設定されている場合はそれで判定
      if (audioLang) return audioLang.startsWith(lang);
      if (defLang) return defLang.startsWith(lang);
      // 言語情報がない場合は文字種で判定
      const text = (item.title || "") + (item.description || "") + (item.channel_title || "");
      if (lang === "ja") return /[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]/.test(text);
      if (lang === "ko") return /[\uAC00-\uD7AF]/.test(text);
      if (lang === "zh") return /[\u4E00-\u9FFF]/.test(text) && !/[\u3040-\u309F\u30A0-\u30FF]/.test(text);
      if (lang === "ar") return /[\u0600-\u06FF]/.test(text);
      if (lang === "hi") return /[\u0900-\u097F]/.test(text);
      return true;
    });
  }

  // クライアント側で動画長さフィルターを追加適用
  if (durationFilter === "short") {
    filtered = filtered.filter((item) => (item.duration_seconds || 0) <= 180);
  } else if (durationFilter === "normal") {
    filtered = filtered.filter((item) => (item.duration_seconds || 0) > 180);
  }

  // タグフィルター（グラフクリック）
  if (chartFilter.tag) {
    filtered = filtered.filter((item) =>
      (item.tags || []).some((t) => t.toLowerCase().trim() === chartFilter.tag)
    );
  }

  // 再生回数レンジフィルター（グラフクリック）
  if (chartFilter.viewRange) {
    const [minStr, maxStr] = chartFilter.viewRange.split("-");
    const min = Number(minStr);
    const max = Number(maxStr);
    filtered = filtered.filter((item) => {
      const v = Number(item.view_count || 0);
      return v >= min && v < max;
    });
  }

  // エンゲージメント率レンジフィルター（グラフクリック）
  if (chartFilter.engRange) {
    const [minStr, maxStr] = chartFilter.engRange.split("-");
    const min = Number(minStr);
    const max = Number(maxStr);
    filtered = filtered.filter((item) => {
      const r = Number(item.engagement_rate || 0);
      return r >= min && r < max;
    });
  }

  // 国フィルター（グラフクリック）
  if (chartFilter.country) {
    const LANG_TO_COUNTRY = {
      "ja": "日本", "en": "英語圏", "ko": "韓国", "zh": "中国",
      "es": "スペイン語圏", "pt": "ポルトガル語圏", "hi": "インド",
      "fr": "フランス語圏", "de": "ドイツ語圏", "ar": "アラビア語圏",
      "ru": "ロシア", "id": "インドネシア", "th": "タイ", "vi": "ベトナム",
    };
    filtered = filtered.filter((item) => {
      const lang = (item.default_audio_language || item.default_language || "").toLowerCase().split("-")[0];
      const country = LANG_TO_COUNTRY[lang] || (lang ? lang.toUpperCase() : "不明");
      return country === chartFilter.country;
    });
  }

  // 曜日フィルター（グラフクリック）
  if (chartFilter.weekday !== null) {
    filtered = filtered.filter((item) => {
      if (!item.published_at) return false;
      return new Date(item.published_at).getDay() === chartFilter.weekday;
    });
  }

  // 時間帯フィルター（グラフクリック）
  if (chartFilter.hour !== null) {
    filtered = filtered.filter((item) => {
      if (!item.published_at) return false;
      return new Date(item.published_at).getHours() === chartFilter.hour;
    });
  }

  // タイトルキーワードフィルター（グラフクリック）
  if (chartFilter.titleWord) {
    filtered = filtered.filter((item) => {
      const title = (item.title || "").toLowerCase();
      return title.includes(chartFilter.titleWord);
    });
  }

  // エンゲージメント率フィルター
  if (filter !== "all") {
    filtered = filtered.filter((item) => {
      const rate = Number(item.engagement_rate || 0);
      if (filter === "level1") return rate >= 0.1 && rate < 0.3;
      if (filter === "level2") return rate >= 0.3 && rate < 0.7;
      if (filter === "level3") return rate >= 0.7 && rate < 1.5;
      if (filter === "level4") return rate >= 1.5 && rate < 3.0;
      if (filter === "level5") return rate >= 3.0;
      return true;
    });
  }

  return filtered;
}

function rerenderWithEngagementFilter() {
  const filtered = applyEngagementFilter(latestItems);
  const filters = [];
  if (chartFilter.tag) filters.push(`タグ: ${chartFilter.tag}`);
  if (chartFilter.viewRange) filters.push(`再生回数: ${chartFilter.viewRange}`);
  if (chartFilter.engRange) filters.push(`エンゲージメント率: ${chartFilter.engRange}`);
  if (chartFilter.country) filters.push(`国: ${chartFilter.country}`);
  if (chartFilter.weekday !== null) {
    const WEEKDAY_NAMES = ["日", "月", "火", "水", "木", "金", "土"];
    filters.push(`曜日: ${WEEKDAY_NAMES[chartFilter.weekday]}`);
  }
  if (chartFilter.hour !== null) filters.push(`時間帯: ${chartFilter.hour}時`);
  if (chartFilter.titleWord) filters.push(`タイトル: ${chartFilter.titleWord}`);
  const filterText = filters.length ? ` [${filters.join(" / ")}]` : "";
  statusEl.textContent = `${filtered.length}件表示中（取得: ${latestItems.length}件）${filterText}`;
  renderResults(filtered);
  renderTrendCharts(filtered);
}

async function runSearch(event) {
  if (event && event.preventDefault) event.preventDefault();
  if (compareMode) {
    return runCompareSearch();
  }
  const q = queryInput.value.trim();
  const maxResults = Number(maxResultsInput.value || 50);
  const durationFilter = durationFilterInput.value === "all" ? "" : durationFilterInput.value;
  const publishedAfter = publishedAfterInput.value;
  const categoryId = categoryFilterInput.value === "all" ? "" : categoryFilterInput.value;
  const language = languageFilterInput.value === "all" ? "" : languageFilterInput.value;
  const region = regionFilterInput.value === "all" ? "" : regionFilterInput.value;

  // キーワードもフィルターも未指定でも検索可能（グローバル人気動画を表示）

  statusEl.textContent = "検索中...";
  resultsEl.innerHTML = "";
  document.getElementById("search-loading").style.display = "flex";

  try {
    const params = new URLSearchParams({ q, max_results: String(maxResults) });
    if (durationFilter) params.set("duration_filter", durationFilter);
    if (publishedAfter) params.set("published_after", publishedAfter);
    if (categoryId) params.set("category_id", categoryId);
    if (language) params.set("language", language);
    if (region) params.set("region", region);
    const res = await fetch(`/api/search?${params.toString()}`);
    const data = await res.json();
    if (!res.ok) {
      if (res.status === 403 || res.status === 502 || (data.detail && (data.detail.includes("403") || data.detail.includes("Forbidden")))) {
        showQuotaAlert();
        return;
      }
      throw new Error(data.detail || "検索に失敗しました");
    }
    latestItems = data.items || [];
    chartFilter = { tag: null, viewRange: null, engRange: null, country: null, weekday: null, hour: null, titleWord: null };
    rerenderWithEngagementFilter();
    updateVideoSchema(latestItems);
    if (q) addToHistory(q, {
      publishedAfter,
      durationFilter,
      categoryId,
      language,
      region,
      maxResults: String(maxResults),
    });
    document.getElementById("search-loading").style.display = "none";
    fetchQuota();
  } catch (err) {
    document.getElementById("search-loading").style.display = "none";
    if (err.message.includes("403") || err.message.includes("Forbidden") || err.message.includes("quota")) {
      showQuotaAlert();
    } else {
      statusEl.textContent = err.message;
    }
  }
}

window.showQuotaAlert = showQuotaAlert;

// ===== 比較モード =====

function toggleCompareMode() {
  compareMode = !compareMode;
  const btn = document.getElementById("compare-toggle-btn");
  const area = document.getElementById("compare-inputs-area");
  const dot1 = document.getElementById("compare-dot-kw1");
  if (compareMode) {
    btn.classList.add("active");
    area.style.display = "";
    dot1.style.display = "inline-block";
    // summary を非表示リセット
    document.getElementById("comparison-summary").style.display = "none";
  } else {
    btn.classList.remove("active");
    area.style.display = "none";
    dot1.style.display = "none";
    comparisonData = [];
    document.getElementById("comparison-summary").style.display = "none";
  }
}

async function fetchKeywordData(keyword, colorObj) {
  const params = new URLSearchParams({
    q: keyword,
    max_results: String(Number(maxResultsInput.value || 50)),
    duration_filter: durationFilterInput.value,
    published_after: publishedAfterInput.value,
    category_id: categoryFilterInput.value,
    language: languageFilterInput.value,
    region: regionFilterInput.value,
  });
  const res = await fetch(`/api/search?${params.toString()}`);
  const data = await res.json();
  if (!res.ok) {
    if (res.status === 403 || res.status === 502 || (data.detail && (data.detail.includes("403") || data.detail.includes("Forbidden")))) {
      showQuotaAlert();
      throw new Error("quota");
    }
    throw new Error(data.detail || "検索に失敗しました");
  }
  return { keyword, color: colorObj, items: data.items || [] };
}

async function runCompareSearch() {
  const kw1 = queryInput.value.trim();
  const kw2 = (document.getElementById("query-2").value || "").trim();
  const kw3 = (document.getElementById("query-3").value || "").trim();
  const keywords = [kw1, kw2, kw3].filter(Boolean);

  if (keywords.length < 2) {
    statusEl.textContent = "比較モードは2つ以上のキーワードが必要です";
    return;
  }

  statusEl.textContent = "比較検索中...";
  resultsEl.innerHTML = "";
  document.getElementById("search-loading").style.display = "flex";

  try {
    const results = await Promise.all(
      keywords.map((kw, i) => fetchKeywordData(kw, COMPARE_COLORS[i]))
    );
    comparisonData = results;
    chartFilter = { tag: null, viewRange: null, engRange: null, country: null, weekday: null, hour: null, titleWord: null };

    document.getElementById("search-loading").style.display = "none";
    renderComparisonSummary(comparisonData);
    renderComparisonCharts(comparisonData);

    // 結果カードは最初のキーワードのみ
    latestItems = results[0].items;
    renderResults(latestItems);

    const kwLabels = keywords.join(" vs ");
    statusEl.textContent = `比較完了: ${kwLabels}（各キーワードの件数: ${results.map(r => r.items.length + "件").join(" / ")}）`;
    keywords.forEach((kw) => { if (kw) addToHistory(kw); });
    fetchQuota();
  } catch (err) {
    document.getElementById("search-loading").style.display = "none";
    if (err.message !== "quota") {
      statusEl.textContent = err.message;
    }
  }
}

function calcAvg(arr) {
  if (!arr.length) return 0;
  return arr.reduce((s, v) => s + v, 0) / arr.length;
}

function renderComparisonSummary(dataArr) {
  const el = document.getElementById("comparison-summary");
  const isLight = document.documentElement.getAttribute("data-theme") === "light";

  const rows = dataArr.map(({ keyword, color, items }) => {
    const avgView = Math.round(calcAvg(items.map((i) => Number(i.view_count || 0))));
    const avgEng  = (calcAvg(items.map((i) => Number(i.engagement_rate || 0)))).toFixed(1);
    const count   = items.length;
    // 推定平均収益: ジャンルが混在するため全体平均CPMで概算
    const avgCpm  = Math.round(calcAvg(items.map((i) => {
      const isShort = (i.duration_seconds || 0) <= 180;
      return isShort ? loadGenreCpm("short") : loadGenreCpm(i.category_id);
    })));
    const avgRev  = formatRevenue(avgView, avgCpm);
    return `<tr>
      <td><span class="compare-dot-inline" style="background:${color.label};"></span>${keyword}</td>
      <td>${formatViewCount(avgView)}</td>
      <td>${avgEng}%</td>
      <td>${count}件</td>
      <td>${avgRev}</td>
    </tr>`;
  }).join("");

  el.innerHTML = `
    <p class="compare-summary-title">比較サマリー</p>
    <table class="compare-summary-table">
      <thead>
        <tr>
          <th>キーワード</th>
          <th>平均再生数</th>
          <th>平均エンゲージメント率</th>
          <th>動画数</th>
          <th>推定平均収益</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
  el.style.display = "";
}

function renderComparisonCharts(dataArr) {
  if (typeof Chart === "undefined") return;
  destroyCharts();

  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  const textColor = isLight ? "#111111" : "#f1f1f1";

  function multiChartOptions(titleX, titleY, indexAxis = "x") {
    const base = chartOptions(titleX, titleY, indexAxis);
    base.plugins.legend = { display: true, labels: { color: textColor, boxWidth: 12, font: { size: 11 } } };
    return base;
  }

  // --- カテゴリ別 ---
  const allCats = [...new Set(
    dataArr.flatMap((d) => d.items.map((i) => CATEGORY_MAP[i.category_id] || "不明"))
  )].sort();
  charts.category = new Chart(categoryChartCanvas, {
    type: "bar",
    data: {
      labels: allCats,
      datasets: dataArr.map(({ keyword, color, items }) => ({
        label: keyword,
        data: allCats.map((cat) =>
          items.filter((i) => (CATEGORY_MAP[i.category_id] || "不明") === cat).length
        ),
        backgroundColor: color.solid,
      })),
    },
    options: {
      ...multiChartOptions("件数", "カテゴリ", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clickedCategory = allCats[index];
          const categoryId = CATEGORY_NAME_TO_ID[clickedCategory];
          if (categoryId) {
            categoryFilterInput.value = categoryId;
            runSearch(new Event("submit"));
          }
        }
      },
    },
  });

  // --- タグ TOP15（最初のキーワードベース） ---
  const tagCounts = {};
  dataArr[0].items.forEach((item) => {
    (item.tags || []).forEach((tag) => {
      const t = tag.toLowerCase().trim();
      if (t) tagCounts[t] = (tagCounts[t] || 0) + 1;
    });
  });
  const sortedTags = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);
  const tagLabels = sortedTags.map(([tag]) => tag);
  charts.tag = new Chart(tagChartCanvas, {
    type: "bar",
    data: {
      labels: tagLabels,
      datasets: dataArr.map(({ keyword, color, items }) => {
        const tc = {};
        items.forEach((item) => {
          (item.tags || []).forEach((tag) => {
            const t = tag.toLowerCase().trim();
            if (t) tc[t] = (tc[t] || 0) + 1;
          });
        });
        return {
          label: keyword,
          data: tagLabels.map((t) => tc[t] || 0),
          backgroundColor: color.solid,
        };
      }),
    },
    options: {
      ...multiChartOptions("件数", "タグ", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clickedTag = tagLabels[index];
          chartFilter.tag = chartFilter.tag === clickedTag ? null : clickedTag;
          rerenderWithEngagementFilter();
        }
      },
    },
  });

  // --- 再生回数分布（固定ビン） ---
  const VIEW_BINS = [
    { label: "0-1千",     min: 0,        max: 1000 },
    { label: "1千-1万",   min: 1000,     max: 10000 },
    { label: "1万-10万",  min: 10000,    max: 100000 },
    { label: "10万-50万", min: 100000,   max: 500000 },
    { label: "50万-100万",min: 500000,   max: 1000000 },
    { label: "100万-500万",min: 1000000, max: 5000000 },
    { label: "500万-1千万",min: 5000000, max: 10000000 },
    { label: "1千万-1億", min: 10000000, max: 100000000 },
    { label: "1億以上",   min: 100000000,max: Infinity },
  ];
  const viewBinsAllMax = Math.max(...dataArr.flatMap(({ items }) => items.map((i) => Number(i.view_count || 0))), 0);
  const viewBinsUnitLabel = viewBinsAllMax >= 100000000 ? "億" : "万";
  const viewBinsReversed = [...VIEW_BINS].reverse();
  charts.view = new Chart(viewChartCanvas, {
    type: "bar",
    data: {
      labels: viewBinsReversed.map((b) => b.label),
      datasets: dataArr.map(({ keyword, color, items }) => ({
        label: keyword,
        data: viewBinsReversed.map((b) =>
          items.filter((i) => {
            const v = Number(i.view_count || 0);
            return v >= b.min && (b.max === Infinity ? true : v < b.max);
          }).length
        ),
        backgroundColor: color.solid,
      })),
    },
    options: multiChartOptions("件数", "再生回数レンジ", "y"),
  });

  // --- エンゲージメント率分布（固定ビン） ---
  const ENG_BINS = [
    { label: "~0.1%",  min: 0,   max: 0.1 },
    { label: "~0.3%",  min: 0.1, max: 0.3 },
    { label: "~0.7%",  min: 0.3, max: 0.7 },
    { label: "~1.5%", min: 0.7, max: 1.5 },
    { label: "~3.0%", min: 1.5, max: 3.0 },
    { label: "~5.0%", min: 3.0, max: 5.0 },
    { label: "5.0%+", min: 5.0, max: Infinity },
  ];
  const engBinsReversed = [...ENG_BINS].reverse();
  charts.engagement = new Chart(engagementChartCanvas, {
    type: "bar",
    data: {
      labels: engBinsReversed.map((b) => b.label),
      datasets: dataArr.map(({ keyword, color, items }) => ({
        label: keyword,
        data: engBinsReversed.map((b) =>
          items.filter((i) => {
            const r = Number(i.engagement_rate || 0);
            return r >= b.min && (b.max === Infinity ? true : r < b.max);
          }).length
        ),
        backgroundColor: color.solid,
      })),
    },
    options: multiChartOptions("件数", "エンゲージメント率レンジ", "y"),
  });

  // --- 国別分布 ---
  const LANG_TO_COUNTRY = {
    "ja": "日本", "en": "英語圏", "ko": "韓国", "zh": "中国",
    "es": "スペイン語圏", "pt": "ポルトガル語圏", "hi": "インド",
    "fr": "フランス語圏", "de": "ドイツ語圏", "ar": "アラビア語圏",
    "ru": "ロシア", "id": "インドネシア", "th": "タイ", "vi": "ベトナム",
  };
  const allCountries = [...new Set(
    dataArr.flatMap((d) => d.items.map((i) => {
      const lang = (i.default_audio_language || i.default_language || "").toLowerCase().split("-")[0];
      return LANG_TO_COUNTRY[lang] || (lang ? lang.toUpperCase() : "不明");
    }))
  )].sort();
  charts.country = new Chart(countryChartCanvas, {
    type: "bar",
    data: {
      labels: allCountries,
      datasets: dataArr.map(({ keyword, color, items }) => {
        const cc = {};
        items.forEach((i) => {
          const lang = (i.default_audio_language || i.default_language || "").toLowerCase().split("-")[0];
          const country = LANG_TO_COUNTRY[lang] || (lang ? lang.toUpperCase() : "不明");
          cc[country] = (cc[country] || 0) + 1;
        });
        return {
          label: keyword,
          data: allCountries.map((c) => cc[c] || 0),
          backgroundColor: color.solid,
        };
      }),
    },
    options: {
      ...multiChartOptions("件数", "国・言語", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clicked = allCountries[index];
          chartFilter.country = chartFilter.country === clicked ? null : clicked;
          rerenderWithEngagementFilter();
        }
      },
    },
  });

  // --- 投稿時間帯 ---
  const hourLabels = Array.from({ length: 24 }, (_, i) => `${i}時`).reverse();
  const isLightTheme2 = document.documentElement.getAttribute("data-theme") === "light";
  const tc2 = isLightTheme2 ? "#111111" : "#f1f1f1";
  const gc2 = isLightTheme2 ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.08)";
  charts.hour = new Chart(hourChartCanvas, {
    type: "bar",
    data: {
      labels: hourLabels,
      datasets: dataArr.map(({ keyword, color, items }) => {
        const counts = new Array(24).fill(0);
        items.forEach((i) => {
          if (i.published_at) counts[new Date(i.published_at).getHours()]++;
        });
        counts.reverse();
        return { label: keyword, data: counts, backgroundColor: color.solid };
      }),
    },
    options: {
      ...multiChartOptions("件数", "時間帯", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const hourNum = 23 - index;
          chartFilter.hour = chartFilter.hour === hourNum ? null : hourNum;
          rerenderWithEngagementFilter();
        }
      },
      scales: {
        x: {
          ticks: { color: tc2 },
          grid: { color: gc2 },
          title: { display: true, text: "件数", color: tc2 },
        },
        y: {
          ticks: {
            color: tc2,
            callback: function(value, index) {
              return index % 2 === 0 ? this.getLabelForValue(value) : '';
            }
          },
          grid: { color: gc2 },
          title: { display: true, text: "時間帯", color: tc2 },
        },
      },
    },
  });

  // --- 国別再生回数分布 ---
  const allCountriesView = [...new Set(
    dataArr.flatMap((d) => d.items.map((i) => {
      const lang = (i.default_audio_language || i.default_language || "").toLowerCase().split("-")[0];
      return LANG_TO_COUNTRY[lang] || (lang ? lang.toUpperCase() : "不明");
    }))
  )].sort();
  charts.countryView = new Chart(countryViewChartCanvas, {
    type: "bar",
    data: {
      labels: allCountriesView,
      datasets: dataArr.map(({ keyword, color, items }) => {
        const m = {};
        items.forEach((i) => {
          const lang = (i.default_audio_language || i.default_language || "").toLowerCase().split("-")[0];
          const c = LANG_TO_COUNTRY[lang] || (lang ? lang.toUpperCase() : "不明");
          m[c] = (m[c] || 0) + Number(i.view_count || 0);
        });
        return { label: keyword, data: allCountriesView.map((c) => Math.round((m[c] || 0) / 10000)), backgroundColor: color.solid };
      }),
    },
    options: {
      ...multiChartOptions("再生回数合計（万回）", "国・言語", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clicked = allCountriesView[index];
          chartFilter.country = chartFilter.country === clicked ? null : clicked;
          rerenderWithEngagementFilter();
        }
      },
    },
  });

  // --- カテゴリ別再生回数分布 ---
  const allCatsView = [...new Set(
    dataArr.flatMap((d) => d.items.map((i) => CATEGORY_MAP[i.category_id] || "不明"))
  )].sort();
  charts.categoryView = new Chart(categoryViewChartCanvas, {
    type: "bar",
    data: {
      labels: allCatsView,
      datasets: dataArr.map(({ keyword, color, items }) => {
        const m = {};
        items.forEach((i) => {
          const k = CATEGORY_MAP[i.category_id] || "不明";
          m[k] = (m[k] || 0) + Number(i.view_count || 0);
        });
        return { label: keyword, data: allCatsView.map((k) => Math.round((m[k] || 0) / 10000)), backgroundColor: color.solid };
      }),
    },
    options: {
      ...multiChartOptions("再生回数合計（万回）", "カテゴリ", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clickedCategory = allCatsView[index];
          const categoryId = CATEGORY_NAME_TO_ID[clickedCategory];
          if (categoryId) {
            categoryFilterInput.value = categoryId;
            runSearch(new Event("submit"));
          }
        }
      },
    },
  });

  // --- カテゴリ別推定収益 ---
  const allCatsRev = [...new Set(
    dataArr.flatMap((d) => d.items.map((i) => CATEGORY_MAP[i.category_id] || "不明"))
  )].sort();
  charts.categoryRevenue = new Chart(categoryRevenueChartCanvas, {
    type: "bar",
    data: {
      labels: allCatsRev,
      datasets: dataArr.map(({ keyword, color, items }) => {
        const m = {};
        items.forEach((i) => {
          const k = CATEGORY_MAP[i.category_id] || "不明";
          const isShort = (i.duration_seconds || 0) <= 180;
          const cpm = isShort ? loadGenreCpm("short") : loadGenreCpm(i.category_id);
          m[k] = (m[k] || 0) + Math.round((Number(i.view_count || 0) * cpm) / 1000);
        });
        return { label: keyword, data: allCatsRev.map((k) => Math.round((m[k] || 0) / 1000)), backgroundColor: color.solid };
      }),
    },
    options: {
      ...multiChartOptions("推定収益合計（千円）", "カテゴリ", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clickedCategory = allCatsRev[index];
          const categoryId = CATEGORY_NAME_TO_ID[clickedCategory];
          if (categoryId) {
            categoryFilterInput.value = categoryId;
            runSearch(new Event("submit"));
          }
        }
      },
    },
  });

  // --- 曜日別投稿動画数 ---
  const weekdayLabelsComp = ["日", "月", "火", "水", "木", "金", "土"].reverse();
  charts.weekday = new Chart(weekdayChartCanvas, {
    type: "bar",
    data: {
      labels: weekdayLabelsComp,
      datasets: dataArr.map(({ keyword, color, items }) => {
        const counts = new Array(7).fill(0);
        items.forEach((i) => {
          if (i.published_at) counts[new Date(i.published_at).getDay()]++;
        });
        counts.reverse();
        return { label: keyword, data: counts, backgroundColor: color.solid };
      }),
    },
    options: {
      ...multiChartOptions("件数", "曜日", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const dayNum = 6 - index;
          chartFilter.weekday = chartFilter.weekday === dayNum ? null : dayNum;
          rerenderWithEngagementFilter();
        }
      },
    },
  });

  // --- タイトル頻出ワード TOP15 ---
  const TITLE_STOPWORDS_COMP = new Set([
    "の","と","は","を","に","が","で","から","まで","より","や","へ","も","です","ます",
    "する","こと","ある","いる","なる","れる","よう","これ","それ","あれ","ここ","そこ","あそこ",
    "この","その","あの",
    "the","a","an","is","are","was","were","be","been","being","have","has","had",
    "do","does","did","will","would","could","should","may","might","must","shall","can",
    "need","dare","ought","used","to","of","in","for","on","with","at","by","from","as",
    "into","through","during","before","after","above","below","between","under","again",
    "further","then","once","here","there","when","where","why","how","all","each","few",
    "more","most","other","some","such","no","nor","not","only","own","same","so","than",
    "too","very","just","and","but","if","or","because","until","while","what","which",
    "who","whom","whose","this","that","these","those","am","you","your","i","my","me",
    "we","our","us","they","their","them","he","him","his","she","her","it","its"
  ]);
  const titleWordCounts0 = {};
  dataArr[0].items.forEach((item) => {
    (item.title || "").split(/[\s\u3000\u00a0]+/)
      .map((w) => w.replace(/[「」【】『』（）()[\]{}《》〈〉、。,.!?！？・:：;；\-_~～|｜]/g, "").toLowerCase())
      .filter((w) => w.length >= 2 && !/^\d+$/.test(w) && !TITLE_STOPWORDS_COMP.has(w))
      .forEach((w) => { titleWordCounts0[w] = (titleWordCounts0[w] || 0) + 1; });
  });
  const titleWordLabelsComp = Object.entries(titleWordCounts0).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([w]) => w);
  charts.titleWord = new Chart(titleWordChartCanvas, {
    type: "bar",
    data: {
      labels: titleWordLabelsComp,
      datasets: dataArr.map(({ keyword, color, items }) => {
        const tc = {};
        items.forEach((item) => {
          (item.title || "").split(/[\s\u3000\u00a0]+/)
            .map((w) => w.replace(/[「」【】『』（）()[\]{}《》〈〉、。,.!?！？・:：;；\-_~～|｜]/g, "").toLowerCase())
            .filter((w) => w.length >= 2 && !/^\d+$/.test(w) && !TITLE_STOPWORDS_COMP.has(w))
            .forEach((w) => { tc[w] = (tc[w] || 0) + 1; });
        });
        return { label: keyword, data: titleWordLabelsComp.map((w) => tc[w] || 0), backgroundColor: color.solid };
      }),
    },
    options: {
      ...multiChartOptions("件数", "ワード", "y"),
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const clickedWord = titleWordLabelsComp[index];
          chartFilter.titleWord = chartFilter.titleWord === clickedWord ? null : clickedWord;
          rerenderWithEngagementFilter();
        }
      },
    },
  });

  // --- 動画の長さと再生回数の相関（散布図）比較版 ---
  const isLightComp = document.documentElement.getAttribute("data-theme") === "light";
  const tcComp = isLightComp ? "#111111" : "#f1f1f1";
  const gcComp = isLightComp ? "rgba(0,0,0,0.08)" : "rgba(255,255,255,0.08)";
  const compCorrViewMax = Math.max(...dataArr.flatMap(({ items }) => items.map((i) => Number(i.view_count || 0))), 0);
  const compCorrViewUnit = compCorrViewMax >= 100000000 ? 100000000 : 10000;
  const compCorrViewUnitLabel = compCorrViewMax >= 100000000 ? "億" : "万";
  charts.correlation = new Chart(correlationChartCanvas, {
    type: "scatter",
    data: {
      datasets: dataArr.map(({ keyword, color, items }) => ({
        label: keyword,
        data: items.map((item) => ({
          x: Math.round((item.duration_seconds || 0) / 60),
          y: Math.round((item.view_count || 0) / compCorrViewUnit),
          title: item.title || "",
          videoId: (item.video_url || "").replace("https://www.youtube.com/watch?v=", ""),
        })),
        backgroundColor: color.solid,
        pointRadius: 5,
        pointHoverRadius: 8,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick: function(event, elements) {
        if (elements.length > 0) {
          const el = elements[0];
          const dataPoint = el.element.$context.raw;
          if (dataPoint.videoId) {
            openVideoPreview(dataPoint.videoId, dataPoint.title, `https://www.youtube.com/watch?v=${dataPoint.videoId}`);
          }
        }
      },
      onHover: function(event, elements) {
        event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
      },
      plugins: {
        legend: { display: true, labels: { color: tcComp, boxWidth: 12, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: function(context) {
              const raw = context.raw;
              return [`[${context.dataset.label}] ${raw.title}`, `長さ: ${raw.x}分`, `再生回数: ${compCorrViewMax >= 100000000 ? raw.y.toFixed(1) : raw.y}`];
            },
          },
        },
      },
      scales: {
        x: {
          ticks: { color: tcComp },
          grid: { color: gcComp },
          title: { display: true, text: "動画の長さ（分）", color: tcComp },
        },
        y: {
          ticks: { color: tcComp, callback: function(value) { return value.toFixed(1) + compCorrViewUnitLabel; } },
          grid: { color: gcComp },
          title: { display: true, text: "再生回数", color: tcComp },
        },
      },
    },
  });
  applyGraphVisibility();
}

function showQuotaAlert() {
  statusEl.textContent = "APIクォータの上限に達しました";
  const existing = document.getElementById("quota-alert");
  if (existing) existing.remove();
  const alert = document.createElement("div");
  alert.id = "quota-alert";
  alert.className = "quota-alert";
  alert.innerHTML = `
    <div class="quota-alert-content">
      <h3>⚠️ APIクォータの上限に達しました</h3>
      <p>YouTube Data APIの1日あたりの使用上限を超えました。<br>新しいAPIキーを追加すると検索を続行できます。</p>
      <div class="quota-alert-buttons">
        <button id="quota-add-key" class="youtube-btn">APIキーを追加する</button>
        <button id="quota-dismiss" class="youtube-btn quota-dismiss-btn">閉じる</button>
      </div>
    </div>
  `;
  document.body.appendChild(alert);
  document.getElementById("quota-add-key").addEventListener("click", () => {
    alert.remove();
    settingsModal.style.display = "flex";
    loadKeys();
  });
  document.getElementById("quota-dismiss").addEventListener("click", () => {
    alert.remove();
  });
}

// --- お気に入り ---
const FAVORITES_KEY = "yt_favorites";
const FAVORITES_MAX = 50;
const favoritesSection = document.getElementById("favorites-section");
const favoritesList = document.getElementById("favorites-list");
const clearFavoritesBtn = document.getElementById("clear-favorites-btn");

function loadFavorites() {
  try {
    return JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveFavorites(favs) {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(favs));
}

function isFavorite(videoUrl) {
  return loadFavorites().some((f) => f.url === videoUrl);
}

function toggleFavorite(item) {
  let favs = loadFavorites();
  const idx = favs.findIndex((f) => f.url === item.video_url);
  if (idx !== -1) {
    favs.splice(idx, 1);
  } else {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const addedAt = `${now.getFullYear()}/${pad(now.getMonth() + 1)}/${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
    favs.unshift({
      url: item.video_url,
      title: item.title,
      thumbnail: item.thumbnail_url,
      channel: item.channel_title,
      addedAt,
    });
    if (favs.length > FAVORITES_MAX) favs = favs.slice(0, FAVORITES_MAX);
  }
  saveFavorites(favs);
}

function renderFavorites() {
  const favs = loadFavorites();
  if (!favs.length) {
    favoritesSection.style.display = "none";
    return;
  }
  favoritesSection.style.display = "";
  favoritesList.innerHTML = favs
    .map(
      (fav) => `
      <div class="fav-item">
        <a href="${fav.url}" target="_blank" rel="noopener noreferrer" class="fav-item-link">
          <img src="${fav.thumbnail}" alt="${fav.title}" loading="lazy" />
          <div class="fav-item-info">
            <span class="fav-item-title">${fav.title}</span>
            <span class="fav-item-channel">${fav.channel}</span>
          </div>
        </a>
        <button class="fav-remove-btn" data-url="${fav.url}" title="削除">&#x2715;</button>
      </div>`
    )
    .join("");
  favoritesList.querySelectorAll(".fav-remove-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      let favs2 = loadFavorites();
      favs2 = favs2.filter((f) => f.url !== btn.dataset.url);
      saveFavorites(favs2);
      renderFavorites();
      // Update star button in results if visible
      const videoId = btn.dataset.url.replace("https://www.youtube.com/watch?v=", "");
      const star = resultsEl.querySelector(`.fav-btn[data-video-id="${videoId}"]`);
      if (star) {
        star.textContent = "☆";
        star.title = "お気に入りに追加";
        star.classList.remove("fav-btn--active");
      }
    });
  });
}

clearFavoritesBtn.addEventListener("click", () => {
  localStorage.removeItem(FAVORITES_KEY);
  renderFavorites();
  // Reset all star buttons
  resultsEl.querySelectorAll(".fav-btn--active").forEach((btn) => {
    btn.textContent = "☆";
    btn.title = "お気に入りに追加";
    btn.classList.remove("fav-btn--active");
  });
});

// 初期表示
renderFavorites();

// --- 検索履歴 ---
const HISTORY_KEY = "yt_search_history";
const HISTORY_MAX = 20;
const historySection = document.getElementById("search-history-section");
const historyList = document.getElementById("search-history-list");
const clearHistoryBtn = document.getElementById("clear-history-btn");

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveHistory(history) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

function addToHistory(keyword, filters) {
  if (!keyword) return;
  let history = loadHistory();
  // 重複を削除して先頭に追加
  history = history.filter((item) => item.keyword !== keyword);
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const dateStr = `${now.getFullYear()}/${pad(now.getMonth() + 1)}/${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
  history.unshift({ keyword, date: dateStr, filters: filters || {} });
  if (history.length > HISTORY_MAX) history = history.slice(0, HISTORY_MAX);
  saveHistory(history);
  renderHistory();
  incrementKeywordCount(keyword);
  renderKeywordRanking();
}

function renderHistory() {
  const history = loadHistory();
  if (!history.length) {
    historySection.style.display = "none";
    return;
  }
  historySection.style.display = "";
  historyList.innerHTML = history
    .map((item, idx) => {
      const f = item.filters || {};
      const tags = [];
      if (f.publishedAfter) tags.push(`期間:${f.publishedAfter}`);
      if (f.durationFilter) tags.push(`時間:${f.durationFilter}`);
      if (f.categoryId) tags.push(`カテゴリ:${f.categoryId}`);
      if (f.language) tags.push(`言語:${f.language}`);
      if (f.region) tags.push(`地域:${f.region}`);
      const filterText = tags.length ? ` [${tags.join(", ")}]` : "";
      return `<button class="history-item" data-idx="${idx}">${item.date} - ${item.keyword}${filterText}</button>`;
    })
    .join("");
  historyList.querySelectorAll(".history-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const item = history[Number(btn.dataset.idx)];
      queryInput.value = item.keyword;
      const f = item.filters || {};
      publishedAfterInput.value = f.publishedAfter || "";
      durationFilterInput.value = f.durationFilter || "all";
      categoryFilterInput.value = f.categoryId || "all";
      languageFilterInput.value = f.language || "all";
      regionFilterInput.value = f.region || "all";
      if (f.maxResults) maxResultsInput.value = f.maxResults;
      chartFilter = { tag: null, viewRange: null, engRange: null, country: null, weekday: null, hour: null, titleWord: null };
      runSearch(new Event("submit"));
    });
  });
}

clearHistoryBtn.addEventListener("click", () => {
  localStorage.removeItem(HISTORY_KEY);
  renderHistory();
});

// 初期表示
renderHistory();

// --- 人気キーワードランキング ---
const KEYWORD_COUNTS_KEY = "yt_keyword_counts";
const RANKING_MAX = 10;
const popularKeywordsSection = document.getElementById("popular-keywords-section");
const popularKeywordsList = document.getElementById("popular-keywords-list");

function loadKeywordCounts() {
  try {
    return JSON.parse(localStorage.getItem(KEYWORD_COUNTS_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveKeywordCounts(counts) {
  localStorage.setItem(KEYWORD_COUNTS_KEY, JSON.stringify(counts));
}

function incrementKeywordCount(keyword) {
  if (!keyword) return;
  const counts = loadKeywordCounts();
  counts[keyword] = (counts[keyword] || 0) + 1;
  saveKeywordCounts(counts);
}

function getKeywordRanking() {
  const counts = loadKeywordCounts();
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, RANKING_MAX);
}

function renderKeywordRanking() {
  const ranking = getKeywordRanking();
  if (!ranking.length) {
    popularKeywordsSection.style.display = "none";
    return;
  }
  popularKeywordsSection.style.display = "";
  popularKeywordsList.innerHTML = ranking
    .map(([keyword, count], index) => {
      const rankClass = index === 0 ? " rank-1" : index === 1 ? " rank-2" : index === 2 ? " rank-3" : "";
      return `<li class="popular-keyword-item${rankClass}">
        <span class="popular-keyword-rank">${index + 1}</span>
        <button class="popular-keyword-btn" data-keyword="${keyword.replace(/"/g, "&quot;")}">${keyword}</button>
        <span class="popular-keyword-badge">${count}回</span>
      </li>`;
    })
    .join("");
  popularKeywordsList.querySelectorAll(".popular-keyword-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      queryInput.value = btn.dataset.keyword;
      runSearch(new Event("submit"));
    });
  });
}

// 初期表示
renderKeywordRanking();

form.addEventListener("submit", runSearch);
document.getElementById("compare-toggle-btn").addEventListener("click", toggleCompareMode);
engagementFilterInput.addEventListener("change", rerenderWithEngagementFilter);
durationFilterInput.addEventListener("change", () => { runSearch(new Event("submit")); });
viewCountFilterInput.addEventListener("input", rerenderWithEngagementFilter);
publishedAfterInput.addEventListener("change", () => { runSearch(new Event("submit")); });
languageFilterInput.addEventListener("change", () => { rerenderWithEngagementFilter(); runSearch(new Event("submit")); });
regionFilterInput.addEventListener("change", () => { runSearch(new Event("submit")); });
exportCsvBtn.addEventListener("click", () => exportCsv(applyEngagementFilter(latestItems)));
exportXlsxBtn.addEventListener("click", () => exportXlsx(applyEngagementFilter(latestItems)));

// --- 設定モーダル ---
const settingsBtn = document.getElementById("settings-btn");
const settingsModal = document.getElementById("settings-modal");
const modalCloseBtn = document.getElementById("modal-close-btn");
const keyListEl = document.getElementById("key-list");
const newKeyInput = document.getElementById("new-key-input");
const addKeyBtn = document.getElementById("add-key-btn");
const keyStatusEl = document.getElementById("key-status");

settingsBtn.addEventListener("click", () => {
  settingsModal.style.display = "flex";
  loadKeys();
  // Sync CPM input with stored value
  const cpmInput = document.getElementById("cpm-input");
  if (cpmInput) cpmInput.value = loadCpm();
  // Sync genre CPM inputs
  renderGenreCpmList();
});
modalCloseBtn.addEventListener("click", () => {
  settingsModal.style.display = "none";
});
settingsModal.addEventListener("click", (e) => {
  if (e.target === settingsModal) settingsModal.style.display = "none";
});

async function loadKeys() {
  try {
    const res = await fetch("/api/keys");
    const data = await res.json();
    keyListEl.innerHTML = "";
    data.keys.forEach((key) => {
      const div = document.createElement("div");
      div.className = "key-item";
      div.innerHTML = `<span>${key.masked}</span><button class="key-delete" data-index="${key.index}">削除</button>`;
      keyListEl.appendChild(div);
    });
    keyListEl.querySelectorAll(".key-delete").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const index = btn.dataset.index;
        const adminPw = document.getElementById("admin-password-input").value;
        const res = await fetch(`/api/keys/${index}`, {
          method: "DELETE",
          headers: { "X-Admin-Password": adminPw },
        });
        const data = await res.json();
        if (res.ok) {
          keyStatusEl.className = "key-status";
          keyStatusEl.textContent = data.message;
          loadKeys();
        } else {
          keyStatusEl.className = "key-status error";
          keyStatusEl.textContent = data.detail;
        }
      });
    });
    keyStatusEl.textContent = "";
  } catch (err) {
    keyStatusEl.className = "key-status error";
    keyStatusEl.textContent = "キーの取得に失敗しました";
  }
}

addKeyBtn.addEventListener("click", async () => {
  const key = newKeyInput.value.trim();
  if (!key) return;
  const adminPw = document.getElementById("admin-password-input").value;
  try {
    const res = await fetch("/api/keys", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Password": adminPw,
      },
      body: JSON.stringify({ key }),
    });
    const data = await res.json();
    if (res.ok) {
      keyStatusEl.className = "key-status";
      keyStatusEl.textContent = data.message;
      newKeyInput.value = "";
      loadKeys();
    } else {
      keyStatusEl.className = "key-status error";
      keyStatusEl.textContent = data.detail;
    }
  } catch (err) {
    keyStatusEl.className = "key-status error";
    keyStatusEl.textContent = "追加に失敗しました";
  }
});
categoryFilterInput.addEventListener("change", () => { runSearch(new Event("submit")); });

// --- CPM保存ボタン ---
const cpmInput = document.getElementById("cpm-input");
const cpmSaveBtn = document.getElementById("cpm-save-btn");
const cpmStatusEl = document.getElementById("cpm-status");

if (cpmSaveBtn) {
  cpmSaveBtn.addEventListener("click", () => {
    const val = Number(cpmInput.value);
    if (!val || val < 1 || val > 1000) {
      cpmStatusEl.className = "key-status error";
      cpmStatusEl.textContent = "1〜1000の範囲で入力してください";
      return;
  }
  saveCpm(val);
  cpmStatusEl.className = "key-status";
  cpmStatusEl.textContent = `CPMを ${val}円 に保存しました`;
  // 即座に表示に反映（再検索不要）
  const filtered = applyEngagementFilter(latestItems);
  renderResults(filtered);
  setTimeout(() => { cpmStatusEl.textContent = ""; }, 2000);
  });
}

// --- ジャンル別CPM ---
function renderGenreCpmList() {
  const listEl = document.getElementById("genre-cpm-list");
  if (!listEl) return;
  
  // CATEGORY_MAPのジャンル + その他・未分類
  const allGenres = { ...CATEGORY_MAP, "other": "その他・未分類" };
  
  listEl.innerHTML = Object.entries(allGenres).map(([id, name]) => {
    const currentVal = loadGenreCpm(id);
    const defaultVal = GENRE_CPM_DEFAULTS[id] || loadCpm();
    return `<div class="genre-cpm-row">
      <span class="genre-cpm-name">${name}</span>
      <input id="genre-cpm-${id}" type="number" min="1" max="100000" value="${currentVal}" data-default="${defaultVal}" />
      <span class="cpm-unit">円</span>
    </div>`;
  }).join("");
}

document.getElementById("genre-cpm-save-btn").addEventListener("click", () => {
  const statusEl = document.getElementById("genre-cpm-status");
  let hasError = false;
  Object.keys(GENRE_CPM_DEFAULTS).forEach((id) => {
    const input = document.getElementById(`genre-cpm-${id}`);
    if (input) {
      const val = Number(input.value);
      if (val >= 1) {
        saveGenreCpm(id, val);
      } else {
        hasError = true;
      }
    }
  });
  if (hasError) {
    statusEl.className = "key-status error";
    statusEl.textContent = "全て1以上の値を入力してください";
  } else {
    statusEl.className = "key-status";
    statusEl.textContent = "ジャンル別CPMを保存しました";
    const filtered = applyEngagementFilter(latestItems);
    renderResults(filtered);
    setTimeout(() => { statusEl.textContent = ""; }, 2000);
  }
});

document.getElementById("genre-cpm-reset-btn").addEventListener("click", () => {
  resetAllGenreCpm();
  renderGenreCpmList();
  const statusEl = document.getElementById("genre-cpm-status");
  statusEl.className = "key-status";
  statusEl.textContent = "全てデフォルト値に戻しました";
  setTimeout(() => { statusEl.textContent = ""; }, 2000);
});

// --- SEO: VideoObject スキーマ動的更新 ---
function updateVideoSchema(items) {
  const schemaEl = document.getElementById("video-schema");
  if (!schemaEl) return;
  if (!items || !items.length) {
    schemaEl.textContent = "";
    return;
  }
  const listItems = items.slice(0, 5).map((item, index) => {
    const obj = {
      "@type": "VideoObject",
      "position": index + 1,
      "name": item.title || "",
      "description": (item.description || "").slice(0, 200),
      "thumbnailUrl": item.thumbnail_url || "",
      "url": item.video_url || "",
    };
    if (item.published_at) {
      obj.uploadDate = item.published_at.split("T")[0];
    }
    if (item.duration_seconds) {
      const sec = Number(item.duration_seconds);
      const h = Math.floor(sec / 3600);
      const m = Math.floor((sec % 3600) / 60);
      const s = sec % 60;
      obj.duration = `PT${h ? h + "H" : ""}${m ? m + "M" : ""}${s}S`;
    }
    return obj;
  });
  const schema = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    "itemListElement": listItems,
  };
  schemaEl.textContent = JSON.stringify(schema, null, 2);
}

// --- 動画プレビューモーダル ---
function openVideoPreview(videoId, title, videoUrl) {
  if (!videoId) return;
  // 既存の iframe を削除して再生停止
  videoModalPlayer.innerHTML = "";
  // iframe を生成
  const iframe = document.createElement("iframe");
  iframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;
  iframe.title = title || "YouTube動画";
  iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
  iframe.allowFullscreen = true;
  iframe.style.cssText = "position:absolute;top:0;left:0;width:100%;height:100%;border:0;";
  videoModalPlayer.appendChild(iframe);
  videoModalTitle.textContent = title || "";
  videoModalLink.href = videoUrl || `https://www.youtube.com/watch?v=${videoId}`;
  videoPreviewModal.style.display = "flex";
  document.body.style.overflow = "hidden";
}

function closeVideoPreview() {
  videoModalPlayer.innerHTML = "";
  videoPreviewModal.style.display = "none";
  document.body.style.overflow = "";
}

// --- グラフカラーピッカー ---
(function initGraphColorPicker() {
  const colorInput = document.getElementById("graph-color-input");
  const resetBtn = document.getElementById("graph-color-reset-btn");
  if (!colorInput || !resetBtn) return;

  // 初期値を現在の graphColor から設定
  colorInput.value = rgbaToHex(graphColor);

  // カラーピッカー変更時に即座に適用
  colorInput.addEventListener("input", () => {
    graphColor = hexToRgba(colorInput.value, 0.8);
    localStorage.setItem(GRAPH_COLOR_KEY, graphColor);
    // 現在のモードに応じて再描画
    if (compareMode && comparisonData.length) {
      renderComparisonCharts(comparisonData);
    } else if (latestItems.length) {
      renderTrendCharts(applyEngagementFilter(latestItems));
    }
  });

  resetBtn.addEventListener("click", () => {
    graphColor = DEFAULT_GRAPH_COLOR;
    localStorage.removeItem(GRAPH_COLOR_KEY);
    colorInput.value = rgbaToHex(DEFAULT_GRAPH_COLOR);
    // 現在のモードに応じて再描画
    if (compareMode && comparisonData.length) {
      renderComparisonCharts(comparisonData);
    } else if (latestItems.length) {
      renderTrendCharts(applyEngagementFilter(latestItems));
    }
  });
})();

// --- 表示モード切替 ---
(function initViewToggle() {
  const cardBtn = document.getElementById("view-card-btn");
  const listBtn = document.getElementById("view-list-btn");
  const resultsEl = document.getElementById("results");
  if (!cardBtn || !listBtn) return;

  function applyViewMode(mode) {
    viewMode = mode;
    localStorage.setItem(VIEW_MODE_KEY, mode);
    listSortState = { key: null, asc: false };
    if (mode === "list") {
      cardBtn.classList.remove("view-toggle-btn--active");
      listBtn.classList.add("view-toggle-btn--active");
      resultsEl.classList.remove("results--card");
      resultsEl.classList.add("results--list");
    } else {
      listBtn.classList.remove("view-toggle-btn--active");
      cardBtn.classList.add("view-toggle-btn--active");
      resultsEl.classList.remove("results--list");
      resultsEl.classList.add("results--card");
    }
    // 現在の検索結果を再描画
    if (latestItems && latestItems.length) {
      renderResults(applyEngagementFilter(latestItems));
    }
  }

  // ページロード時に保存されたモードを適用（再描画はせず見た目だけ反映）
  if (viewMode === "list") {
    cardBtn.classList.remove("view-toggle-btn--active");
    listBtn.classList.add("view-toggle-btn--active");
    resultsEl.classList.remove("results--card");
    resultsEl.classList.add("results--list");
  }

  cardBtn.addEventListener("click", () => applyViewMode("card"));
  listBtn.addEventListener("click", () => applyViewMode("list"));
})();

async function openChannelModal(channelId) {
  const body = document.getElementById("channel-modal-body");
  channelModal.style.display = "flex";
  body.innerHTML = '<div class="channel-loading">読み込み中...</div>';
  try {
    const [infoRes, videosRes] = await Promise.all([
      fetch(`/api/channel/${channelId}`),
      fetch(`/api/channel/${channelId}/videos`),
    ]);

    if (!infoRes.ok) {
      const err = await infoRes.json();
      throw new Error(err.detail || "チャンネル情報の取得に失敗しました");
    }
    const info = await infoRes.json();
    const videos = videosRes.ok ? await videosRes.json() : [];

    const descShort = (info.description || "").slice(0, 100) + ((info.description || "").length > 100 ? "…" : "");
    const publishedYear = info.published_at ? new Date(info.published_at).getFullYear() + "年" : "不明";

    const videosHtml = videos.length
      ? videos.map((v) => `
        <div class="channel-video-item">
          <a href="${v.video_url}" target="_blank" rel="noopener noreferrer">
            <img class="channel-video-thumb" src="${v.thumbnail_url}" alt="${v.title}" loading="lazy" />
          </a>
          <div class="channel-video-info">
            <a class="channel-video-title" href="${v.video_url}" target="_blank" rel="noopener noreferrer">${v.title}</a>
            <span class="channel-video-meta">再生回数: ${formatViewCount(v.view_count)} ・ ${new Date(v.published_at).toLocaleDateString("ja-JP")}</span>
          </div>
        </div>`).join("")
      : "<p style='color:#888;font-size:13px;'>動画情報を取得できませんでした。</p>";

    body.innerHTML = `
      <div class="channel-profile">
        <img class="channel-avatar" src="${info.thumbnail_url}" alt="${info.title}" />
        <div class="channel-profile-info">
          <span class="channel-profile-name">${info.title}</span>
          ${info.custom_url ? `<span class="channel-custom-url">${info.custom_url}</span>` : ""}
        </div>
      </div>
      <div class="channel-stats-grid">
        <div class="channel-stat-box">
          <div class="channel-stat-value">${formatViewCount(info.subscriber_count)}</div>
          <div class="channel-stat-label">登録者数</div>
        </div>
        <div class="channel-stat-box">
          <div class="channel-stat-value">${formatViewCount(info.view_count)}</div>
          <div class="channel-stat-label">総再生回数</div>
        </div>
        <div class="channel-stat-box">
          <div class="channel-stat-value">${fmt(info.video_count)}</div>
          <div class="channel-stat-label">動画数</div>
        </div>
        <div class="channel-stat-box">
          <div class="channel-stat-value">${publishedYear}</div>
          <div class="channel-stat-label">開設年</div>
        </div>
      </div>
      ${descShort ? `<div class="channel-description">${descShort}</div>` : ""}
      <div class="channel-videos-title">最新動画</div>
      <div class="channel-videos-list">${videosHtml}</div>
      <a class="channel-page-btn" href="${info.channel_url}" target="_blank" rel="noopener noreferrer">YouTubeでチャンネルを開く</a>
    `;
  } catch (err) {
    body.innerHTML = `<div class="channel-error">${err.message}</div>`;
  }
}
