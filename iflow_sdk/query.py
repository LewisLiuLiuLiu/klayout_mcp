"""Convenience functions for simple iFlow queries.

This module provides simple, one-shot query functions for cases where
you don't need the full interactive capabilities of IFlowClient.
"""

import asyncio
from typing import List, Optional, Union
from pathlib import Path

from .client import IFlowClient
from .types import AssistantMessage, IFlowOptions, Message, TaskFinishMessage


async def query(
    prompt: str,
    files: Optional[List[Union[str, Path]]] = None,
    options: Optional[IFlowOptions] = None,
) -> str:
    """Send a simple query to iFlow and return the complete response.

    This is a convenience function for simple, one-shot queries where you
    just want to send a message and get back the complete response as a string.

    For interactive conversations or streaming responses, use IFlowClient directly.

    Args:
        prompt: The message to send
        files: Optional list of file paths to include
        options: Optional configuration options

    Returns:
        The complete assistant response as a string

    Raises:
        ConnectionError: If connection fails
        TimeoutError: If response times out

    Example:
        ```python
        # Simple query
        response = await query("What is 2 + 2?")
        print(response)  # "4"

        # With files
        response = await query(
            "Explain this code",
            files=["main.py", "utils.py"]
        )

        # With custom options (e.g., sandbox)
        options = IFlowOptions().for_sandbox()
        response = await query("Hello from sandbox!", options=options)
        ```
    """
    response_text = []

    async with IFlowClient(options) as client:
        # Send message
        await client.send_message(prompt, files)

        # Collect response
        async for message in client.receive_messages():
            if isinstance(message, AssistantMessage):
                if message.chunk.text:
                    response_text.append(message.chunk.text)
            elif isinstance(message, TaskFinishMessage):
                break

    return "".join(response_text)


async def query_stream(
    prompt: str,
    files: Optional[List[Union[str, Path]]] = None,
    options: Optional[IFlowOptions] = None,
):
    """Send a query and yield response chunks as they arrive.

    This is a convenience function for streaming responses where you want
    to process or display the response as it arrives.

    Args:
        prompt: The message to send
        files: Optional list of file paths to include
        options: Optional configuration options

    Yields:
        Response text chunks as they arrive

    Example:
        ```python
        # Stream response
        async for chunk in query_stream("Tell me a story"):
            print(chunk, end="", flush=True)
        ```
    """
    async with IFlowClient(options) as client:
        # Send message
        await client.send_message(prompt, files)

        # Stream response
        async for message in client.receive_messages():
            if isinstance(message, AssistantMessage):
                if message.chunk.text:
                    yield message.chunk.text
            elif isinstance(message, TaskFinishMessage):
                break


def query_sync(
    prompt: str,
    files: Optional[List[Union[str, Path]]] = None,
    options: Optional[IFlowOptions] = None,
) -> str:
    """Synchronous wrapper for query function.

    This allows using the SDK from synchronous code. Note that this
    will block the current thread while waiting for the response.

    Args:
        prompt: The message to send
        files: Optional list of file paths to include
        options: Optional configuration options

    Returns:
        The complete assistant response as a string

    Example:
        ```python
        # From synchronous code
        response = query_sync("What is 2 + 2?")
        print(response)
        ```
    """
    return asyncio.run(query(prompt, files, options))
