"""Static validation of project config: TOML, the GitLab component, k8s manifests,
and the compose file. These run in CI without building any container."""

from __future__ import annotations

import pathlib
import tomllib

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent


def _load_yaml(relpath):
    with open(REPO / relpath) as fh:
        return yaml.safe_load(fh)


def _load_kind(relpath, kind):
    """Return the first document of the given `kind` from a (multi-doc) manifest."""
    with open(REPO / relpath) as fh:
        for doc in yaml.safe_load_all(fh):
            if doc and doc.get("kind") == kind:
                return doc
    raise AssertionError(f"no {kind} document in {relpath}")


# --------------------------------------------------------------------------- #
# zensical.toml
# --------------------------------------------------------------------------- #

def test_zensical_toml_parses_and_has_nav():
    with open(REPO / "zensical.toml", "rb") as fh:
        cfg = tomllib.load(fh)
    project = cfg["project"]
    assert project["site_name"]
    assert isinstance(project["nav"], list) and project["nav"]


def test_zensical_nav_targets_exist():
    with open(REPO / "zensical.toml", "rb") as fh:
        cfg = tomllib.load(fh)
    for entry in cfg["project"]["nav"]:
        target = next(iter(entry.values()))
        assert (REPO / "docs" / target).is_file(), f"nav target missing: {target}"


# --------------------------------------------------------------------------- #
# GitLab CI/CD component (templates/claude-agent.yml)
# --------------------------------------------------------------------------- #

def test_gitlab_component_is_spec_plus_job():
    with open(REPO / "templates/claude-agent.yml") as fh:
        docs = list(yaml.safe_load_all(fh))
    assert len(docs) == 2, "component must be a spec document + a job document"
    spec, job = docs
    assert "prompt" in spec["spec"]["inputs"], "component needs a 'prompt' input"
    assert "claude-agent" in job


def test_gitlab_ci_is_component_release_only():
    # The GitLab side is a mirror that only publishes the component on tags.
    # It must NOT carry the project's own agent/test pipeline (that's on GitHub).
    pipeline = _load_yaml(".gitlab-ci.yml")
    jobs = [k for k, v in pipeline.items()
            if isinstance(v, dict) and ("script" in v or "trigger" in v)]
    assert jobs, "expected at least one job"
    for stale in ("claude-advisor", "claude-agent", "build-agent-image", "pytest"):
        assert stale not in pipeline, f"{stale} should live on GitHub, not the GitLab mirror"
    release = pipeline.get("create-component-release", {})
    assert "release" in release, "must create a release to publish the component"
    rule = release["rules"][0]["if"]
    assert "CI_COMMIT_TAG" in rule, "release must be gated on a tag"


# --------------------------------------------------------------------------- #
# GitHub Action (action.yml) — reusable analog of the GitLab component
# --------------------------------------------------------------------------- #

def test_github_action_is_docker_with_required_inputs():
    action = _load_yaml("action.yml")
    assert "prompt" in action["inputs"]
    assert action["inputs"]["prompt"]["required"] is True
    assert action["inputs"]["anthropic_api_key"]["required"] is True
    assert action["runs"]["using"] == "docker"
    assert action["runs"]["image"].startswith("docker://")


def test_github_agent_workflow_parses():
    # PyYAML loads the bare `on:` key as boolean True — accept either form.
    wf = _load_yaml(".github/workflows/claude-agent.yml")
    assert ("on" in wf) or (True in wf)
    assert "agent" in wf["jobs"]


# --------------------------------------------------------------------------- #
# Kubernetes manifests (deploy/) — hardened for AKS + OpenShift
# --------------------------------------------------------------------------- #

def test_agent_job_is_hardened():
    job = _load_kind("deploy/agent-job.yaml", "Job")
    pod = job["spec"]["template"]["spec"]
    assert pod["securityContext"]["runAsNonRoot"] is True
    container = pod["containers"][0]["securityContext"]
    assert container["allowPrivilegeEscalation"] is False
    assert container["capabilities"]["drop"] == ["ALL"]


def test_networkpolicy_denies_ingress():
    netpol = _load_yaml("deploy/networkpolicy.yaml")
    assert netpol["kind"] == "NetworkPolicy"
    assert netpol["spec"]["ingress"] == []


# --------------------------------------------------------------------------- #
# compose.yaml — local stack
# --------------------------------------------------------------------------- #

def test_compose_has_expected_services():
    compose = _load_yaml("compose.yaml")
    services = compose["services"]
    for name in ("elasticsearch", "kibana", "otel-collector", "agent"):
        assert name in services, f"compose missing service: {name}"


def test_compose_collector_mounts_local_config():
    compose = _load_yaml("compose.yaml")
    mounts = compose["services"]["otel-collector"]["volumes"]
    assert any("collector-config.local.yaml" in m for m in mounts)


def test_otel_local_config_scrubs_and_exports_to_elasticsearch():
    cfg = _load_yaml("otel/collector-config.local.yaml")
    assert "transform/scrub" in cfg["processors"]
    assert "elasticsearch" in cfg["exporters"]
    logs = cfg["service"]["pipelines"]["logs"]
    assert "transform/scrub" in logs["processors"]
    assert "elasticsearch" in logs["exporters"]
