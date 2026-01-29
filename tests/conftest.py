import pytest
from coreason_identity.models import UserContext


@pytest.fixture
def test_context() -> UserContext:
    return UserContext(
        user_id="test-user",
        email="test@coreason.ai",
        groups=["researcher"],
        scopes=["*"],
        claims={},
    )
