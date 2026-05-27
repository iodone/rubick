"""Tests for rub._install_skills module."""

from __future__ import annotations

from pathlib import Path

import pytest

from rub._install_skills import copy_skills_to_agents


@pytest.fixture()
def skills_source(tmp_path: Path) -> Path:
    """Create a fake skills source directory."""
    source = tmp_path / "skills"
    source.mkdir()
    (source / "rub").mkdir()
    (source / "rub" / "SKILL.md").write_text("# Rub")
    (source / "rub-skill-creator").mkdir()
    (source / "rub-skill-creator" / "SKILL.md").write_text("# Creator")
    (source / "__pycache__").mkdir()
    return source


class TestCopySkillsToAgents:
    """Test copy_skills_to_agents utility function."""

    def test_copy_creates_dirs_and_installs(
        self, tmp_path: Path, skills_source: Path
    ) -> None:
        agents = tmp_path / ".agents" / "skills"
        claude = tmp_path / ".claude" / "skills"

        installed = copy_skills_to_agents(skills_source, agents, claude)

        assert "rub" in installed
        assert "rub-skill-creator" in installed
        assert len(installed) == 2
        assert (agents / "rub" / "SKILL.md").exists()
        assert (claude / "rub").is_symlink()
        assert (claude / "rub").resolve() == (agents / "rub").resolve()

    def test_copy_idempotent(self, tmp_path: Path, skills_source: Path) -> None:
        agents = tmp_path / ".agents" / "skills"
        claude = tmp_path / ".claude" / "skills"

        copy_skills_to_agents(skills_source, agents, claude)
        installed = copy_skills_to_agents(skills_source, agents, claude)

        assert len(installed) == 2

    def test_copy_handles_existing_real_dir(
        self, tmp_path: Path, skills_source: Path
    ) -> None:
        """Real directories at symlink location are replaced."""
        agents = tmp_path / ".agents" / "skills"
        claude = tmp_path / ".claude" / "skills"
        claude.mkdir(parents=True)
        (claude / "rub").mkdir()

        installed = copy_skills_to_agents(skills_source, agents, claude)

        assert "rub" in installed
        assert (claude / "rub").is_symlink()

    def test_copy_skips_non_dirs(self, tmp_path: Path) -> None:
        source = tmp_path / "skills"
        source.mkdir()
        (source / "file.txt").write_text("not a dir")
        (source / "rub").mkdir()
        (source / "rub" / "SKILL.md").write_text("# Rub")

        agents = tmp_path / ".agents" / "skills"
        claude = tmp_path / ".claude" / "skills"

        installed = copy_skills_to_agents(source, agents, claude)

        assert installed == ["rub"]

    def test_copy_skips_hidden_dirs(self, tmp_path: Path) -> None:
        source = tmp_path / "skills"
        source.mkdir()
        (source / ".hidden").mkdir()
        (source / "__pycache__").mkdir()
        (source / "rub").mkdir()

        agents = tmp_path / ".agents" / "skills"
        claude = tmp_path / ".claude" / "skills"

        installed = copy_skills_to_agents(source, agents, claude)

        assert installed == ["rub"]

    def test_copy_silences_output(self, tmp_path: Path, skills_source: Path) -> None:
        """print_fn can be set to suppress output."""
        agents = tmp_path / ".agents" / "skills"
        claude = tmp_path / ".claude" / "skills"

        installed = copy_skills_to_agents(
            skills_source, agents, claude, print_fn=lambda *_: None
        )

        assert len(installed) == 2
