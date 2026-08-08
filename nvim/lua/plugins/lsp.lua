return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        pyright = {},
        ts_ls = {},
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
        "lua-language-server",
        "svelte-language-server",
        "marksman",
      })
      opts.ensure_installed = vim.tbl_filter(function(package)
        return package ~= "rust-analyzer"
      end, opts.ensure_installed)
    end,
  },

  -- LazyVim's Rust extra launches rust-analyzer through rustaceanvim.
  {
    "mrcjkb/rustaceanvim",
    opts = function(_, opts)
      opts.server = opts.server or {}
      opts.server.cmd = { vim.fn.expand("~/.local/bin/rust-analyzer") }
      return opts
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
