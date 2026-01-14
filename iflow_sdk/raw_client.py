"""Raw data client for iFlow SDK.

This module provides access to raw protocol data for advanced users
who need to work with unprocessed JSON/SSE messages.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional, Union

from ._internal.protocol import ACPProtocol
from ._internal.transport import WebSocketTransport
from .client import IFlowClient
from .types import IFlowOptions, Message

logger = logging.getLogger(__name__)


@dataclass
class RawMessage:
    """Container for raw protocol messages."""

    # Raw data as received from transport
    raw_data: str

    # Parsed JSON (if applicable)
    json_data: Optional[Dict[str, Any]] = None

    # Message type for filtering
    message_type: Optional[str] = None

    # Timestamp when received
    timestamp: float = 0.0

    # Whether this is a control message (starts with //)
    is_control: bool = False

    # Parsed high-level message (if applicable)
    parsed_message: Optional[Message] = None

    def __post_init__(self):
        """Parse the raw data."""
        import time

        self.timestamp = time.time()

        # Check if control message
        if self.raw_data.startswith("//"):
            self.is_control = True
            self.message_type = "control"
            return

        # Try to parse as JSON
        try:
            self.json_data = json.loads(self.raw_data)

            # Extract message type
            if "method" in self.json_data:
                self.message_type = f"method:{self.json_data['method']}"
            elif "result" in self.json_data or "error" in self.json_data:
                self.message_type = "response"
            elif "type" in self.json_data:
                self.message_type = self.json_data["type"]

        except json.JSONDecodeError:
            # Not valid JSON, keep as raw text
            self.message_type = "text"


class RawDataClient(IFlowClient):
    """Extended iFlow client with raw data access.

    This client extends the base IFlowClient to provide access to:
    - Raw WebSocket messages
    - Unparsed JSON data
    - Protocol-level details
    - Both parsed and raw message streams

    Example - Accessing raw data:
        ```python
        async with RawDataClient() as client:
            await client.send_message("Hello")

            # Get raw messages
            async for raw_msg in client.receive_raw_messages():
                print(f"Raw: {raw_msg.raw_data}")
                if raw_msg.json_data:
                    print(f"JSON: {json.dumps(raw_msg.json_data, indent=2)}")
        ```

    Example - Dual stream (raw + parsed):
        ```python
        async with RawDataClient() as client:
            await client.send_message("What is 2+2?")

            async for raw_msg, parsed_msg in client.receive_dual_stream():
                # raw_msg is always available
                print(f"Raw type: {raw_msg.message_type}")

                # parsed_msg may be None for some protocol messages
                if parsed_msg:
                    print(f"Parsed: {type(parsed_msg).__name__}")
        ```
    """

    def __init__(self, options: Optional[IFlowOptions] = None, capture_raw: bool = True):
        """Initialize raw data client.

        Args:
            options: Configuration options
            capture_raw: Whether to capture raw messages (default True)
        """
        super().__init__(options)
        self.capture_raw = capture_raw
        self._raw_queue: asyncio.Queue[RawMessage] = asyncio.Queue()
        self._raw_history: list[RawMessage] = []

    async def _handle_messages(self) -> None:
        """Override to capture raw messages."""
        if not self._protocol:
            return

        try:
            # Direct access to transport for raw messages
            if self.capture_raw and self._transport:
                # Create tasks for both raw and parsed streams
                raw_task = asyncio.create_task(self._capture_raw_stream())
                parsed_task = asyncio.create_task(self._handle_parsed_stream())

                # Wait for both
                await asyncio.gather(raw_task, parsed_task)
            else:
                # Fall back to standard handling
                await super()._handle_messages()

        except asyncio.CancelledError:
            logger.debug("Message handler cancelled")
        except Exception as e:
            logger.error("Error in message handler: %s", e)

    async def _capture_raw_stream(self) -> None:
        """Capture raw messages from transport."""
        if not self._transport:
            return

        try:
            async for message in self._transport.receive():
                # Create raw message object
                raw_msg = RawMessage(
                    raw_data=message if isinstance(message, str) else json.dumps(message)
                )

                # Store in history
                self._raw_history.append(raw_msg)

                # Queue for streaming
                await self._raw_queue.put(raw_msg)

        except Exception as e:
            logger.error("Error capturing raw stream: %s", e)

    async def _handle_parsed_stream(self) -> None:
        """Handle parsed message stream."""
        if not self._protocol:
            return

        async for message_data in self._protocol.handle_messages():
            message = self._process_message(message_data)
            if message:
                await self._message_queue.put(message)

    async def receive_raw_messages(self) -> AsyncIterator[RawMessage]:
        """Receive raw protocol messages.

        Yields:
            RawMessage objects containing raw and parsed data
        """
        while self._connected or not self._raw_queue.empty():
            try:
                raw_msg = await asyncio.wait_for(self._raw_queue.get(), timeout=0.1)
                yield raw_msg
            except asyncio.TimeoutError:
                continue

    async def receive_dual_stream(self) -> AsyncIterator[tuple[RawMessage, Optional[Message]]]:
        """Receive both raw and parsed messages together.

        This correlates raw protocol messages with their parsed equivalents.

        Yields:
            Tuple of (RawMessage, Optional[Message])
        """
        # Create two tasks to receive from both queues
        raw_queue = self._raw_queue
        parsed_queue = self._message_queue

        # Track correlation between raw and parsed
        pending_raw: list[RawMessage] = []
        pending_parsed: list[Message] = []

        while self._connected or not raw_queue.empty() or not parsed_queue.empty():
            # Try to get raw message
            try:
                raw_msg = await asyncio.wait_for(raw_queue.get(), timeout=0.01)

                # Try to correlate with parsed message
                parsed_msg = None
                try:
                    parsed_msg = await asyncio.wait_for(parsed_queue.get(), timeout=0.01)
                except asyncio.TimeoutError:
                    pass

                # Attach parsed message to raw
                raw_msg.parsed_message = parsed_msg

                yield (raw_msg, parsed_msg)

            except asyncio.TimeoutError:
                # Check if we have parsed messages without raw
                try:
                    parsed_msg = await asyncio.wait_for(parsed_queue.get(), timeout=0.01)
                    # Create synthetic raw message
                    raw_msg = RawMessage(raw_data="<no-raw-data>", message_type="parsed_only")
                    yield (raw_msg, parsed_msg)
                except asyncio.TimeoutError:
                    continue

    def get_raw_history(self) -> list[RawMessage]:
        """Get history of all raw messages received.

        Returns:
            List of RawMessage objects in chronological order
        """
        return self._raw_history.copy()

    def get_protocol_stats(self) -> Dict[str, Any]:
        """Get protocol statistics.

        Returns:
            Dictionary with protocol stats
        """
        stats = {
            "total_messages": len(self._raw_history),
            "message_types": {},
            "control_messages": 0,
            "json_messages": 0,
            "text_messages": 0,
            "errors": 0,
        }

        for msg in self._raw_history:
            # Count by type
            if msg.message_type:
                stats["message_types"][msg.message_type] = (
                    stats["message_types"].get(msg.message_type, 0) + 1
                )

            # Count categories
            if msg.is_control:
                stats["control_messages"] += 1
            elif msg.json_data:
                stats["json_messages"] += 1
            else:
                stats["text_messages"] += 1

            # Count errors
            if msg.json_data and "error" in msg.json_data:
                stats["errors"] += 1

        return stats

    async def send_raw(self, data: Union[str, Dict[str, Any]]) -> None:
        """Send raw data directly to the transport.

        WARNING: This bypasses protocol validation. Use with caution.

        Args:
            data: Raw string or dictionary to send
        """
        if not self._transport:
            raise RuntimeError("Not connected")

        if isinstance(data, dict):
            await self._transport.send(data)
        else:
            await self._transport.send(data)

        logger.info("Sent raw data: %s", data if isinstance(data, str) else json.dumps(data)[:100])


class ProtocolDebugger:
    """Helper class for debugging protocol interactions."""

    def __init__(self, client: RawDataClient):
        """Initialize debugger.

        Args:
            client: RawDataClient instance to debug
        """
        self.client = client

    def print_message(self, msg: RawMessage, verbose: bool = False) -> None:
        """Pretty print a raw message.

        Args:
            msg: RawMessage to print
            verbose: Whether to show full content
        """
        print(f"\n{'='*60}")
        print(f"⏰ Timestamp: {msg.timestamp}")
        print(f"📦 Type: {msg.message_type}")
        print(f"🎛️  Control: {msg.is_control}")

        if msg.is_control:
            print(f"🔧 Control: {msg.raw_data}")
        elif msg.json_data:
            if verbose:
                print(f"📄 JSON:\n{json.dumps(msg.json_data, indent=2)}")
            else:
                # Show summary
                keys = list(msg.json_data.keys())
                print(f"🔑 Keys: {', '.join(keys)}")

                # Show method if present
                if "method" in msg.json_data:
                    print(f"📞 Method: {msg.json_data['method']}")

                # Show update type if present
                if "update_type" in msg.json_data:
                    print(f"🔄 Update: {msg.json_data['update_type']}")
        else:
            print(f"📝 Raw: {msg.raw_data[:100]}...")

    def analyze_session(self) -> None:
        """Analyze the entire session."""
        history = self.client.get_raw_history()
        stats = self.client.get_protocol_stats()

        print("\n" + "=" * 60)
        print("📊 SESSION ANALYSIS")
        print("=" * 60)

        print(f"\n📈 Statistics:")
        print(f"  Total messages: {stats['total_messages']}")
        print(f"  Control: {stats['control_messages']}")
        print(f"  JSON: {stats['json_messages']}")
        print(f"  Text: {stats['text_messages']}")
        print(f"  Errors: {stats['errors']}")

        print(f"\n📋 Message Types:")
        for msg_type, count in stats["message_types"].items():
            print(f"  {msg_type}: {count}")

        print(f"\n📜 Timeline:")
        for i, msg in enumerate(history[:10]):  # Show first 10
            print(f"  {i+1}. [{msg.message_type}] at {msg.timestamp:.2f}")

        if len(history) > 10:
            print(f"  ... and {len(history) - 10} more messages")
