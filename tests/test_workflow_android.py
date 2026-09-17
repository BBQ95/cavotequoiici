"""Tests de non-régression pour les workflows GitHub Actions.

Contexte : le build Android (run 35236499277) a échoué sur un échec réseau
intermittent du téléchargement de la distribution Gradle
(``Connection reset by peer`` vers ``services.gradle.org``), sans régression
de code — les runs précédents et la PR avaient réussi. Le workflow
``android-test.yml`` ne reprenait pas ce téléchargement : un seul reset TCP
faisait échouer tout le build.

Ce test garantit que le workflow contient une étape de pré-téléchargement
Gradle avec retry avant ``./gradlew assembleRelease``, sur le même modèle
anti-flaky que l'étape « Pré-installer CMake 3.22.1 » déjà présente.
"""

import os
from pathlib import Path
import subprocess

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "android-test.yml"


def _load_workflow() -> dict:
    assert WORKFLOW.exists(), f"Workflow introuvable : {WORKFLOW}"
    with WORKFLOW.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _step_names() -> list[str]:
    doc = _load_workflow()
    steps = doc["jobs"]["build"]["steps"]
    return [s.get("name", s.get("uses", "?")) for s in steps]


def _gradle_step() -> dict:
    steps = _load_workflow()["jobs"]["build"]["steps"]
    candidates = [step for step in steps if "./gradlew --version" in step.get("run", "")]
    assert len(candidates) == 1, "Une seule étape de pré-téléchargement Gradle attendue"
    return candidates[0]


def test_workflow_inclut_prechargement_gradle_avant_build() -> None:
    steps = _load_workflow()["jobs"]["build"]["steps"]
    preload = _gradle_step()
    build = next(step for step in steps if "./gradlew assembleRelease" in step.get("run", ""))
    prebuild = next(step for step in steps if "expo prebuild" in step.get("run", ""))
    assert steps.index(prebuild) < steps.index(preload) < steps.index(build)
    assert preload["working-directory"] == build["working-directory"] == "mobile/android"


@pytest.mark.parametrize("success_on", [1, 3, 5, None])
def test_gradle_retry_execute_script_et_conserve_logs(tmp_path: Path, success_on: int | None) -> None:
    """Exécute le vrai script sous bash -e/pipefail, sans réseau ni attente."""
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    sleep = bin_dir / "sleep"
    sleep.write_text("#!/bin/bash\nprintf '%s\\n' \"$*\" >> \"$HOME/sleeps\"\n", encoding="utf-8")
    sleep.chmod(0o755)
    wrapper = tmp_path / "gradlew"
    wrapper.write_text(
        "#!/bin/bash\n"
        "set -eu\n"
        "test \"$#\" -eq 1 && test \"$1\" = --version\n"
        "count=0\n"
        "if [ -f \"$HOME/calls\" ]; then read -r count < \"$HOME/calls\"; fi\n"
        "count=$((count + 1))\n"
        "printf '%s\\n' \"$count\" > \"$HOME/calls\"\n"
        "echo \"wrapper stdout $count\"\n"
        "echo \"wrapper stderr $count\" >&2\n"
        "test \"$count\" -ge \"$SUCCESS_ON\"\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", _gradle_step()["run"]],
        cwd=tmp_path,
        env={
            **os.environ,
            "HOME": str(home),
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "SUCCESS_ON": str(success_on or 99),
        },
        text=True,
        capture_output=True,
        timeout=10,
    )
    attempts = success_on or 5
    # Les diagnostics de chaque tentative doivent rester disponibles, même
    # lorsqu'une tentative ultérieure réussit (le reset réseau est sur stderr).
    logs = result.stdout + result.stderr
    for attempt in range(1, attempts + 1):
        assert f"wrapper stdout {attempt}" in logs, logs
        assert f"wrapper stderr {attempt}" in logs, logs
    assert int((home / "calls").read_text()) == attempts
    assert (result.returncode == 0) == (success_on is not None), logs
    sleep_log = home / "sleeps"
    sleeps = sleep_log.read_text().splitlines() if sleep_log.exists() else []
    assert sleeps == ["10"] * (attempts - 1)


def test_fichiers_terminent_par_newline() -> None:
    for path in (WORKFLOW, Path(__file__)):
        assert path.read_bytes().endswith(b"\n"), f"Newline finale absente : {path}"


def test_workflow_conserve_etape_build_apk() -> None:
    """L'étape principale de build APK doit rester présente et inchangée."""
    names = _step_names()
    assert any("Build APK" in n for n in names), (
        f"L'étape « Build APK release » a disparu du workflow : {names}"
    )


def test_workflow_conserve_etape_cmake() -> None:
    """L'étape anti-flaky CMake 3.22.1 doit rester présente (non régression)."""
    names = _step_names()
    assert any("CMake" in n for n in names), (
        f"L'étape « Pré-installer CMake 3.22.1 » a disparu : {names}"
    )
