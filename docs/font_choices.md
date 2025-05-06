# Font Choices for Open Karaoke Studio

## Overview

Open Karaoke Studio aims for a "modern retro" aesthetic—blending nostalgic, throwback vibes with clean, contemporary design. The right font pairing helps evoke the feel of classic karaoke bars, vintage music tech, and 80s/90s pop culture, while ensuring readability and a modern user experience.

This document summarizes recommended font pairings, rationale, and integration steps. Use it as a reference for updating or switching fonts in the future.

---

## Recommended Font Pairings (Modern Retro)

### 1. Syne (Headings) + Manrope (Body)

- **Syne:** Bold, geometric, retro-futuristic. Great for impactful headings and branding.
- **Manrope:** Clean, modern sans-serif. Excellent readability for body text.
- **Vibe:** Playful, energetic, and distinctly modern-retro.

### 2. Space Grotesk (Headings) + DM Sans (Body)

- **Space Grotesk:** Geometric, slightly quirky sans-serif with a techy, retro feel.
- **DM Sans:** Simple, highly readable sans-serif for body content.
- **Vibe:** Tech-inspired, approachable, and fresh.

### 3. Bungee (Headings) + Plus Jakarta Sans (Body)

- **Bungee:** Display font inspired by signage and arcade lettering. Very nostalgic.
- **Plus Jakarta Sans:** Modern, versatile sans-serif for body.
- **Vibe:** Fun, bold, and reminiscent of classic karaoke/arcade signage.

---

## Why Not Use Inter, Roboto, or Open Sans?

These fonts are excellent for general web apps but are widely used and can feel generic. The above pairings offer a more distinctive, memorable look while maintaining usability.

---

## Integration Steps

### 1. Import Fonts via Google Fonts

Add the following `<link>` tags to your `frontend/index.html` `<head>` section. Example for Syne + Manrope:

```html
<link
  href="https://fonts.googleapis.com/css2?family=Syne:wght@700&family=Manrope:wght@400;600&display=swap"
  rel="stylesheet"
/>
```

Replace with the appropriate Google Fonts URLs for other pairings as needed.

### 2. Update Tailwind CSS Configuration

Edit `frontend/tailwind.config.js` (or `tailwind.config.ts`) to set the font families:

```js
module.exports = {
  theme: {
    extend: {
      fontFamily: {
        heading: ["Syne", "sans-serif"],
        body: ["Manrope", "sans-serif"],
      },
    },
  },
  // ...existing config...
};
```

### 3. Use Font Classes in React Components

Apply the font classes in your components:

```tsx
<h1 className="font-heading text-4xl">Welcome to Open Karaoke Studio</h1>
<p className="font-body">Create karaoke tracks with ease!</p>
```

You can also set defaults in your main layout or App component for consistent usage.

---

## Switching Fonts

To switch fonts in the future:

1. Update the Google Fonts `<link>` in `index.html`.
2. Change the `fontFamily` values in Tailwind config.
3. (Optional) Adjust font weights or classes in your components for best appearance.

---

## References

- [Google Fonts](https://fonts.google.com/)
- [Tailwind CSS Font Family Docs](https://tailwindcss.com/docs/font-family)

---

**Last updated:** May 2025
