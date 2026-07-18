"""``python -m aviary_kernel.install`` writes the kernelspec into Jupyter's
kernel directory, so the kernel shows up as "Aviary (Combinator Calculus)"
in Jupyter frontends (SPEC.md §2)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from jupyter_client.kernelspec import KernelSpecManager

KERNEL_NAME = "aviary"
SPEC_DIR = Path(__file__).parent / "kernelspec"


def install(user: bool = False, prefix: str | None = None) -> str:
    ksm = KernelSpecManager()
    with open(SPEC_DIR / "kernel.json") as f:
        spec = json.load(f)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp_spec_dir = Path(td) / KERNEL_NAME
        tmp_spec_dir.mkdir()
        with open(tmp_spec_dir / "kernel.json", "w") as f:
            json.dump(spec, f, indent=2)
        dest = ksm.install_kernel_spec(
            str(tmp_spec_dir), kernel_name=KERNEL_NAME, user=user, prefix=prefix,
        )
    return dest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Install the Aviary Jupyter kernelspec")
    parser.add_argument("--user", action="store_true", help="install to the per-user kernel directory")
    parser.add_argument("--prefix", default=None, help="install under this prefix instead")
    args = parser.parse_args(argv)
    dest = install(user=args.user, prefix=args.prefix)
    print(f"Installed Aviary kernelspec in {dest}")


if __name__ == "__main__":
    main()
