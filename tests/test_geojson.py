import pytest
from pydantic import ValidationError

from geo_intelligence_api.schemas import GeoJSONFeatureCollection


def test_wgs84_rejeita_latitude_fora_do_intervalo() -> None:
    with pytest.raises(ValidationError):
        GeoJSONFeatureCollection.model_validate(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"nome": "X", "tipo": "outro"},
                        "geometry": {"type": "Point", "coordinates": [0, 91]},
                    }
                ],
            }
        )


def test_apenas_point_e_aceito() -> None:
    with pytest.raises(ValidationError):
        GeoJSONFeatureCollection.model_validate(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"nome": "X", "tipo": "outro"},
                        "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                    }
                ],
            }
        )
