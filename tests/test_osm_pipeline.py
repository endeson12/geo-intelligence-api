from typing import Any

from scripts.fetch_osm import to_feature_collection


def test_overpass_vira_geojson_com_proveniencia() -> None:
    payload: dict[str, Any] = {
        "osm3s": {"timestamp_osm_base": "2026-08-19T13:37:17Z"},
        "elements": [
            {
                "type": "node",
                "id": 123,
                "lat": -5.09,
                "lon": -42.80,
                "tags": {"name": "Unidade de teste", "amenity": "hospital"},
            },
            {
                "type": "node",
                "id": 999,
                "lat": -5.10,
                "lon": -42.81,
                "tags": {"amenity": "clinic"},
            },
        ],
    }

    result = to_feature_collection(payload)

    assert result["type"] == "FeatureCollection"
    assert result["metadata"]["license"] == "ODbL 1.0"
    assert len(result["features"]) == 1
    feature = result["features"][0]
    assert feature["geometry"]["coordinates"] == [-42.80, -5.09]
    assert feature["properties"]["tipo"] == "hospital"
    assert "osm:node/123" in feature["properties"]["fonte"]
