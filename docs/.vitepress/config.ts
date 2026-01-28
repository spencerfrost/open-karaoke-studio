import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Open Karaoke Studio',
  description: 'Self-hosted AI-powered karaoke application',
  lang: 'en-US',
  
  themeConfig: {
    logo: '/logo.svg',
    
    nav: [
      { text: 'Guide', link: '/guide' },
      { text: 'Features', link: '/FEATURES' },
      { text: 'Architecture', link: '/ARCHITECTURE' },
      { text: 'API Reference', link: '/api-reference' },
      { text: 'Roadmap', link: '/ROADMAP' },
    ],

    sidebar: {
      '/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Introduction', link: '/' },
            { text: 'User Guide', link: '/guide' },
            { text: 'Architecture Overview', link: '/ARCHITECTURE' },
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
            { text: 'Metadata API', link: '/api/metadata' },
            { text: 'Authentication', link: '/api/authentication' },
            { text: 'Error Handling', link: '/api/error-handling' },
          ]
        },
        {
          text: 'Documentation',
          items: [
            { text: 'Features', link: '/FEATURES' },
            { text: 'Roadmap', link: '/ROADMAP' },
            { text: 'Tech Debt', link: '/TECH-DEBT' },
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

  ignoreDeadLinks: true,

  vite: {
    build: {
      rollupOptions: {
        external: ['vue/server-renderer']
      }
    }
  }
})
