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
};
