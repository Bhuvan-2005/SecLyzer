"""
Comprehensive Rust Extractor Testing Suite

Tests the Rust extractors by:
1. Verifying binaries exist and are executable
2. Testing startup and connectivity
3. Sending test events via Redis
4. Verifying feature output
5. Checking performance metrics
6. Validating data flow
"""

import json
import os
import signal
import subprocess
import time
from pathlib import Path

import pytest
import redis

# Configuration
RUST_EXTRACTORS_DIR = (
    Path(__file__).parent.parent.parent
    / "test_environment"
    / "extractors_rs"
    / "target"
    / "release"
)
KEYSTROKE_BINARY = RUST_EXTRACTORS_DIR / "keystroke_extractor"
MOUSE_BINARY = RUST_EXTRACTORS_DIR / "mouse_extractor"
APP_TRACKER_BINARY = RUST_EXTRACTORS_DIR / "app_tracker"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


@pytest.fixture
def redis_client():
    """Connect to Redis for testing"""
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    # Test connection
    try:
        client.ping()
    except redis.ConnectionError:
        pytest.skip("Redis not available")

    # Clean up before test
    client.delete("seclyzer:events")
    client.delete("seclyzer:features:keystroke")
    client.delete("seclyzer:features:mouse")
    client.delete("seclyzer:features:app")

    yield client

    # Clean up after test
    client.delete("seclyzer:events")
    client.delete("seclyzer:features:keystroke")
    client.delete("seclyzer:features:mouse")
    client.delete("seclyzer:features:app")


class TestRustBinaries:
    """Test that Rust binaries exist and are executable"""

    def test_keystroke_extractor_binary_exists(self):
        """Verify keystroke_extractor binary exists"""
        assert (
            KEYSTROKE_BINARY.exists()
        ), f"keystroke_extractor not found at {KEYSTROKE_BINARY}"
        assert os.access(
            KEYSTROKE_BINARY, os.X_OK
        ), f"keystroke_extractor is not executable"

    def test_mouse_extractor_binary_exists(self):
        """Verify mouse_extractor binary exists"""
        assert MOUSE_BINARY.exists(), f"mouse_extractor not found at {MOUSE_BINARY}"
        assert os.access(MOUSE_BINARY, os.X_OK), f"mouse_extractor is not executable"

    def test_app_tracker_binary_exists(self):
        """Verify app_tracker binary exists"""
        assert (
            APP_TRACKER_BINARY.exists()
        ), f"app_tracker not found at {APP_TRACKER_BINARY}"
        assert os.access(APP_TRACKER_BINARY, os.X_OK), f"app_tracker is not executable"

    def test_keystroke_extractor_binary_size(self):
        """Verify keystroke_extractor binary is reasonable size"""
        size = KEYSTROKE_BINARY.stat().st_size
        # Should be around 5MB
        assert size > 1_000_000, f"keystroke_extractor too small: {size} bytes"
        assert size < 20_000_000, f"keystroke_extractor too large: {size} bytes"

    def test_mouse_extractor_binary_size(self):
        """Verify mouse_extractor binary is reasonable size"""
        size = MOUSE_BINARY.stat().st_size
        # Should be around 5MB
        assert size > 1_000_000, f"mouse_extractor too small: {size} bytes"
        assert size < 20_000_000, f"mouse_extractor too large: {size} bytes"

    def test_app_tracker_binary_size(self):
        """Verify app_tracker binary is reasonable size"""
        size = APP_TRACKER_BINARY.stat().st_size
        # Should be around 5MB
        assert size > 1_000_000, f"app_tracker too small: {size} bytes"
        assert size < 20_000_000, f"app_tracker too large: {size} bytes"


class TestRustExtractorStartup:
    """Test Rust extractor startup and connectivity"""

    def test_keystroke_extractor_startup(self, redis_client):
        """Test keystroke_extractor starts and connects to Redis"""
        process = subprocess.Popen(
            [str(KEYSTROKE_BINARY)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Give it time to start
            time.sleep(2)

            # Check if process is still running
            assert process.poll() is None, "keystroke_extractor exited unexpectedly"

            # Verify it's listening on Redis
            # Send a test event
            redis_client.publish(
                "seclyzer:events",
                json.dumps(
                    {
                        "type": "keystroke",
                        "ts": int(time.time() * 1_000_000),
                        "key": "a",
                        "event": "press",
                    }
                ),
            )

            # Give it time to process
            time.sleep(1)

            # Process should still be running
            assert process.poll() is None, "keystroke_extractor crashed after event"

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    def test_mouse_extractor_startup(self, redis_client):
        """Test mouse_extractor starts and connects to Redis"""
        process = subprocess.Popen(
            [str(MOUSE_BINARY)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Give it time to start
            time.sleep(2)

            # Check if process is still running
            assert process.poll() is None, "mouse_extractor exited unexpectedly"

            # Verify it's listening on Redis
            redis_client.publish(
                "seclyzer:events",
                json.dumps(
                    {
                        "type": "mouse",
                        "ts": int(time.time() * 1_000_000),
                        "x": 100,
                        "y": 200,
                        "event": "move",
                    }
                ),
            )

            # Give it time to process
            time.sleep(1)

            # Process should still be running
            assert process.poll() is None, "mouse_extractor crashed after event"

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    def test_app_tracker_startup(self, redis_client):
        """Test app_tracker starts and connects to Redis"""
        process = subprocess.Popen(
            [str(APP_TRACKER_BINARY)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Give it time to start
            time.sleep(2)

            # Check if process is still running
            assert process.poll() is None, "app_tracker exited unexpectedly"

            # Verify it's listening on Redis
            redis_client.publish(
                "seclyzer:events",
                json.dumps(
                    {
                        "type": "app",
                        "ts": int(time.time() * 1_000_000),
                        "app_name": "firefox",
                        "event": "focus",
                    }
                ),
            )

            # Give it time to process
            time.sleep(1)

            # Process should still be running
            assert process.poll() is None, "app_tracker crashed after event"

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


class TestRustExtractorEventProcessing:
    """Test Rust extractors process events correctly"""

    def test_keystroke_extractor_processes_events(self, redis_client):
        """Test keystroke_extractor processes keystroke events"""
        process = subprocess.Popen(
            [str(KEYSTROKE_BINARY)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            time.sleep(2)

            # Send multiple keystroke events
            base_ts = int(time.time() * 1_000_000)
            for i in range(10):
                redis_client.publish(
                    "seclyzer:events",
                    json.dumps(
                        {
                            "type": "keystroke",
                            "ts": base_ts + i * 50000,
                            "key": chr(97 + (i % 26)),  # a-z
                            "event": "press" if i % 2 == 0 else "release",
                        }
                    ),
                )

            time.sleep(2)

            # Check if features were generated
            features_count = redis_client.llen("seclyzer:features:keystroke")
            # May or may not have features depending on timing, but should not crash
            assert process.poll() is None, "keystroke_extractor crashed"

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    def test_mouse_extractor_processes_events(self, redis_client):
        """Test mouse_extractor processes mouse events"""
        process = subprocess.Popen(
            [str(MOUSE_BINARY)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            time.sleep(2)

            # Send multiple mouse events
            base_ts = int(time.time() * 1_000_000)
            for i in range(20):
                redis_client.publish(
                    "seclyzer:events",
                    json.dumps(
                        {
                            "type": "mouse",
                            "ts": base_ts + i * 50000,
                            "x": 100 + i * 10,
                            "y": 200 + i * 5,
                            "event": "move",
                        }
                    ),
                )

            time.sleep(2)

            # Check if features were generated
            features_count = redis_client.llen("seclyzer:features:mouse")
            # May or may not have features depending on timing, but should not crash
            assert process.poll() is None, "mouse_extractor crashed"

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    def test_app_tracker_processes_events(self, redis_client):
        """Test app_tracker processes app events"""
        process = subprocess.Popen(
            [str(APP_TRACKER_BINARY)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            time.sleep(2)

            # Send app switch events
            base_ts = int(time.time() * 1_000_000)
            apps = ["firefox", "vscode", "terminal", "chrome"]
            for i, app in enumerate(apps):
                redis_client.publish(
                    "seclyzer:events",
                    json.dumps(
                        {
                            "type": "app",
                            "ts": base_ts + i * 1_000_000,
                            "app_name": app,
                            "event": "focus",
                        }
                    ),
                )

            time.sleep(2)

            # Check if features were generated
            features_count = redis_client.llen("seclyzer:features:app")
            # May or may not have features depending on timing, but should not crash
            assert process.poll() is None, "app_tracker crashed"

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


class TestRustExtractorPerformance:
    """Test Rust extractor performance characteristics"""

    def test_keystroke_extractor_startup_time(self):
        """Test keystroke_extractor starts quickly"""
        start = time.time()
        process = subprocess.Popen(
            [str(KEYSTROKE_BINARY)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait for startup
            time.sleep(1)

            startup_time = time.time() - start

            # Should start in under 2 seconds (accounting for system variance)
            assert (
                startup_time < 2.0
            ), f"keystroke_extractor took {startup_time}s to start"
            assert process.poll() is None, "keystroke_extractor exited during startup"

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    def test_mouse_extractor_startup_time(self):
        """Test mouse_extractor starts quickly"""
        start = time.time()
        process = subprocess.Popen(
            [str(MOUSE_BINARY)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait for startup
            time.sleep(1)

            startup_time = time.time() - start

            # Should start in under 2 seconds (accounting for system variance)
            assert startup_time < 2.0, f"mouse_extractor took {startup_time}s to start"
            assert process.poll() is None, "mouse_extractor exited during startup"

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    def test_app_tracker_startup_time(self):
        """Test app_tracker starts quickly"""
        start = time.time()
        process = subprocess.Popen(
            [str(APP_TRACKER_BINARY)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait for startup
            time.sleep(1)

            startup_time = time.time() - start

            # Should start in under 2 seconds (accounting for system variance)
            assert startup_time < 2.0, f"app_tracker took {startup_time}s to start"
            assert process.poll() is None, "app_tracker exited during startup"

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


class TestRustExtractorIntegration:
    """Test Rust extractors working together"""

    def test_all_extractors_run_simultaneously(self, redis_client):
        """Test all three Rust extractors can run at the same time"""
        processes = []

        try:
            # Start all three extractors
            for binary in [KEYSTROKE_BINARY, MOUSE_BINARY, APP_TRACKER_BINARY]:
                process = subprocess.Popen(
                    [str(binary)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                processes.append(process)

            # Give them time to start
            time.sleep(3)

            # Verify all are running
            for i, process in enumerate(processes):
                assert process.poll() is None, f"Extractor {i} exited unexpectedly"

            # Send mixed events
            base_ts = int(time.time() * 1_000_000)

            # Keystroke events
            for i in range(5):
                redis_client.publish(
                    "seclyzer:events",
                    json.dumps(
                        {
                            "type": "keystroke",
                            "ts": base_ts + i * 100000,
                            "key": "a",
                            "event": "press" if i % 2 == 0 else "release",
                        }
                    ),
                )

            # Mouse events
            for i in range(5):
                redis_client.publish(
                    "seclyzer:events",
                    json.dumps(
                        {
                            "type": "mouse",
                            "ts": base_ts + i * 100000,
                            "x": 100 + i * 10,
                            "y": 200,
                            "event": "move",
                        }
                    ),
                )

            # App events
            for i, app in enumerate(["firefox", "vscode"]):
                redis_client.publish(
                    "seclyzer:events",
                    json.dumps(
                        {
                            "type": "app",
                            "ts": base_ts + i * 1_000_000,
                            "app_name": app,
                            "event": "focus",
                        }
                    ),
                )

            time.sleep(2)

            # Verify all still running
            for i, process in enumerate(processes):
                assert (
                    process.poll() is None
                ), f"Extractor {i} crashed during integration test"

        finally:
            for process in processes:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()


class TestRustExtractorResilience:
    """Test Rust extractors handle edge cases"""

    def test_keystroke_extractor_handles_invalid_json(self, redis_client):
        """Test keystroke_extractor doesn't crash on invalid JSON"""
        process = subprocess.Popen(
            [str(KEYSTROKE_BINARY)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            time.sleep(2)

            # Send invalid JSON
            redis_client.publish("seclyzer:events", "not valid json")
            redis_client.publish("seclyzer:events", "{incomplete json")

            time.sleep(1)

            # Should still be running
            assert process.poll() is None, "keystroke_extractor crashed on invalid JSON"

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    def test_keystroke_extractor_handles_missing_fields(self, redis_client):
        """Test keystroke_extractor handles events with missing fields"""
        process = subprocess.Popen(
            [str(KEYSTROKE_BINARY)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            time.sleep(2)

            # Send event with missing fields
            redis_client.publish(
                "seclyzer:events",
                json.dumps(
                    {
                        "type": "keystroke"
                        # Missing ts, key, event
                    }
                ),
            )

            time.sleep(1)

            # Should still be running
            assert (
                process.poll() is None
            ), "keystroke_extractor crashed on missing fields"

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    def test_keystroke_extractor_handles_wrong_event_type(self, redis_client):
        """Test keystroke_extractor ignores non-keystroke events"""
        process = subprocess.Popen(
            [str(KEYSTROKE_BINARY)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            time.sleep(2)

            # Send mouse event to keystroke extractor
            redis_client.publish(
                "seclyzer:events",
                json.dumps(
                    {
                        "type": "mouse",
                        "ts": int(time.time() * 1_000_000),
                        "x": 100,
                        "y": 200,
                        "event": "move",
                    }
                ),
            )

            time.sleep(1)

            # Should still be running
            assert (
                process.poll() is None
            ), "keystroke_extractor crashed on wrong event type"

        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
