from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Optional, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CircuitBreakerState:
    """Circuit breaker state management."""
    failure_count: int = 0
    last_failure_time: float = 0
    state: str = "closed"  # closed, open, half-open

    def record_success(self) -> None:
        """Record a successful call."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= 5:  # threshold
            self.state = "open"

    def should_attempt_call(self) -> bool:
        """Check if call should be attempted."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            # Check if timeout has passed (30 seconds)
            if time.time() - self.last_failure_time > 30:
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True


class ResilientAPICaller:
    """Resilient API caller with retry logic and circuit breaker pattern."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        timeout: float = 30.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.circuit_breakers: dict[str, CircuitBreakerState] = {}

    def _get_circuit_breaker(self, service_name: str) -> CircuitBreakerState:
        """Get or create circuit breaker for a service."""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreakerState()
        return self.circuit_breakers[service_name]

    async def call_with_retry(
        self,
        func: Callable[..., T],
        service_name: str,
        *args,
        **kwargs
    ) -> T:
        """Call a function with retry logic and circuit breaker."""
        circuit_breaker = self._get_circuit_breaker(service_name)

        if not circuit_breaker.should_attempt_call():
            raise Exception(f"Circuit breaker is OPEN for {service_name}")

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Add timeout to the call
                if asyncio.iscoroutinefunction(func):
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self.timeout
                    )
                else:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: func(*args, **kwargs)
                    )

                circuit_breaker.record_success()
                return result

            except Exception as e:
                last_exception = e
                circuit_breaker.record_failure()

                if attempt < self.max_retries:
                    delay = min(
                        self.base_delay * (self.backoff_factor ** attempt),
                        self.max_delay
                    )
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {service_name}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries + 1} attempts failed for {service_name}: {e}"
                    )

        raise last_exception

    @asynccontextmanager
    async def circuit_context(self, service_name: str) -> AsyncGenerator[None, None]:
        """Context manager for circuit breaker monitoring."""
        circuit_breaker = self._get_circuit_breaker(service_name)

        if not circuit_breaker.should_attempt_call():
            raise Exception(f"Circuit breaker is OPEN for {service_name}")

        try:
            yield
            circuit_breaker.record_success()
        except Exception:
            circuit_breaker.record_failure()
            raise


# Global instance
resilient_caller = ResilientAPICaller()


async def call_llm_with_resilience(
    llm_func: Callable[..., Any],
    service_name: str = "groq_llm",
    *args,
    **kwargs
) -> Any:
    """Call LLM function with resilience patterns."""
    return await resilient_caller.call_with_retry(llm_func, service_name, *args, **kwargs)


def call_llm_with_resilience_sync(
    llm_func: Callable[..., Any],
    service_name: str = "groq_llm",
    *args,
    **kwargs
) -> Any:
    """Synchronous version of LLM call with resilience patterns."""
    import asyncio
    try:
        # Try to get running loop first (Python 3.7+)
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # If loop is already running, we need to handle this differently
            # For now, just call directly (can be improved with proper async handling)
            return llm_func(*args, **kwargs)
    except RuntimeError:
        # No running loop, try to get current loop
        pass

    try:
        loop = asyncio.get_running_loop()
        # If we have a running loop, we can't use run_until_complete
        # This means we're already in an async context, so call directly
        return llm_func(*args, **kwargs)
    except RuntimeError:
        # No running loop, create a new one
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                resilient_caller.call_with_retry(llm_func, service_name, *args, **kwargs)
            )
        finally:
            loop.close()
            asyncio.set_event_loop(None)


async def call_embedding_with_resilience(
    embed_func: Callable[..., Any],
    service_name: str = "deepinfra_embedding",
    *args,
    **kwargs
) -> Any:
    """Call embedding function with resilience patterns."""
    return await resilient_caller.call_with_retry(embed_func, service_name, *args, **kwargs)


def call_embedding_with_resilience_sync(
    embed_func: Callable[..., Any],
    service_name: str = "deepinfra_embedding",
    *args,
    **kwargs
) -> Any:
    """Synchronous version of embedding call with resilience patterns."""
    import asyncio
    try:
        # Try to get running loop first
        loop = asyncio.get_running_loop()
        if loop.is_running():
            return embed_func(*args, **kwargs)
    except RuntimeError:
        pass

    try:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            return loop.run_until_complete(
                resilient_caller.call_with_retry(embed_func, service_name, *args, **kwargs)
            )
        else:
            return embed_func(*args, **kwargs)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                resilient_caller.call_with_retry(embed_func, service_name, *args, **kwargs)
            )
        finally:
            loop.close()
            asyncio.set_event_loop(None)


async def call_scraper_with_resilience(
    scrape_func: Callable[..., Any],
    service_name: str = "firecrawl_scraper",
    *args,
    **kwargs
) -> Any:
    """Call scraper function with resilience patterns."""
    return await resilient_caller.call_with_retry(scrape_func, service_name, *args, **kwargs)


def call_scraper_with_resilience_sync(
    scrape_func: Callable[..., Any],
    service_name: str = "firecrawl_scraper",
    *args,
    **kwargs
) -> Any:
    """Call scraper function with resilience patterns (sync wrapper)."""
    try:
        loop = asyncio.get_running_loop()
        # If we have a running loop, we can't use run_until_complete
        # This means we're already in an async context, so call directly
        return scrape_func(*args, **kwargs)
    except RuntimeError:
        # No running loop, create a new one
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                resilient_caller.call_with_retry(scrape_func, service_name, *args, **kwargs)
            )
        finally:
            loop.close()
            asyncio.set_event_loop(None)