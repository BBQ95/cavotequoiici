/** Choisit une couleur de texte lisible (noir/blanc) sur un fond hex donné. */
export function texteSurFond(hex: string): "#ffffff" | "#1a1a1a" {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16) / 255;
  const g = parseInt(h.slice(2, 4), 16) / 255;
  const b = parseInt(h.slice(4, 6), 16) / 255;
  // luminance perçue (sRGB approx.)
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return lum > 0.55 ? "#1a1a1a" : "#ffffff";
}

export function pourcent(x: number): string {
  return `${Math.round(x * 100)} %`;
}
