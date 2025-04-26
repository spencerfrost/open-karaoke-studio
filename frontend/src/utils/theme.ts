// Vintage enamel sign palette
export const vintageColors = {
  russet: "#774320", // Deep brown
  rust: "#B44819", // Reddish-brown/orange
  lemonChiffon: "#F5F3C7", // Creamy off-white
  orangePeel: "#FD9A02", // Vibrant orange
  darkCyan: "#01928B", // Teal/turquoise
};

export const vintageTheme = {
  colors: vintageColors,

  // Background with vintage gradient
  background: `linear-gradient(135deg, ${vintageColors.russet} 0%, ${vintageColors.rust} 100%)`,

  // Generate a texture overlay CSS
  getTextureOverlay: () => ({
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='4' height='4' viewBox='0 0 4 4'%3E%3Cpath fill='%23ffffff' fill-opacity='0.05' d='M1 3h1v1H1V3zm2-2h1v1H3V1z'%3E%3C/path%3E%3C/svg%3E")`,
    backgroundRepeat: "repeat" as const,
    position: "absolute" as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 10,
    pointerEvents: "none" as const,
  }),

  // Generate a sunburst pattern CSS
  getSunburstPattern: () => ({
    background: `
      radial-gradient(circle at center, transparent 0, transparent 40%, rgba(0,0,0,0.2) 41%, transparent 42%),
      repeating-conic-gradient(
        ${vintageColors.rust}80 0deg, 
        ${vintageColors.rust}80 6deg, 
        ${vintageColors.russet}80 6deg,
        ${vintageColors.russet}80 12deg
      )
    `,
    backgroundSize: "100% 100%, 100% 100%" as const,
    position: "absolute" as const,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    opacity: 0.2,
    zIndex: 5,
    pointerEvents: "none" as const,
  }),
};

// For future theme expansion
export const themes = {
  vintage: vintageTheme,
  // Add more themes here
};

export default vintageTheme;
