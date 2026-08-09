local opt = vim.opt

-- GUI-launched Neovim may not inherit .zprofile. Keep the rustup proxies and
-- repo-managed shims ahead of a standalone Homebrew Rust installation.
local local_bin = vim.fn.expand("~/.local/bin")
local path_separator = vim.fn.has("win32") == 1 and ";" or ":"
local existing_path = vim.env.PATH or ""
local path_entries = existing_path == "" and {} or vim.split(existing_path, path_separator, { plain = true })

local function prepend_path(path)
  if vim.fn.isdirectory(path) == 1 and not vim.tbl_contains(path_entries, path) then
    table.insert(path_entries, 1, path)
  end
end

local rustup_candidates = {}
if vim.env.HOMEBREW_PREFIX and vim.env.HOMEBREW_PREFIX ~= "" then
  table.insert(rustup_candidates, vim.env.HOMEBREW_PREFIX .. "/opt/rustup/bin")
end
for _, path in ipairs({
  "/opt/homebrew/opt/rustup/bin",
  "/usr/local/opt/rustup/bin",
  "/home/linuxbrew/.linuxbrew/opt/rustup/bin",
}) do
  table.insert(rustup_candidates, path)
end

for _, path in ipairs(rustup_candidates) do
  if vim.fn.isdirectory(path) == 1 then
    prepend_path(path)
    break
  end
end
prepend_path(local_bin)
vim.env.PATH = table.concat(path_entries, path_separator)

opt.relativenumber = true
opt.scrolloff = 8
opt.termguicolors = true
