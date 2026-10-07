import unittest
from unittest.mock import Mock
from shared_access import RequestLimiter, LimitedProvider


class SharedTests(unittest.TestCase):
    def test_process_limit_is_shared_between_sessions(self):
        limiter = RequestLimiter()
        for _ in range(15):
            limiter.reserve({}, now=0)
        with self.assertRaises(ValueError):
            limiter.reserve({}, now=1)
        limiter.reserve({}, now=60)

    def test_session_limit(self):
        limiter, session = RequestLimiter(), {}
        for index in range(30):
            limiter.reserve(session, now=index * 61)
        with self.assertRaises(ValueError):
            limiter.reserve(session, now=2000)

    def test_failure_counts_and_limit_prevents_call(self):
        limiter = RequestLimiter()
        session = {"shared_model_requests": 29}
        provider = Mock()
        provider.decide.side_effect = ValueError("Quota")
        wrapped = LimitedProvider(provider, limiter, session)
        with self.assertRaises(ValueError):
            wrapped.decide("rules", {}, {})
        self.assertEqual(session["shared_model_requests"], 30)
        with self.assertRaises(ValueError):
            wrapped.decide("rules", {}, {})
        self.assertEqual(provider.decide.call_count, 1)
