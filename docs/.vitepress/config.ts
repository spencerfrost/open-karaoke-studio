import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

export default withMermaid(defineConfig({
  base: '/docs/',
  title: 'Open Karaoke Studio',
  description: 'Self-hosted AI-powered karaoke application',
  lang: 'en-US',

  // Internal working docs — keep in the repo, out of the published site
  srcExclude: ['plans/**', 'superpowers/**', 'research/**'],

  // The guide links to the local dev servers
  ignoreDeadLinks: 'localhostLinks',

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
          text: 'How It Works',
          collapsed: false,
          items: [
            { text: 'Ingestion & Processing', link: '/domains/ingestion-pipeline' },
            { text: 'Song & Library Metadata', link: '/domains/song-library' },
            { text: 'Lyrics System', link: '/domains/lyrics-system' },
            { text: 'Sessions, Queue & Realtime', link: '/domains/sessions-realtime' },
            { text: 'Player, Stage & Performance', link: '/domains/player-stage' },
            { text: 'Platform Foundations', link: '/domains/platform-foundations' },
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
            { text: 'Admin API', link: '/api/admin' },
            { text: 'YouTube & Metadata Search', link: '/api/youtube' },
            { text: 'Authentication', link: '/api/authentication' },
            { text: 'Demo API', link: '/api/demo' },
            { text: 'Error Handling', link: '/api/error-handling' },
            { text: 'Usage Examples', link: '/api/examples/README' },
          ]
        },
        {
          text: 'Reference',
          collapsed: false,
          items: [
            { text: 'WebSocket Protocol', link: '/websocket-protocol' },
            { text: 'Lyrics Analysis', link: '/lyrics-analysis-system' },
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
}))
