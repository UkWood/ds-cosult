"""Bounded incremental DeepSeek Chat Completions SSE assembler."""
import json

LINE_LIMIT = 1024**2


class StreamFormat(ValueError):
    pass


class ChatStream:
    def __init__(self):
        self.pending = bytearray()
        self.data = []
        self.event_bytes = 0
        self.content = []
        self.model = self.response_id = self.finish = self.usage = None
        self.observed = {}
        self.done = False
        self.events = self.keepalives = self.content_bytes = self.reasoning_bytes = 0

    def feed(self, chunk):
        self.pending.extend(chunk)
        start = 0
        while not self.done:
            end = self.pending.find(b"\n", start)
            if end < 0:
                break
            if end - start > LINE_LIMIT:
                raise StreamFormat("Oversized SSE line")
            self.line(bytes(self.pending[start:end]).removesuffix(b"\r"))
            start = end + 1
        del self.pending[:start]
        if len(self.pending) > LINE_LIMIT:
            raise StreamFormat("Oversized SSE line")
        if self.done and self.pending.strip():
            raise StreamFormat("Data after DONE")

    def line(self, line):
        if not line:
            if self.data:
                raw = b"\n".join(self.data)
                self.data.clear()
                self.event_bytes = 0
                self.event(raw)
            return
        if line.startswith(b":"):
            self.keepalives += 1
            return
        name, _, value = line.partition(b":")
        if name == b"data":
            self.event_bytes += len(value) + 1
            if self.event_bytes > LINE_LIMIT:
                raise StreamFormat("Oversized SSE event")
            self.data.append(value.removeprefix(b" "))

    def event(self, raw):
        self.events += 1
        if raw == b"[DONE]":
            self.done = True
            return
        if self.usage is not None:
            raise StreamFormat("Chunk after final usage")
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise StreamFormat("Invalid SSE chunk")
        model, response_id = value.get("model"), value.get("id")
        if not isinstance(model, str) or not isinstance(response_id, str):
            raise StreamFormat("Missing model or response ID")
        if self.model is None:
            self.model, self.response_id = model, response_id
        elif (model, response_id) != (self.model, self.response_id):
            raise StreamFormat("Model or response ID changed")
        for field in ("thinking", "reasoning_effort"):
            if field in value:
                self.observed[field] = value[field]
        choices = value.get("choices")
        usage = value.get("usage")
        if choices == [] and self.finish is not None and usage is not None:
            self.usage = usage
            return
        if not isinstance(choices, list) or len(choices) != 1 or self.finish is not None:
            raise StreamFormat("Invalid choice sequence")
        choice = choices[0]
        if not isinstance(choice, dict) or type(choice.get("index")) is not int or choice["index"] != 0:
            raise StreamFormat("Unsupported choice")
        delta, finish = choice.get("delta"), choice.get("finish_reason")
        if not isinstance(delta, dict) or finish is not None and (
                not isinstance(finish, str) or not finish.strip()):
            raise StreamFormat("Invalid choice delta")
        if delta.get("tool_calls"):
            raise StreamFormat("Unexpected tools")
        for field in ("content", "reasoning_content"):
            text = delta.get(field)
            if text is None:
                continue
            if not isinstance(text, str):
                raise StreamFormat("Invalid text delta")
            size = len(text.encode())
            if field == "content":
                self.content.append(text)
                self.content_bytes += size
            else:
                self.reasoning_bytes += size
        self.finish = finish
        if usage is not None:
            if finish is None:
                raise StreamFormat("Usage before finish")
            self.usage = usage

    def metadata(self):
        return dict(sse_events=self.events, sse_keepalives=self.keepalives, sse_done=self.done,
                    sse_finish_seen=self.finish is not None, sse_usage_seen=self.usage is not None,
                    sse_content_bytes=self.content_bytes, sse_reasoning_bytes=self.reasoning_bytes)

    def assembled(self):
        if not self.done or self.finish is None:
            raise StreamFormat("Missing DONE or finish reason")
        return dict(model=self.model, **self.observed, usage=self.usage,
                    choices=[dict(finish_reason=self.finish, message={"content": "".join(self.content)})])
