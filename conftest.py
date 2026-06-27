"""Configuration pytest — exclut les tests d'intégration du run par défaut.

Les tests marqués @pytest.mark.integration nécessitent le fichier de données
data/municipales_2026_t1_communes.csv (non committé, ~plusieurs Mo).
Sur un clone frais, ces tests sont skip automatiquement.

Pour les lancer : pytest -m integration
"""

import pytest


def pytest_configure(config):
    """Enregistre le mark 'integration' pour éviter PytestUnknownMarkWarning."""
    config.addinivalue_line("markers", "integration: tests nécessitant le fichier de données (non committé)")


def pytest_collection_modifyitems(config, items):
    """Skip les tests d'intégration sauf si -m integration est explicitement demandé."""
    markexpr = config.getoption("markexpr", "")
    if "integration" in markexpr:
        return  # Ne pas skipper si -m integration est explicitement demandé
    skip_integration = pytest.mark.skip(
        reason="Test d'intégration — nécessite le fichier de données (non committé). "
        "Lancer avec: pytest -m integration"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
