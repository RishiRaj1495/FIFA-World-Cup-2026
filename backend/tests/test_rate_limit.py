from app.core.rate_limit import RateLimiter


def test_allows_requests_under_the_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    assert limiter.is_allowed("client-a", now=0)
    assert limiter.is_allowed("client-a", now=1)
    assert limiter.is_allowed("client-a", now=2)


def test_blocks_requests_over_the_limit_within_the_window():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    for i in range(3):
        assert limiter.is_allowed("client-a", now=i)
    assert limiter.is_allowed("client-a", now=3) is False


def test_window_resets_after_it_elapses():
    limiter = RateLimiter(max_requests=2, window_seconds=10)
    assert limiter.is_allowed("client-a", now=0)
    assert limiter.is_allowed("client-a", now=1)
    assert limiter.is_allowed("client-a", now=2) is False
    # Once 10 seconds have passed, the earliest hits fall out of the window.
    assert limiter.is_allowed("client-a", now=11)


def test_clients_are_tracked_independently():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.is_allowed("client-a", now=0)
    assert limiter.is_allowed("client-a", now=1) is False
    # A different client has its own independent quota.
    assert limiter.is_allowed("client-b", now=1)


def test_rate_limiter_memory_cleanup():
    limiter = RateLimiter(max_requests=2, window_seconds=10)
    limiter.last_cleanup = 0

    assert limiter.is_allowed("client-a", now=0)
    assert "client-a" in limiter._hits

    # 11 seconds later, check should trigger cleanup
    assert limiter.is_allowed("client-b", now=11)
    assert "client-a" not in limiter._hits
    assert "client-b" in limiter._hits
