from typing import Any

from scripts.data_quality import analyze_feature_collection


def test_relatorio_aprova_amostra_valida_e_detecta_duplicata() -> None:
    feature: dict[str, Any] = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-42.8, -5.1]},
        "properties": {
            "nome": "Unidade A",
            "tipo": "hospital",
            "fonte": "OpenStreetMap contributors (ODbL)",
        },
    }
    report = analyze_feature_collection(
        {
            "type": "FeatureCollection",
            "metadata": {"license": "ODbL 1.0"},
            "features": [feature, feature],
        }
    )

    assert report["status"] == "aprovado"
    assert report["feature_count"] == 2
    assert report["duplicate_count"] == 1
    assert report["bbox"] == [-42.8, -5.1, -42.8, -5.1]


def test_relatorio_reprova_crs_e_campos_invalidos() -> None:
    report = analyze_feature_collection(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-42.8, 95]},
                    "properties": {"nome": "Inválida"},
                }
            ],
        }
    )

    assert report["status"] == "reprovado"
    assert report["valid_feature_count"] == 0
    assert report["errors"][0]["code"] == "out_of_wgs84"
