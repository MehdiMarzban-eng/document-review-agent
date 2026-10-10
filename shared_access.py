"""Process-local shared-key request allowances, including failed attempts."""
from collections import deque
from threading import Lock
import time


class RequestLimiter:
    def __init__(self):
        self.requests = deque()
        self.lock = Lock()

    def reserve(self, session, now=None):
        now = time.monotonic() if now is None else now
        with self.lock:
            while self.requests and now - self.requests[0] >= 86400:
                self.requests.popleft()
            if len(self.requests) >= 100:
                raise ValueError("The shared demo's daily request allowance has been reached.")
            if sum(now - instant < 60 for instant in self.requests) >= 15:
                raise ValueError("The shared demo is busy. Wait a minute before trying again.")
            if session.get("shared_model_requests", 0) >= 30:
                raise ValueError("This session's shared-model request allowance has been reached.")
            self.requests.append(now)
            session["shared_model_requests"] = session.get("shared_model_requests", 0) + 1


class LimitedProvider:
    @property
    def understands_questions(self):
        return getattr(self.provider, "understands_questions", False)

    def __init__(self, provider, limiter, session):
        self.provider, self.limiter, self.session = provider, limiter, session

    def decide(self, system, context, schema):
        self.limiter.reserve(self.session)
        return self.provider.decide(system, context, schema)
