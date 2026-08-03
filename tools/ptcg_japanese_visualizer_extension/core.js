(function initializePtcgJapaneseCore(root) {
  "use strict";

  function translateCardParams(value, cardNames) {
    if (!Array.isArray(value) || !cardNames) {
      return value;
    }

    value.forEach((entry, index) => {
      if (!entry || typeof entry !== "object") {
        return;
      }

      const cardId = Number.isInteger(entry.cardId) ? entry.cardId : index;
      const translatedName = cardNames[String(cardId)];
      if (translatedName) {
        entry.name = translatedName;
      }
    });

    return value;
  }

  function translateAttackNames(value, attackNames) {
    if (!Array.isArray(value) || !attackNames) {
      return value;
    }

    value.forEach((name, index) => {
      if (typeof name === "string" && attackNames[name]) {
        value[index] = attackNames[name];
      }
    });

    return value;
  }

  function installGlobalInterceptor(target, propertyName, transform) {
    const descriptor = Object.getOwnPropertyDescriptor(target, propertyName);

    if (descriptor && !descriptor.configurable) {
      if ("value" in descriptor && descriptor.writable) {
        target[propertyName] = transform(target[propertyName]);
        return "direct";
      }
      return "unavailable";
    }

    let currentValue;
    if (descriptor && "value" in descriptor) {
      currentValue = descriptor.value;
    } else if (descriptor && descriptor.get) {
      currentValue = descriptor.get.call(target);
    } else {
      currentValue = target[propertyName];
    }

    if (currentValue !== undefined) {
      currentValue = transform(currentValue);
    }

    Object.defineProperty(target, propertyName, {
      configurable: true,
      enumerable: descriptor ? descriptor.enumerable : true,
      get() {
        return currentValue;
      },
      set(nextValue) {
        currentValue = transform(nextValue);
      }
    });

    return "intercepted";
  }

  function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function compileReplacements(...maps) {
    const replacements = Object.create(null);

    for (const map of maps) {
      if (!map) {
        continue;
      }
      for (const [english, japanese] of Object.entries(map)) {
        if (
          typeof english === "string" &&
          english.length > 1 &&
          typeof japanese === "string" &&
          japanese &&
          !Object.prototype.hasOwnProperty.call(replacements, english)
        ) {
          replacements[english] = japanese;
        }
      }
    }

    const keys = Object.keys(replacements).sort(
      (left, right) => right.length - left.length || left.localeCompare(right)
    );

    return {
      replacements,
      regex: keys.length ? new RegExp(keys.map(escapeRegExp).join("|"), "g") : null
    };
  }

  function replaceKnownText(value, compiled) {
    if (
      typeof value !== "string" ||
      !value ||
      !compiled ||
      !compiled.regex
    ) {
      return value;
    }

    compiled.regex.lastIndex = 0;
    return value.replace(
      compiled.regex,
      (matched) => compiled.replacements[matched] || matched
    );
  }

  root.PTCG_JA_CORE = Object.freeze({
    compileReplacements,
    installGlobalInterceptor,
    replaceKnownText,
    translateAttackNames,
    translateCardParams
  });
})(globalThis);
