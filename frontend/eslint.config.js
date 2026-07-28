import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { STAGE_3_PENDING } from './eslint.theme-migration.js'

/*
 * Theme-token migration guardrails.
 * See docs/plans/2026-07-19-theme-token-migration.md — components must
 * reference colors by role, never by name, so that a theme is just a block of
 * CSS variables. Each pattern is checked against both Literal and
 * TemplateElement so `"..."` and `` `...${}` `` className forms are caught.
 */
const RETIRED_COLOR_CLASSES = [
  {
    pattern: 'text-background',
    message:
      'text-background is retired — use text-foreground (on the page) or text-card-foreground (on cards).',
  },
  {
    pattern: '\\b(bg|border|text|from|via|to|ring)-(white|black)\\b',
    message:
      'Untokenized color. Use bg-glass/N or border-glass-border/N for translucent panels, bg-overlay/N for scrims, and text-foreground / text-card-foreground for text.',
  },
  {
    pattern:
      '\\b(bg|border|text|from|via|to|ring|fill|stroke)-(red|green|yellow|amber|blue|gray|slate|zinc|neutral|stone)-\\d{2,3}\\b',
    message:
      'Stock Tailwind color. Use a status role: destructive, success, warning or info (add -strong for text on light surfaces), or muted for neutrals.',
  },
]

// Stage 3 of the migration is still in flight, so this ban is lifted for the
// files listed in STAGE_3_PENDING. Shrink that list as screens are converted;
// when it is empty, delete it and the override block at the bottom of this file.
const RAW_PALETTE_CLASSES = [
  {
    pattern: '(orange-peel|lemon-chiffon|russet|dark-cyan)|\\b-rust\\b',
    message:
      'Raw palette class. Use a role token instead: primary, secondary, accent, foreground, card, surface, muted.',
  },
]

const asSelectors = (rules) =>
  rules.flatMap(({ pattern, message }) => [
    { selector: `Literal[value=/${pattern}/]`, message },
    { selector: `TemplateElement[value.raw=/${pattern}/]`, message },
  ])

export default tseslint.config(
  { ignores: ['dist'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      // Prevent console.log usage - use logger instead
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'no-restricted-syntax': [
        'error',
        ...asSelectors([...RETIRED_COLOR_CLASSES, ...RAW_PALETTE_CLASSES]),
      ],
    },
  },
  {
    // Screens Stage 3 has not reached yet: everything above still applies
    // except the raw-palette ban.
    files: STAGE_3_PENDING,
    rules: {
      'no-restricted-syntax': ['error', ...asSelectors(RETIRED_COLOR_CLASSES)],
    },
  },
)
