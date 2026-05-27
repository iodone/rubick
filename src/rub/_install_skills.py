"""Install Rub skills to ~/.agents/skills/

Provides:
- install_skills(): install rub's own skills
- copy_skills_to_agents(): reusable utility for copying skills with
  cross-platform symlink support
"""

import shutil
import sys
from collections.abc import Callable
from pathlib import Path


def copy_skills_to_agents(
    skills_source: Path,
    agents_dir: Path | None = None,
    claude_dir: Path | None = None,
    *,
    print_fn: Callable[..., object] = print,
) -> list[str]:
    """Copy skill directories to ~/.agents/skills/ and link to ~/.claude/skills/.

    Cross-platform: uses symlinks on Unix, copytree on Windows.

    Args:
        skills_source: directory containing skill subdirectories
        agents_dir: target for skill files (default ~/.agents/skills/)
        claude_dir: target for symlinks (default ~/.claude/skills/)
        print_fn: function for progress output (set to lambda *a: None to silence)

    Returns:
        list of installed skill names
    """
    if agents_dir is None:
        agents_dir = Path.home() / ".agents" / "skills"
    if claude_dir is None:
        claude_dir = Path.home() / ".claude" / "skills"

    agents_dir.mkdir(parents=True, exist_ok=True)
    claude_dir.mkdir(parents=True, exist_ok=True)

    installed = []
    for skill_dir in skills_source.iterdir():
        if not skill_dir.is_dir():
            continue
        if skill_dir.name.startswith(("__", ".")):
            continue

        target = agents_dir / skill_dir.name
        if target.exists():
            shutil.rmtree(target)
            print_fn(f"  Updating: {skill_dir.name}")
        else:
            print_fn(f"  Installing: {skill_dir.name}")

        shutil.copytree(skill_dir, target)
        installed.append(skill_dir.name)

    for name in installed:
        link = claude_dir / name
        target = agents_dir / name
        if sys.platform == "win32":
            if link.exists():
                shutil.rmtree(link)
            shutil.copytree(target, link)
        else:
            if link.is_symlink() or link.exists():
                if link.is_symlink() or link.is_file():
                    link.unlink()
                else:
                    shutil.rmtree(link)
            link.symlink_to(target)

    return installed


def install_skills() -> int:
    """Install rub's own skills from package to ~/.agents/skills/."""
    try:
        import rub

        package_dir = Path(rub.__file__).parent.parent
        skills_source = package_dir / "skills"

        if not skills_source.exists():
            print(f"⚠️  Skills directory not found at {skills_source}", file=sys.stderr)
            return 1

        installed = copy_skills_to_agents(skills_source)

        if installed:
            print(f"\n✨ Installed {len(installed)} rub skill(s)")
            return 0
        else:
            print("⚠️  No skills found to install", file=sys.stderr)
            return 1

    except ImportError:
        print("❌ Rub package not found. Please install rub first:", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error installing skills: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


def main() -> None:
    """CLI entry point"""
    sys.exit(install_skills())


if __name__ == "__main__":
    main()
