from pathlib import Path


def test_demo_publica_declara_escopo_e_usa_amostra_versionada() -> None:
    html = Path("web-demo/index.html").read_text(encoding="utf-8")

    assert "Demonstração estática" in html
    assert "data/osm-teresina-health.geojson" in html
    assert "data/ibge-teresina-boundary.geojson" in html
    assert "L.geoJSON" in html
    assert "OpenStreetMap" in html
    assert "haversine" in html
    assert "invalidateSize" in html
    assert "height:clamp(620px,100vh,900px)" in html
    assert ".map-wrap{min-width:0;min-height:0" in html


def test_workflow_publica_apenas_o_diretorio_da_demo() -> None:
    workflow = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")

    assert "actions/configure-pages@v6" in workflow
    assert "actions/upload-pages-artifact@v5" in workflow
    assert "actions/deploy-pages@v5" in workflow
    assert "path: web-demo" in workflow
