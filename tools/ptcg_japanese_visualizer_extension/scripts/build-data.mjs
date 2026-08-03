import fs from "node:fs";
import path from "node:path";
import process from "node:process";

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];

    if (quoted) {
      if (character === '"' && text[index + 1] === '"') {
        value += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        value += character;
      }
    } else if (character === '"') {
      quoted = true;
    } else if (character === ",") {
      row.push(value);
      value = "";
    } else if (character === "\n") {
      row.push(value.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      value = "";
    } else {
      value += character;
    }
  }

  if (value || row.length) {
    row.push(value.replace(/\r$/, ""));
    rows.push(row);
  }

  return rows;
}

function readObjects(csvPath) {
  const rows = parseCsv(fs.readFileSync(csvPath, "utf8").replace(/^\uFEFF/, ""));
  const headers = rows.shift();
  return rows
    .filter((row) => row.some((value) => value !== ""))
    .map((row) =>
      Object.fromEntries(headers.map((header, index) => [header, row[index] || ""]))
    );
}

function clean(value) {
  const normalized = String(value || "").trim();
  return !normalized || /^n\/a$/i.test(normalized) ? "" : normalized;
}

function groupBy(rows, keyName) {
  const groups = new Map();
  for (const row of rows) {
    const key = clean(row[keyName]);
    if (!key) {
      continue;
    }
    if (!groups.has(key)) {
      groups.set(key, []);
    }
    groups.get(key).push(row);
  }
  return groups;
}

function sortedObject(value) {
  return Object.fromEntries(
    Object.entries(value).sort(([left], [right]) =>
      left.localeCompare(right, "en", { numeric: true })
    )
  );
}

function buildTranslations(enRows, jpRows) {
  const enById = groupBy(enRows, "Card ID");
  const jpById = groupBy(jpRows, "カード ID");
  const cardNames = {};
  const englishCardNames = {};
  const attackNames = {};
  const conflicts = [];
  let pairedMoveRows = 0;

  for (const [cardId, enCardRows] of enById) {
    const jpCardRows = jpById.get(cardId) || [];
    const englishName = clean(enCardRows[0]?.["Card Name"]);
    const japaneseName = clean(jpCardRows[0]?.["カード名"]);

    if (japaneseName) {
      cardNames[cardId] = japaneseName;
      if (englishName && englishName !== japaneseName) {
        englishCardNames[englishName] = japaneseName;
      }
    }

    const pairedLength = Math.min(enCardRows.length, jpCardRows.length);
    for (let index = 0; index < pairedLength; index += 1) {
      const englishMove = clean(enCardRows[index]["Move Name"]);
      const japaneseMove = clean(jpCardRows[index]["ワザ名"]);
      if (!englishMove || !japaneseMove || englishMove === japaneseMove) {
        continue;
      }

      pairedMoveRows += 1;
      if (attackNames[englishMove] && attackNames[englishMove] !== japaneseMove) {
        conflicts.push({
          english: englishMove,
          kept: attackNames[englishMove],
          ignored: japaneseMove,
          cardId
        });
      } else {
        attackNames[englishMove] = japaneseMove;
      }
    }
  }

  return {
    payload: {
      cardNames: sortedObject(cardNames),
      englishCardNames: sortedObject(englishCardNames),
      attackNames: sortedObject(attackNames),
      source: {
        englishCsv: "EN_Card_Data.csv",
        japaneseCsv: "JP_Card_Data.csv",
        cardCount: Object.keys(cardNames).length,
        englishCardNameCount: Object.keys(englishCardNames).length,
        attackNameCount: Object.keys(attackNames).length,
        pairedMoveRows,
        conflictCount: conflicts.length
      }
    },
    conflicts
  };
}

function buildRedirectRules(cardIds) {
  const imageRoot = "|https://ptcgvis.heroz.jp/img/bqucewmzuceknw/";
  const rules = [];

  cardIds.forEach((cardId, index) => {
    const baseRuleId = index * 2 + 1;
    rules.push({
      id: baseRuleId,
      priority: 1,
      action: {
        type: "redirect",
        redirect: {
          extensionPath: `/assets/cards_jp/${cardId}.jpg`
        }
      },
      condition: {
        urlFilter: `${imageRoot}${cardId}.png`,
        // Phaser loads textures through XHR rather than a plain <img> request.
        resourceTypes: ["image", "xmlhttprequest"]
      }
    });
    rules.push({
      id: baseRuleId + 1,
      priority: 1,
      action: {
        type: "redirect",
        redirect: {
          extensionPath: `/assets/cards_jp_m/${cardId}.jpg`
        }
      },
      condition: {
        urlFilter: `${imageRoot}${cardId}m.png`,
        resourceTypes: ["image", "xmlhttprequest"]
      }
    });
  });

  return rules;
}

function main() {
  const [enCsv, jpCsv, extensionRootArg] = process.argv.slice(2);
  if (!enCsv || !jpCsv || !extensionRootArg) {
    throw new Error(
      "Usage: node build-data.mjs EN_Card_Data.csv JP_Card_Data.csv EXTENSION_ROOT"
    );
  }

  const extensionRoot = path.resolve(extensionRootArg);
  const { payload, conflicts } = buildTranslations(
    readObjects(enCsv),
    readObjects(jpCsv)
  );

  const translationBody =
    "// Generated from the competition-provided EN/JP card CSV files.\n" +
    `globalThis.PTCG_JA_TRANSLATIONS = Object.freeze(${JSON.stringify(
      payload,
      null,
      2
    )});\n`;
  fs.writeFileSync(
    path.join(extensionRoot, "translations.js"),
    translationBody,
    "utf8"
  );

  const cardIds = Object.keys(payload.cardNames).sort(
    (left, right) => Number(left) - Number(right)
  );
  fs.writeFileSync(
    path.join(extensionRoot, "rules.json"),
    `${JSON.stringify(buildRedirectRules(cardIds), null, 2)}\n`,
    "utf8"
  );

  process.stdout.write(
    `${JSON.stringify(
      {
        ...payload.source,
        redirectRuleCount: cardIds.length * 2,
        conflicts: conflicts.slice(0, 20)
      },
      null,
      2
    )}\n`
  );
}

main();
