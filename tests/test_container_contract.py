from pathlib import Path


def test_imagem_inclui_dados_versionados_usados_pelos_scripts() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "COPY --chown=app:app data data" in dockerfile
