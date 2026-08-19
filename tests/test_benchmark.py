from scripts.benchmark_postgis import extract_plan_nodes, normalize_database_url, summarize_explain


def test_normaliza_url_sqlalchemy_para_psycopg() -> None:
    assert (
        normalize_database_url("postgresql+psycopg://localhost/geo") == "postgresql://localhost/geo"
    )


def test_resume_explain_com_tempo_e_nos() -> None:
    explain = [
        {
            "Plan": {
                "Node Type": "Aggregate",
                "Plans": [
                    {
                        "Node Type": "Bitmap Heap Scan",
                        "Plans": [{"Node Type": "Bitmap Index Scan", "Index Name": "idx_geog"}],
                    }
                ],
            },
            "Execution Time": 3.25,
        }
    ]

    assert extract_plan_nodes(explain[0]["Plan"]) == [
        "Aggregate",
        "Bitmap Heap Scan",
        "Bitmap Index Scan (idx_geog)",
    ]
    assert summarize_explain(explain) == {
        "execution_ms": 3.25,
        "plan_nodes": ["Aggregate", "Bitmap Heap Scan", "Bitmap Index Scan (idx_geog)"],
    }
