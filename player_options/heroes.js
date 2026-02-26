/**
 * Deadlock hero list for player options.
 * itemName: used in start_inventory (e.g. "Unlock Abrams").
 * displayName: shown in UI.
 * portraitFile: optional override for filename in deadlock-portraits/. If omitted, uses 88px-{Name}_card.png (spaces → underscores).
 */
const HEROES = [
  { itemName: "Unlock Abrams", displayName: "Abrams" },
  { itemName: "Unlock Apollo", displayName: "Apollo" },
  { itemName: "Unlock Bebop", displayName: "Bebop" },
  { itemName: "Unlock Billy", displayName: "Billy" },
  { itemName: "Unlock Calico", displayName: "Calico" },
  { itemName: "Unlock Celeste", displayName: "Celeste" },
  { itemName: "Unlock Doorman", displayName: "Doorman", portraitFile: "88px-The_Doorman_card.png" },
  { itemName: "Unlock Drifter", displayName: "Drifter" },
  { itemName: "Unlock Dynamo", displayName: "Dynamo" },
  { itemName: "Unlock Graves", displayName: "Graves" },
  { itemName: "Unlock Grey Talon", displayName: "Grey Talon" },
  { itemName: "Unlock Haze", displayName: "Haze" },
  { itemName: "Unlock Holliday", displayName: "Holliday" },
  { itemName: "Unlock Infernus", displayName: "Infernus" },
  { itemName: "Unlock Ivy", displayName: "Ivy" },
  { itemName: "Unlock Kelvin", displayName: "Kelvin" },
  { itemName: "Unlock Lady Geist", displayName: "Lady Geist" },
  { itemName: "Unlock Lash", displayName: "Lash" },
  { itemName: "Unlock McGinnis", displayName: "McGinnis" },
  { itemName: "Unlock Mina", displayName: "Mina" },
  { itemName: "Unlock Mirage", displayName: "Mirage" },
  { itemName: "Unlock Mo & Krill", displayName: "Mo & Krill" },
  { itemName: "Unlock Paige", displayName: "Paige" },
  { itemName: "Unlock Paradox", displayName: "Paradox" },
  { itemName: "Unlock Pocket", displayName: "Pocket" },
  { itemName: "Unlock Rem", displayName: "Rem" },
  { itemName: "Unlock Seven", displayName: "Seven" },
  { itemName: "Unlock Shiv", displayName: "Shiv" },
  { itemName: "Unlock Silver", displayName: "Silver" },
  { itemName: "Unlock Sinclair", displayName: "Sinclair" },
  { itemName: "Unlock Venator", displayName: "Venator" },
  { itemName: "Unlock Victor", displayName: "Victor" },
  { itemName: "Unlock Vindicta", displayName: "Vindicta" },
  { itemName: "Unlock Viscous", displayName: "Viscous" },
  { itemName: "Unlock Vyper", displayName: "Vyper" },
  { itemName: "Unlock Warden", displayName: "Warden" },
  { itemName: "Unlock Wraith", displayName: "Wraith" },
  { itemName: "Unlock Yamato", displayName: "Yamato" },
];

const PORTRAIT_BASE = "deadlock-portraits";

function portraitUrl(hero) {
  const filename = hero.portraitFile != null
    ? hero.portraitFile
    : "88px-" + hero.displayName.replace(/ /g, "_") + "_card.png";
  return `${PORTRAIT_BASE}/${encodeURIComponent(filename)}`;
}
