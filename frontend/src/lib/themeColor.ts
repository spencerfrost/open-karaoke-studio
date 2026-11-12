export type RGB = [r: number, g: number, b: number];

/**
 * Resolves a theme role token (e.g. "primary") to the sRGB color the current
 * theme gives it, for code that paints outside CSS — canvas drawing, color math.
 *
 * A probe element resolves the `var()`. A plain color computes to rgb(), read
 * as-is. A color-mix() token computes to oklab() or color(srgb …) instead, so
 * it's painted onto a 1×1 canvas and read back as sRGB bytes — not used for
 * every color because the readback can round a channel off by one.
 */
export function resolveThemeColor(token: string): RGB {
  const probe = document.createElement("span");
  probe.style.color = `var(--${token})`;
  probe.style.display = "none";
  document.body.appendChild(probe);
  const computed = getComputedStyle(probe).color;
  probe.remove();

  const rgb = computed.match(/^rgba?\((\d+), (\d+), (\d+)/);
  if (rgb) return [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])];

  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 1;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return [0, 0, 0];
  ctx.fillStyle = computed;
  ctx.fillRect(0, 0, 1, 1);
  const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data;
  return [r, g, b];
}
