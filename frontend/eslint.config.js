import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

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
      // text-background inverted its meaning in the theme-token migration
      // (docs/plans/2026-07-19-theme-token-migration.md); use text-foreground
      // on the page or text-card-foreground on raised surfaces instead.
      'no-restricted-syntax': [
        'error',
        {
          selector: 'Literal[value=/text-background/]',
          message:
            'text-background is retired — use text-foreground (on the page) or text-card-foreground (on cards).',
        },
        {
          selector: 'TemplateElement[value.raw=/text-background/]',
          message:
            'text-background is retired — use text-foreground (on the page) or text-card-foreground (on cards).',
        },
      ],
    },
  },
)
