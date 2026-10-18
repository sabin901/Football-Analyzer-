const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: 'tests/browser',
  timeout: 45000,
  fullyParallel: false,
  use: {
    baseURL: 'http://127.0.0.1:8770',
    viewport: { width: 1440, height: 1000 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'python -m http.server 8770 --bind 127.0.0.1 --directory site',
    url: 'http://127.0.0.1:8770',
    reuseExistingServer: false,
  },
});
