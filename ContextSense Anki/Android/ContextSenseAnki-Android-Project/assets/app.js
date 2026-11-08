(function () {
  "use strict";

  const STORAGE_KEY = "memorize-anki-v1";
  const BUNDLED_SEED_KEY = "memorize-anki-bundled-seed-2026-10-08";
  const DEFAULT_KNOWN_TARGET = 3;
  const DEFAULT_TTS_RATE = 0.9;
  const STUDY_IDLE_DELAY = 2000;
  const state = loadState();
  ensureLearningTarget();
  ensureTtsSetting();
  ensureWordForgetCounts();
  ensureWordCardPositions();
  ensureLanguageSetting();
  let session = null;
  let pendingDeckId = null;
  let pendingCombinedDeckId = null;
  let pendingEasyDeckId = null;
  let toastTimer = null;
  let transitionTimer = null;
  let ttsLoopTimer = null;
  let ttsRateRestartTimer = null;
  let ttsGeneration = 0;
  let studyTimerInterval = null;
  let studyTimerLastTick = 0;
  let studyTimerActiveUntil = 0;
  let studyTimerSavedSecond = -1;
  let wordCardCenterFrame = null;
  let wordCardCenterTimers = [];
  let wordCardPointerStartY = null;
  let wordCardPointerMoved = false;
  let wordCardManualCaptureUntil = 0;
  let wordCardPositionSaveTimer = null;
  let lastRenderedReviewType = null;
  let dashboardPositionFrame = null;
  let dashboardPositionTimers = [];

  const $ = (id) => document.getElementById(id);
  const views = [$("dashboard-view"), $("study-view"), $("complete-view")];

  const UI_TEXT = {
    zh: {
      languageSettings: "语言设置", language: "语言", chooseLanguage: "选择网页界面语言。", chinese: "中文", english: "English", close: "关闭",
      brand: "语境多感记忆卡", home: "返回数据页", exportCurrent: "导出当前卡片文件", addCards: "增加卡片", plus: "＋",
      heroCopy: "上传按规则整理的文本，卡片会自动生成并保存在当前设备。不同设备数据不连通，更换设备，请使用“备份数据”和“恢复数据”功能。",
      allCards: "全部卡片", imported: "已导入", learning: "待学习", unknownStatus: "状态 unknown", known: "已掌握", studyBefore: "学习前可设置", mastery: "掌握率", accumulating: "持续积累", cardLibrary: "卡片库", importedFiles: "已导入文件", backupAll: "备份全部数据", restore: "恢复数据", startAll: "开始全部学习", noCards: "还没有卡片", chooseFile: "选择文件", emptyHint: "点击右上角“增加卡片”，选择一个 TXT 文件。",
      templateSummary: "上传模板说明", templateFormat: "模板格式：txt文件", templateRule: "模板说明：每张卡片用 <code>===</code> 分隔", maskRule: "遮挡说明：需要遮挡的内容放在双花括号中。如 <code>{{拼写记忆的内容 / 解释内容}}</code>，第一个“/”前是拼写内容，后面是解释内容（可包含音标）。",
      studyBack: "结束学习并返回", pause: "⏸ 暂停", play: "▶ 播放", unsupportedSpeech: "不支持朗读", edit: "编辑", finish: "结束", speed: "朗读语速", reveal: "取消遮挡", hide: "进行遮挡", revealHint: "显示答案或单词详情", hideHint: "隐藏答案或单词详情", forgot: "忘记", remember: "记住", undo: "撤回上一次标记", undoHint: "恢复上一张卡片及学习记录", forgotHint: "3 张后再出现", rememberHint: "达到设定次数即掌握", complete: "本轮完成", completeTitle: "做得好，记忆又前进了一步。", continue: "继续学习", homeButton: "返回数据页",
      learningSettings: "学习设置", targetQuestion: "连续记住多少次后掌握？", targetDescription: "连续第 {n} 次记住后，卡片状态变为 <code>known</code>，不再出现。", cancel: "取消", startLearning: "开始学习", editor: "编辑卡片", editorHelp: "使用 <code>{{英文 /音标/ 中文}}</code> 添加遮挡；删除双花括号即可取消遮挡。", editorCount: "{n} 个遮挡", savedImmediately: "保存后立即生效", save: "保存修改", combined: "组合模式", combinedTitle: "设置学习与分组", combinedTarget: "连续记住次数", combinedTargetHint: "达到该次数后，句子卡片变为 <code>known</code>。", combinedGroup: "每组句子卡片数", combinedRange: "范围 1 到当前词库总卡片数。", startCombined: "开始组合学习", easy: "易忘词", easyTitle: "按遗忘次数复习", easyDescription: "单词按累计遗忘次数从高到低排列。", word: "单词/词组", forgetCount: "遗忘次数", start: "开始", resume: "继续", exportTitle: "导出当前卡片文件", selectAll: "全选", confirmExport: "确认导出", cards: "张", pending: "张待学习", delete: "删除", reset: "重置", exportWords: "导出生词", learn: "学习", continueLearn: "继续", review: "复习熟词", continueReview: "继续熟词", groupMode: "组合模式", noExport: "当前没有可导出的卡片文件", selectOne: "请至少选择一组卡片", groupExported: "已打包导出 {n} 组卡片",
    },
    en: {
      languageSettings: "Language", language: "Language", chooseLanguage: "Choose the web interface language.", chinese: "中文", english: "English", close: "Close",
      brand: "ContextSense Anki", home: "Return to dashboard", exportCurrent: "Export card files", addCards: "Add cards", plus: "+",
      heroCopy: "Upload a text file in the supported format to generate cards. Data is saved on this device. Different devices do not share data; use “Back up data” and “Restore data” when switching devices.",
      allCards: "All cards", imported: "Imported", learning: "To learn", unknownStatus: "Status: unknown", known: "Known", studyBefore: "Set before studying", mastery: "Mastery", accumulating: "Keep building", cardLibrary: "Card library", importedFiles: "Imported files", backupAll: "Back up all data", restore: "Restore data", startAll: "Study all", noCards: "No cards yet", chooseFile: "Choose file", emptyHint: "Click “Add cards” above and choose a TXT file.",
      templateSummary: "Upload template", templateFormat: "Template format: TXT file", templateRule: "Template rule: separate cards with <code>===</code>", maskRule: "Masking: put content to hide inside double braces. For example, <code>{{word to spell / explanation}}</code>; the text before the first “/” is the spelling answer, and the rest is its explanation (which may include phonetics).",
      studyBack: "End study and return", pause: "⏸ Pause", play: "▶ Play", unsupportedSpeech: "Speech unsupported", edit: "Edit", finish: "Finish", speed: "Speech rate", reveal: "Reveal", hide: "Mask", revealHint: "Show answer or word details", hideHint: "Hide answer or word details", forgot: "Forgot", remember: "Remember", undo: "Undo last mark", undoHint: "Restore the previous card and study record", forgotHint: "Show again after 3 cards", rememberHint: "Master after the set count", complete: "Round complete", completeTitle: "Great work—your memory moved forward.", continue: "Continue studying", homeButton: "Return to dashboard",
      learningSettings: "Study settings", targetQuestion: "How many consecutive remembers to master?", targetDescription: "After the {n}th consecutive remember, the card becomes <code>known</code> and leaves the queue.", cancel: "Cancel", startLearning: "Start studying", editor: "Edit card", editorHelp: "Use <code>{{English /phonetic/ Chinese}}</code> to add a mask; remove the braces to remove a mask.", editorCount: "{n} masks", savedImmediately: "Effective immediately after saving", save: "Save changes", combined: "Combined mode", combinedTitle: "Study and group settings", combinedTarget: "Consecutive remembers", combinedTargetHint: "Cards become <code>known</code> after this count.", combinedGroup: "Cards per group", combinedRange: "From 1 to the total cards in this deck.", startCombined: "Start combined study", easy: "Difficult words", easyTitle: "Review by forget count", easyDescription: "Words are ordered by cumulative forget count, highest first.", word: "Word/phrase", forgetCount: "Forget count", start: "Start", resume: "Resume", exportTitle: "Export card files", selectAll: "Select all", confirmExport: "Export selected", cards: "cards", pending: "to learn", delete: "Delete", reset: "Reset", exportWords: "Export words", learn: "Study", continueLearn: "Continue", review: "Review known", continueReview: "Continue review", groupMode: "Combined mode", noExport: "No card files to export", selectOne: "Select at least one card set", groupExported: "Exported {n} card sets",
    },
  };

  function ensureLanguageSetting() {
    if (state.language === "zh" || state.language === "en") return;
    state.language = "zh";
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function tr(key, values = {}) {
    const language = state.language === "en" ? "en" : "zh";
    let text = UI_TEXT[language][key] || UI_TEXT.zh[key] || key;
    Object.entries(values).forEach(([name, value]) => { text = text.replaceAll(`{${name}}`, String(value)); });
    return text;
  }

  function updateLanguageSelection() {
    $("language-zh-button").classList.toggle("is-selected", state.language === "zh");
    $("language-en-button").classList.toggle("is-selected", state.language === "en");
  }

  function applyLanguage(shouldRender = true) {
    const english = state.language === "en";
    document.documentElement.lang = english ? "en" : "zh-CN";
    document.title = english ? "ContextSense Anki" : "语境多感记忆卡";
    $("language-settings-button").textContent = tr("language");
    $("language-eyebrow").textContent = tr("language");
    $("language-title").textContent = tr("languageSettings");
    $("language-description").textContent = tr("chooseLanguage");
    $("language-zh-button").textContent = tr("chinese");
    $("language-en-button").textContent = tr("english");
    $("language-close-button").setAttribute("aria-label", tr("close"));
    $("home-link").setAttribute("aria-label", tr("home"));
    $("home-link").querySelector("span:last-child").textContent = tr("brand");
    $("export-current-button").textContent = tr("exportCurrent");
    $("add-button").innerHTML = `<span aria-hidden="true">${tr("plus")}</span> ${tr("addCards")}`;
    $("empty-add-button").textContent = tr("chooseFile");
    $("backup-button").textContent = tr("backupAll");
    $("restore-button").textContent = tr("restore");
    $("start-all-button").textContent = tr("startAll");
    $("empty-state").querySelector("h3").textContent = tr("noCards");
    $("empty-state").querySelector("p").textContent = tr("emptyHint");
    $("dashboard-view").querySelector(".panel-heading .eyebrow").textContent = tr("cardLibrary");
    $("dashboard-view").querySelector(".panel-heading h2").textContent = tr("importedFiles");
    const statCards = $("dashboard-view").querySelectorAll(".stat-card");
    [[tr("allCards"), tr("imported")], [tr("learning"), tr("unknownStatus")], [tr("known"), tr("studyBefore")], [tr("mastery"), tr("accumulating")]].forEach((labels, index) => {
      statCards[index].querySelector(".stat-label").textContent = labels[0];
      statCards[index].querySelector(".stat-hint").textContent = labels[1];
    });
    const formatHelp = $("dashboard-view").querySelector(".format-help");
    formatHelp.querySelector("summary").textContent = tr("templateSummary");
    formatHelp.querySelector("div").innerHTML = `<p>${tr("templateFormat")}</p><p>${tr("templateRule")}</p><p>${tr("maskRule")}</p><pre>There is a {{beautiful /ˈbjuːtɪfl/ 美丽的}} garden.\n===\nThis is the next {{card /kɑːd/ 卡片}}.</pre>`;
    $("back-button").setAttribute("aria-label", tr("studyBack"));
    $("edit-card-button").textContent = tr("edit");
    $("finish-button").textContent = tr("finish");
    document.querySelector(".tts-speed-control label").textContent = tr("speed");
    const left = $("forgot-button");
    const right = $("remember-button");
    left.querySelectorAll("span")[1].textContent = tr("forgot");
    right.querySelectorAll("span")[1].textContent = tr("remember");
    left.querySelector("small").textContent = tr("forgotHint");
    right.querySelector("small").textContent = tr("rememberHint");
    [["reveal-button", "reveal", "revealHint"], ["hide-button", "hide", "hideHint"]].forEach(([id, label, hint]) => {
      const button = $(id);
      button.querySelectorAll("span")[1].textContent = tr(label);
      button.querySelector("small").textContent = tr(hint);
    });
    $("undo-button").querySelectorAll("span")[1].textContent = tr("undo");
    $("undo-button").querySelector("small").textContent = tr("undoHint");
    $("complete-view").querySelector(".eyebrow").textContent = tr("complete");
    $("complete-view").querySelector("h1").textContent = tr("completeTitle");
    $("continue-button").textContent = tr("continue");
    $("complete-home-button").textContent = tr("homeButton");
    ["settings-close-button", "editor-close-button", "combined-close-button", "easy-words-close-button", "deck-export-close-button"].forEach((id) => $(id).setAttribute("aria-label", tr("close")));
    $("settings-start-button").textContent = tr("startLearning");
    $("settings-cancel-button").textContent = tr("cancel");
    $("settings-title").textContent = tr("targetQuestion");
    $("settings-description").innerHTML = tr("targetDescription", { n: `<strong id="target-count-display">${$("target-count-display").textContent}</strong>` });
    $("card-editor-modal").querySelector(".eyebrow").textContent = tr("editor");
    $("card-editor-modal").querySelector(".editor-help").innerHTML = tr("editorHelp");
    $("editor-save-button").textContent = tr("save");
    $("editor-cancel-button").textContent = tr("cancel");
    $("combined-close-button").parentElement.querySelector(".eyebrow").textContent = tr("combined");
    $("combined-title").textContent = tr("combinedTitle");
    $("combined-target-range").parentElement.parentElement.querySelector("label").textContent = tr("combinedTarget");
    $("combined-target-range").parentElement.parentElement.querySelector("p").innerHTML = tr("combinedTargetHint");
    $("combined-group-range").parentElement.parentElement.querySelector("label").textContent = tr("combinedGroup");
    $("combined-group-hint").textContent = tr("combinedRange");
    $("combined-start-button").textContent = tr("startCombined");
    $("combined-cancel-button").textContent = tr("cancel");
    $("easy-words-close-button").parentElement.querySelector(".eyebrow").textContent = tr("easy");
    $("easy-words-title").textContent = tr("easyTitle");
    const easyHeaders = $("easy-words-modal").querySelectorAll(".easy-words-head span");
    easyHeaders[0].textContent = tr("word");
    easyHeaders[1].textContent = tr("forgetCount");
    $("easy-words-start-button").textContent = tr("start");
    $("easy-words-cancel-button").textContent = tr("cancel");
    $("deck-export-title").textContent = tr("exportTitle");
    $("deck-export-select-all").querySelector("span").textContent = tr("selectAll");
    $("deck-export-cancel-button").textContent = tr("cancel");
    $("deck-export-confirm-button").textContent = tr("confirmExport");
    updateTtsButton();
    updateLanguageSelection();
    if (shouldRender) {
      renderDashboard();
      if (session && !$('study-view').hidden) renderCard();
    }
  }

  function loadState() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (saved && Array.isArray(saved.decks) && Array.isArray(saved.cards)) {
        if (!saved.activeSessions || typeof saved.activeSessions !== "object") saved.activeSessions = {};
        const hasSavedData = saved.decks.length > 0 || saved.cards.length > 0;
        const seedAlreadyHandled = localStorage.getItem(BUNDLED_SEED_KEY) === "done";
        if (hasSavedData || !window.BUNDLED_BACKUP || seedAlreadyHandled) {
          if (hasSavedData && window.BUNDLED_BACKUP && !seedAlreadyHandled) {
            localStorage.setItem(BUNDLED_SEED_KEY, "done");
          }
          return saved;
        }
      }
    } catch (_) {}

    try {
      const bundled = window.BUNDLED_BACKUP;
      if (bundled) {
        if (bundled.format && bundled.format !== "memorize-anki-backup") {
          throw new Error("预置数据不是记忆卡片备份文件");
        }
        const restored = validateBackup(bundled.data || bundled);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(restored));
        localStorage.setItem(BUNDLED_SEED_KEY, "done");
        return restored;
      }
    } catch (error) {
      console.error("无法载入 APK 预置数据", error);
    }
    return { decks: [], cards: [], activeSessions: {} };
  }

  function saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function ensureLearningTarget() {
    const target = Number(state.learningTarget);
    if (Number.isInteger(target) && target >= 1 && target <= 10) return;
    state.learningTarget = DEFAULT_KNOWN_TARGET;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function ensureTtsSetting() {
    let changed = false;
    if (typeof state.ttsEnabled !== "boolean") {
      state.ttsEnabled = true;
      changed = true;
    }
    const rate = Number(state.ttsRate);
    if (!Number.isFinite(rate) || rate < 0.5 || rate > 2) {
      state.ttsRate = DEFAULT_TTS_RATE;
      changed = true;
    }
    if (changed) localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function ensureWordForgetCounts() {
    if (!state.wordForgetCounts || typeof state.wordForgetCounts !== "object" || Array.isArray(state.wordForgetCounts)) {
      state.wordForgetCounts = {};
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }
  }

  function ensureWordCardPositions() {
    let changed = false;
    if (!state.wordCardPositions || typeof state.wordCardPositions !== "object" || Array.isArray(state.wordCardPositions)) {
      state.wordCardPositions = {};
      changed = true;
    }
    ["portrait", "landscape"].forEach((key) => {
      if (!Object.prototype.hasOwnProperty.call(state.wordCardPositions, key)) return;
      const ratio = Number(state.wordCardPositions[key]);
      if (!Number.isFinite(ratio) || ratio < -0.75 || ratio > 0.95) {
        delete state.wordCardPositions[key];
        changed = true;
      } else if (state.wordCardPositions[key] !== ratio) {
        state.wordCardPositions[key] = ratio;
        changed = true;
      }
    });
    if (changed) localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function uid(prefix) {
    return prefix + "-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
  }

  function showView(view) {
    if (view !== $("dashboard-view")) clearDashboardPositioning();
    views.forEach((item) => { item.hidden = item !== view; });
    if (view === $("dashboard-view")) scheduleDashboardPositioning();
  }

  function clearDashboardPositioning() {
    if (dashboardPositionFrame !== null) cancelAnimationFrame(dashboardPositionFrame);
    dashboardPositionFrame = null;
    dashboardPositionTimers.forEach((timer) => clearTimeout(timer));
    dashboardPositionTimers = [];
  }

  function positionDashboardAtFirstDeck() {
    const dashboard = $("dashboard-view");
    if (dashboard.hidden) return;
    const scrollingElement = document.scrollingElement || document.documentElement || document.body;
    const firstDeck = $("deck-list").querySelector(".deck-row");
    if (!firstDeck) {
      dashboard.style.paddingBottom = "";
      scrollingElement.scrollTop = 0;
      window.scrollTo(0, 0);
      return;
    }

    // A short dashboard may not otherwise have enough content below the first row
    // for the browser to align that row with the top of the viewport.
    dashboard.style.paddingBottom = "0px";
    const metrics = visualViewportMetrics();
    let currentScroll = Number(scrollingElement.scrollTop) || Number(window.pageYOffset) || 0;
    let firstRect = firstDeck.getBoundingClientRect();
    let targetScroll = Math.max(0, currentScroll + firstRect.top - metrics.top);
    const viewportHeight = Math.max(metrics.height, Number(scrollingElement.clientHeight) || 0);
    const missingRoom = Math.ceil(targetScroll + viewportHeight - scrollingElement.scrollHeight);
    if (missingRoom > 0) {
      dashboard.style.paddingBottom = `${missingRoom + 2}px`;
      currentScroll = Number(scrollingElement.scrollTop) || Number(window.pageYOffset) || 0;
      firstRect = firstDeck.getBoundingClientRect();
      targetScroll = Math.max(0, currentScroll + firstRect.top - metrics.top);
    }
    scrollingElement.scrollTop = targetScroll;
    window.scrollTo(0, targetScroll);
  }

  function scheduleDashboardPositioning() {
    clearDashboardPositioning();
    dashboardPositionFrame = requestAnimationFrame(() => {
      dashboardPositionFrame = null;
      positionDashboardAtFirstDeck();
    });
    [100, 350, 700].forEach((delay) => {
      const timer = setTimeout(() => {
        dashboardPositionTimers = dashboardPositionTimers.filter((item) => item !== timer);
        positionDashboardAtFirstDeck();
      }, delay);
      dashboardPositionTimers.push(timer);
    });
  }

  function handleDashboardViewportResize() {
    if (!$("dashboard-view").hidden) scheduleDashboardPositioning();
  }

  function clearWordCardPositioning() {
    if (wordCardCenterFrame !== null) cancelAnimationFrame(wordCardCenterFrame);
    wordCardCenterFrame = null;
    wordCardCenterTimers.forEach((timer) => clearTimeout(timer));
    wordCardCenterTimers = [];
  }

  function visualViewportMetrics() {
    const viewport = window.visualViewport;
    return {
      top: viewport ? Number(viewport.offsetTop) || 0 : 0,
      width: viewport ? Number(viewport.width) || window.innerWidth : window.innerWidth,
      height: viewport ? Number(viewport.height) || window.innerHeight : window.innerHeight,
    };
  }

  function wordCardOrientation(metrics) {
    return metrics.width >= metrics.height ? "landscape" : "portrait";
  }

  function savedWordCardTopRatio(metrics) {
    const ratio = Number(state.wordCardPositions[wordCardOrientation(metrics)]);
    return Number.isFinite(ratio) && ratio >= -0.75 && ratio <= 0.95 ? ratio : null;
  }

  function rememberAdjustedWordCardPosition() {
    if (lastRenderedReviewType !== "word" || $("study-view").hidden) return false;
    const flashcard = $("flashcard");
    if (!flashcard.classList.contains("word-card")) return false;
    const metrics = visualViewportMetrics();
    if (!metrics.height) return false;
    const rect = flashcard.getBoundingClientRect();
    const ratio = Math.max(-0.75, Math.min(0.95, (rect.top - metrics.top) / metrics.height));
    state.wordCardPositions[wordCardOrientation(metrics)] = ratio;
    saveState();
    return true;
  }

  function scheduleAdjustedWordCardPositionSave() {
    clearTimeout(wordCardPositionSaveTimer);
    wordCardPositionSaveTimer = setTimeout(() => {
      wordCardPositionSaveTimer = null;
      rememberAdjustedWordCardPosition();
    }, 90);
  }

  function flushAdjustedWordCardPosition() {
    const hasPendingAdjustment = wordCardPointerMoved || wordCardManualCaptureUntil > Date.now();
    clearTimeout(wordCardPositionSaveTimer);
    wordCardPositionSaveTimer = null;
    if (hasPendingAdjustment) rememberAdjustedWordCardPosition();
    wordCardManualCaptureUntil = 0;
    wordCardPointerStartY = null;
    wordCardPointerMoved = false;
  }

  function positionWordCardInViewport(expectedCardId) {
    if (!session || $("study-view").hidden) return;
    const card = currentCard();
    const flashcard = $("flashcard");
    if (!card || card.id !== expectedCardId || !flashcard.classList.contains("word-card")) return;
    const rect = flashcard.getBoundingClientRect();
    const metrics = visualViewportMetrics();
    const savedRatio = savedWordCardTopRatio(metrics);
    const targetTop = savedRatio === null
      ? metrics.top + (metrics.height - rect.height) / 2
      : metrics.top + metrics.height * savedRatio;
    const scrollingElement = document.scrollingElement || document.documentElement || document.body;
    const currentScroll = Number(scrollingElement.scrollTop) || Number(window.pageYOffset) || 0;
    const targetScroll = Math.max(0, currentScroll + rect.top - targetTop);
    scrollingElement.scrollTop = targetScroll;
    window.scrollTo(0, targetScroll);
  }

  function scheduleWordCardPositioning(expectedCardId) {
    clearWordCardPositioning();
    wordCardCenterFrame = requestAnimationFrame(() => {
      wordCardCenterFrame = null;
      positionWordCardInViewport(expectedCardId);
    });
    [80, 250, 600, 900].forEach((delay) => {
      const timer = setTimeout(() => {
        wordCardCenterTimers = wordCardCenterTimers.filter((item) => item !== timer);
        positionWordCardInViewport(expectedCardId);
      }, delay);
      wordCardCenterTimers.push(timer);
    });
  }

  function beginWordCardPositionGesture(event) {
    clearDashboardPositioning();
    if (isManagedTextInput(event.target)) {
      const hardwareConnected = setTextInputModeForCurrentKeyboard(event.target);
      if (hardwareConnected) hideSoftKeyboardForHardwareInput();
    }
    if (wordCardManualCaptureUntil > Date.now()) rememberAdjustedWordCardPosition();
    wordCardManualCaptureUntil = 0;
    wordCardPointerMoved = false;
    wordCardPointerStartY = lastRenderedReviewType === "word" && !$("study-view").hidden
      ? Number(event.clientY)
      : null;
    clearWordCardPositioning();
    recordStudyActivity();
  }

  function continueWordCardPositionGesture(event) {
    if (wordCardPointerStartY === null || lastRenderedReviewType !== "word") return;
    if (Math.abs(Number(event.clientY) - wordCardPointerStartY) < 5) return;
    wordCardPointerMoved = true;
    wordCardManualCaptureUntil = Date.now() + 800;
    clearWordCardPositioning();
    scheduleAdjustedWordCardPositionSave();
  }

  function endWordCardPositionGesture() {
    if (wordCardPointerMoved) {
      wordCardManualCaptureUntil = Date.now() + 800;
      scheduleAdjustedWordCardPositionSave();
    }
    wordCardPointerStartY = null;
    wordCardPointerMoved = false;
  }

  function noteWordCardWheelAdjustment() {
    clearDashboardPositioning();
    if (lastRenderedReviewType !== "word" || $("study-view").hidden) return;
    clearWordCardPositioning();
    wordCardManualCaptureUntil = Date.now() + 500;
    scheduleAdjustedWordCardPositionSave();
  }

  function captureWordCardPositionDuringManualScroll() {
    if (wordCardPointerStartY !== null && lastRenderedReviewType === "word") {
      wordCardPointerMoved = true;
      wordCardManualCaptureUntil = Date.now() + 800;
    }
    if (wordCardPointerMoved || wordCardManualCaptureUntil > Date.now()) {
      wordCardManualCaptureUntil = Date.now() + 300;
      scheduleAdjustedWordCardPositionSave();
    }
  }

  function formatStudyTime(milliseconds) {
    const totalSeconds = Math.floor(Math.max(0, milliseconds) / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return hours > 0
      ? [hours, minutes, seconds].map((value) => String(value).padStart(2, "0")).join(":")
      : [minutes, seconds].map((value) => String(value).padStart(2, "0")).join(":");
  }

  function studyTimerIsRunning(now = Date.now()) {
    return Boolean(session && !$("study-view").hidden && !document.hidden && now < studyTimerActiveUntil);
  }

  function renderStudyTimer(now = Date.now()) {
    const timer = $("study-timer");
    if (!timer) return;
    const running = studyTimerIsRunning(now);
    timer.textContent = `⏱ ${formatStudyTime((session && session.activeStudyMs) || 0)}${running ? "" : (state.language === "en" ? " (paused)" : "（暂停）")}`;
    timer.classList.toggle("is-paused", !running);
    timer.title = running
      ? (state.language === "en" ? "Running; pauses after 2 seconds without activity" : "正在计时；连续 2 秒无操作后暂停")
      : (state.language === "en" ? "Paused; interact with the page to resume" : "计时已暂停；操作页面后继续");
  }

  function accrueStudyTime(now = Date.now()) {
    if (!session || !studyTimerLastTick) return;
    const countUntil = Math.min(now, studyTimerActiveUntil);
    if (countUntil > studyTimerLastTick && !document.hidden && !$("study-view").hidden) {
      session.activeStudyMs += countUntil - studyTimerLastTick;
    }
    studyTimerLastTick = now;
  }

  function tickStudyTimer() {
    if (!session || $("study-view").hidden) return;
    const now = Date.now();
    accrueStudyTime(now);
    renderStudyTimer(now);
    const elapsedSecond = Math.floor(session.activeStudyMs / 1000);
    if (elapsedSecond !== studyTimerSavedSecond) {
      studyTimerSavedSecond = elapsedSecond;
      persistSession();
    }
  }

  function startStudyTimer() {
    if (!session) return;
    session.activeStudyMs = Math.max(0, Number(session.activeStudyMs) || 0);
    const now = Date.now();
    studyTimerLastTick = now;
    studyTimerActiveUntil = now + STUDY_IDLE_DELAY;
    studyTimerSavedSecond = Math.floor(session.activeStudyMs / 1000);
    clearInterval(studyTimerInterval);
    studyTimerInterval = setInterval(tickStudyTimer, 200);
    renderStudyTimer(now);
  }

  function recordStudyActivity() {
    if (!session || $("study-view").hidden || document.hidden) return;
    const now = Date.now();
    accrueStudyTime(now);
    studyTimerActiveUntil = now + STUDY_IDLE_DELAY;
    studyTimerLastTick = now;
    renderStudyTimer(now);
  }

  function pauseStudyTimer() {
    if (!session) return;
    const now = Date.now();
    accrueStudyTime(now);
    studyTimerActiveUntil = 0;
    studyTimerLastTick = now;
    renderStudyTimer(now);
    persistSession();
  }

  function stopStudyTimer() {
    if (session) accrueStudyTime(Date.now());
    clearInterval(studyTimerInterval);
    studyTimerInterval = null;
    studyTimerLastTick = 0;
    studyTimerActiveUntil = 0;
  }

  function toast(message) {
    const element = $("toast");
    element.textContent = message;
    element.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => element.classList.remove("show"), 2800);
  }

  function safeAction(action) {
    return function () {
      try {
        action();
      } catch (error) {
        console.error("操作失败", error);
        toast(`操作失败：${error && error.message ? error.message : "请重试"}`);
      }
    };
  }

  function ttsSupported() {
    return "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  }

  function speechTextForCard(card) {
    let speechContent = card.content;
    if (isTermReviewPhase() && session.queue[0] && session.queue[0].type === "sentence") {
      const source = state.cards.find((item) => item.id === session.queue[0].sourceCardId);
      if (source) speechContent = source.content;
    }
    return speechContent
      .replace(/\{\{([\s\S]*?)\}\}/g, (_, answer) => englishPart(answer.trim()))
      .replace(/\s+/g, " ")
      .replace(/\s+([,.!?;:])/g, "$1")
      .trim();
  }

  function updateTtsButton() {
    const button = $("tts-toggle-button");
    if (!button) return;
    const range = $("tts-speed-range");
    if (!ttsSupported()) {
      button.textContent = tr("unsupportedSpeech");
      button.disabled = true;
      button.classList.add("is-paused");
      button.setAttribute("aria-pressed", "false");
      if (range) range.disabled = true;
      return;
    }
    button.disabled = false;
    if (range) range.disabled = false;
    button.textContent = state.ttsEnabled ? tr("pause") : tr("play");
    button.classList.toggle("is-paused", !state.ttsEnabled);
    button.setAttribute("aria-pressed", String(state.ttsEnabled));
  }

  function formatTtsRate(rate) {
    return `${Number(rate).toFixed(2).replace(/0+$/, "").replace(/\.$/, "")}×`;
  }

  function updateTtsRateControl() {
    const range = $("tts-speed-range");
    if (!range) return;
    range.value = String(state.ttsRate);
    $("tts-speed-value").textContent = formatTtsRate(state.ttsRate);
  }

  function changeTtsRate(value) {
    state.ttsRate = Math.max(0.5, Math.min(2, Number(value) || DEFAULT_TTS_RATE));
    saveState();
    updateTtsRateControl();
    clearTimeout(ttsRateRestartTimer);
    if (state.ttsEnabled && currentCard() && !$("study-view").hidden) {
      ttsRateRestartTimer = setTimeout(startCardSpeech, 160);
    }
  }

  function stopCardSpeech() {
    ttsGeneration += 1;
    clearTimeout(ttsLoopTimer);
    clearTimeout(ttsRateRestartTimer);
    ttsLoopTimer = null;
    ttsRateRestartTimer = null;
    if (ttsSupported()) window.speechSynthesis.cancel();
  }

  function startCardSpeech() {
    stopCardSpeech();
    updateTtsButton();
    const card = currentCard();
    if (!state.ttsEnabled || !ttsSupported() || !card || $("study-view").hidden) return;
    const text = speechTextForCard(card);
    if (!text) return;
    const cardId = card.id;
    const generation = ttsGeneration;

    const speakOnce = () => {
      if (
        generation !== ttsGeneration ||
        !state.ttsEnabled ||
        $("study-view").hidden ||
        !currentCard() ||
        currentCard().id !== cardId
      ) return;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-GB";
      utterance.rate = state.ttsRate;
      utterance.onend = () => {
        if (generation !== ttsGeneration) return;
        ttsLoopTimer = setTimeout(speakOnce, 500);
      };
      utterance.onerror = (event) => {
        if (generation !== ttsGeneration || event.error === "canceled" || event.error === "interrupted") return;
        if (event.error === "not-allowed") {
          toast("浏览器阻止了自动朗读，请点击“播放”重试");
          return;
        }
        ttsLoopTimer = setTimeout(speakOnce, 500);
      };
      window.speechSynthesis.speak(utterance);
    };

    speakOnce();
  }

  function toggleTts() {
    if (!ttsSupported()) {
      toast("当前浏览器不支持网页朗读");
      return;
    }
    state.ttsEnabled = !state.ttsEnabled;
    saveState();
    updateTtsButton();
    if (state.ttsEnabled) {
      startCardSpeech();
    } else {
      stopCardSpeech();
    }
  }

  function splitCards(text) {
    return text
      .replace(/^\uFEFF/, "")
      .split(/\s*===\s*/g)
      .map((part) => part.trim())
      .filter(Boolean);
  }

  async function importFiles(fileList) {
    const files = Array.from(fileList || []);
    if (!files.length) return;
    let imported = 0;

    for (const file of files) {
      try {
        const text = await file.text();
        const count = addDeckFromText(file.name, text);
        if (!count) {
          toast(`${file.name} 中没有可用卡片`);
          continue;
        }
        imported += count;
      } catch (_) {
        toast(`无法读取 ${file.name}`);
      }
    }

    saveState();
    renderDashboard();
    scheduleDashboardPositioning();
    if (imported) toast(`已生成 ${imported} 张卡片`);
    $("file-input").value = "";
  }

  function addDeckFromText(name, text) {
    const contents = splitCards(text);
    if (!contents.length) return 0;
    const deckId = uid("deck");
    state.decks.push({ id: deckId, name, createdAt: Date.now() });
    contents.forEach((content, index) => {
      state.cards.push({
        id: uid("card"), deckId, content, order: index,
        status: "unknown", rememberStreak: 0, reviews: 0,
      });
    });
    return contents.length;
  }

  async function loadBundledFiles() {
    if (state.decks.length || !Array.isArray(window.BUNDLED_FILES)) return;
    let imported = 0;
    for (const item of window.BUNDLED_FILES) {
      try {
        const response = await fetch(encodeURIComponent(item.file));
        if (!response.ok) throw new Error("read failed");
        imported += addDeckFromText(item.name, await response.text());
      } catch (_) {
        toast(`预置文件 ${item.name} 载入失败`);
      }
    }
    saveState();
    renderDashboard();
    scheduleDashboardPositioning();
    if (imported) toast(`已载入 ${window.BUNDLED_FILES.length} 个预置文件，共 ${imported} 张卡片`);
  }

  function deckCards(deckId) {
    return state.cards.filter((card) => card.deckId === deckId);
  }

  function renderDashboard() {
    const total = state.cards.length;
    const known = state.cards.filter((card) => card.status === "known").length;
    const unknown = total - known;
    $("stat-total").textContent = total;
    $("stat-unknown").textContent = unknown;
    $("stat-known").textContent = known;
    $("stat-rate").textContent = total ? Math.round(known / total * 100) + "%" : "0%";
    $("export-current-button").disabled = state.decks.length === 0;
    $("start-all-button").disabled = unknown === 0;
    const savedAllSession = state.activeSessions[sessionKey(null)];
    $("start-all-button").textContent = savedAllSession && savedAllSession.queue && savedAllSession.queue.length
      ? `${tr("continueLearn")}${state.language === "en" ? " all" : "全部学习"}`
      : tr("startAll");

    const list = $("deck-list");
    list.innerHTML = "";
    if (!state.decks.length) $("dashboard-view").style.paddingBottom = "";
    state.decks.forEach((deck) => {
      const cards = deckCards(deck.id);
      const deckKnown = cards.filter((card) => card.status === "known").length;
      const percent = cards.length ? Math.round(deckKnown / cards.length * 100) : 0;
      const savedSession = state.activeSessions[sessionKey(deck.id)];
      const savedReview = state.activeSessions[sessionKey(deck.id, "knownReview")];
      const hasSavedSession = Boolean(savedSession && savedSession.queue && savedSession.queue.length);
      const hasSavedReview = Boolean(savedReview && savedReview.queue && savedReview.queue.length);
      const row = document.createElement("article");
      row.className = "deck-row";
      const cardSummary = state.language === "en"
        ? `${cards.length} cards · ${cards.length - deckKnown} to learn`
        : `${cards.length} 张卡片 · ${cards.length - deckKnown} 张待学习`;
      row.innerHTML = `
        <div class="deck-name">
          <span class="file-icon">TXT</span>
          <div><h3></h3><p>${cardSummary}</p></div>
        </div>
        <div class="deck-progress">
          <strong>${percent}% ${tr("known")}</strong>
          <div class="small-progress"><span style="width:${percent}%"></span></div>
        </div>
        <div class="deck-actions">
          <button class="deck-delete" type="button">${tr("delete")}</button>
          <button class="deck-reset" type="button">${tr("reset")}</button>
          <button class="deck-export" type="button">${tr("exportWords")}</button>
          <button class="deck-review" type="button">${hasSavedReview ? tr("continueReview") : tr("review")}</button>
          <button class="deck-easy" type="button">${tr("easy")}</button>
          <button class="deck-combined" type="button">${tr("groupMode")}</button>
          <button class="deck-start" type="button">${hasSavedSession ? tr("continueLearn") : tr("learn")}</button>
        </div>`;
      row.querySelector("h3").textContent = deck.name;
      row.querySelector(".deck-start").addEventListener("click", safeAction(() => openStudySettings(deck.id)));
      row.querySelector(".deck-delete").addEventListener("click", () => deleteDeck(deck.id));
      row.querySelector(".deck-reset").addEventListener("click", () => resetDeck(deck.id));
      row.querySelector(".deck-export").addEventListener("click", safeAction(() => exportDeckWords(deck.id)));
      row.querySelector(".deck-review").addEventListener("click", safeAction(() => startKnownReview(deck.id)));
      row.querySelector(".deck-easy").addEventListener("click", safeAction(() => openEasyWords(deck.id)));
      row.querySelector(".deck-combined").addEventListener("click", safeAction(() => openCombinedSettings(deck.id)));
      list.appendChild(row);
    });

    $("empty-state").hidden = state.decks.length > 0;
    list.hidden = state.decks.length === 0;
  }

  function deleteDeck(deckId) {
    const deck = state.decks.find((item) => item.id === deckId);
    if (!deck || !confirm(`确定删除“${deck.name}”及其所有学习记录吗？`)) return;
    state.decks = state.decks.filter((item) => item.id !== deckId);
    state.cards = state.cards.filter((card) => card.deckId !== deckId);
    delete state.activeSessions[sessionKey(deckId)];
    delete state.activeSessions[sessionKey(deckId, "knownReview")];
    delete state.activeSessions[sessionKey(deckId, "easyReview")];
    delete state.activeSessions[sessionKey(deckId, "combined")];
    delete state.wordForgetCounts[deckId];
    delete state.activeSessions[sessionKey(null)];
    saveState();
    renderDashboard();
    toast("已删除卡片文件");
  }

  function resetDeck(deckId) {
    const deck = state.decks.find((item) => item.id === deckId);
    if (!deck || !confirm(`确定重置“${deck.name}”的全部学习进度吗？卡片内容会保留。`)) return;
    deckCards(deckId).forEach((card) => {
      card.status = "unknown";
      card.rememberStreak = 0;
      card.reviews = 0;
    });
    delete state.activeSessions[sessionKey(deckId)];
    delete state.activeSessions[sessionKey(deckId, "knownReview")];
    delete state.activeSessions[sessionKey(deckId, "easyReview")];
    delete state.activeSessions[sessionKey(deckId, "combined")];
    delete state.wordForgetCounts[deckId];
    delete state.activeSessions[sessionKey(null)];
    saveState();
    renderDashboard();
    toast("学习进度已重置");
  }

  function exportDeckWords(deckId) {
    const deck = state.decks.find((item) => item.id === deckId);
    if (!deck) return;
    const words = [];
    const seen = new Set();
    const pattern = /\{\{([\s\S]*?)\}\}/g;

    deckCards(deckId)
      .slice()
      .sort((a, b) => a.order - b.order)
      .forEach((card) => {
        let match;
        pattern.lastIndex = 0;
        while ((match = pattern.exec(card.content)) !== null) {
          const word = englishPart(match[1].trim());
          const key = normalizedSpelling(word);
          if (word && !seen.has(key)) {
            seen.add(key);
            words.push(word);
          }
        }
      });

    if (!words.length) {
      toast("该文件中没有可导出的生词");
      return;
    }

    const content = "\uFEFF" + words.join("\r\n");
    const baseName = deck.name.replace(/\.txt$/i, "");
    const fileName = `${baseName}-生词.txt`;
    if (window.AndroidFileBridge && typeof window.AndroidFileBridge.saveTextFile === "function") {
      window.AndroidFileBridge.saveTextFile(fileName, "text/plain", content);
      toast("请选择生词文件的保存位置");
      return;
    }

    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast(`已导出 ${words.length} 个生词或词组`);
  }

  function exportDeckFileName(deckName) {
    const baseName = String(deckName || "卡片")
      .replace(/\.txt$/i, "")
      .replace(/[<>:"/\\|?*\x00-\x1f]/g, "_")
      .replace(/[. ]+$/g, "") || "卡片";
    return `${baseName}-导出.txt`;
  }

  function currentDeckText(deckId) {
    const contents = deckCards(deckId)
      .slice()
      .sort((left, right) => left.order - right.order)
      .map((card) => String(card.content || ""));
    return "\uFEFF" + contents.join("\r\n===\r\n");
  }

  function crc32(bytes) {
    if (!crc32.table) {
      crc32.table = Array.from({ length: 256 }, (_, value) => {
        let current = value;
        for (let bit = 0; bit < 8; bit += 1) {
          current = (current & 1) ? (0xedb88320 ^ (current >>> 1)) : (current >>> 1);
        }
        return current >>> 0;
      });
    }
    let value = 0xffffffff;
    bytes.forEach((byte) => { value = crc32.table[(value ^ byte) & 0xff] ^ (value >>> 8); });
    return (value ^ 0xffffffff) >>> 0;
  }

  function zipDateTime(date = new Date()) {
    const year = Math.max(1980, date.getFullYear());
    return {
      time: (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2),
      date: ((year - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate(),
    };
  }

  function joinByteArrays(parts) {
    const total = parts.reduce((sum, part) => sum + part.length, 0);
    const output = new Uint8Array(total);
    let offset = 0;
    parts.forEach((part) => {
      output.set(part, offset);
      offset += part.length;
    });
    return output;
  }

  function createZipArchive(files) {
    const encoder = new TextEncoder();
    const localParts = [];
    const centralParts = [];
    const timestamp = zipDateTime();
    let localOffset = 0;

    files.forEach((file) => {
      const nameBytes = encoder.encode(file.name);
      const dataBytes = encoder.encode(file.content);
      const checksum = crc32(dataBytes);
      const localHeader = new Uint8Array(30);
      const localView = new DataView(localHeader.buffer);
      localView.setUint32(0, 0x04034b50, true);
      localView.setUint16(4, 20, true);
      localView.setUint16(6, 0x0800, true);
      localView.setUint16(8, 0, true);
      localView.setUint16(10, timestamp.time, true);
      localView.setUint16(12, timestamp.date, true);
      localView.setUint32(14, checksum, true);
      localView.setUint32(18, dataBytes.length, true);
      localView.setUint32(22, dataBytes.length, true);
      localView.setUint16(26, nameBytes.length, true);
      localView.setUint16(28, 0, true);
      localParts.push(localHeader, nameBytes, dataBytes);

      const centralHeader = new Uint8Array(46);
      const centralView = new DataView(centralHeader.buffer);
      centralView.setUint32(0, 0x02014b50, true);
      centralView.setUint16(4, 20, true);
      centralView.setUint16(6, 20, true);
      centralView.setUint16(8, 0x0800, true);
      centralView.setUint16(10, 0, true);
      centralView.setUint16(12, timestamp.time, true);
      centralView.setUint16(14, timestamp.date, true);
      centralView.setUint32(16, checksum, true);
      centralView.setUint32(20, dataBytes.length, true);
      centralView.setUint32(24, dataBytes.length, true);
      centralView.setUint16(28, nameBytes.length, true);
      centralView.setUint16(30, 0, true);
      centralView.setUint16(32, 0, true);
      centralView.setUint16(34, 0, true);
      centralView.setUint16(36, 0, true);
      centralView.setUint32(38, 0, true);
      centralView.setUint32(42, localOffset, true);
      centralParts.push(centralHeader, nameBytes);
      localOffset += localHeader.length + nameBytes.length + dataBytes.length;
    });

    const centralDirectory = joinByteArrays(centralParts);
    const end = new Uint8Array(22);
    const endView = new DataView(end.buffer);
    endView.setUint32(0, 0x06054b50, true);
    endView.setUint16(4, 0, true);
    endView.setUint16(6, 0, true);
    endView.setUint16(8, files.length, true);
    endView.setUint16(10, files.length, true);
    endView.setUint32(12, centralDirectory.length, true);
    endView.setUint32(16, localOffset, true);
    endView.setUint16(20, 0, true);
    return joinByteArrays([...localParts, centralDirectory, end]);
  }

  function updateDeckExportSelection() {
    const boxes = Array.from($("deck-export-list").querySelectorAll('input[type="checkbox"]'));
    const selected = boxes.filter((box) => box.checked).length;
    const selectAll = $("deck-export-select-all");
    selectAll.checked = boxes.length > 0 && selected === boxes.length;
    selectAll.indeterminate = selected > 0 && selected < boxes.length;
    $("deck-export-confirm-button").disabled = selected === 0;
  }

  function openDeckExportModal() {
    const list = $("deck-export-list");
    list.innerHTML = "";
    state.decks.forEach((deck) => {
      const row = document.createElement("label");
      row.className = "deck-export-row";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = deck.id;
      checkbox.addEventListener("change", updateDeckExportSelection);
      const name = document.createElement("span");
      name.className = "deck-export-name";
      name.textContent = deck.name;
      const count = document.createElement("span");
      count.className = "deck-export-count";
      count.textContent = cardCountText(deckCards(deck.id).length);
      row.append(checkbox, name, count);
      list.appendChild(row);
    });
    if (!state.decks.length) {
      const empty = document.createElement("div");
      empty.className = "deck-export-empty";
      empty.textContent = tr("noExport");
      list.appendChild(empty);
    }
    $("deck-export-select-all").checked = false;
    $("deck-export-select-all").indeterminate = false;
    updateDeckExportSelection();
    $("deck-export-modal").hidden = false;
  }

  function closeDeckExportModal() {
    $("deck-export-modal").hidden = true;
  }

  function confirmDeckExport() {
    const selectedIds = Array.from($("deck-export-list").querySelectorAll('input[type="checkbox"]:checked'))
      .map((box) => box.value);
    if (!selectedIds.length) {
      toast(tr("selectOne"));
      return;
    }

    const usedNames = new Map();
    const files = selectedIds.map((deckId) => {
      const deck = state.decks.find((item) => item.id === deckId);
      let name = exportDeckFileName(deck ? deck.name : "卡片");
      const key = name.toLocaleLowerCase();
      const duplicateNumber = (usedNames.get(key) || 0) + 1;
      usedNames.set(key, duplicateNumber);
      if (duplicateNumber > 1) name = name.replace(/-导出\.txt$/i, `-${duplicateNumber}-导出.txt`);
      return { name, content: currentDeckText(deckId) };
    });
    const zipBytes = createZipArchive(files);
    const blob = new Blob([zipBytes], { type: "application/zip" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `当前卡片文件-${new Date().toISOString().slice(0, 10)}.zip`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    closeDeckExportModal();
    toast(tr("groupExported", { n: files.length }));
  }

  function downloadBackup() {
    const payload = {
      format: "memorize-anki-backup",
      version: 1,
      exportedAt: new Date().toISOString(),
      data: state,
    };
    const date = new Date().toISOString().slice(0, 10);
    const fileName = `记忆卡片-完整备份-${date}.json`;
    const json = JSON.stringify(payload, null, 2);
    if (window.AndroidFileBridge && typeof window.AndroidFileBridge.saveBackup === "function") {
      window.AndroidFileBridge.saveBackup(fileName, json);
      toast("请选择备份文件的保存位置");
      return;
    }

    const blob = new Blob([json], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast(`已备份 ${state.decks.length} 本词库、${state.cards.length} 张卡片`);
  }

  function validateBackup(candidate) {
    if (!candidate || !Array.isArray(candidate.decks) || !Array.isArray(candidate.cards)) {
      throw new Error("备份文件缺少词库或卡片数据");
    }
    const restored = JSON.parse(JSON.stringify(candidate));
    const deckIds = new Set();
    restored.decks.forEach((deck) => {
      if (!deck || typeof deck.id !== "string" || typeof deck.name !== "string" || deckIds.has(deck.id)) {
        throw new Error("备份中的词库数据无效");
      }
      deckIds.add(deck.id);
    });
    const cardIds = new Set();
    restored.cards.forEach((card) => {
      if (
        !card ||
        typeof card.id !== "string" ||
        typeof card.deckId !== "string" ||
        typeof card.content !== "string" ||
        !deckIds.has(card.deckId) ||
        cardIds.has(card.id)
      ) {
        throw new Error("备份中的卡片数据无效");
      }
      cardIds.add(card.id);
      card.status = card.status === "known" ? "known" : "unknown";
      card.rememberStreak = Math.max(0, Number(card.rememberStreak) || 0);
      card.reviews = Math.max(0, Number(card.reviews) || 0);
    });
    if (!restored.activeSessions || typeof restored.activeSessions !== "object" || Array.isArray(restored.activeSessions)) {
      restored.activeSessions = {};
    }
    return restored;
  }

  function restoreBackupText(rawText) {
    try {
      const parsed = JSON.parse(String(rawText || "").replace(/^\uFEFF/, ""));
      if (parsed.format && parsed.format !== "memorize-anki-backup") throw new Error("不是记忆卡片备份文件");
      const restored = validateBackup(parsed.data || parsed);
      const confirmed = confirm(
        `将恢复 ${restored.decks.length} 本词库、${restored.cards.length} 张卡片。\n\n` +
        "当前浏览器中的全部数据将被替换，是否继续？"
      );
      if (!confirmed) return;

      stopCardSpeech();
      session = null;
      Object.keys(state).forEach((key) => delete state[key]);
      Object.assign(state, restored);
      ensureLearningTarget();
      ensureTtsSetting();
      ensureWordForgetCounts();
      ensureWordCardPositions();
      ensureLanguageSetting();
      saveState();
      renderDashboard();
      updateTtsButton();
      updateTtsRateControl();
      showView($("dashboard-view"));
      toast(`恢复完成：${state.decks.length} 本词库、${state.cards.length} 张卡片`);
    } catch (error) {
      toast(`恢复失败：${error.message || "文件无法读取"}`);
    }
  }

  async function restoreBackup(file) {
    if (!file) return;
    try {
      restoreBackupText(await file.text());
    } catch (error) {
      toast(`恢复失败：${error.message || "文件无法读取"}`);
    } finally {
      $("restore-file-input").value = "";
    }
  }

  function chooseBackupFile() {
    if (window.AndroidFileBridge && typeof window.AndroidFileBridge.openBackup === "function") {
      window.AndroidFileBridge.openBackup();
      return;
    }
    $("restore-file-input").click();
  }

  window.onNativeBackupSelected = restoreBackupText;
  window.onNativeFileSaved = (fileName) => {
    toast(`已保存：${fileName || "文件"}`);
  };
  window.onNativeFileError = (message) => {
    toast(`文件操作失败：${message || "无法访问文件"}`);
  };

  function shuffle(items) {
    const result = items.slice();
    for (let index = result.length - 1; index > 0; index -= 1) {
      const swapIndex = Math.floor(Math.random() * (index + 1));
      [result[index], result[swapIndex]] = [result[swapIndex], result[index]];
    }
    return result;
  }

  function knownWordItems(deckId) {
    return knownWordItemsFromCards(deckCards(deckId).filter((card) => card.status === "known"));
  }

  function deckForgetCounts(deckId) {
    if (!state.wordForgetCounts[deckId] || typeof state.wordForgetCounts[deckId] !== "object") {
      state.wordForgetCounts[deckId] = {};
    }
    return state.wordForgetCounts[deckId];
  }

  function wordForgetCount(deckId, wordKey) {
    return Math.max(0, Number(deckForgetCounts(deckId)[wordKey]) || 0);
  }

  function setWordForgetCount(deckId, wordKey, count) {
    deckForgetCounts(deckId)[wordKey] = Math.max(0, Number(count) || 0);
  }

  function easyWordItems(deckId) {
    return knownWordItems(deckId).sort((left, right) => (
      wordForgetCount(deckId, right.key) - wordForgetCount(deckId, left.key)
    ));
  }

  function knownWordItemsFromCards(cards) {
    const occurrencesByWord = new Map();
    cards.forEach((card) => {
        const pattern = /\{\{([\s\S]*?)\}\}/g;
        let match;
        let clozeIndex = 0;
        while ((match = pattern.exec(card.content)) !== null) {
          const fullAnswer = match[1].trim();
          const word = englishPart(fullAnswer);
          const key = normalizedSpelling(word);
          if (word && key) {
            if (!occurrencesByWord.has(key)) occurrencesByWord.set(key, []);
            occurrencesByWord.get(key).push({
              word,
              fullAnswer,
              sourceCardId: card.id,
              clozeIndex,
            });
          }
          clozeIndex += 1;
        }
    });

    const selected = [];
    occurrencesByWord.forEach((occurrences, key) => {
      const occurrence = occurrences[Math.floor(Math.random() * occurrences.length)];
      const relationId = uid("known-word");
      selected.push({
        type: "word",
        id: `${relationId}-word`,
        relationId,
        key,
        ...occurrence,
      });
    });
    return shuffle(selected);
  }

  function startKnownReview(deckId) {
    const deck = state.decks.find((item) => item.id === deckId);
    if (!deck) return;
    const saved = state.activeSessions[sessionKey(deckId, "knownReview")];
    const sourceCardIds = new Set(deckCards(deckId).map((card) => card.id));
    const savedQueue = saved && Number(saved.logicVersion) >= 2 && Array.isArray(saved.queue)
      ? saved.queue.filter((item) => item && (item.type === "word" || item.type === "sentence") && sourceCardIds.has(item.sourceCardId))
      : [];
    const isResuming = savedQueue.length > 0;
    const queue = isResuming ? savedQueue : knownWordItems(deckId);
    if (!queue.length) {
      toast("当前词库没有可复习的熟词");
      return;
    }
    session = isResuming ? {
      ...saved,
      mode: "knownReview",
      deckId,
      deckName: `${deck.name} · 熟词复习`,
      queue,
      completed: Math.max(0, Number(saved.completed) || 0),
      remembered: Math.max(0, Number(saved.remembered) || 0),
      forgotten: Math.max(0, Number(saved.forgotten) || 0),
      revealed: false,
      transitioning: false,
      history: [],
      activeStudyMs: Math.max(0, Number(saved.activeStudyMs) || 0),
      knownTarget: 1,
    } : {
      mode: "knownReview",
      deckId,
      deckName: `${deck.name} · 熟词复习`,
      queue,
      initialCount: queue.length,
      completed: 0,
      remembered: 0,
      forgotten: 0,
      revealed: false,
      transitioning: false,
      history: [],
      currentDraft: null,
      activeStudyMs: 0,
      knownTarget: 1,
    };
    persistSession();
    $("study-deck-name").textContent = session.deckName;
    showView($("study-view"));
    startStudyTimer();
    lastRenderedReviewType = null;
    renderCard();
    toast(isResuming ? "已从上次中断的位置继续熟词复习" : `已随机生成 ${queue.length} 张熟词卡`);
  }

  function openEasyWords(deckId) {
    const deck = state.decks.find((item) => item.id === deckId);
    if (!deck) return;
    const items = easyWordItems(deckId);
    if (!items.length) {
      toast("当前词库没有可复习的熟词");
      return;
    }
    pendingEasyDeckId = deckId;
    const list = $("easy-words-list");
    list.innerHTML = "";
    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "easy-words-row";
      row.setAttribute("role", "row");
      const word = document.createElement("span");
      word.setAttribute("role", "cell");
      word.textContent = item.word;
      const count = document.createElement("strong");
      count.setAttribute("role", "cell");
      count.textContent = String(wordForgetCount(deckId, item.key));
      row.append(word, count);
      list.appendChild(row);
    });
    const saved = state.activeSessions[sessionKey(deckId, "easyReview")];
    const canResume = Boolean(saved && saved.queue && saved.queue.length);
    $("easy-words-description").textContent = state.language === "en"
      ? `${deck.name} · ${items.length} words/phrases, ordered by forget count.`
      : `${deck.name} · 共 ${items.length} 个单词/词组，按累计遗忘次数从高到低排列。`;
    $("easy-words-start-button").textContent = canResume ? tr("resume") : tr("start");
    $("easy-words-modal").hidden = false;
    $("easy-words-start-button").focus();
  }

  function closeEasyWords() {
    $("easy-words-modal").hidden = true;
    pendingEasyDeckId = null;
  }

  function confirmEasyWords() {
    const deckId = pendingEasyDeckId;
    $("easy-words-modal").hidden = true;
    pendingEasyDeckId = null;
    startEasyReview(deckId);
  }

  function startEasyReview(deckId) {
    const deck = state.decks.find((item) => item.id === deckId);
    if (!deck) return;
    const saved = state.activeSessions[sessionKey(deckId, "easyReview")];
    const sourceCardIds = new Set(deckCards(deckId).map((card) => card.id));
    const savedQueue = saved && Number(saved.logicVersion) >= 3 && Array.isArray(saved.queue)
      ? saved.queue.filter((item) => item && (item.type === "word" || item.type === "sentence") && sourceCardIds.has(item.sourceCardId))
      : [];
    const isResuming = savedQueue.length > 0;
    const queue = isResuming ? savedQueue : easyWordItems(deckId);
    if (!queue.length) {
      toast("当前词库没有可复习的易忘词");
      return;
    }
    session = isResuming ? {
      ...saved,
      mode: "easyReview",
      deckId,
      deckName: `${deck.name} · 易忘词`,
      queue,
      completed: Math.max(0, Number(saved.completed) || 0),
      remembered: Math.max(0, Number(saved.remembered) || 0),
      forgotten: Math.max(0, Number(saved.forgotten) || 0),
      revealed: false,
      transitioning: false,
      history: [],
      activeStudyMs: Math.max(0, Number(saved.activeStudyMs) || 0),
      knownTarget: 1,
    } : {
      mode: "easyReview",
      deckId,
      deckName: `${deck.name} · 易忘词`,
      queue,
      initialCount: queue.length,
      completed: 0,
      remembered: 0,
      forgotten: 0,
      revealed: false,
      transitioning: false,
      history: [],
      currentDraft: null,
      activeStudyMs: 0,
      knownTarget: 1,
    };
    persistSession();
    $("study-deck-name").textContent = session.deckName;
    showView($("study-view"));
    startStudyTimer();
    lastRenderedReviewType = null;
    renderCard();
    toast(isResuming ? "已从上次中断的位置继续易忘词复习" : `已按遗忘次数排列 ${queue.length} 张易忘词卡`);
  }

  function openCombinedSettings(deckId) {
    const cards = deckCards(deckId);
    if (!cards.length) {
      toast("当前词库没有卡片");
      return;
    }
    pendingCombinedDeckId = deckId;
    const saved = state.activeSessions[sessionKey(deckId, "combined")];
    const target = Math.max(1, Math.min(10, Number((saved && saved.knownTarget) || state.combinedKnownTarget || DEFAULT_KNOWN_TARGET)));
    const groupSize = Math.max(1, Math.min(cards.length, Number((saved && saved.groupSize) || state.combinedGroupSize || Math.min(10, cards.length))));
    $("combined-target-range").value = String(target);
    $("combined-target-value").textContent = state.language === "en" ? `${target} times` : `${target} 次`;
    $("combined-group-range").max = String(cards.length);
    $("combined-group-range").value = String(groupSize);
    $("combined-group-value").textContent = state.language === "en" ? `${groupSize} cards` : `${groupSize} 张`;
    $("combined-group-max").textContent = String(cards.length);
    $("combined-group-hint").textContent = state.language === "en"
      ? `${cards.length} sentence cards in this deck.`
      : `当前词库共 ${cards.length} 张句子卡片。`;
    $("combined-settings-modal").hidden = false;
    $("combined-target-range").focus();
  }

  function closeCombinedSettings() {
    $("combined-settings-modal").hidden = true;
    pendingCombinedDeckId = null;
  }

  function confirmCombinedSettings() {
    const deckId = pendingCombinedDeckId;
    const total = deckCards(deckId).length;
    const target = Math.max(1, Math.min(10, Number($("combined-target-range").value) || DEFAULT_KNOWN_TARGET));
    const groupSize = Math.max(1, Math.min(total, Number($("combined-group-range").value) || 1));
    $("combined-settings-modal").hidden = true;
    pendingCombinedDeckId = null;
    startCombinedStudy(deckId, target, groupSize);
  }

  function chunkCardIds(ids, size) {
    const groups = [];
    for (let index = 0; index < ids.length; index += size) groups.push(ids.slice(index, index + size));
    return groups;
  }

  function regroupCombinedSession(saved, orderedCards, groupSize) {
    const validIds = new Set(orderedCards.map((card) => card.id));
    const oldGroups = saved.groups.map((group) => group.filter((id) => validIds.has(id)));
    const isReviewing = saved.phase === "review";
    const preservedGroupCount = isReviewing
      ? Math.max(0, Math.min(oldGroups.length, Number(saved.reviewingGroupIndex) + 1 || 0))
      : Math.max(0, Math.min(oldGroups.length, Number(saved.currentGroupIndex) || 0));
    const preservedGroups = oldGroups.slice(0, preservedGroupCount).filter((group) => group.length);
    const preservedIds = new Set([].concat.apply([], preservedGroups));
    const remainingIds = orderedCards.map((card) => card.id).filter((id) => !preservedIds.has(id));
    saved.groups = [...preservedGroups, ...chunkCardIds(remainingIds, groupSize)];
    saved.groupSize = groupSize;
    saved.totalSentenceCount = orderedCards.length;
    if (isReviewing) {
      saved.reviewingGroupIndex = Math.max(0, preservedGroups.length - 1);
      saved.currentGroupIndex = saved.reviewingGroupIndex;
    } else {
      saved.currentGroupIndex = preservedGroups.length;
      saved.reviewingGroupIndex = null;
    }
  }

  function repairResetCombinedSessions() {
    let changed = false;
    state.decks.forEach((deck) => {
      const key = sessionKey(deck.id, "combined");
      const saved = state.activeSessions[key];
      if (!saved || saved.mode !== "combined" || !Array.isArray(saved.groups) || !Array.isArray(saved.queue)) return;
      const orderedCards = deckCards(deck.id).slice().sort((a, b) => a.order - b.order);
      let knownPrefixCount = 0;
      while (knownPrefixCount < orderedCards.length && orderedCards[knownPrefixCount].status === "known") knownPrefixCount += 1;
      const groupSize = Math.max(1, Math.min(orderedCards.length || 1, Number(saved.groupSize) || 1));
      const looksLikeAccidentalReset = saved.phase === "review"
        && Number(saved.currentGroupIndex) === 0
        && knownPrefixCount > groupSize;
      if (!looksLikeAccidentalReset) return;

      const completedIds = orderedCards.slice(0, knownPrefixCount).map((card) => card.id);
      const remainingCards = orderedCards.slice(knownPrefixCount);
      saved.phase = "sentences";
      saved.groups = [completedIds, ...chunkCardIds(remainingCards.map((card) => card.id), groupSize)].filter((group) => group.length);
      saved.currentGroupIndex = completedIds.length ? 1 : 0;
      saved.reviewingGroupIndex = null;
      saved.queue = remainingCards.filter((card) => card.status !== "known").map((card) => card.id);
      saved.sentenceQueue = null;
      saved.completed = orderedCards.filter((card) => card.status === "known").length;
      saved.reviewCompleted = 0;
      saved.currentDraft = null;
      saved.logicVersion = 3;
      changed = true;
    });
    if (changed) saveState();
    return changed;
  }

  function startCombinedStudy(deckId, knownTarget, groupSize) {
    const deck = state.decks.find((item) => item.id === deckId);
    if (!deck) return;
    state.combinedKnownTarget = knownTarget;
    state.combinedGroupSize = groupSize;
    deckCards(deckId).forEach((card) => {
      if (card.status !== "known" && Number(card.rememberStreak) >= knownTarget) card.status = "known";
    });

    const saved = state.activeSessions[sessionKey(deckId, "combined")];
    const canResume = Boolean(
      saved &&
      saved.mode === "combined" &&
      Number(saved.logicVersion) >= 2 &&
      Array.isArray(saved.queue) &&
      Array.isArray(saved.groups)
    );

    if (canResume) {
      const orderedCards = deckCards(deckId).slice().sort((a, b) => a.order - b.order);
      if (Number(saved.groupSize) !== groupSize) regroupCombinedSession(saved, orderedCards, groupSize);
      session = {
        ...saved,
        deckId,
        deckName: `${deck.name} · 组合模式`,
        groupSize,
        knownTarget,
        totalSentenceCount: orderedCards.length,
        completed: orderedCards.filter((card) => card.status === "known").length,
        history: [],
        transitioning: false,
        revealed: false,
      };
      if (session.phase === "sentences") beginCombinedReviewIfReady();
    } else {
      const cards = deckCards(deckId).slice().sort((a, b) => a.order - b.order);
      const groups = [];
      for (let index = 0; index < cards.length; index += groupSize) {
        groups.push(cards.slice(index, index + groupSize).map((card) => card.id));
      }
      session = {
        mode: "combined",
        phase: "sentences",
        deckId,
        deckName: `${deck.name} · 组合模式`,
        queue: cards.filter((card) => card.status !== "known").map((card) => card.id),
        sentenceQueue: null,
        groups,
        currentGroupIndex: 0,
        reviewingGroupIndex: null,
        groupSize,
        totalSentenceCount: cards.length,
        initialCount: cards.length,
        completed: cards.filter((card) => card.status === "known").length,
        reviewCompleted: 0,
        remembered: 0,
        forgotten: 0,
        revealed: false,
        transitioning: false,
        history: [],
        currentDraft: null,
        activeStudyMs: 0,
        knownTarget,
      };
      beginCombinedReviewIfReady();
    }

    persistSession();
    $("study-deck-name").textContent = session.deckName;
    showView($("study-view"));
    startStudyTimer();
    lastRenderedReviewType = null;
    renderCard();
    if (canResume) toast("已恢复上次的组合模式进度");
  }

  function combinedGroupCards(groupIndex) {
    const ids = new Set(session.groups[groupIndex] || []);
    return state.cards.filter((card) => ids.has(card.id));
  }

  function combinedGroupIsKnown(groupIndex) {
    const cards = combinedGroupCards(groupIndex);
    return cards.length > 0 && cards.every((card) => card.status === "known");
  }

  function beginCombinedReviewIfReady() {
    if (!session || session.mode !== "combined" || session.phase !== "sentences") return false;
    while (session.currentGroupIndex < session.groups.length) {
      if (!combinedGroupIsKnown(session.currentGroupIndex)) return false;
      const groupIndex = session.currentGroupIndex;
      const words = knownWordItemsFromCards(combinedGroupCards(groupIndex));
      if (!words.length) {
        session.currentGroupIndex += 1;
        continue;
      }
      session.sentenceQueue = session.queue.slice();
      session.queue = words;
      session.phase = "review";
      session.reviewingGroupIndex = groupIndex;
      session.reviewCompleted = 0;
      session.currentDraft = null;
      return true;
    }
    return false;
  }

  function finishCombinedReviewPhase() {
    session.phase = "sentences";
    session.queue = Array.isArray(session.sentenceQueue) ? session.sentenceQueue : [];
    session.sentenceQueue = null;
    session.currentGroupIndex = Number(session.reviewingGroupIndex) + 1;
    session.reviewingGroupIndex = null;
    session.reviewCompleted = 0;
    session.currentDraft = null;
    beginCombinedReviewIfReady();
    persistSession();
    renderCard();
  }

  function openStudySettings(deckId) {
    const hasEligible = state.cards.some((card) => card.status !== "known" && (!deckId || card.deckId === deckId));
    if (!hasEligible) {
      toast("当前没有待学习卡片");
      return;
    }
    pendingDeckId = deckId || null;
    const savedSession = state.activeSessions[sessionKey(deckId)];
    const savedTarget = Number(savedSession && savedSession.knownTarget);
    const target = Number.isInteger(savedTarget) ? savedTarget : Number(state.learningTarget) || DEFAULT_KNOWN_TARGET;
    $("target-count-range").value = String(target);
    $("target-count-display").textContent = String(target);
    $("study-settings-modal").hidden = false;
    $("target-count-range").focus();
  }

  function closeStudySettings() {
    $("study-settings-modal").hidden = true;
    pendingDeckId = null;
  }

  function confirmStudySettings() {
    const deckId = pendingDeckId;
    const target = Math.max(1, Math.min(10, Number($("target-count-range").value) || DEFAULT_KNOWN_TARGET));
    $("study-settings-modal").hidden = true;
    pendingDeckId = null;
    startStudy(deckId, target);
  }

  function startStudy(deckId, knownTarget) {
    state.learningTarget = knownTarget;
    state.cards.forEach((card) => {
      if (card.status !== "known" && (!deckId || card.deckId === deckId) && Number(card.rememberStreak) >= knownTarget) {
        card.status = "known";
      }
    });
    const eligible = state.cards.filter((card) => card.status !== "known" && (!deckId || card.deckId === deckId));
    if (!eligible.length) {
      delete state.activeSessions[sessionKey(deckId)];
      saveState();
      renderDashboard();
      toast("当前没有待学习卡片");
      return;
    }
    const deck = deckId ? state.decks.find((item) => item.id === deckId) : null;
    const savedSession = state.activeSessions[sessionKey(deckId)];
    const eligibleIds = new Set(eligible.map((card) => card.id));
    const savedQueue = savedSession && Number(savedSession.logicVersion) >= 2 && Array.isArray(savedSession.queue)
      ? savedSession.queue.filter((id) => eligibleIds.has(id))
      : [];
    const isResuming = savedQueue.length > 0;

    session = isResuming ? {
      mode: "normal",
      deckId: deckId || null,
      deckName: deck ? deck.name : "全部卡片",
      queue: savedQueue,
      initialCount: Math.max(savedQueue.length, Number(savedSession.initialCount) || savedQueue.length),
      completed: Number(savedSession.completed) || 0,
      remembered: Number(savedSession.remembered) || 0,
      forgotten: Number(savedSession.forgotten) || 0,
      revealed: false,
      transitioning: false,
      history: [],
      currentDraft: savedSession.currentDraft || null,
      activeStudyMs: Math.max(0, Number(savedSession.activeStudyMs) || 0),
      knownTarget,
    } : {
      mode: "normal",
      deckId: deckId || null,
      deckName: deck ? deck.name : "全部卡片",
      queue: eligible.map((card) => card.id),
      initialCount: eligible.length,
      completed: 0,
      remembered: 0,
      forgotten: 0,
      revealed: false,
      transitioning: false,
      history: [],
      currentDraft: null,
      activeStudyMs: 0,
      knownTarget,
    };
    persistSession();
    $("study-deck-name").textContent = session.deckName;
    showView($("study-view"));
    startStudyTimer();
    lastRenderedReviewType = null;
    renderCard();
    if (isResuming) toast("已从上次中断的位置继续");
  }

  function sessionKey(deckId, mode = "normal") {
    if (mode === "knownReview") return `known-review:${deckId}`;
    if (mode === "easyReview") return `easy-review:${deckId}`;
    if (mode === "combined") return `combined:${deckId}`;
    return deckId ? `deck:${deckId}` : "all";
  }

  function persistSession() {
    if (!session) return;
    state.activeSessions[sessionKey(session.deckId, session.mode)] = {
      mode: session.mode,
      queue: session.queue.slice(),
      initialCount: session.initialCount,
      completed: session.completed,
      remembered: session.remembered,
      forgotten: session.forgotten,
      currentDraft: session.currentDraft,
      activeStudyMs: Math.max(0, Number(session.activeStudyMs) || 0),
      knownTarget: session.knownTarget,
      logicVersion: 3,
      savedAt: Date.now(),
      ...(session.mode === "combined" ? {
        phase: session.phase,
        groups: session.groups.map((group) => group.slice()),
        sentenceQueue: session.sentenceQueue ? session.sentenceQueue.slice() : null,
        currentGroupIndex: session.currentGroupIndex,
        reviewingGroupIndex: session.reviewingGroupIndex,
        groupSize: session.groupSize,
        totalSentenceCount: session.totalSentenceCount,
        reviewCompleted: session.reviewCompleted || 0,
      } : {}),
    };
    saveState();
  }

  function currentCard() {
    if (!session || !session.queue.length) return null;
    if (isTermReviewPhase()) return reviewCardFromItem(session.queue[0]);
    return state.cards.find((card) => card.id === session.queue[0]) || null;
  }

  function isTermReviewPhase() {
    return Boolean(session && (
      session.mode === "knownReview" ||
      session.mode === "easyReview" ||
      (session.mode === "combined" && session.phase === "review")
    ));
  }

  function isReviewWordCard() {
    return Boolean(isTermReviewPhase() && session.queue[0] && session.queue[0].type === "word");
  }

  function reviewWordDetails(fullAnswer) {
    const slashIndex = String(fullAnswer || "").indexOf("/");
    return slashIndex >= 0
      ? String(fullAnswer).slice(slashIndex).trim()
      : "暂无音标、中文等其他详情";
  }

  function setDecisionControl(button, label, hint, remembers) {
    button.querySelectorAll("span")[1].textContent = label;
    button.querySelector("small").textContent = hint;
    button.classList.toggle("control-remember", remembers);
    button.classList.toggle("control-forgot", !remembers);
  }

  function configureDecisionControls(reviewItem = null) {
    const left = $("forgot-button");
    const right = $("remember-button");
    if (reviewItem && reviewItem.type === "word") {
      const detailsShown = Boolean(reviewItem.detailsRevealed);
      setDecisionControl(left, detailsShown ? tr("remember") : (state.language === "en" ? "View details" : "查看详情"), detailsShown ? (state.language === "en" ? "Leaves this round" : "本轮不再出现") : (state.language === "en" ? "Press ← again to remember" : "再次按 ← 即记住"), true);
      setDecisionControl(right, tr("forgot"), state.language === "en" ? "Open the source sentence" : "立即用原句复习", false);
      return;
    }
    setDecisionControl(left, tr("forgot"), reviewItem ? (state.language === "en" ? "Show the source sentence after 3 words" : "3 个词后再显示原句") : tr("forgotHint"), false);
    setDecisionControl(right, tr("remember"), reviewItem ? (state.language === "en" ? "Test this word again after 3 words" : "3 个词后再测该词") : tr("rememberHint"), true);
  }

  function revealCurrentWordDetails() {
    if (!isReviewWordCard() || session.transitioning) return false;
    const item = session.queue[0];
    if (item.detailsRevealed) return false;
    item.detailsRevealed = true;
    const details = $("word-details");
    details.textContent = reviewWordDetails(item.fullAnswer);
    details.hidden = false;
    $("reveal-tip").textContent = state.language === "en" ? "Details shown: press ← to remember; press → to forget" : "已显示详情：再按 ← 标记记住；按 → 标记忘记";
    configureDecisionControls(item);
    persistSession();
    return true;
  }

  function reviewCardFromItem(item) {
    if (!item) return null;
    if (item.type === "word") {
      return {
        id: item.id,
        deckId: session.deckId,
        content: item.word,
        status: "known",
        rememberStreak: 0,
        reviews: 0,
      };
    }
    const source = state.cards.find((card) => card.id === item.sourceCardId);
    if (!source) return null;
    let clozeIndex = 0;
    const content = source.content.replace(/\{\{([\s\S]*?)\}\}/g, (_, answer) => {
      const currentIndex = clozeIndex;
      clozeIndex += 1;
      return currentIndex === item.clozeIndex ? `{{${answer}}}` : answer;
    });
    return {
      id: item.id,
      deckId: session.deckId,
      content,
      status: "unknown",
      rememberStreak: 0,
      reviews: 0,
    };
  }

  function renderCard() {
    flushAdjustedWordCardPosition();
    clearWordCardPositioning();
    const card = currentCard();
    if (!card) {
      if (session && session.mode === "combined" && session.phase === "review") {
        finishCombinedReviewPhase();
        return;
      }
      if (session && session.mode === "combined" && session.phase === "sentences" && beginCombinedReviewIfReady()) {
        persistSession();
        renderCard();
        return;
      }
      finishSession();
      return;
    }
    const reviewItem = isTermReviewPhase() ? session.queue[0] : null;
    const currentReviewType = reviewItem ? reviewItem.type : null;
    const isWordReview = currentReviewType === "word";
    const shouldReleaseTextInput = isWordReview && lastRenderedReviewType !== "word";
    lastRenderedReviewType = currentReviewType;
    if (shouldReleaseTextInput) {
      const activeElement = document.activeElement;
      if (activeElement && typeof activeElement.blur === "function") activeElement.blur();
    }
    session.revealed = false;
    session.transitioning = false;
    clearTimeout(transitionTimer);
    const content = $("card-content");
    notifyNativeManagedTextInputFocus(false);
    content.innerHTML = "";
    content.classList.remove("show-answers", "hide-answers");
    const wordDetails = $("word-details");
    wordDetails.hidden = true;
    wordDetails.textContent = "";
    if (!session.currentDraft || session.currentDraft.cardId !== card.id) {
      session.currentDraft = { cardId: card.id, values: [], solved: [] };
    }
    const draft = session.currentDraft;
    const pattern = /\{\{([\s\S]*?)\}\}/g;
    let lastIndex = 0;
    let match;
    let clozeIndex = 0;
    while ((match = pattern.exec(card.content)) !== null) {
      content.appendChild(document.createTextNode(card.content.slice(lastIndex, match.index)));
      const cloze = document.createElement("span");
      const fullAnswer = match[1].trim();
      const expectedEnglish = englishPart(fullAnswer);
      cloze.className = "cloze";
      if (draft.solved[clozeIndex]) cloze.classList.add("solved");

      const answer = document.createElement("span");
      answer.className = "cloze-answer";
      answer.textContent = fullAnswer;

      const input = document.createElement("input");
      input.className = "cloze-input";
      input.type = "text";
      input.autocomplete = "off";
      input.autocapitalize = "off";
      input.spellcheck = false;
      setTextInputModeForCurrentKeyboard(input);
      input.value = draft.values[clozeIndex] || "";
      input.setAttribute("aria-label", state.language === "en" ? `Spell: ${expectedEnglish.length} characters` : `拼写：${expectedEnglish.length} 个字符`);
      input.style.setProperty("--answer-length", `${Math.max(5, Math.min(26, expectedEnglish.length + 1))}ch`);
      const inputIndex = clozeIndex;
      input.addEventListener("beforeinput", (event) => {
        if (
          event.inputType &&
          event.inputType.startsWith("insert") &&
          typeof event.data === "string" &&
          filterClozeEnglishText(event.data) !== event.data
        ) {
          event.preventDefault();
        }
      });
      input.addEventListener("input", () => {
        sanitizeClozeEnglishInput(input);
        checkSpelling(cloze, input, expectedEnglish, inputIndex);
      });
      if (input.value && !draft.solved[clozeIndex] && normalizedSpelling(input.value) !== normalizedSpelling(expectedEnglish)) {
        input.classList.add("has-error");
      }

      cloze.append(answer, input);
      content.appendChild(cloze);
      lastIndex = pattern.lastIndex;
      clozeIndex += 1;
    }
    content.appendChild(document.createTextNode(card.content.slice(lastIndex)));
    $("flashcard").classList.toggle("word-card", isWordReview);
    if (reviewItem) {
      const isWord = reviewItem.type === "word";
      $("card-status").textContent = isWord
        ? (session.mode === "easyReview" ? tr("easy") : tr("review"))
        : (state.language === "en" ? "Source sentence" : "原句强化");
      $("remember-streak").textContent = isWord
        ? (state.language === "en" ? "View details, then confirm" : "先查看详情，再确认记住")
        : (state.language === "en" ? `Masking: ${reviewItem.word}` : `只遮挡：${reviewItem.word}`);
      if (isWord && reviewItem.detailsRevealed) {
        wordDetails.textContent = reviewWordDetails(reviewItem.fullAnswer);
        wordDetails.hidden = false;
        $("reveal-tip").textContent = state.language === "en" ? "Details shown: press ← to remember; press → to forget" : "已显示详情：再按 ← 标记记住；按 → 标记忘记";
      } else {
        $("reveal-tip").textContent = isWord
          ? (state.language === "en" ? "← View details (press again to remember)　　→ Forget and open source" : "← 查看详情（再按一次即记住）　　→ 忘记并查看原句")
          : (state.language === "en" ? "Spell correctly or press →; test again after 3 words" : "拼写正确或按 → 后，间隔 3 个词再次测试");
      }
      configureDecisionControls(reviewItem);
      $("edit-card-button").disabled = true;
      $("edit-card-button").title = state.language === "en" ? "Review cards are generated from source cards; edit the source card in regular study" : "熟词复习卡由原句动态生成，请在普通学习中编辑原卡片";
    } else {
      if (session.mode === "combined") {
        const groupIndex = session.groups.findIndex((group) => group.includes(card.id));
        $("card-status").textContent = state.language === "en" ? `Group ${groupIndex + 1}` : `组合 · 第 ${groupIndex + 1} 组`;
      } else {
        $("card-status").textContent = card.status.toUpperCase();
      }
      $("remember-streak").textContent = state.language === "en"
        ? `Consecutive remembers ${card.rememberStreak} / ${session.knownTarget}`
        : `连续记住 ${card.rememberStreak} / ${session.knownTarget}`;
      $("reveal-tip").textContent = content.querySelector(".cloze-input")
        ? (state.language === "en" ? "Type English at the mask; press ↑ to reveal the full content" : "在遮挡处输入英文，按 ↑ 可显示完整内容")
        : (state.language === "en" ? "This card has no spelling fields; use the arrow keys to mark it" : "本卡没有可拼写字段，可使用方向键标记");
      configureDecisionControls();
      $("edit-card-button").disabled = false;
      $("edit-card-button").removeAttribute("title");
    }
    if (session.mode === "combined") {
      const completedSentences = Math.max(0, Math.min(session.totalSentenceCount, Number(session.completed) || 0));
      $("study-progress").textContent = state.language === "en" ? `Sentences ${completedSentences} / ${session.totalSentenceCount}` : `句子 ${completedSentences} / ${session.totalSentenceCount}`;
      $("progress-bar").style.width = `${Math.min(100, completedSentences / session.totalSentenceCount * 100)}%`;
    } else {
      $("study-progress").textContent = state.language === "en"
        ? `${reviewItem ? "Remembered" : "Mastered"} ${Math.min(session.completed, session.initialCount)} / ${session.initialCount}`
        : `${reviewItem ? "已记住" : "已掌握"} ${Math.min(session.completed, session.initialCount)} / ${session.initialCount}`;
      $("progress-bar").style.width = `${Math.min(100, session.completed / session.initialCount * 100)}%`;
    }
    persistSession();
    if (clozeIndex > 0 && !content.querySelector(".cloze:not(.solved)")) scheduleAutoRemember();
    requestAnimationFrame(() => focusNextCloze());
    if (isWordReview) scheduleWordCardPositioning(card.id);
    startCardSpeech();
  }

  function englishPart(fullAnswer) {
    return fullAnswer.split("/")[0].trim();
  }

  function normalizedSpelling(value) {
    return value
      .normalize("NFKC")
      .trim()
      .toLocaleLowerCase("en")
      .replace(/[‘’]/g, "'")
      .replace(/[‐‑–—]/g, "-")
      .replace(/\s+/g, " ");
  }

  function checkSpelling(cloze, input, expectedEnglish, inputIndex) {
    if (cloze.classList.contains("solved") || session.transitioning) return;
    session.currentDraft.values[inputIndex] = input.value;
    const typed = normalizedSpelling(input.value);
    const expected = normalizedSpelling(expectedEnglish);
    input.classList.toggle("has-error", typed.length > 0 && typed !== expected);
    if (!expected || typed !== expected) {
      persistSession();
      return;
    }

    $("card-content").classList.remove("show-answers", "hide-answers");
    session.revealed = false;
    cloze.classList.add("solved");
    session.currentDraft.solved[inputIndex] = true;
    input.classList.remove("has-error");
    persistSession();

    const next = document.querySelector(".cloze:not(.solved) .cloze-input");
    if (next) {
      focusTextInputForCurrentKeyboard(next);
      $("reveal-tip").textContent = state.language === "en" ? "Correct—continue spelling the next mask" : "正确，继续拼写下一个遮挡处";
      return;
    }

    scheduleAutoRemember();
  }

  function scheduleAutoRemember() {
    if (!session || session.transitioning) return;
    session.transitioning = true;
    $("reveal-tip").textContent = state.language === "en" ? "All correct—moving to the next card…" : "全部正确，正在进入下一张卡片…";
    transitionTimer = setTimeout(() => {
      if (!session || !session.transitioning) return;
      session.transitioning = false;
      applyRemembered();
    }, 550);
  }

  function isManagedTextInput(input) {
    return isClozeTextInput(input);
  }

  function isClozeTextInput(input) {
    return Boolean(input && input.classList && input.classList.contains("cloze-input"));
  }

  function isCardEditorTextInput(input) {
    return Boolean(input && input.id === "card-editor-textarea");
  }

  function isEditableStudyTextInput(input) {
    return isClozeTextInput(input) || isCardEditorTextInput(input);
  }

  function filterClozeEnglishText(value) {
    return Array.from(String(value || "")).filter((character) => (
      /^[\x20-\x7E\u00C0-\u024F\u0300-\u036F\u2010-\u201F]$/.test(character)
    )).join("");
  }

  function sanitizeClozeEnglishInput(input) {
    const original = String(input.value || "");
    const cleaned = filterClozeEnglishText(original);
    if (cleaned === original) return;
    const originalCaret = Number.isInteger(input.selectionStart) ? input.selectionStart : original.length;
    const cleanedCaret = filterClozeEnglishText(original.slice(0, originalCaret)).length;
    input.value = cleaned;
    if (typeof input.setSelectionRange === "function") {
      input.setSelectionRange(cleanedCaret, cleanedCaret);
    }
  }

  function insertNativePrintableText(rawText) {
    const input = document.activeElement;
    const text = filterClozeEnglishText(rawText);
    if (!text || !isClozeTextInput(input) || !input.isConnected || input.disabled || input.readOnly) return false;
    const cloze = input.closest(".cloze");
    if (cloze && cloze.classList.contains("solved")) return false;

    const value = String(input.value || "");
    const start = Number.isInteger(input.selectionStart) ? input.selectionStart : value.length;
    const end = Number.isInteger(input.selectionEnd) ? input.selectionEnd : start;
    input.setRangeText(text, start, end, "end");

    let inputEvent;
    try {
      inputEvent = new InputEvent("input", {
        bubbles: true,
        inputType: "insertText",
        data: text,
      });
    } catch (_) {
      inputEvent = new Event("input", { bubbles: true });
    }
    input.dispatchEvent(inputEvent);
    return true;
  }

  window.handleNativePrintableText = insertNativePrintableText;

  function printableTextFromDomKey(event) {
    if (event.isComposing || event.metaKey || (event.ctrlKey && !event.altKey)) return "";
    const key = typeof event.key === "string" ? event.key : "";
    if (!key || key === "Dead" || key === "Unidentified") return "";
    const codePoints = Array.from(key);
    if (codePoints.length !== 1) return "";
    const codePoint = codePoints[0].codePointAt(0);
    return codePoint >= 32 && codePoint !== 127 ? key : "";
  }

  function resolveKeyboardKey(event) {
    const legacyKeys = {
      9: "Tab",
      32: "Space",
      37: "ArrowLeft",
      38: "ArrowUp",
      39: "ArrowRight",
      40: "ArrowDown",
    };
    const codeKeys = {
      Tab: "Tab",
      ArrowLeft: "ArrowLeft",
      ArrowUp: "ArrowUp",
      ArrowRight: "ArrowRight",
      ArrowDown: "ArrowDown",
    };
    let key = event.key;
    if (!key || key === "Unidentified") {
      key = legacyKeys[event.keyCode || event.which] || codeKeys[event.code] || key;
    }
    if (key === " " || key === "Spacebar" || key === "Space" || event.code === "Space") return "Space";
    return key;
  }

  function studyModalIsOpen() {
    return [
      "card-editor-modal",
      "study-settings-modal",
      "combined-settings-modal",
      "easy-words-modal",
      "deck-export-modal",
      "language-modal",
    ].some((id) => !$(id).hidden);
  }

  function handlePhysicalSpace(shiftKey = false, target = document.activeElement) {
    // Never edit a focused input through JavaScript. Let WebView's native
    // InputConnection own text, selection, composition and undo as one state.
    if (isEditableStudyTextInput(target) || isEditableStudyTextInput(document.activeElement)) return false;

    clearDashboardPositioning();
    const trackingWordPosition = lastRenderedReviewType === "word" && !$("study-view").hidden;
    if (trackingWordPosition) {
      clearWordCardPositioning();
      wordCardManualCaptureUntil = Date.now() + 700;
    }
    const distance = Math.max(1, Math.round(visualViewportMetrics().height * 2 / 3));
    window.scrollBy(0, (shiftKey ? -1 : 1) * distance);
    if (trackingWordPosition) scheduleAdjustedWordCardPositionSave();
    return true;
  }

  function nativeHardwareKeyboardConnected() {
    const bridge = window.AndroidFileBridge;
    if (!bridge || typeof bridge.hasHardwareKeyboard !== "function") return false;
    try {
      return Boolean(bridge.hasHardwareKeyboard());
    } catch (_) {
      return false;
    }
  }

  function setTextInputModeForCurrentKeyboard(input, hardwareConnected = nativeHardwareKeyboardConnected()) {
    if (!isManagedTextInput(input)) return hardwareConnected;
    input.setAttribute("inputmode", "text");
    return hardwareConnected;
  }

  function hideSoftKeyboardForHardwareInput() {
    const bridge = window.AndroidFileBridge;
    if (bridge && typeof bridge.hideSoftKeyboardIfHardwareKeyboard === "function") {
      bridge.hideSoftKeyboardIfHardwareKeyboard();
    }
  }

  function focusTextInputForCurrentKeyboard(input) {
    if (!input) return;
    if (input.classList.contains("cloze-input")) notifyNativeCardEditorFocus(false);
    const hardwareConnected = setTextInputModeForCurrentKeyboard(input);
    input.focus();
    notifyNativeManagedTextInputFocus(isClozeTextInput(input) && document.activeElement === input);
    if (hardwareConnected) hideSoftKeyboardForHardwareInput();
  }

  function focusNextCloze() {
    const input = document.querySelector(".cloze:not(.solved) .cloze-input");
    if (input && !$("card-content").classList.contains("show-answers")) {
      focusTextInputForCurrentKeyboard(input);
    }
  }

  window.onNativeHardwareKeyboardChanged = function (connected) {
    const hardwareConnected = Boolean(connected);
    document.querySelectorAll(".cloze-input").forEach((input) => {
      setTextInputModeForCurrentKeyboard(input, hardwareConnected);
    });
    $("card-editor-textarea").setAttribute("inputmode", "text");
    if (hardwareConnected) hideSoftKeyboardForHardwareInput();
  };

  function countClozes(content) {
    return (content.match(/\{\{[\s\S]*?\}\}/g) || []).length;
  }

  function updateEditorClozeCount() {
    const count = countClozes($("card-editor-textarea").value);
    $("editor-cloze-count").textContent = `${count} 个遮挡`;
  }

  function notifyNativeCardEditorFocus(focused) {
    if (window.AndroidFileBridge && typeof window.AndroidFileBridge.setCardEditorFocused === "function") {
      window.AndroidFileBridge.setCardEditorFocused(Boolean(focused));
    }
  }

  function notifyNativeManagedTextInputFocus(focused) {
    if (window.AndroidFileBridge && typeof window.AndroidFileBridge.setManagedTextInputFocused === "function") {
      window.AndroidFileBridge.setManagedTextInputFocused(Boolean(focused));
    }
  }

  function focusCardEditorInput() {
    const input = $("card-editor-textarea");
    input.setAttribute("inputmode", "text");
    notifyNativeManagedTextInputFocus(false);
    input.focus();
    notifyNativeCardEditorFocus(document.activeElement === input);
    if (nativeHardwareKeyboardConnected()) hideSoftKeyboardForHardwareInput();
  }

  function leaveCardEditorInput() {
    $("card-editor-textarea").blur();
    notifyNativeCardEditorFocus(false);
  }

  function openCardEditor() {
    const card = currentCard();
    if (!card || session.transitioning || isTermReviewPhase()) return;
    $("card-editor-textarea").value = card.content;
    updateEditorClozeCount();
    $("card-editor-modal").hidden = false;
    focusCardEditorInput();
  }

  function closeCardEditor() {
    leaveCardEditorInput();
    $("card-editor-modal").hidden = true;
    requestAnimationFrame(() => focusNextCloze());
  }

  function saveCardEdit() {
    const card = currentCard();
    if (!card) {
      closeCardEditor();
      return;
    }
    const content = $("card-editor-textarea").value.trim();
    if (!content) {
      toast("卡片内容不能为空");
      focusCardEditorInput();
      return;
    }
    card.content = content;
    session.currentDraft = null;
    persistSession();
    leaveCardEditorInput();
    $("card-editor-modal").hidden = true;
    renderCard();
    toast(state.language === "en" ? "Card updated; masks were re-detected" : "卡片已更新，遮挡内容已重新识别");
  }

  function setMask(revealed) {
    if (!currentCard() || session.transitioning) return;
    if (isReviewWordCard()) {
      const item = session.queue[0];
      if (revealed) {
        revealCurrentWordDetails();
      } else if (item.detailsRevealed) {
        item.detailsRevealed = false;
        $("word-details").hidden = true;
        $("word-details").textContent = "";
        $("reveal-tip").textContent = "← 或 ↑ 查看详情　　→ 忘记并查看原句";
        configureDecisionControls(item);
        persistSession();
      }
      return;
    }
    const content = $("card-content");
    if (!content.querySelector(".cloze")) return;
    session.revealed = revealed;
    content.classList.toggle("show-answers", revealed);
    content.classList.toggle("hide-answers", !revealed);
    $("reveal-tip").textContent = revealed
      ? (state.language === "en" ? "Press ↓ to mask again" : "按 ↓ 再次遮挡")
      : (state.language === "en" ? "Press ↑ to reveal the masked content" : "按 ↑ 显示遮挡内容");
    if (!revealed) requestAnimationFrame(() => focusNextCloze());
  }

  function markForgotten() {
    if (isTermReviewPhase()) {
      markKnownReviewForgotten();
      return;
    }
    const card = currentCard();
    if (!card || session.transitioning) return;
    rememberBeforeMark(card);
    card.rememberStreak = 0;
    card.status = "unknown";
    card.reviews += 1;
    session.forgotten += 1;
    session.currentDraft = null;
    const cardId = session.queue.shift();
    // 插到三张其他卡片之后；不足三张时放到队尾。
    session.queue.splice(Math.min(3, session.queue.length), 0, cardId);
    persistSession();
    renderCard();
  }

  function markRemembered() {
    if (!currentCard() || session.transitioning) return;
    applyRemembered();
  }

  function handleLeftDecision() {
    if (isReviewWordCard()) {
      if (!revealCurrentWordDetails()) markKnownReviewRemembered();
      return;
    }
    markForgotten();
  }

  function handleRightDecision() {
    if (isReviewWordCard()) {
      markKnownReviewForgotten();
      return;
    }
    markRemembered();
  }

  function applyRemembered() {
    if (isTermReviewPhase()) {
      markKnownReviewRemembered();
      return;
    }
    const card = currentCard();
    if (!card) return;
    rememberBeforeMark(card);
    card.rememberStreak += 1;
    card.reviews += 1;
    session.remembered += 1;
    session.currentDraft = null;
    const cardId = session.queue.shift();
    if (card.rememberStreak >= session.knownTarget) {
      card.status = "known";
      session.completed += 1;
    } else {
      // 与“忘记”使用相同的间隔规则：三张其他卡片后再次出现。
      session.queue.splice(Math.min(3, session.queue.length), 0, cardId);
    }
    if (session.mode === "combined" && session.phase === "sentences") beginCombinedReviewIfReady();
    persistSession();
    renderCard();
  }

  function reviewWordItem(item) {
    return { ...item, type: "word", id: `${item.relationId}-word`, detailsRevealed: false };
  }

  function reviewSentenceItem(item) {
    return { ...item, type: "sentence", id: `${item.relationId}-sentence` };
  }

  function insertAfterThreeWords(item) {
    let wordCount = 0;
    let insertIndex = session.queue.length;
    for (let index = 0; index < session.queue.length; index += 1) {
      if (session.queue[index].type === "word") wordCount += 1;
      if (wordCount === 3) {
        insertIndex = index + 1;
        break;
      }
    }
    session.queue.splice(insertIndex, 0, item);
  }

  function rememberBeforeReviewMark() {
    const snapshot = {
      review: true,
      queue: session.queue.map((item) => ({ ...item })),
      completed: session.completed,
      remembered: session.remembered,
      forgotten: session.forgotten,
      combinedState: combinedHistoryState(),
    };
    session.history.push(snapshot);
    return snapshot;
  }

  function markKnownReviewForgotten() {
    const item = session.queue[0];
    if (!item || session.transitioning) return;
    const previous = rememberBeforeReviewMark();
    if (item.type === "word" && (session.mode === "knownReview" || session.mode === "easyReview")) {
      const oldCount = wordForgetCount(session.deckId, item.key);
      previous.wordForgetCount = { deckId: session.deckId, key: item.key, count: oldCount };
      setWordForgetCount(session.deckId, item.key, oldCount + 1);
    }
    session.queue.shift();
    session.forgotten += 1;
    session.currentDraft = null;
    if (item.type === "word") {
      // 单词忘记后，原句紧接着出现。
      session.queue.unshift(reviewSentenceItem(item));
    } else {
      // 原句仍忘记时，经过三个其他词后再次强化原句。
      insertAfterThreeWords(reviewSentenceItem(item));
    }
    persistSession();
    renderCard();
  }

  function markKnownReviewRemembered() {
    const item = session.queue[0];
    if (!item) return;
    rememberBeforeReviewMark();
    session.queue.shift();
    session.remembered += 1;
    session.currentDraft = null;
    if (item.type === "word") {
      // 熟词确认记住，本轮永久退出。
      if (session.mode === "combined") session.reviewCompleted += 1;
      else session.completed += 1;
    } else {
      // 原句强化成功后，经过三个词再次测试该词。
      insertAfterThreeWords(reviewWordItem(item));
    }
    persistSession();
    renderCard();
  }

  function rememberBeforeMark(card) {
    session.history.push({
      queue: session.queue.slice(),
      cardId: card.id,
      cardState: {
        status: card.status,
        rememberStreak: card.rememberStreak,
        reviews: card.reviews,
      },
      completed: session.completed,
      remembered: session.remembered,
      forgotten: session.forgotten,
      combinedState: combinedHistoryState(),
    });
  }

  function combinedHistoryState() {
    if (session.mode !== "combined") return null;
    return {
      phase: session.phase,
      sentenceQueue: session.sentenceQueue ? session.sentenceQueue.slice() : null,
      currentGroupIndex: session.currentGroupIndex,
      reviewingGroupIndex: session.reviewingGroupIndex,
      reviewCompleted: session.reviewCompleted || 0,
    };
  }

  function undoLastMark() {
    if (!session) return;
    if (session.transitioning) {
      clearTimeout(transitionTimer);
      session.transitioning = false;
      // 最后一处拼写完成但尚在跳转动画中时，先落下该标记，再立即撤回。
      applyRemembered();
    }
    const previous = session.history.pop();
    if (!previous) {
      focusNextCloze();
      return;
    }
    if (!previous.review) {
      const card = state.cards.find((item) => item.id === previous.cardId);
      if (card) Object.assign(card, previous.cardState);
    }
    session.queue = previous.queue;
    session.completed = previous.completed;
    session.remembered = previous.remembered;
    session.forgotten = previous.forgotten;
    session.currentDraft = null;
    if (previous.combinedState) Object.assign(session, previous.combinedState);
    if (previous.wordForgetCount) {
      setWordForgetCount(previous.wordForgetCount.deckId, previous.wordForgetCount.key, previous.wordForgetCount.count);
    }
    persistSession();
    showView($("study-view"));
    renderCard();
  }

  function performStudyControl(key) {
    if (studyModalIsOpen()) return false;
    const canUndo = session && (!$("study-view").hidden || !$("complete-view").hidden);
    if (key === "Tab") {
      if (!canUndo) return false;
      undoLastMark();
      return true;
    }
    if ($("study-view").hidden) return false;
    const actions = {
      ArrowUp: () => setMask(true),
      ArrowDown: () => setMask(false),
      ArrowLeft: handleLeftDecision,
      ArrowRight: handleRightDecision,
    };
    if (!actions[key]) return false;
    actions[key]();
    return true;
  }

  window.handleNativeStudyKey = function (key) {
    recordStudyActivity();
    return performStudyControl(key);
  };
  window.handleNativePhysicalKey = function (key, shiftKey) {
    recordStudyActivity();
    if (key === "Tab") return performStudyControl("Tab");
    if (key === "Space") return handlePhysicalSpace(Boolean(shiftKey));
    return false;
  };

  function finishSession() {
    if (!session) return;
    if (document.activeElement && typeof document.activeElement.blur === "function") {
      document.activeElement.blur();
    }
    notifyNativeManagedTextInputFocus(false);
    flushAdjustedWordCardPosition();
    clearWordCardPositioning();
    lastRenderedReviewType = null;
    stopStudyTimer();
    stopCardSpeech();
    delete state.activeSessions[sessionKey(session.deckId, session.mode)];
    saveState();
    if (session.mode === "knownReview") {
      $("complete-summary").textContent = state.language === "en"
        ? `Completed random review of ${session.initialCount} known words; remembered ${session.remembered} times and forgot ${session.forgotten} times this round.`
        : `已完成 ${session.initialCount} 个熟词的随机复习；本轮标记记住 ${session.remembered} 次，忘记 ${session.forgotten} 次。`;
      $("continue-button").hidden = true;
    } else if (session.mode === "easyReview") {
      $("complete-summary").textContent = state.language === "en"
        ? `Completed ordered review of ${session.initialCount} difficult words; remembered ${session.remembered} times and forgot ${session.forgotten} times this round.`
        : `已完成 ${session.initialCount} 个易忘词的顺序复习；本轮标记记住 ${session.remembered} 次，忘记 ${session.forgotten} 次。`;
      $("continue-button").hidden = true;
    } else if (session.mode === "combined") {
      $("complete-summary").textContent = state.language === "en"
        ? `Combined mode complete: all ${session.totalSentenceCount} sentence cards are known, with ${session.groups.length} word-review groups completed.`
        : `组合模式已完成：${session.totalSentenceCount} 张句子卡片均已掌握，并完成 ${session.groups.length} 组熟词复习。`;
      $("continue-button").hidden = true;
    } else {
      const known = state.cards.filter((card) => card.status === "known" && (!session.deckId || card.deckId === session.deckId)).length;
      $("complete-summary").textContent = state.language === "en"
        ? `Remembered ${session.remembered} times and forgot ${session.forgotten} times this round; ${known} cards are now known.`
        : `本轮记住 ${session.remembered} 次，忘记 ${session.forgotten} 次；当前已有 ${known} 张卡片达到 known。`;
      $("continue-button").hidden = !state.cards.some((card) => card.status !== "known" && (!session.deckId || card.deckId === session.deckId));
    }
    showView($("complete-view"));
  }

  function goHome() {
    clearTimeout(transitionTimer);
    flushAdjustedWordCardPosition();
    clearWordCardPositioning();
    if (document.activeElement && typeof document.activeElement.blur === "function") {
      document.activeElement.blur();
    }
    notifyNativeManagedTextInputFocus(false);
    lastRenderedReviewType = null;
    stopStudyTimer();
    stopCardSpeech();
    if (session && session.queue.length) persistSession();
    session = null;
    renderDashboard();
    showView($("dashboard-view"));
  }

  function handleNativeBack() {
    if (!$("card-editor-modal").hidden) {
      closeCardEditor();
      return true;
    }
    if (!$("study-settings-modal").hidden) {
      closeStudySettings();
      return true;
    }
    if (!$("combined-settings-modal").hidden) {
      closeCombinedSettings();
      return true;
    }
    if (!$("easy-words-modal").hidden) {
      closeEasyWords();
      return true;
    }
    if (!$("deck-export-modal").hidden) {
      closeDeckExportModal();
      return true;
    }
    if (!$("language-modal").hidden) {
      closeLanguageSettings();
      return true;
    }
    if (!$("study-view").hidden || !$("complete-view").hidden) {
      goHome();
      return true;
    }
    return false;
  }

  window.handleNativeBack = handleNativeBack;

  function chooseFiles() { $("file-input").click(); }

  function openLanguageSettings() {
    updateLanguageSelection();
    $("language-modal").hidden = false;
  }

  function closeLanguageSettings() {
    $("language-modal").hidden = true;
  }

  function setLanguage(language) {
    if (language !== "zh" && language !== "en") return;
    state.language = language;
    saveState();
    closeLanguageSettings();
    applyLanguage(true);
  }

  $("add-button").addEventListener("click", chooseFiles);
  $("language-settings-button").addEventListener("click", openLanguageSettings);
  $("language-zh-button").addEventListener("click", () => setLanguage("zh"));
  $("language-en-button").addEventListener("click", () => setLanguage("en"));
  $("language-close-button").addEventListener("click", closeLanguageSettings);
  $("language-modal").addEventListener("click", (event) => {
    if (event.target === $("language-modal")) closeLanguageSettings();
  });
  $("export-current-button").addEventListener("click", safeAction(openDeckExportModal));
  $("empty-add-button").addEventListener("click", chooseFiles);
  $("file-input").addEventListener("change", (event) => importFiles(event.target.files));
  $("backup-button").addEventListener("click", downloadBackup);
  $("restore-button").addEventListener("click", chooseBackupFile);
  $("restore-file-input").addEventListener("change", (event) => restoreBackup(event.target.files[0]));
  $("start-all-button").addEventListener("click", () => openStudySettings(null));
  $("home-link").addEventListener("click", (event) => { event.preventDefault(); goHome(); });
  $("back-button").addEventListener("click", goHome);
  $("finish-button").addEventListener("click", goHome);
  $("complete-home-button").addEventListener("click", goHome);
  $("continue-button").addEventListener("click", () => startStudy(session && session.deckId, (session && session.knownTarget) || state.learningTarget));
  $("tts-toggle-button").addEventListener("click", toggleTts);
  $("tts-speed-range").addEventListener("input", (event) => changeTtsRate(event.target.value));
  $("edit-card-button").addEventListener("click", openCardEditor);
  $("card-editor-textarea").addEventListener("input", updateEditorClozeCount);
  $("card-editor-textarea").addEventListener("focus", () => notifyNativeCardEditorFocus(true));
  $("card-editor-textarea").addEventListener("blur", () => notifyNativeCardEditorFocus(false));
  $("editor-save-button").addEventListener("click", saveCardEdit);
  $("editor-cancel-button").addEventListener("click", closeCardEditor);
  $("editor-close-button").addEventListener("click", closeCardEditor);
  $("card-editor-modal").addEventListener("click", (event) => {
    if (event.target === $("card-editor-modal")) closeCardEditor();
  });
  document.addEventListener("focusin", (event) => {
    if (isClozeTextInput(event.target)) notifyNativeManagedTextInputFocus(true);
  }, true);
  document.addEventListener("focusout", (event) => {
    if (!isClozeTextInput(event.target)) return;
    notifyNativeManagedTextInputFocus(isClozeTextInput(event.relatedTarget));
  }, true);
  $("target-count-range").addEventListener("input", (event) => {
    $("target-count-display").textContent = event.target.value;
  });
  $("settings-start-button").addEventListener("click", confirmStudySettings);
  $("settings-cancel-button").addEventListener("click", closeStudySettings);
  $("settings-close-button").addEventListener("click", closeStudySettings);
  $("study-settings-modal").addEventListener("click", (event) => {
    if (event.target === $("study-settings-modal")) closeStudySettings();
  });
  $("combined-target-range").addEventListener("input", (event) => {
    $("combined-target-value").textContent = state.language === "en" ? `${event.target.value} times` : `${event.target.value} 次`;
  });
  $("combined-group-range").addEventListener("input", (event) => {
    $("combined-group-value").textContent = state.language === "en" ? `${event.target.value} cards` : `${event.target.value} 张`;
  });
  $("combined-start-button").addEventListener("click", confirmCombinedSettings);
  $("combined-cancel-button").addEventListener("click", closeCombinedSettings);
  $("combined-close-button").addEventListener("click", closeCombinedSettings);
  $("combined-settings-modal").addEventListener("click", (event) => {
    if (event.target === $("combined-settings-modal")) closeCombinedSettings();
  });
  $("easy-words-start-button").addEventListener("click", confirmEasyWords);
  $("easy-words-cancel-button").addEventListener("click", closeEasyWords);
  $("easy-words-close-button").addEventListener("click", closeEasyWords);
  $("easy-words-modal").addEventListener("click", (event) => {
    if (event.target === $("easy-words-modal")) closeEasyWords();
  });
  $("deck-export-select-all").addEventListener("change", (event) => {
    $("deck-export-list").querySelectorAll('input[type="checkbox"]').forEach((box) => {
      box.checked = event.target.checked;
    });
    updateDeckExportSelection();
  });
  $("deck-export-confirm-button").addEventListener("click", safeAction(confirmDeckExport));
  $("deck-export-cancel-button").addEventListener("click", closeDeckExportModal);
  $("deck-export-close-button").addEventListener("click", closeDeckExportModal);
  $("deck-export-modal").addEventListener("click", (event) => {
    if (event.target === $("deck-export-modal")) closeDeckExportModal();
  });
  $("reveal-button").addEventListener("click", () => performStudyControl("ArrowUp"));
  $("hide-button").addEventListener("click", () => performStudyControl("ArrowDown"));
  $("forgot-button").addEventListener("click", () => performStudyControl("ArrowLeft"));
  $("remember-button").addEventListener("click", () => performStudyControl("ArrowRight"));
  $("undo-button").addEventListener("click", () => performStudyControl("Tab"));

  document.addEventListener("keydown", (event) => {
    clearDashboardPositioning();
    recordStudyActivity(event);
  }, true);
  document.addEventListener("pointerdown", beginWordCardPositionGesture, true);
  document.addEventListener("pointermove", continueWordCardPositionGesture, true);
  document.addEventListener("pointerup", endWordCardPositionGesture, true);
  document.addEventListener("pointercancel", endWordCardPositionGesture, true);
  document.addEventListener("wheel", noteWordCardWheelAdjustment, true);
  window.addEventListener("scroll", captureWordCardPositionDuringManualScroll);
  window.addEventListener("resize", handleDashboardViewportResize);
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", handleDashboardViewportResize);
  }
  document.addEventListener("input", recordStudyActivity, true);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pauseStudyTimer();
  });

  document.addEventListener("keydown", (event) => {
    const key = resolveKeyboardKey(event);
    if (event.target === $("tts-speed-range") && key !== "Tab") return;
    const managedTarget = isManagedTextInput(event.target) ? event.target : document.activeElement;
    if (isClozeTextInput(managedTarget) && nativeHardwareKeyboardConnected()) {
      const printableText = printableTextFromDomKey(event);
      if (printableText && insertNativePrintableText(printableText)) {
        event.preventDefault();
        return;
      }
    }
    if (key === "Space" && !event.ctrlKey && !event.altKey && !event.metaKey && !event.isComposing) {
      const target = managedTarget;
      if (isManagedTextInput(target)) return;
      if (handlePhysicalSpace(Boolean(event.shiftKey), target)) event.preventDefault();
      return;
    }
    if (!$("card-editor-modal").hidden) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeCardEditor();
      }
      return;
    }
    if (key === "Tab" && event.repeat) {
      const canUndo = session && (!$("study-view").hidden || !$("complete-view").hidden);
      if (canUndo) event.preventDefault();
      return;
    }
    if (event.key === "Escape" && !$("study-settings-modal").hidden) {
      event.preventDefault();
      closeStudySettings();
      return;
    }
    if (event.key === "Escape" && !$("combined-settings-modal").hidden) {
      event.preventDefault();
      closeCombinedSettings();
      return;
    }
    if (event.key === "Escape" && !$("easy-words-modal").hidden) {
      event.preventDefault();
      closeEasyWords();
      return;
    }
    if (event.key === "Escape" && !$("deck-export-modal").hidden) {
      event.preventDefault();
      closeDeckExportModal();
      return;
    }
    if (event.key === "Escape" && !$("language-modal").hidden) {
      event.preventDefault();
      closeLanguageSettings();
      return;
    }
    if (performStudyControl(key)) {
      event.preventDefault();
    }
  });

  window.addEventListener("beforeunload", () => {
    stopStudyTimer();
    if (session && session.queue.length) persistSession();
    stopCardSpeech();
  });

  const repairedCombinedProgress = repairResetCombinedSessions();
  applyLanguage(false);
  renderDashboard();
  scheduleDashboardPositioning();
  updateTtsButton();
  updateTtsRateControl();
  loadBundledFiles();
  if (repairedCombinedProgress) setTimeout(() => toast("已自动恢复组合模式进度，请继续学习"), 150);
})();
