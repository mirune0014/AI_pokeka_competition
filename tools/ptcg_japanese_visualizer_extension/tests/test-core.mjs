import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const testRoot = path.dirname(fileURLToPath(import.meta.url));
const extensionRoot = path.resolve(testRoot, "..");
const context = vm.createContext({});
context.globalThis = context;

for (const fileName of ["translations.js", "core.js"]) {
  vm.runInContext(
    fs.readFileSync(path.join(extensionRoot, fileName), "utf8"),
    context,
    { filename: fileName }
  );
}

const data = context.PTCG_JA_TRANSLATIONS;
const core = context.PTCG_JA_CORE;
const rules = JSON.parse(
  fs.readFileSync(path.join(extensionRoot, "rules.json"), "utf8")
);

assert.ok(data.source.cardCount > 1200);
assert.equal(data.cardNames["66"], "ノココッチ");
assert.equal(rules.length, data.source.cardCount * 2);
assert.ok(rules.every((rule) => rule.condition.urlFilter));
assert.ok(rules.every((rule) => !rule.condition.regexFilter));
assert.ok(
  rules.every((rule) =>
    rule.condition.resourceTypes.includes("xmlhttprequest")
  )
);
assert.ok(
  rules.every((rule) => rule.condition.resourceTypes.includes("image"))
);
for (const cardId of Object.keys(data.cardNames)) {
  assert.ok(
    fs.existsSync(path.join(extensionRoot, "assets", "cards_jp", `${cardId}.jpg`)),
    `missing full-size image for card ${cardId}`
  );
  assert.ok(
    fs.existsSync(
      path.join(extensionRoot, "assets", "cards_jp_m", `${cardId}.jpg`)
    ),
    `missing miniature image for card ${cardId}`
  );
}

const cardParams = Array.from({ length: 67 }, () => ({ name: "unknown" }));
cardParams[66] = { name: "Dudunsparce", hp: 140 };
core.translateCardParams(cardParams, data.cardNames);
assert.equal(cardParams[66].name, "ノココッチ");

const attacks = ["", "Land Crush"];
core.translateAttackNames(attacks, data.attackNames);
assert.notEqual(attacks[1], "Land Crush");

const intercepted = {};
assert.equal(
  core.installGlobalInterceptor(intercepted, "cardParams", (value) =>
    core.translateCardParams(value, data.cardNames)
  ),
  "intercepted"
);
intercepted.cardParams = cardParams;
assert.equal(intercepted.cardParams[66].name, "ノココッチ");

const replacements = core.compileReplacements(
  { "Selected Action": "選択した行動" },
  data.englishCardNames
);
assert.equal(
  core.replaceKnownText("Selected Action: Dudunsparce", replacements),
  "選択した行動: ノココッチ"
);

process.stdout.write(
  `ok: cards=${data.source.cardCount} attacks=${data.source.attackNameCount}\n`
);
