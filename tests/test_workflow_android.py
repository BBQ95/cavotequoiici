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

from pathlib import Path

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


def test_workflow_inclut_prechargement_gradle_avec_retry() -> None:
    """Le build Android doit pré-télécharger Gradle avec retry anti-flaky réseau."""
    doc = _load_workflow()
    steps = doc["jobs"]["build"]["steps"]
    run_scripts = [s.get("run", "") for s in steps if isinstance(s, dict)]

    # Une étape doit mentionner explicitement Gradle ET contenir une boucle de
    # retry (au moins 2 tentatives) ciblant le téléchargement de la distribution.
    found = False
    for script in run_scripts:
        if "gradle" in script.lower() and "retry" in script.lower():
            # Compter les occurrences de "tentative" ou d'indices de boucle 1 2 3.
            if any(marker in script for marker in ("tentative", "Tentative", "for i in", "attempt")):
                found = True
                break
    assert found, (
        "Aucune étape de pré-téléchargement Gradle avec retry trouvée dans "
        "android-test.yml. Le téléchargement de la distribution Gradle par le "
        "wrapper reste sans retry → un échec réseau intermittent fait échouer "
        "le build (cf. run 35236499277)."
    )


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