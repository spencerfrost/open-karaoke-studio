import { defineConfig } from 'vitepress'

export default defineConfig({
  base: '/docs/',
  title: 'Open Karaoke Studio',
  description: 'Self-hosted AI-powered karaoke application',
  lang: 'en-US',

  // Internal working docs — keep in the repo, out of the published site
  srcExclude: ['plans/**', 'superpowers/**', 'research/**'],

  themeConfig: {
    nav: [
      { text: 'Guide', link: '/guide' },
      { text: 'Features', link: '/features' },
      { text: 'Architecture', link: '/architecture' },
      { text: 'API Reference', link: '/api-reference' },
      { text: 'Roadmap', link: '/roadmap' },
    ],

    sidebar: {
      '/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Introduction', link: '/' },
            { text: 'User Guide', link: '/guide' },
            { text: 'Architecture Overview', link: '/architecture' },
          ]
        },
        {
          text: 'API Reference',
          collapsed: false,
          items: [
            { text: 'Overview', link: '/api-reference' },
            { text: 'Songs API', link: '/api/songs' },
            { text: 'Jobs API', link: '/api/jobs' },
            { text: 'Queue API', link: '/api/queue' },
            { text: 'Sessions API', link: '/api/sessions' },
            { text: 'Lyrics API', link: '/api/lyrics' },
            { text: 'Library API', link: '/api/library' },
            { text: 'YouTube & Metadata Search', link: '/api/youtube' },
            { text: 'Authentication', link: '/api/authentication' },
            { text: 'Error Handling', link: '/api/error-handling' },
            { text: 'Usage Examples', link: '/api/examples/README' },
          ]
        },
        {
          text: 'Internals',
          collapsed: false,
          items: [
            { text: 'WebSocket Protocol', link: '/websocket-protocol' },
            { text: 'Lyrics Analysis System', link: '/lyrics-analysis-system' },
            { text: 'Instrumental Intervals (Frontend)', link: '/instrumental-intervals-frontend' },
          ]
        },
        {
          text: 'Documentation',
          items: [
            { text: 'Features', link: '/features' },
            { text: 'Demo Accounts', link: '/demo-accounts' },
            { text: 'Roadmap', link: '/roadmap' },
            { text: 'Tech Debt', link: '/tech-debt' },
          ]
        },
        {
          text: 'Development',
          items: [
            { text: 'Contributing', link: '/contributing' },
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/spencerfrost/open-karaoke-studio' }
    ],

    footer: {
      message: 'Open source karaoke application',
      copyright: 'Copyright © 2024-present Spencer Frost'
    },

    search: {
      provider: 'local'
    }
  },

  markdown: {
    lineNumbers: true
  },

  vite: {
    build: {
      rollupOptions: {
        external: ['vue/server-renderer']
      }
    }
  }
})
