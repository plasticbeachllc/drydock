import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARCH_LIVE_PATH = REPO_ROOT / "install" / "arch-live.sh"
ARCH_README_PATH = REPO_ROOT / "install" / "README.md"


class ArchInstallScriptTests(unittest.TestCase):
    def test_arch_live_script_exists(self):
        self.assertTrue(ARCH_LIVE_PATH.exists())

    def test_arch_live_script_documents_reversible_mode(self):
        content = ARCH_LIVE_PATH.read_text()
        self.assertIn("dual-boot-use-partition", content)
        self.assertIn("dual-boot-create-partition", content)
        self.assertIn("never formats the EFI partition", content)
        self.assertIn("FORMAT $root_part", content)

    def test_arch_live_script_supports_dry_run(self):
        content = ARCH_LIVE_PATH.read_text()
        self.assertIn("--dry-run", content)
        self.assertIn("Dry run complete", content)
        self.assertIn("No filesystems were formatted", content)

    def test_arch_live_script_reads_prompts_from_tty(self):
        content = ARCH_LIVE_PATH.read_text()
        self.assertIn('TTY_PATH="/dev/tty"', content)
        self.assertIn('<"$TTY_PATH"', content)

    def test_arch_live_script_prints_full_device_paths(self):
        content = ARCH_LIVE_PATH.read_text()
        self.assertIn("show_block_devices", content)
        self.assertIn("NAME,SIZE,FSTYPE,FSVER,LABEL,PARTLABEL", content)
        self.assertIn("lsblk -p", content)
        self.assertNotIn("lsblk -f", content)

    def test_arch_live_script_reprints_devices_before_efi_prompt(self):
        content = ARCH_LIVE_PATH.read_text()
        self.assertIn("Current block devices:", content)
        self.assertLess(
            content.index("Current block devices:"),
            content.index("Existing EFI System Partition"),
        )

    def test_arch_live_script_guards_x86_64_and_chroot_dns(self):
        content = ARCH_LIVE_PATH.read_text()
        self.assertIn('uname -m', content)
        self.assertIn("x86_64", content)
        self.assertIn('cp -L /etc/resolv.conf "$TARGET_MOUNT/etc/resolv.conf"', content)

    def test_arch_live_script_create_partition_guardrails(self):
        content = ARCH_LIVE_PATH.read_text()
        self.assertIn("parted", content)
        self.assertIn("mkpart ArchLinux", content)
        self.assertIn("CREATE-LINUX-PARTITION", content)
        self.assertIn("Linux root end [max", content)
        self.assertIn("normalize_gib_position", content)
        self.assertIn("max_partition_end_inside_free_space", content)
        self.assertIn("v - 0.1", content)
        self.assertIn("invalid disk position", content)
        self.assertIn("No existing partitions will be resized, moved, or formatted.", content)

    def test_arch_live_script_uses_zram_not_swap_partition(self):
        content = ARCH_LIVE_PATH.read_text()
        self.assertIn("zram-generator", content)
        self.assertIn("zram-size", content)
        self.assertNotIn("mkswap", content)
        self.assertNotIn("swapon", content)

    def test_arch_live_script_installs_graphical_baseline(self):
        content = ARCH_LIVE_PATH.read_text()
        self.assertIn("gdm", content)
        self.assertIn("gnome-shell", content)
        self.assertIn("gdm.service", content)

    def test_arch_live_script_enables_windows_detection(self):
        content = ARCH_LIVE_PATH.read_text()
        self.assertIn("os-prober", content)
        self.assertIn("GRUB_DISABLE_OS_PROBER=false", content)

    def test_arch_install_readme_mentions_standard_iso(self):
        content = ARCH_README_PATH.read_text()
        self.assertIn("standard Arch ISO", content)
        self.assertIn("raw.githubusercontent.com", content)
        self.assertIn("dual-boot-create-partition", content)
        self.assertIn("Path To Custom ISO", content)


if __name__ == "__main__":
    unittest.main()
