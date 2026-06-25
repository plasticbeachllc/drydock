#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${DRYDOCK_REPO_URL:-https://github.com/plasticbeachllc/drydock.git}"
TARGET_MOUNT="${DRYDOCK_TARGET_MOUNT:-/mnt}"
DEFAULT_TIMEZONE="${DRYDOCK_TIMEZONE:-America/New_York}"
DRY_RUN=0
TTY_PATH="/dev/tty"
MODE="dual-boot-use-partition"

banner() {
    echo ""
    echo "==> $1"
    echo ""
}

die() {
    echo "error: $*" >&2
    exit 1
}

need_root() {
    if [[ "$EUID" -ne 0 ]]; then
        die "run this from the Arch live ISO as root"
    fi
    [[ -r "$TTY_PATH" && -w "$TTY_PATH" ]] || die "$TTY_PATH is required for interactive prompts"
    [[ "$(uname -m)" == "x86_64" ]] || die "this installer currently supports x86_64 UEFI laptops only"
}

read_required() {
    local prompt="$1"
    local value
    while true; do
        read -r -p "$prompt" value <"$TTY_PATH"
        if [[ -n "$value" ]]; then
            printf '%s\n' "$value"
            return 0
        fi
    done
}

read_optional() {
    local prompt="$1"
    local default="$2"
    local value
    read -r -p "$prompt" value <"$TTY_PATH"
    printf '%s\n' "${value:-$default}"
}

read_secret_twice() {
    local prompt="$1"
    local first
    local second
    while true; do
        read -r -s -p "$prompt" first <"$TTY_PATH"
        echo "" >"$TTY_PATH"
        read -r -s -p "confirm $prompt" second <"$TTY_PATH"
        echo "" >"$TTY_PATH"
        if [[ -n "$first" && "$first" == "$second" ]]; then
            printf '%s\n' "$first"
            return 0
        fi
        echo "Passwords did not match."
    done
}

confirm_exact() {
    local prompt="$1"
    local expected="$2"
    local actual
    read -r -p "$prompt" actual <"$TTY_PATH"
    [[ "$actual" == "$expected" ]] || die "confirmation did not match"
}

require_block_device() {
    local path="$1"
    [[ -b "$path" ]] || die "$path is not a block device"
}

require_disk_device() {
    local path="$1"
    require_block_device "$path"
    [[ "$(lsblk -no TYPE "$path" | head -n 1)" == "disk" ]] || die "$path is not a whole-disk device"
}

require_command() {
    local cmd="$1"
    command -v "$cmd" >/dev/null 2>&1 || die "$cmd is required"
}

require_efi_partition() {
    local path="$1"
    local fstype
    fstype="$(lsblk -no FSTYPE "$path" | head -n 1)"
    [[ "$fstype" == "vfat" || "$fstype" == "fat32" || "$fstype" == "fat" ]] || \
        die "$path does not look like an EFI System Partition (expected vfat/FAT, got ${fstype:-unknown})"
}

normalize_gib_position() {
    local value="$1"

    if [[ "$value" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
        printf '%sGiB\n' "$value"
    elif [[ "$value" =~ ^[0-9]+([.][0-9]+)?(MiB|GiB|TiB|MB|GB|TB)$ ]]; then
        printf '%s\n' "$value"
    else
        die "invalid disk position '$value' (use a number like 355, or include units like 355GiB)"
    fi
}

detect_ucode_package() {
    if grep -qi genuineintel /proc/cpuinfo; then
        echo "intel-ucode"
    elif grep -qi authenticamd /proc/cpuinfo; then
        echo "amd-ucode"
    fi
}

detect_profile() {
    local vendor=""
    local product=""
    vendor="$(cat /sys/class/dmi/id/sys_vendor 2>/dev/null || true)"
    product="$(cat /sys/class/dmi/id/product_name 2>/dev/null || true)"

    case "${vendor} ${product}" in
        *Framework*"Laptop 13"*|*Framework*"13"*)
            echo "framework-13"
            ;;
        *LENOVO*"ThinkPad X1 Carbon"*|*Lenovo*"ThinkPad X1 Carbon"*)
            echo "x1-carbon"
            ;;
        *)
            echo "generic-laptop"
            ;;
    esac
}

write_zram_config() {
    mkdir -p "$TARGET_MOUNT/etc/systemd/zram-generator.conf.d"
    cat >"$TARGET_MOUNT/etc/systemd/zram-generator.conf.d/drydock.conf" <<'EOF'
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
EOF
}

write_cleanup_note() {
    local username="$1"
    local root_part="$2"
    local efi_part="$3"
    local note_dir="$TARGET_MOUNT/home/$username"

    mkdir -p "$note_dir"
    cat >"$note_dir/DRYDOCK_WINDOWS_RESTORE.md" <<EOF
# Drydock Windows Restore Notes

This Arch install was created in reversible dual-boot mode.

Partitions touched:

- Linux root partition formatted by installer: $root_part
- Existing EFI partition reused without formatting: $efi_part

To remove Linux later:

1. Boot Windows.
2. Open Disk Management.
3. Delete the Linux root partition listed above.
4. Extend the Windows partition into the free space if desired.
5. Remove the "Arch" UEFI boot entry from firmware settings or with a Windows EFI tool.
6. Optionally remove the Linux bootloader directory from the EFI System Partition.

Windows data partitions were not intentionally formatted or repartitioned by this installer.
EOF
    arch-chroot "$TARGET_MOUNT" chown "$username:$username" "/home/$username/DRYDOCK_WINDOWS_RESTORE.md"
}

write_first_boot_note() {
    local username="$1"
    local note_dir="$TARGET_MOUNT/home/$username"

    mkdir -p "$note_dir"
    cat >"$note_dir/DRYDOCK_FIRST_BOOT.md" <<'EOF'
# Drydock First Boot

After rebooting into Arch, connect to the network and run:

```bash
cd ~/worktable/drydock
./bootstrap.sh
```

The bootstrap installs user tools, applies dotfiles, configures themes, and runs the
Claude/Codex native installers.
EOF
    arch-chroot "$TARGET_MOUNT" chown "$username:$username" "/home/$username/DRYDOCK_FIRST_BOOT.md"
}

collect_common_inputs() {
    echo ""
    echo "Current block devices:"
    lsblk -pf
    echo ""
    efi_part="$(read_required "Existing EFI System Partition to reuse, not format (example /dev/nvme0n1p1): ")"
    fs_type="$(read_optional "Root filesystem [ext4/btrfs] (default ext4): " "ext4")"
    hostname="$(read_required "Hostname: ")"
    username="$(read_required "Username: ")"
    timezone="$(read_optional "Timezone (default $DEFAULT_TIMEZONE): " "$DEFAULT_TIMEZONE")"
    if [[ "$DRY_RUN" == "1" ]]; then
        user_password=""
    else
        user_password="$(read_secret_twice "password for $username: ")"
    fi
    profile="$(detect_profile)"

    require_block_device "$efi_part"
    require_efi_partition "$efi_part"
    [[ "$fs_type" == "ext4" || "$fs_type" == "btrfs" ]] || die "filesystem must be ext4 or btrfs"
    [[ "$username" =~ ^[a-z_][a-z0-9_-]*$ ]] || die "username must be a valid lowercase Linux account name"
}

validate_root_partition() {
    require_block_device "$root_part"
    [[ "$root_part" != "$efi_part" ]] || die "root and EFI partitions must be different"
}

print_install_plan() {
    banner "Install plan"
    echo "Mode: $MODE"
    echo "Hardware profile: $profile"
    if [[ -n "${create_disk:-}" ]]; then
        echo "Disk to modify:           $create_disk"
        echo "Free-space start:         $create_start"
        echo "Free-space end:           $create_free_end"
        echo "Linux partition end:      $create_end"
        echo "Partition command:        parted --script $create_disk mkpart 'Arch Linux' $fs_type $create_start $create_end"
        echo "Root partition:           detected after creation"
    else
        echo "Root partition to FORMAT: $root_part"
    fi
    echo "EFI partition to reuse:   $efi_part"
    echo "Filesystem:               $fs_type"
    echo "Hostname:                 $hostname"
    echo "Username:                 $username"
    echo "Timezone:                 $timezone"
    echo ""
    if [[ -n "${create_disk:-}" ]]; then
        echo "No existing partitions will be resized, moved, or formatted."
        echo "A single Linux partition will be created inside the selected free-space range."
    else
        echo "No disk partition table will be changed."
    fi
    echo "The EFI partition will be mounted but not formatted."
    if [[ "$DRY_RUN" == "1" ]]; then
        echo "Dry run: yes"
    fi
    echo ""
}

maybe_exit_after_dry_run() {
    if [[ "$DRY_RUN" == "1" ]]; then
        banner "Dry run complete"
        echo "No filesystems were formatted, no partitions were mounted, and no packages were installed."
        echo "Re-run without --dry-run when the plan is correct."
        return 0
    fi
    return 1
}

create_root_partition() {
    local before
    local after

    before="$(lsblk -nrpo NAME "$create_disk" | sort)"
    confirm_exact "Type CREATE-LINUX-PARTITION $create_disk to continue: " "CREATE-LINUX-PARTITION $create_disk"

    banner "Create Linux root partition"
    parted --script "$create_disk" mkpart "Arch Linux" "$fs_type" "$create_start" "$create_end"
    partprobe "$create_disk"
    udevadm settle

    after="$(lsblk -nrpo NAME "$create_disk" | sort)"
    root_part="$(comm -13 <(printf '%s\n' "$before") <(printf '%s\n' "$after") | tail -n 1)"
    [[ -n "$root_part" ]] || die "could not detect newly-created Linux root partition"
    validate_root_partition
    echo "Created Linux root partition: $root_part"
}

install_to_root_partition() {
    confirm_exact "Type FORMAT $root_part to continue: " "FORMAT $root_part"

    banner "Prepare target"
    umount -R "$TARGET_MOUNT" 2>/dev/null || true
    if [[ "$fs_type" == "ext4" ]]; then
        mkfs.ext4 -F "$root_part"
    else
        mkfs.btrfs -f "$root_part"
    fi
    mount "$root_part" "$TARGET_MOUNT"
    mkdir -p "$TARGET_MOUNT/efi"
    mount "$efi_part" "$TARGET_MOUNT/efi"
    mkdir -p "$TARGET_MOUNT/etc"
    cp -L /etc/resolv.conf "$TARGET_MOUNT/etc/resolv.conf"

    banner "Install base system"
    pacman -Sy --needed --noconfirm arch-install-scripts git curl
    local ucode
    ucode="$(detect_ucode_package)"
    local packages=(
        base
        linux
        linux-firmware
        sof-firmware
        grub
        efibootmgr
        os-prober
        networkmanager
        sudo
        zsh
        git
        curl
        jq
        vim
        zram-generator
        fwupd
        tuned
        bluez
        bluez-utils
        pipewire
        pipewire-pulse
        wireplumber
        fprintd
        mesa
        vulkan-intel
        vulkan-radeon
        intel-media-driver
        libva-mesa-driver
        gdm
        gnome-shell
        gnome-control-center
        gnome-terminal
        nautilus
        xdg-desktop-portal-gnome
        gnome-keyring
        gvfs
    )
    [[ -n "$ucode" ]] && packages+=("$ucode")
    [[ "$fs_type" == "btrfs" ]] && packages+=(btrfs-progs)
    pacstrap -K "$TARGET_MOUNT" "${packages[@]}"

    genfstab -U "$TARGET_MOUNT" >>"$TARGET_MOUNT/etc/fstab"
    write_zram_config

    banner "Configure installed system"
    arch-chroot "$TARGET_MOUNT" ln -sf "/usr/share/zoneinfo/$timezone" /etc/localtime
    arch-chroot "$TARGET_MOUNT" hwclock --systohc
    sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' "$TARGET_MOUNT/etc/locale.gen"
    arch-chroot "$TARGET_MOUNT" locale-gen
    echo "LANG=en_US.UTF-8" >"$TARGET_MOUNT/etc/locale.conf"
    echo "$hostname" >"$TARGET_MOUNT/etc/hostname"

    arch-chroot "$TARGET_MOUNT" useradd -m -G wheel -s /bin/zsh "$username"
    printf '%s:%s\n' "$username" "$user_password" | arch-chroot "$TARGET_MOUNT" chpasswd
    sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' "$TARGET_MOUNT/etc/sudoers"

    arch-chroot "$TARGET_MOUNT" systemctl enable NetworkManager.service bluetooth.service tuned.service gdm.service

    banner "Install bootloader"
    sed -i 's/^#*GRUB_DISABLE_OS_PROBER=.*/GRUB_DISABLE_OS_PROBER=false/' "$TARGET_MOUNT/etc/default/grub"
    if ! grep -q '^GRUB_DISABLE_OS_PROBER=' "$TARGET_MOUNT/etc/default/grub"; then
        echo "GRUB_DISABLE_OS_PROBER=false" >>"$TARGET_MOUNT/etc/default/grub"
    fi
    arch-chroot "$TARGET_MOUNT" grub-install --target=x86_64-efi --efi-directory=/efi --bootloader-id=Arch
    arch-chroot "$TARGET_MOUNT" grub-mkconfig -o /boot/grub/grub.cfg

    banner "Clone drydock"
    arch-chroot "$TARGET_MOUNT" sudo -iu "$username" mkdir -p "/home/$username/worktable"
    arch-chroot "$TARGET_MOUNT" sudo -iu "$username" git clone "$REPO_URL" "/home/$username/worktable/drydock"

    write_cleanup_note "$username" "$root_part" "$efi_part"
    write_first_boot_note "$username"

    banner "Done"
    echo "Reboot into Arch, sign in as $username, then run:"
    echo ""
    echo "  cd ~/worktable/drydock"
    echo "  ./bootstrap.sh"
    echo ""
    echo "A Windows restore note was written to /home/$username/DRYDOCK_WINDOWS_RESTORE.md."
}

install_dual_boot_use_partition() {
    need_root

    banner "Drydock Arch dual-boot installer"
    echo "This mode never repartitions a disk and never formats the EFI partition."
    echo "It formats exactly one selected Linux root partition."
    echo ""
    lsblk -pf
    echo ""

    root_part="$(read_required "Linux root partition to format (example /dev/nvme0n1p6): ")"
    collect_common_inputs
    validate_root_partition
    print_install_plan
    maybe_exit_after_dry_run && return 0
    install_to_root_partition
}

install_dual_boot_create_partition() {
    need_root
    require_command parted
    require_command partprobe
    require_command udevadm

    banner "Drydock Arch dual-boot partition creator"
    echo "This mode creates one Linux root partition in already-shrunk free space."
    echo "It does not shrink Windows, move partitions, format EFI, or repartition the whole disk."
    echo ""
    lsblk -pf
    echo ""

    create_disk="$(read_required "Whole disk containing the Windows install (example /dev/nvme0n1): ")"
    require_disk_device "$create_disk"

    banner "Free space on $create_disk"
    parted "$create_disk" unit GiB print free
    echo ""
    echo "Use the free-space range created by shrinking Windows."
    create_start="$(normalize_gib_position "$(read_required "Free-space start exactly as shown (example 350GiB): ")")"
    create_free_end="$(normalize_gib_position "$(read_required "Free-space end exactly as shown (example 475GiB): ")")"
    local requested_end
    requested_end="$(read_optional "Linux root end [max, or an end position like 450GiB] (default max): " "max")"
    if [[ "$requested_end" == "max" ]]; then
        create_end="$create_free_end"
    else
        create_end="$(normalize_gib_position "$requested_end")"
    fi

    collect_common_inputs
    root_part=""
    print_install_plan
    maybe_exit_after_dry_run && return 0
    create_root_partition
    install_to_root_partition
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            ;;
        --help|-h)
            cat <<'EOF'
Usage: arch-live.sh [dual-boot-use-partition|dual-boot-create-partition] [--dry-run]

Modes:
  dual-boot-use-partition     Install Arch into an existing selected Linux root
                              partition, reusing EFI without formatting it.
  dual-boot-create-partition  Create one Linux root partition in already-shrunk
                              free space, then install Arch into it.

Options:
  --dry-run             Gather inputs, validate partitions, print the install
                        plan, and exit before formatting or mounting anything.
EOF
            exit 0
            ;;
        dual-boot-use-partition|dual-boot-create-partition)
            MODE="$1"
            ;;
        *)
            die "unknown argument: $1"
            ;;
    esac
    shift
done

case "$MODE" in
    dual-boot-use-partition)
        install_dual_boot_use_partition
        ;;
    dual-boot-create-partition)
        install_dual_boot_create_partition
        ;;
    *)
        die "unknown mode: $MODE"
        ;;
esac
