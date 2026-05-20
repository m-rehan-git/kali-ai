import json
from config import MAX_MEMORY_ENTRIES


class Memory:
    def __init__(self, max_entries: int = MAX_MEMORY_ENTRIES):
        self._buffer: list[dict] = []
        self._max = max_entries

    def add(self, role: str, content: str) -> None:
        self._buffer.append({"role": role, "content": content})
        if len(self._buffer) > self._max:
            self._buffer = self._buffer[-self._max:]

    def add_tool_result(self, tool: str, args: dict, result: str) -> None:
        entry = (
            f"[Tool: {tool}] Args: {json.dumps(args)}\n"
            f"Output:\n{result[:1000]}"
        )
        self._buffer.append({"role": "tool", "name": tool, "content": entry})
        if len(self._buffer) > self._max:
            self._buffer = self._buffer[-self._max:]

    def as_messages(self) -> list[dict]:
        return list(self._buffer)

    def __len__(self):
        return len(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()
