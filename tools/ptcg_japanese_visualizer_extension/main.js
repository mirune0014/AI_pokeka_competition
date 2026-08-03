(function initializePtcgJapaneseVisualizer(root) {
  "use strict";

  const data = root.PTCG_JA_TRANSLATIONS;
  const core = root.PTCG_JA_CORE;
  if (!data || !core) {
    return;
  }

  core.installGlobalInterceptor(root, "cardParams", (value) =>
    core.translateCardParams(value, data.cardNames)
  );
  core.installGlobalInterceptor(root, "attackNames", (value) =>
    core.translateAttackNames(value, data.attackNames)
  );

  const uiTranslations = Object.freeze({
    "Selected Action": "選択した行動",
    "Your select type": "選択タイプ",
    "Prize Cards": "サイド",
    "Active Spot": "バトル場",
    "YOU WIN.": "あなたの勝ちです。",
    "YOU LOSE.": "あなたの負けです。",
    "OPPONENT": "相手",
    "Observation": "観測",
    "minCount": "最小枚数",
    "maxCount": "最大枚数",
    "Discard": "トラッシュ",
    "Select": "選択",
    "Bench": "ベンチ",
    "context": "コンテキスト",
    "Deck": "山札",
    "Hand": "手札",
    "Log": "ログ",
    "YOU": "自分"
  });

  const compiled = core.compileReplacements(
    uiTranslations,
    data.englishCardNames,
    data.attackNames
  );
  const skippedTags = new Set([
    "SCRIPT",
    "STYLE",
    "NOSCRIPT",
    "CANVAS",
    "TEXTAREA",
    "INPUT"
  ]);

  function translateTextNode(node) {
    if (
      !node ||
      node.nodeType !== Node.TEXT_NODE ||
      !node.parentElement ||
      skippedTags.has(node.parentElement.tagName)
    ) {
      return;
    }

    const translated = core.replaceKnownText(node.nodeValue, compiled);
    if (translated !== node.nodeValue) {
      node.nodeValue = translated;
    }
  }

  function translateTextNodes(rootNode) {
    if (!rootNode) {
      return;
    }

    if (rootNode.nodeType === Node.TEXT_NODE) {
      translateTextNode(rootNode);
      return;
    }

    if (
      rootNode.nodeType !== Node.ELEMENT_NODE &&
      rootNode.nodeType !== Node.DOCUMENT_NODE
    ) {
      return;
    }

    const walker = document.createTreeWalker(rootNode, NodeFilter.SHOW_TEXT);
    let node = walker.nextNode();
    while (node) {
      translateTextNode(node);
      node = walker.nextNode();
    }
  }

  function translateFormValues() {
    for (const element of document.querySelectorAll("textarea, input")) {
      if (
        element instanceof HTMLTextAreaElement &&
        /^\s*[\[{]/.test(element.value)
      ) {
        continue;
      }

      const translated = core.replaceKnownText(element.value, compiled);
      if (translated !== element.value) {
        element.value = translated;
      }

      if (element.placeholder) {
        const translatedPlaceholder = core.replaceKnownText(
          element.placeholder,
          compiled
        );
        if (translatedPlaceholder !== element.placeholder) {
          element.placeholder = translatedPlaceholder;
        }
      }
    }
  }

  function addStatusBadge() {
    if (document.getElementById("ptcg-ja-status")) {
      return;
    }

    const badge = document.createElement("div");
    badge.id = "ptcg-ja-status";
    badge.textContent = "日本語カード表示";
    badge.title =
      "コンペ配布の日本語カード画像と日英カードデータを使って表示しています。";
    Object.assign(badge.style, {
      position: "fixed",
      top: "8px",
      right: "8px",
      zIndex: "2147483647",
      padding: "6px 10px",
      border: "1px solid rgba(255,255,255,.35)",
      borderRadius: "999px",
      background: "rgba(20, 78, 45, .92)",
      boxShadow: "0 2px 10px rgba(0,0,0,.25)",
      color: "#fff",
      font: "600 12px/1.2 system-ui, sans-serif",
      pointerEvents: "none"
    });
    document.body.appendChild(badge);
  }

  function startDomLocalization() {
    document.documentElement.lang = "ja";
    translateTextNodes(document.body);
    translateFormValues();
    addStatusBadge();

    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "characterData") {
          translateTextNode(mutation.target);
        } else {
          for (const addedNode of mutation.addedNodes) {
            translateTextNodes(addedNode);
          }
        }
      }
    });
    observer.observe(document.body, {
      childList: true,
      characterData: true,
      subtree: true
    });

    // The official viewer writes log and action values directly to form controls.
    root.setInterval(translateFormValues, 400);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startDomLocalization, {
      once: true
    });
  } else {
    startDomLocalization();
  }
})(globalThis);
