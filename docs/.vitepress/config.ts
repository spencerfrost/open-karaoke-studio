import { defineConfig } from 'vitepress'

export default defineConfig({
  base: '/docs/',
  title: 'Open Karaoke Studio',
  description: 'Self-hosted AI-powered karaoke application',
  lang: 'en-US',
  
  themeConfig: {
    logo: '/logo.svg',
    
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
            { text: 'Metadata API', link: '/api/metadata' },
            { text: 'Authentication', link: '/api/authentication' },
            { text: 'Error Handling', link: '/api/error-handling' },
          ]
        },
        {
          text: 'Documentation',
          items: [
            { text: 'Features', link: '/features' },
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

  ignoreDeadLinks: true,

  vite: {
    build: {
      rollupOptions: {
        external: ['vue/server-renderer']
      }
    }
  }
})
