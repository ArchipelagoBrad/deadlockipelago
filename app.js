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
  });

  const goalTypeSelect = document.getElementById("goal_type");
  const goalTypeDesc = document.getElementById("goal_type_description");
  const fieldUnique = document.getElementById("field-unique-characters");
  const fieldTotalWins = document.getElementById("field-total-wins");

  const GOAL_DESCRIPTIONS = {
    unique_characters: "Win with a set number of different characters. Each character you win a match with counts once toward the goal.",
    total_wins: "Win a set number of matches in total. Every match win counts toward the goal, regardless of which character you used.",
  };

  function updateGoalDependentVisibility() {
    const goal = goalTypeSelect.value;
    goalTypeDesc.textContent = GOAL_DESCRIPTIONS[goal] || "";
    if (goal === "unique_characters") {
      fieldUnique.classList.remove("hidden");
      fieldTotalWins.classList.add("hidden");
    } else {
      fieldUnique.classList.add("hidden");
      fieldTotalWins.classList.remove("hidden");
    }
  }

  goalTypeSelect.addEventListener("change", updateGoalDependentVisibility);
  updateGoalDependentVisibility();

  function getStartInventory() {
    if (RANDOM_CHECK.checked) {
      const shuffled = HEROES.slice().sort(() => Math.random() - 0.5);
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
    const uniqueNum = Math.min(38, Math.max(1, parseInt(document.getElementById("unique_characters_to_win").value, 10) || 10));
    const totalWinsNum = Math.min(100, Math.max(1, parseInt(document.getElementById("total_wins_to_win").value, 10) || 25));
    const startInv = getStartInventory();
    const startInvStr = JSON.stringify(startInv);

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
