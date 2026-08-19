"""Carrega pontos inteiramente sintéticos em torno de Teresina; não são dados oficiais."""

from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from geo_intelligence_api.database import SessionLocal
from geo_intelligence_api.models import Facility

DATA = [
    ("UBS Sintética Norte", "saude", -42.812, -5.055),
    ("Escola Sintética Centro", "educacao", -42.803, -5.091),
    ("Abrigo Sintético Sul", "assistencia", -42.789, -5.132),
    ("Base Sintética Leste", "seguranca", -42.755, -5.083),
]


def main() -> None:
    with SessionLocal() as db:
        if db.query(Facility).filter(Facility.fonte == "DADO SINTÉTICO — DEMONSTRAÇÃO").count():
            print("Seed já aplicado; nenhuma alteração.")
            return
        db.add_all(
            [
                Facility(
                    nome=n,
                    tipo=t,
                    fonte="DADO SINTÉTICO — DEMONSTRAÇÃO",
                    geom=from_shape(Point(lon, lat), srid=4326),
                )
                for n, t, lon, lat in DATA
            ]
        )
        db.commit()
        print(f"{len(DATA)} instalações sintéticas inseridas.")


if __name__ == "__main__":
    main()
