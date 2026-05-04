module.exports = {
  testDir: "./tests",
  use: {
    headless: true,
  },
  projects: [
    {
      name: "chromium",
      use: {
        channel: "chromium",
      },
    },
  ],
  // Visual tests (visual.spec.js) require a running HTTP server.
  // Use: npm run test:visual   (starts python -m http.server 8770 automatically)
  // Or manually: python -m http.server 8770 &  then  npx playwright test tests/visual.spec.js
  webServer: process.env.PW_SERVER
    ? { command: "python -m http.server 8770", port: 8770, reuseExistingServer: true }
    : undefined,
};
