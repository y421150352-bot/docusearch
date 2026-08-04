from app.services import health_service


def test_health_report_is_ok_when_all_components_are_ready(monkeypatch) -> None:
    monkeypatch.setattr(
        health_service,
        "_check_storage",
        lambda: {"name": "storage", "ok": True, "detail": "ok", "critical": True},
    )
    monkeypatch.setattr(
        health_service,
        "_check_database",
        lambda: {"name": "database", "ok": True, "detail": "ok", "critical": True},
    )
    monkeypatch.setattr(
        health_service,
        "_check_redis",
        lambda: {"name": "redis", "ok": True, "detail": "ok", "critical": True},
    )
    monkeypatch.setattr(
        health_service,
        "_check_qdrant",
        lambda: {"name": "qdrant", "ok": True, "detail": "ok", "critical": True},
    )
    monkeypatch.setattr(
        health_service,
        "_check_index_artifacts",
        lambda: {"name": "index", "ok": True, "detail": "ok", "critical": False},
    )
    monkeypatch.setattr(
        health_service,
        "_check_llm",
        lambda: {"name": "llm", "ok": True, "detail": "ok", "critical": False},
    )

    report = health_service.get_health_report()

    assert report["status"] == "ok"
    assert len(report["components"]) == 6


def test_health_report_is_degraded_when_critical_component_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        health_service,
        "_check_storage",
        lambda: {"name": "storage", "ok": True, "detail": "ok", "critical": True},
    )
    monkeypatch.setattr(
        health_service,
        "_check_database",
        lambda: {"name": "database", "ok": True, "detail": "ok", "critical": True},
    )
    monkeypatch.setattr(
        health_service,
        "_check_redis",
        lambda: {"name": "redis", "ok": False, "detail": "down", "critical": True},
    )
    monkeypatch.setattr(
        health_service,
        "_check_qdrant",
        lambda: {"name": "qdrant", "ok": True, "detail": "ok", "critical": True},
    )
    monkeypatch.setattr(
        health_service,
        "_check_index_artifacts",
        lambda: {"name": "index", "ok": True, "detail": "ok", "critical": False},
    )
    monkeypatch.setattr(
        health_service,
        "_check_llm",
        lambda: {"name": "llm", "ok": True, "detail": "ok", "critical": False},
    )

    report = health_service.get_health_report()

    assert report["status"] == "degraded"


def test_health_report_is_warning_when_only_optional_components_fail(monkeypatch) -> None:
    monkeypatch.setattr(
        health_service,
        "_check_storage",
        lambda: {"name": "storage", "ok": True, "detail": "ok", "critical": True},
    )
    monkeypatch.setattr(
        health_service,
        "_check_database",
        lambda: {"name": "database", "ok": True, "detail": "ok", "critical": True},
    )
    monkeypatch.setattr(
        health_service,
        "_check_redis",
        lambda: {"name": "redis", "ok": True, "detail": "ok", "critical": True},
    )
    monkeypatch.setattr(
        health_service,
        "_check_qdrant",
        lambda: {"name": "qdrant", "ok": True, "detail": "ok", "critical": True},
    )
    monkeypatch.setattr(
        health_service,
        "_check_index_artifacts",
        lambda: {"name": "index", "ok": False, "detail": "missing", "critical": False},
    )
    monkeypatch.setattr(
        health_service,
        "_check_llm",
        lambda: {"name": "llm", "ok": True, "detail": "ok", "critical": False},
    )

    report = health_service.get_health_report()

    assert report["status"] == "warning"
