import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import User, Watch, Article, Event, EventArticle, WatchMatch, Notification
from app.schemas.watch import StructuredWatchRules
from app.services.notification_service import notification_service
from app.jobs.monitoring_job import run_watch_monitoring


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


def test_watch_creation_and_ownership(test_db):
    user_a = User(email="analyst_a@worldamaze.io")
    user_b = User(email="analyst_b@worldamaze.io")
    test_db.add_all([user_a, user_b])
    test_db.commit()

    rules = StructuredWatchRules(
        title="Semiconductor Restrictions",
        description="Monitor semiconductor export controls",
        subjects=["Semiconductor"],
        include_terms=["export restriction"],
        importance_threshold="high",
        evidence_requirement="official_confirmation"
    )

    watch_a = Watch(
        user_id=user_a.id,
        title=rules.title,
        description=rules.description,
        structured_rules=json.dumps(rules.model_dump()),
        status="active"
    )
    test_db.add(watch_a)
    test_db.commit()

    # User A owns it
    found_a = test_db.query(Watch).filter(Watch.id == watch_a.id, Watch.user_id == user_a.id).first()
    assert found_a is not None

    # User B cannot access it
    found_b = test_db.query(Watch).filter(Watch.id == watch_a.id, Watch.user_id == user_b.id).first()
    assert found_b is None


def test_watch_pause_and_resume(test_db):
    user = User(email="operator@worldamaze.io")
    test_db.add(user)
    test_db.commit()

    watch = Watch(
        user_id=user.id,
        title="Test Watch",
        description="Prompt",
        status="active"
    )
    test_db.add(watch)
    test_db.commit()

    # Pause
    watch.status = "paused"
    test_db.commit()
    assert watch.status == "paused"

    # Resume
    watch.status = "active"
    test_db.commit()
    assert watch.status == "active"


def test_duplicate_notification_prevention(test_db):
    user = User(email="subscriber@worldamaze.io", email_notifications_enabled=False)
    watch = Watch(user_id="u1", title="Cyber Watch", description="Prompt")
    event = Event(
        dedup_key="cyber-zero-day-cve-2026",
        headline="Critical Remote Code Execution Zero-Day Patched",
        summary="A major vendor released an out-of-band security patch.",
        event_category="vulnerability",
        importance="critical",
        evidence_status="official_confirmed"
    )
    test_db.add_all([user, watch, event])
    test_db.commit()
    watch.user_id = user.id
    test_db.commit()

    sources = [{"source_name": "CISA", "title": "Security Advisory", "url": "https://cisa.gov/advisory"}]

    # First notification creation
    notif1 = notification_service.create_notification(
        db=test_db,
        user=user,
        watch=watch,
        event=event,
        match_rationale="Matches critical CVE trigger",
        sources=sources,
        send_email=False
    )
    assert notif1 is not None

    # Attempting duplicate notification
    notif2 = notification_service.create_notification(
        db=test_db,
        user=user,
        watch=watch,
        event=event,
        match_rationale="Matches critical CVE trigger",
        sources=sources,
        send_email=False
    )

    # Must return the same existing notification record, not create a duplicate
    assert notif1.id == notif2.id
    total = test_db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.event_id == event.id
    ).count()
    assert total == 1
