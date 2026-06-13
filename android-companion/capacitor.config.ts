import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.takura.aiteamroom',
  appName: 'AI Team Room',
  webDir: '../static',
  server: {
    url: process.env.AI_TEAM_SERVER || 'http://80.78.245.66/mobile',
    cleartext: true,
  },
  android: {
    allowMixedContent: true,
  },
};

export default config;
