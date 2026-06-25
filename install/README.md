# Arch Install

This directory contains the standard-ISO installer path for Arch Linux.

## Current Supported Mode

`arch-live.sh` currently supports two Windows dual-boot modes where Linux should
be removable later:

- `dual-boot-use-partition`: install into an existing Linux root partition.
- `dual-boot-create-partition`: create one Linux root partition in already-shrunk
  free space, then install into it.

The mode is deliberately conservative:

- It does not repartition disks.
- It does not format the EFI System Partition.
- It formats exactly one Linux root partition.
- In create-partition mode, it creates only one new partition in the selected
  free-space range.
- It keeps `/home` inside the Linux root partition.
- It uses zram instead of a swap partition.
- It writes a restore note to the installed user's home directory.
- It installs a GNOME/GDM graphical baseline for first boot.

## From The Arch ISO

Boot the standard Arch ISO, connect to the network, then run:

```bash
curl -fsSL https://raw.githubusercontent.com/plasticbeachllc/drydock/main/install/arch-live.sh | bash
```

That defaults to `dual-boot-use-partition`. The installer will show `lsblk -pf`,
ask for the Linux root partition and existing EFI partition, and require a typed
confirmation before formatting root.

To inspect the plan without formatting or mounting anything:

```bash
curl -fsSL https://raw.githubusercontent.com/plasticbeachllc/drydock/main/install/arch-live.sh | bash -s -- --dry-run
```

To create the Linux root partition from already-shrunk free space:

```bash
curl -fsSL https://raw.githubusercontent.com/plasticbeachllc/drydock/main/install/arch-live.sh | bash -s -- dual-boot-create-partition --dry-run
```

The installer prints `parted ... print free`, then asks for the free-space start
and end exactly as shown. For the Linux root size, press Enter for `max` to use
the selected free-space range with a small safety margin before the displayed end
boundary, or type a smaller end position such as `450GiB`.
After checking the plan, rerun without `--dry-run`.

## First Boot

After rebooting into the installed system:

```bash
cd ~/worktable/drydock
./bootstrap.sh
```

That installed-system bootstrap handles packages, AUR tools, dotfiles, generated
themes, Claude, Codex, and user-level app configuration.

## Path To Custom ISO

The custom-ISO path should reuse this same installer. A future ISO only needs to
pre-bundle the repo and expose a small command such as `drydock-install` that
runs `install/arch-live.sh`.
