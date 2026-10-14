import pytest
from unittest.mock import patch
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import User, Watch, Event, WatchMatch, Digest
from app.services.digest_service import digest_service


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def test_digest_preview_and_generation(test_db):
    user = User(
        email="digest_tester@worldamaze.io",
        email_notifications_enabled=True,
        digest_frequency="daily",
        digest_time="08:00"
    )
    test_db.add(user)
    test_db.commit()

    watch = Watch(
        user_id=user.id,
        title="Renewable Energy Watch",
        description="Follow India's renewable energy policy",
        status="active"
    )
    test_db.add(watch)
    test_db.commit()

    event = Event(
        dedup_key="india-solar-policy-approval-2026",
        headline="Ministry announces 50GW renewable energy tender framework",
        summary="India's power ministry has cleared a major solar and wind allocation framework.",
        event_category="policy",
        importance="high",
        evidence_status="official_confirmed",
        first_detected_at=datetime.now(timezone.utc)
    )
    test_db.add(event)
    test_db.commit()

    match = WatchMatch(
        watch_id=watch.id,
        event_id=event.id,
        relevance_score=0.92,
        match_rationale="Matches renewable tender policy",
        decision="digest_only",
        created_at=datetime.now(timezone.utc)
    )
    test_db.add(match)
    test_db.commit()

    # Test preview compilation
    preview = digest_service.compile_digest_preview(test_db, user, period="daily")
    assert preview["total_events"] == 1
    assert len(preview["watch_groups"]) == 1
    assert preview["watch_groups"][0]["watch_title"] == "Renewable Energy Watch"
    assert preview["watch_groups"][0]["events"][0]["headline"] == event.headline

    # Test generation with mocked email send
    with patch("resend.Emails.send", return_value={"id": "mock_email_123"}):
        digest = digest_service.generate_and_deliver_digest(test_db, user, period="daily", force_send_email=True)

    assert digest is not None
    assert digest.event_count == 1
    assert digest.email_sent is True
    assert digest.email_status == "delivered"
