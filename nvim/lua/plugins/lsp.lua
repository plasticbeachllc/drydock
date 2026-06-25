return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        pyright = {},
        ts_ls = {},
        rust_analyzer = {},
        lua_ls = {},
        svelte = {},
        marksman = {},
      },
    },
  },

  -- Ensure language servers are installed
  {
    "mason-org/mason.nvim",
    opts = function(_, opts)
      opts.ensure_installed = vim.list_extend(opts.ensure_installed or {}, {
        "pyright",
        "typescript-language-server",
        "rust-analyzer",
        "lua-language-server",
        "svelte-language-server",
        "marksman",
      })
    end,
  },

  -- Treesitter parsers
  {
    "nvim-treesitter/nvim-treesitter",
    opts = {
      ensure_installed = {
        "python",
        "typescript",
        "tsx",
        "javascript",
        "rust",
        "lua",
        "svelte",
        "markdown",
        "markdown_inline",
        "html",
        "css",
        "json",
        "toml",
        "yaml",
        "bash",
      },
    },
  },
}
