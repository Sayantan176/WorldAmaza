import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.database import get_db_context
from app.models import Watch, Article, Event, EventArticle, WatchMatch, MonitoringRun, User
from app.schemas.watch import StructuredWatchRules
from app.services.news_service import news_ingestion_service
from app.services.event_matcher import evaluate_article_for_watch
from app.services.deduplication_service import generate_event_dedup_key, calculate_jaccard_similarity
from app.services.notification_service import notification_service
from app.config import settings

logger = logging.getLogger("worldamaze.monitoring_job")


def run_watch_monitoring(watch_id: str, trigger_type: str = "scheduled") -> dict:
    """
    Executes a complete monitoring cycle for a given watch.
    Idempotent, safe, and logs execution details to MonitoringRun.
    """
    with get_db_context() as db:
        watch = db.query(Watch).filter(Watch.id == watch_id).first()
        if not watch or watch.status != "active":
            logger.info(f"Watch {watch_id} is not active or does not exist. Skipping.")
            return {"status": "skipped", "reason": "watch_inactive"}

        user = db.query(User).filter(User.id == watch.user_id).first()
        if not user:
            logger.warning(f"Owner user not found for watch {watch_id}")
            return {"status": "error", "reason": "user_not_found"}

        run_record = MonitoringRun(
            watch_id=watch.id,
            trigger_type=trigger_type,
            status="running",
            articles_fetched=0,
            articles_evaluated=0,
            events_matched=0,
            notifications_created=0,
            started_at=datetime.now(timezone.utc)
        )
        db.add(run_record)
        db.commit()
        db.refresh(run_record)

        try:
            rules_dict = watch.rules_dict
            rules = StructuredWatchRules.model_validate(rules_dict)

            # 1. Determine search query
            # Combine primary subjects and include terms
            search_query = ""
            if rules.include_terms:
                search_query = " ".join(rules.include_terms[:3])
            elif rules.subjects:
                search_query = " ".join(rules.subjects[:2])
            else:
                search_query = watch.title

            logger.info(f"Executing watch '{watch.title}' query: '{search_query}'")

            # 2. Ingest articles
            candidate_articles = news_ingestion_service.discover_articles(
                query=search_query,
                max_articles=settings.MAX_ARTICLES_PER_SEARCH
            )
            run_record.articles_fetched = len(candidate_articles)

            matched_events_count = 0
            notifications_count = 0

            # 3. Process candidate articles
            eval_count = 0
            for art in candidate_articles:
                if eval_count >= settings.MAX_LLM_EVALUATIONS_PER_RUN:
                    break

                # Persist or load Article record
                existing_art = db.query(Article).filter(
                    (Article.canonical_url == art.canonical_url) |
                    (Article.content_hash == art.content_hash)
                ).first()

                if not existing_art:
                    existing_art = Article(
                        canonical_url=art.canonical_url,
                        title=art.title,
                        source_name=art.source_name,
                        author=art.author,
                        published_at=art.published_at,
                        retrieved_at=art.retrieved_at,
                        snippet=art.snippet,
                        content=art.content,
                        content_hash=art.content_hash,
                        source_type=art.source_type,
                        language=art.language,
                        source_metadata=str(art.source_metadata)
                    )
                    db.add(existing_art)
                    db.commit()
                    db.refresh(existing_art)

                # 4. Evaluate article against watch
                eval_count += 1
                run_record.articles_evaluated += 1

                eval_result = evaluate_article_for_watch(art, rules)
                if not eval_result:
                    continue

                # 5. Deduplication & Event Clustering
                dedup_key = generate_event_dedup_key(
                    headline=eval_result.headline,
                    category=eval_result.event_category,
                    topic_key=eval_result.dedup_topic_key
                )

                event = db.query(Event).filter(Event.dedup_key == dedup_key).first()
                if not event:
                    # Check semantic title similarity among recent events
                    recent_events = db.query(Event).order_by(Event.first_detected_at.desc()).limit(20).all()
                    for re in recent_events:
                        if calculate_jaccard_similarity(re.headline, eval_result.headline) > 0.65:
                            event = re
                            break

                if not event:
                    event = Event(
                        dedup_key=dedup_key,
                        headline=eval_result.headline,
                        summary=eval_result.summary,
                        event_category=eval_result.event_category,
                        importance=eval_result.importance,
                        evidence_status=eval_result.evidence_status,
                        what_changed=eval_result.what_changed,
                        first_detected_at=datetime.now(timezone.utc),
                        last_updated_at=datetime.now(timezone.utc),
                        status="active"
                    )
                    db.add(event)
                    db.commit()
                    db.refresh(event)

                # Link Article to Event
                existing_link = db.query(EventArticle).filter(
                    EventArticle.event_id == event.id,
                    EventArticle.article_id == existing_art.id
                ).first()
                if not existing_link:
                    link = EventArticle(
                        event_id=event.id,
                        article_id=existing_art.id,
                        relevance_score=eval_result.relevance_score,
                        is_primary=True if eval_result.relevance_score > 0.8 else False
                    )
                    db.add(link)
                    db.commit()

                # Link WatchMatch
                existing_match = db.query(WatchMatch).filter(
                    WatchMatch.watch_id == watch.id,
                    WatchMatch.event_id == event.id
                ).first()

                if not existing_match:
                    watch_match = WatchMatch(
                        watch_id=watch.id,
                        event_id=event.id,
                        relevance_score=eval_result.relevance_score,
                        match_rationale=eval_result.match_rationale,
                        decision=eval_result.decision
                    )
                    db.add(watch_match)
                    db.commit()
                    matched_events_count += 1

                    # Trigger Notification if qualified
                    sources_meta = [{
                        "source_name": art.source_name,
                        "title": art.title,
                        "url": art.canonical_url
                    }]

                    send_email = (eval_result.decision == "immediate_alert")
                    notification = notification_service.create_notification(
                        db=db,
                        user=user,
                        watch=watch,
                        event=event,
                        match_rationale=eval_result.match_rationale,
                        sources=sources_meta,
                        send_email=send_email
                    )
                    notifications_count += 1

            # Update Watch metrics
            watch.last_checked_at = datetime.now(timezone.utc)
            if matched_events_count > 0:
                watch.last_matched_at = datetime.now(timezone.utc)
                watch.events_count += matched_events_count
            watch.last_error = None

            run_record.status = "success" if matched_events_count > 0 else "no_updates"
            run_record.events_matched = matched_events_count
            run_record.notifications_created = notifications_count
            run_record.completed_at = datetime.now(timezone.utc)
            db.commit()

            return {
                "status": run_record.status,
                "articles_fetched": run_record.articles_fetched,
                "articles_evaluated": run_record.articles_evaluated,
                "events_matched": matched_events_count,
                "notifications_created": notifications_count
            }

        except Exception as e:
            logger.error(f"Error in monitoring run for watch {watch_id}: {type(e).__name__} {e}")
            watch.last_error = str(e)[:300]
            run_record.status = "failed"
            run_record.error_message = str(e)[:500]
            run_record.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "failed", "error": str(e)}


def run_all_active_watches_monitoring() -> dict:
    """Executes monitoring cycle for all active watches."""
    with get_db_context() as db:
        active_watches = db.query(Watch).filter(Watch.status == "active").all()
        watch_ids = [w.id for w in active_watches]

    results = {}
    for wid in watch_ids:
        results[wid] = run_watch_monitoring(wid, trigger_type="scheduled")
    return results
