return {
  {
    "folke/snacks.nvim",
    opts = {
      dashboard = {
        preset = {
          header = table.concat({
            "",
            "   ░▒▓  plastic beach  ▓▒░",
            "",
            "   ── nvim ──",
            "",
          }, "\n"),
        },
      },
    },
    init = function()
      vim.api.nvim_set_hl(0, "SnacksDashboardHeader", { fg = "#40bfb0" })
    end,
  },
}
