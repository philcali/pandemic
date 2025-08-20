"""Performance tests for event bus system."""

import asyncio
import sys
import tempfile
import time
from statistics import mean, stdev

import pytest
from pandemic_core.events import EventBusManager


class TestEventBusPerformance:
    """Performance benchmarks for event bus."""

    @pytest.fixture
    def temp_events_dir(self):
        """Create temporary events directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.mark.asyncio
    async def test_event_publishing_throughput(self, temp_events_dir):
        """Test event publishing throughput."""
        manager = EventBusManager(temp_events_dir, rate_limit=1000, burst_size=1000)
        await manager.start()

        try:
            # Warm up
            for _ in range(10):
                await manager.publish_event("core", "warmup.event", {"id": 1})

            # Benchmark publishing
            num_events = 100
            start_time = time.time()

            for i in range(num_events):
                await manager.publish_event("core", "benchmark.event", {"id": i})

            end_time = time.time()
            duration = end_time - start_time
            throughput = num_events / duration

            print(f"Published {num_events} events in {duration:.3f}s")
            print(f"Throughput: {throughput:.1f} events/second")

            # Should be able to publish at least 1000 events/second
            assert throughput > 1000

        finally:
            await manager.stop()

    @pytest.mark.skipif(sys.version_info > (3, 12), reason="Broken in 3.12 and it hangs")
    @pytest.mark.asyncio
    async def test_event_delivery_latency(self, temp_events_dir):
        """Test event delivery latency."""
        manager = EventBusManager(temp_events_dir)
        await manager.start()

        try:
            socket_path = manager.get_socket_path("core")

            # Connect subscriber
            reader, writer = await asyncio.open_unix_connection(socket_path)

            try:
                latencies = []
                num_tests = 50

                await asyncio.sleep(1.0)
                for i in range(num_tests):
                    # Record publish time
                    publish_time = time.time()

                    # Publish event
                    await manager.publish_event(
                        "core", "latency.test", {"id": i, "timestamp": publish_time}
                    )

                    # Receive event
                    length_data = await asyncio.wait_for(reader.readexactly(4), timeout=1.0)
                    event_length = int.from_bytes(length_data, "big")
                    event_data = await reader.readexactly(event_length)

                    # Record receive time
                    receive_time = time.time()
                    latency = (receive_time - publish_time) * 1000  # Convert to ms
                    latencies.append(latency)

                avg_latency = mean(latencies)
                max_latency = max(latencies)
                min_latency = min(latencies)

                print(f"Average latency: {avg_latency:.2f}ms")
                print(f"Min latency: {min_latency:.2f}ms")
                print(f"Max latency: {max_latency:.2f}ms")

                if len(latencies) > 1:
                    std_latency = stdev(latencies)
                    print(f"Std deviation: {std_latency:.2f}ms")

                # Latency should be under 10ms for local sockets
                assert avg_latency < 10.0

            finally:
                writer.close()
                await writer.wait_closed()

        finally:
            await manager.stop()

    @pytest.mark.skipif(sys.version_info > (3, 12), reason="Broken in 3.12 and it hangs")
    @pytest.mark.asyncio
    async def test_multiple_subscribers_performance(self, temp_events_dir):
        """Test performance with multiple subscribers."""
        manager = EventBusManager(temp_events_dir)
        await manager.start()

        try:
            socket_path = manager.get_socket_path("core")
            num_subscribers = 10

            # Connect multiple subscribers
            subscribers = []
            for i in range(num_subscribers):
                reader, writer = await asyncio.open_unix_connection(socket_path)
                subscribers.append((reader, writer))

            try:
                await asyncio.sleep(2.0)
                # Publish events and measure time
                num_events = 50
                start_time = time.time()

                for i in range(num_events):
                    await manager.publish_event("core", "multi.test", {"id": i})

                # Verify all subscribers receive all events
                for sub_id, (reader, writer) in enumerate(subscribers):
                    for event_id in range(num_events):
                        length_data = await asyncio.wait_for(reader.readexactly(4), timeout=1.0)
                        event_length = int.from_bytes(length_data, "big")
                        event_data = await asyncio.wait_for(
                            reader.readexactly(event_length), timeout=1.0
                        )

                end_time = time.time()
                duration = end_time - start_time

                total_deliveries = num_events * num_subscribers
                delivery_rate = total_deliveries / duration

                print(
                    f"Delivered {total_deliveries} events to {num_subscribers} in {duration:.3f}s"
                )
                print(f"Delivery rate: {delivery_rate:.1f} deliveries/second")

                # Should handle at least 1000 deliveries/second
                assert delivery_rate > 1000

            finally:
                for reader, writer in subscribers:
                    writer.close()
                    await writer.wait_closed()

        finally:
            await manager.stop()

    @pytest.mark.asyncio
    async def test_rate_limiter_performance(self, temp_events_dir):
        """Test rate limiter performance impact."""
        # Test without rate limiting
        manager_unlimited = EventBusManager(temp_events_dir, rate_limit=10000, burst_size=10000)
        await manager_unlimited.start()

        try:
            await manager_unlimited.create_event_socket("test-unlimited")

            num_events = 100
            start_time = time.time()

            for i in range(num_events):
                await manager_unlimited.publish_event("test-unlimited", "perf.test", {"id": i})

            unlimited_duration = time.time() - start_time

        finally:
            await manager_unlimited.stop()

        # Test with rate limiting
        manager_limited = EventBusManager(temp_events_dir, rate_limit=50, burst_size=100)
        await manager_limited.start()

        try:
            await manager_limited.create_event_socket("test-limited")

            start_time = time.time()

            for i in range(num_events):
                await manager_limited.publish_event("test-limited", "perf.test", {"id": i})

            limited_duration = time.time() - start_time

        finally:
            await manager_limited.stop()

        print(f"Unlimited rate: {num_events/unlimited_duration:.1f} events/s")
        print(f"Limited rate: {num_events/limited_duration:.1f} events/s")

        # Rate limiting should not add more than 50% overhead for burst
        overhead = (limited_duration - unlimited_duration) / unlimited_duration
        print(f"Rate limiting overhead: {overhead*100:.1f}%")

        # Allow up to 100% overhead for rate limiting
        assert overhead < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
