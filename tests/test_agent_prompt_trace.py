from __future__ import annotations

from contextlib import contextmanager

from app import agent as agent_module


class ManagedPrompt:
    version = 3

    def compile(self, **variables: str) -> str:
        return (
            f"Feature={variables['feature']}\n"
            f"Docs={variables['docs']}\n"
            f"Question={variables['message']}"
        )


class RecordingLangfuseClient:
    def __init__(self) -> None:
        self.prompt = ManagedPrompt()
        self.span_updates: list[dict] = []

    def get_prompt(self, name: str, **kwargs):
        return self.prompt

    def update_current_span(self, **kwargs) -> None:
        self.span_updates.append(kwargs)


def test_agent_records_prompt_version_with_v4_observation_api(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PROMPT_NAME", "day13-chat")
    monkeypatch.setenv("LANGFUSE_PROMPT_LABEL", "production")
    client = RecordingLangfuseClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(agent_module, "tracing_enabled", lambda: True)

    propagated: list[dict] = []

    @contextmanager
    def record_attributes(**kwargs):
        propagated.append(kwargs)
        yield

    monkeypatch.setattr(agent_module, "propagate_attributes", record_attributes)

    agent = agent_module.LabAgent()
    agent_module.LabAgent.run.__wrapped__(
        agent,
        user_id="student-01",
        feature="qa",
        session_id="session-01",
        message="Explain traces",
        correlation_id="req-12345678",
    )

    span_update = client.span_updates[-1]
    assert span_update["metadata"] == {
        "doc_count": 1,
        "query_preview": "Explain traces",
        "prompt_name": "day13-chat",
        "prompt_label": "production",
        "prompt_version": "3",
        "prompt_source": "langfuse",
        "prompt_fetch_error": "",
    }
    assert span_update["version"] == "3"
    assert propagated[0]["metadata"]["correlation_id"] == "req-12345678"
    assert propagated[-1]["prompt"] is client.prompt


class RecordingObservation:
    def __init__(self, name: str, as_type: str) -> None:
        self.name = name
        self.as_type = as_type
        self.updates: list[dict] = []

    def update(self, **kwargs) -> None:
        self.updates.append(kwargs)


class RecordingObservationClient(RecordingLangfuseClient):
    def __init__(self) -> None:
        super().__init__()
        self.observations: list[RecordingObservation] = []

    def start_as_current_observation(self, *, name: str, as_type: str = "span", **_):
        @contextmanager
        def manager():
            observation = RecordingObservation(name, as_type)
            self.observations.append(observation)
            yield observation

        return manager()


def test_agent_creates_retrieval_and_generation_child_observations(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_PROMPT_NAME", "day13-chat")
    monkeypatch.setenv("LANGFUSE_PROMPT_LABEL", "production")
    client = RecordingObservationClient()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(agent_module, "tracing_enabled", lambda: True)

    @contextmanager
    def passthrough(**_kwargs):
        yield

    monkeypatch.setattr(agent_module, "propagate_attributes", passthrough)

    agent = agent_module.LabAgent()
    agent_module.LabAgent.run.__wrapped__(
        agent,
        user_id="student-01",
        feature="qa",
        session_id="session-01",
        message="Explain traces for student@vinuni.edu.vn",
        correlation_id="req-12345678",
    )

    by_type = {observation.as_type: observation for observation in client.observations}
    assert set(by_type) == {"retriever", "generation"}

    retriever_update = by_type["retriever"].updates[-1]
    assert retriever_update["output"] == {"doc_count": 1}
    assert retriever_update["metadata"]["correlation_id"] == "req-12345678"

    generation_update = by_type["generation"].updates[-1]
    assert generation_update["model"] == "claude-sonnet-4-5"
    assert generation_update["usage_details"]["input"] > 0
    assert generation_update["usage_details"]["output"] > 0
    assert generation_update["cost_details"]["total_cost"] > 0
    assert generation_update["metadata"]["correlation_id"] == "req-12345678"
    assert generation_update["version"] == "3"
    assert "student@vinuni.edu.vn" not in str(generation_update["input"])
    assert "REDACTED_EMAIL" in str(generation_update["input"])
