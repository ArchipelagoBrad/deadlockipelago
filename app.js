(function () {
  "use strict";

  const FORM = document.getElementById("options-form");
  const HERO_GRID = document.getElementById("hero-grid");
  const RANDOM_CHECK = document.getElementById("starting-heroes-random");
  const SLOTS = [0, 1, 2].map((i) => ({
    el: document.querySelector(`.hero-slot[data-slot="${i}"] .slot-portrait`),
    clearBtn: document.querySelector(`.slot-clear[data-slot="${i}"]`),
  }));

  let selectedHeroes = [null, null, null]; // itemName or null per slot

  function renderHeroGrid() {
    HERO_GRID.innerHTML = "";
    HEROES.forEach((hero) => {
      const idx = selectedHeroes.indexOf(hero.itemName);
      const inSlot = idx >= 0;
      const selected = inSlot || (selectedHeroes.includes(null) && !RANDOM_CHECK.checked);
      const div = document.createElement("div");
      div.className = "hero-option" + (inSlot ? " in-slot" : selected ? " selected" : "");
      div.dataset.itemName = hero.itemName;
      const portraitDiv = document.createElement("div");
      portraitDiv.className = "hero-portrait";
      const img = document.createElement("img");
      img.src = portraitUrl(hero);
      img.alt = hero.displayName;
      img.loading = "lazy";
      const placeholder = document.createElement("span");
      placeholder.className = "placeholder";
      placeholder.style.display = "none";
      img.onerror = function () {
        img.style.display = "none";
        placeholder.style.display = "block";
        placeholder.textContent = (hero.displayName && hero.displayName.charAt(0)) || "?";
      };
      portraitDiv.appendChild(img);
      portraitDiv.appendChild(placeholder);
      const nameSpan = document.createElement("span");
      nameSpan.className = "hero-name";
      nameSpan.textContent = hero.displayName;
      div.appendChild(portraitDiv);
      div.appendChild(nameSpan);
      div.addEventListener("click", () => onHeroClick(hero));
      HERO_GRID.appendChild(div);
    });
  }

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function onHeroClick(hero) {
    if (RANDOM_CHECK.checked) return;
    const idx = selectedHeroes.indexOf(hero.itemName);
    if (idx >= 0) {
      selectedHeroes[idx] = null;
      updateSlots();
      renderHeroGrid();
      return;
    }
    const firstEmpty = selectedHeroes.indexOf(null);
    if (firstEmpty >= 0) {
      selectedHeroes[firstEmpty] = hero.itemName;
      updateSlots();
      renderHeroGrid();
    } else {
      // replace slot 0
      selectedHeroes[0] = hero.itemName;
      updateSlots();
      renderHeroGrid();
    }
  }

  function updateSlots() {
    const isRandom = RANDOM_CHECK.checked;
    selectedHeroes.forEach((itemName, i) => {
      const slot = SLOTS[i];
      slot.el.innerHTML = "";
      if (isRandom) {
        const span = document.createElement("span");
        span.className = "placeholder";
        span.textContent = "?";
        slot.el.appendChild(span);
      } else if (itemName) {
        const hero = HEROES.find((h) => h.itemName === itemName);
        if (hero) {
          const img = document.createElement("img");
          img.src = portraitUrl(hero);
          img.alt = hero.displayName;
          img.onerror = function () {
            img.style.display = "none";
            const span = document.createElement("span");
            span.className = "placeholder";
            span.textContent = hero.displayName.charAt(0);
            slot.el.appendChild(span);
          };
          slot.el.appendChild(img);
        }
      } else {
        const span = document.createElement("span");
        span.className = "placeholder";
        span.textContent = "—";
        slot.el.appendChild(span);
      }
    });
  }

  SLOTS.forEach((slot, i) => {
    slot.clearBtn.addEventListener("click", (e) => {
      e.preventDefault();
      selectedHeroes[i] = null;
      updateSlots();
      renderHeroGrid();
      startingHeroesSection.classList.toggle("random-heroes", RANDOM_CHECK.checked);
      if (goalTypeSelect.value === "win_with_character") updateFinalCharacterDropdown();
    });
  });

  const startingHeroesSection = document.getElementById("starting-heroes-section");
  RANDOM_CHECK.addEventListener("change", () => {
    if (RANDOM_CHECK.checked) {
      selectedHeroes = [null, null, null];
      updateSlots();
    } else {
      updateSlots();
    }
    startingHeroesSection.classList.toggle("random-heroes", RANDOM_CHECK.checked);
    renderHeroGrid();
    if (goalTypeSelect.value === "win_with_character") updateFinalCharacterDropdown();
  });

  const goalTypeSelect = document.getElementById("goal_type");
  const goalTypeDesc = document.getElementById("goal_type_description");
  const fieldUnique = document.getElementById("field-unique-characters");
  const fieldTotalWins = document.getElementById("field-total-wins");
  const fieldSpirits = document.getElementById("field-spirits");
  const spiritsSlider = document.getElementById("spirits_to_win");
  const spiritsDisplay = document.getElementById("spirits_to_win_display");
  const spiritsHint = document.getElementById("spirits_to_win_hint");
  const gameModeSelect = document.getElementById("game_mode");

  // Max Spirits = number of check locations (pool size). Depends on game mode and exclude hard locations.
  const SPIRITS_MAX = {
    standard: 162,
    standard_exclude_hard: 135,   // 162 - 27 hard locations in standard
    street_brawl: 143,
    street_brawl_exclude_hard: 119, // 143 - 24 hard locations in street brawl
  };

  const excludeHardCheckbox = document.getElementById("exclude_hard_locations");

  function getSpiritsMax() {
    const isStreetBrawl = gameModeSelect.value === "street_brawl";
    const excludeHard = excludeHardCheckbox && excludeHardCheckbox.checked;
    if (isStreetBrawl) return excludeHard ? SPIRITS_MAX.street_brawl_exclude_hard : SPIRITS_MAX.street_brawl;
    return excludeHard ? SPIRITS_MAX.standard_exclude_hard : SPIRITS_MAX.standard;
  }

  function getSpiritsMaxLabel() {
    const isStreetBrawl = gameModeSelect.value === "street_brawl";
    const excludeHard = excludeHardCheckbox && excludeHardCheckbox.checked;
    const mode = isStreetBrawl ? "Street Brawl" : "Standard";
    return excludeHard ? `${mode} (excl. hard)` : mode;
  }

  function updateSpiritsDisplay() {
    const max = getSpiritsMax();
    const val = Math.min(max, Math.max(1, parseInt(spiritsSlider.value, 10) || 1));
    spiritsSlider.value = val;
    const pct = max > 0 ? ((val / max) * 100).toFixed(1) : "0";
    spiritsDisplay.innerHTML = `${val} <span class="spirits-percent">(${pct}%)</span>`;
    spiritsHint.textContent = `Number of Spirits (MacGuffin) you must collect to win. Max ${max} (${getSpiritsMaxLabel()}).`;
  }

  function updateSpiritsSliderMax() {
    const max = getSpiritsMax();
    spiritsSlider.max = max;
    const val = parseInt(spiritsSlider.value, 10) || 10;
    if (val > max) spiritsSlider.value = max;
    updateSpiritsDisplay();
  }

  const GOAL_DESCRIPTIONS = {
    unique_characters: "Win with a set number of different characters. Each character you win a match with counts once toward the goal.",
    total_wins: "Win a set number of matches in total. Every match win counts toward the goal, regardless of which character you used.",
    spirits: "Collect a set number of Spirits (MacGuffin items) to win. Spirits are received from the item pool like other items.",
    win_with_character: "Collect a set number of Spirits to unlock your chosen final character, then win one match with that character to complete. The final character cannot be one of your starting heroes.",
  };

  function heroNameToOptionKey(displayName) {
    return displayName.toLowerCase().replace(/ /g, "_").replace(/&/g, "and");
  }

  const fieldWinWithChar = document.getElementById("field-win-with-character");
  const spiritsUnlockSlider = document.getElementById("spirits_to_unlock_final");
  const spiritsUnlockDisplay = document.getElementById("spirits_to_unlock_final_display");
  const finalCharacterSelect = document.getElementById("final_character");

  function updateFinalCharacterDropdown() {
    const startSet = new Set(selectedHeroes.filter(Boolean));
    const available = HEROES.filter((h) => !startSet.has(h.itemName));
    const selected = finalCharacterSelect.value;
    finalCharacterSelect.innerHTML = "";
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "— Select —";
    finalCharacterSelect.appendChild(empty);
    const randomOpt = document.createElement("option");
    randomOpt.value = "random";
    randomOpt.textContent = "Random (not a starting hero)";
    if (selected === "random") randomOpt.selected = true;
    finalCharacterSelect.appendChild(randomOpt);
    available.forEach((hero) => {
      const opt = document.createElement("option");
      opt.value = heroNameToOptionKey(hero.displayName);
      opt.textContent = hero.displayName;
      if (opt.value === selected) opt.selected = true;
      finalCharacterSelect.appendChild(opt);
    });
  }

  function updateSpiritsUnlockDisplay() {
    const max = getSpiritsMax();
    const val = Math.min(max, parseInt(spiritsUnlockSlider.value, 10) || 10);
    spiritsUnlockDisplay.textContent = val;
  }

  function updateGoalDependentVisibility() {
    const goal = goalTypeSelect.value;
    goalTypeDesc.textContent = GOAL_DESCRIPTIONS[goal] || "";
    fieldUnique.classList.toggle("hidden", goal !== "unique_characters");
    fieldTotalWins.classList.toggle("hidden", goal !== "total_wins");
    fieldSpirits.classList.toggle("hidden", goal !== "spirits");
    fieldWinWithChar.classList.toggle("hidden", goal !== "win_with_character");
    if (goal === "spirits") updateSpiritsSliderMax();
    if (goal === "win_with_character") {
      spiritsUnlockSlider.max = getSpiritsMax();
      updateSpiritsUnlockDisplay();
      updateFinalCharacterDropdown();
    }
  }

  function updateAllSpiritsLimits() {
    const max = getSpiritsMax();
    spiritsSlider.max = max;
    spiritsUnlockSlider.max = max;
    const spiritsVal = parseInt(spiritsSlider.value, 10) || 10;
    const unlockVal = parseInt(spiritsUnlockSlider.value, 10) || 10;
    if (spiritsVal > max) spiritsSlider.value = max;
    if (unlockVal > max) spiritsUnlockSlider.value = max;
    if (goalTypeSelect.value === "spirits") updateSpiritsDisplay();
    if (goalTypeSelect.value === "win_with_character") updateSpiritsUnlockDisplay();
  }

  goalTypeSelect.addEventListener("change", updateGoalDependentVisibility);
  gameModeSelect.addEventListener("change", () => {
    updateAllSpiritsLimits();
    if (goalTypeSelect.value === "spirits") updateSpiritsDisplay();
    if (goalTypeSelect.value === "win_with_character") updateFinalCharacterDropdown();
  });
  if (excludeHardCheckbox) {
    excludeHardCheckbox.addEventListener("change", () => {
      updateAllSpiritsLimits();
      if (goalTypeSelect.value === "spirits") updateSpiritsDisplay();
      if (goalTypeSelect.value === "win_with_character") updateSpiritsUnlockDisplay();
    });
  }
  spiritsSlider.addEventListener("input", updateSpiritsDisplay);
  spiritsSlider.addEventListener("change", updateSpiritsDisplay);
  spiritsUnlockSlider.addEventListener("input", updateSpiritsUnlockDisplay);
  spiritsUnlockSlider.addEventListener("change", updateSpiritsUnlockDisplay);
  HERO_GRID.addEventListener("click", () => {
    if (goalTypeSelect.value === "win_with_character") updateFinalCharacterDropdown();
  });
  RANDOM_CHECK.addEventListener("change", () => {
    if (goalTypeSelect.value === "win_with_character") updateFinalCharacterDropdown();
  });
  updateGoalDependentVisibility();
  updateSpiritsDisplay();

  /**
   * @param {string | null} excludeFromRandomPool - When Random starters and Win with Character goal, exclude this hero (itemName) so the final character is not a starter.
   */
  function getStartInventory(excludeFromRandomPool) {
    if (RANDOM_CHECK.checked) {
      let pool = HEROES.slice();
      if (excludeFromRandomPool) {
        pool = pool.filter((h) => h.itemName !== excludeFromRandomPool);
      }
      const shuffled = pool.sort(() => Math.random() - 0.5);
      return {
        [shuffled[0].itemName]: 1,
        [shuffled[1].itemName]: 1,
        [shuffled[2].itemName]: 1,
      };
    }
    const chosen = selectedHeroes.filter(Boolean);
    const inv = {};
    chosen.forEach((itemName) => (inv[itemName] = 1));
    return inv;
  }

  function buildYaml() {
    const name = (document.getElementById("name").value || "Player").trim().slice(0, 16);
    const goalType = document.getElementById("goal_type").value;
    const gameMode = document.getElementById("game_mode").value;
    const excludeHard = document.getElementById("exclude_hard_locations").checked;
    const uniqueNum = Math.min(38, Math.max(1, parseInt(document.getElementById("unique_characters_to_win").value, 10) || 10));
    const totalWinsNum = Math.min(100, Math.max(1, parseInt(document.getElementById("total_wins_to_win").value, 10) || 25));
    const spiritsMax = getSpiritsMax();
    const spiritsNum = Math.min(spiritsMax, Math.max(1, parseInt(document.getElementById("spirits_to_win").value, 10) || 10));
    const spiritsUnlockMax = getSpiritsMax();
    const spiritsUnlockNum = Math.min(spiritsUnlockMax, Math.max(1, parseInt(document.getElementById("spirits_to_unlock_final").value, 10) || 10));
    const finalCharSelectValue = document.getElementById("final_character").value;

    // Resolve final character for Win with Character goal (before getStartInventory so Random starters can exclude it)
    let finalCharHero = null;
    if (goalType === "win_with_character") {
      if (finalCharSelectValue === "random") {
        if (RANDOM_CHECK.checked) {
          finalCharHero = HEROES[Math.floor(Math.random() * HEROES.length)];
        } else {
          const pool = HEROES.filter((h) => !selectedHeroes.includes(h.itemName));
          finalCharHero = pool.length ? pool[Math.floor(Math.random() * pool.length)] : HEROES[0];
        }
      } else if (finalCharSelectValue) {
        finalCharHero = HEROES.find((h) => heroNameToOptionKey(h.displayName) === finalCharSelectValue) || HEROES[0];
      } else {
        finalCharHero = HEROES[0];
      }
    }
    const finalCharKey = finalCharHero ? heroNameToOptionKey(finalCharHero.displayName) : heroNameToOptionKey(HEROES[0].displayName);
    const startInv = getStartInventory(goalType === "win_with_character" && finalCharHero ? finalCharHero.itemName : null);
    const startInvStr = JSON.stringify(startInv);
    const finalCharLines = HEROES.map((h) => {
      const k = heroNameToOptionKey(h.displayName);
      return `    ${k}: ${k === finalCharKey ? "50" : "0"}`;
    }).join("\n");

    return `# Archipelago Deadlock Player Options
# Generated from player options page

name: ${yamlEsc(name)}
description: Generated from player options page
game: Deadlock
requires:
  version: 0.6.6

Deadlock:
  progression_balancing:
    random: 0
    random-low: 0
    random-high: 0
    random-range-0-99: 0
    disabled: 0
    normal: 50
    extreme: 0

  accessibility:
    full: 50
    minimal: 0

  goal_type:
    unique_characters: ${goalType === "unique_characters" ? "50" : "0"}
    total_wins: ${goalType === "total_wins" ? "50" : "0"}
    spirits: ${goalType === "spirits" ? "50" : "0"}
    win_with_character: ${goalType === "win_with_character" ? "50" : "0"}

  unique_characters_to_win:
    ${uniqueNum}: 50
    random: 0
    random-low: 0
    random-high: 0
    random-range-1-38: 0

  total_wins_to_win:
    ${totalWinsNum}: 50
    random: 0
    random-low: 0
    random-high: 0
    random-range-1-100: 0

  spirits_to_win:
    ${spiritsNum}: 50
    random: 0
    random-low: 0
    random-high: 0
    random-range-1-162: 0

  spirits_to_unlock_final:
    ${spiritsUnlockNum}: 50
    random: 0
    random-low: 0
    random-high: 0
    random-range-1-162: 0

  final_character:
${finalCharLines}

  game_mode:
    standard: ${gameMode === "standard" ? "50" : "0"}
    street_brawl: ${gameMode === "street_brawl" ? "50" : "0"}

  exclude_hard_locations:
    0: ${excludeHard ? "0" : "50"}
    1: ${excludeHard ? "50" : "0"}

  local_items: []
  non_local_items: []
  start_inventory: ${startInvStr}
  start_hints: []
  start_location_hints: []
  exclude_locations: []
  priority_locations: []
  item_links: []
  plando_items: []
`;
  }

  function yamlEsc(s) {
    if (/[#:\[\]{}|>*&!%@"'`,\s]/.test(s) || s === "" || s.toLowerCase() === "null" || s.toLowerCase() === "true" || s.toLowerCase() === "false") {
      return "'" + s.replace(/'/g, "''") + "'";
    }
    return s;
  }

  FORM.addEventListener("submit", (e) => {
    e.preventDefault();
    const yaml = buildYaml();
    const blob = new Blob([yaml], { type: "application/x-yaml" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "DeadlockOptions.yaml";
    a.click();
    URL.revokeObjectURL(a.href);
  });

  updateSlots();
  renderHeroGrid();
})();
