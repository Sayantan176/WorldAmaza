from app.services.deduplication_service import (
    canonicalize_url,
    compute_content_hash,
    calculate_jaccard_similarity,
    generate_event_dedup_key,
)


def test_url_canonicalization():
    url1 = "https://www.reuters.com/world/india/fighter-jet-rollout/?utm_source=twitter&utm_medium=social#comments"
    url2 = "https://reuters.com/world/india/fighter-jet-rollout?fbclid=12345"
    
    canon1 = canonicalize_url(url1)
    canon2 = canonicalize_url(url2)

    assert canon1 == "https://reuters.com/world/india/fighter-jet-rollout"
    assert canon2 == "https://reuters.com/world/india/fighter-jet-rollout"
    assert canon1 == canon2


def test_content_hashing_determinism():
    title1 = "India approves Tejas Mk1A prototype delivery schedule"
    title2 = "india approves tejas mk1a prototype delivery schedule!"
    snippet = "The Ministry of Defence officially confirmed the revised delivery schedule today."

    hash1 = compute_content_hash(title1, snippet)
    hash2 = compute_content_hash(title2, snippet)
    
    assert hash1 == hash2

    hash3 = compute_content_hash("Completely different story title", snippet)
    assert hash1 != hash3


def test_jaccard_similarity():
    text1 = "Indian Air Force receives new fighter aircraft prototype"
    text2 = "Indian Air Force receives prototype fighter aircraft"
    text3 = "US stock market rallies on tech earnings"

    sim_high = calculate_jaccard_similarity(text1, text2)
    sim_low = calculate_jaccard_similarity(text1, text3)

    assert sim_high > 0.7
    assert sim_low < 0.1


def test_event_dedup_key():
    key1 = generate_event_dedup_key(
        headline="Tejas Mk1A first flight achieved",
        category="first_flight",
        topic_key="tejas-mk1a-first-flight"
    )
    key2 = generate_event_dedup_key(
        headline="Tejas Mk1A first flight achieved successfully",
        category="first_flight",
        topic_key="tejas-mk1a-first-flight"
    )
    assert isinstance(key1, str)
    assert len(key1) == 32
