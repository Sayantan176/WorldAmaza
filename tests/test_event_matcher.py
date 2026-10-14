from unittest.mock import patch
from datetime import datetime, timezone
from app.schemas.article import ArticleNormalized
from app.schemas.watch import StructuredWatchRules
from app.schemas.event import EventEvaluationResult
from app.services.event_matcher import prefilter_article, evaluate_article_for_watch


def test_prefilter_exclude_noise():
    rules = StructuredWatchRules(
        title="India Fighter Aviation",
        description="Track India fighter aircraft",
        subjects=["India", "fighter aircraft"],
        include_terms=["Tejas", "AMCA"],
        exclude_terms=["rumor", "speculation", "airline"],
        trigger_conditions=["First flight or rollout"],
        importance_threshold="high",
        evidence_requirement="official_confirmation",
        uncertainty_policy="suppress"
    )

    art_noise = ArticleNormalized(
        canonical_url="https://example.com/airline-news",
        title="Commercial airline travel surges in India",
        source_name="Travel Weekly",
        snippet="Airlines in India see record passenger growth this season.",
        content_hash="h1",
        retrieved_at=datetime.now(timezone.utc)
    )
    # Excluded because 'airline' is in exclude_terms
    assert prefilter_article(art_noise, rules) is False

    art_valid = ArticleNormalized(
        canonical_url="https://example.com/tejas-rollout",
        title="HAL rolls out new Tejas fighter aircraft prototype",
        source_name="Defense News",
        snippet="Hindustan Aeronautics Limited unveiled the first prototype of Tejas Mk1A.",
        content_hash="h2",
        retrieved_at=datetime.now(timezone.utc)
    )
    assert prefilter_article(art_valid, rules) is True


@patch("app.services.event_matcher.groq_service.generate_structured")
def test_evaluate_article_evidence_policy_suppression(mock_groq):
    # Rule requires official_confirmation and uncertainty_policy is suppress
    rules = StructuredWatchRules(
        title="Ceasefire Agreements",
        description="Notify me only when a ceasefire is officially confirmed. No rumors or speculation.",
        subjects=["Ceasefire"],
        include_terms=["ceasefire agreement"],
        exclude_terms=[],
        trigger_conditions=["Signed ceasefire agreement"],
        importance_threshold="high",
        evidence_requirement="official_confirmation",
        uncertainty_policy="suppress"
    )

    art = ArticleNormalized(
        canonical_url="https://example.com/rumored-truce",
        title="Delegates rumor possible ceasefire agreement next week",
        source_name="Market Blog",
        snippet="Anonymous sources speculate that talks might lead to a truce.",
        content_hash="h3",
        retrieved_at=datetime.now(timezone.utc)
    )

    # Groq returns speculative event
    mock_groq.return_value = EventEvaluationResult(
        matches_watch=True,
        relevance_score=0.7,
        event_category="announcement",
        importance="medium",
        evidence_status="unverified_rumor",
        is_new_development=True,
        what_changed="Rumors surfaced about ongoing discussions.",
        headline="Rumors of upcoming ceasefire talks",
        summary="Anonymous delegates report potential future talks.",
        match_rationale="Mentions ceasefire discussions.",
        decision="immediate_alert",
        dedup_topic_key="ceasefire-talks"
    )

    # Must be suppressed according to policy
    result = evaluate_article_for_watch(art, rules)
    assert result is None  # Suppressed!


@patch("app.services.event_matcher.groq_service.generate_structured")
def test_evaluate_article_importance_downgrade(mock_groq):
    # Rule requires high importance
    rules = StructuredWatchRules(
        title="Defence Aviation",
        description="Track major aviation milestones",
        subjects=["fighter aircraft"],
        include_terms=["fighter aircraft"],
        exclude_terms=[],
        trigger_conditions=["Major contract"],
        importance_threshold="high",
        evidence_requirement="any_report",
        uncertainty_policy="allow",
        delivery_mode="both"
    )

    art = ArticleNormalized(
        canonical_url="https://example.com/minor-paint",
        title="New paint livery tested on fighter aircraft",
        source_name="Aero Weekly",
        snippet="Routine livery tests were conducted today.",
        content_hash="h4",
        retrieved_at=datetime.now(timezone.utc)
    )

    # Low importance event claiming immediate_alert
    mock_groq.return_value = EventEvaluationResult(
        matches_watch=True,
        relevance_score=0.6,
        event_category="announcement",
        importance="low",
        evidence_status="single_report",
        is_new_development=True,
        what_changed="Minor livery paint test.",
        headline="Livery test conducted",
        summary="Routine paint scheme evaluation.",
        match_rationale="Mentions fighter aircraft.",
        decision="immediate_alert",
        dedup_topic_key="aircraft-paint"
    )

    result = evaluate_article_for_watch(art, rules)
    assert result is not None
    # Because importance is 'low' and rule threshold is 'high', it should be downgraded to digest_only
    assert result.decision == "digest_only"
