from app.api.v1.health_check import liveness


def test_check_live():
    result = liveness()

    assert result["status"] == "ok"
