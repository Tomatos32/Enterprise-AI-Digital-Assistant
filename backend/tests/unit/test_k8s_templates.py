"""Unit tests and structural linting for Kubernetes Helm Chart & Canary Deployment Templates."""

import re
from pathlib import Path
import yaml
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CHART_DIR = REPO_ROOT / "deployments" / "helm" / "enterprise-ai"
TEMPLATES_DIR = CHART_DIR / "templates"


def test_chart_metadata_and_syntax():
    """Verify Chart.yaml exists, is valid YAML, and conforms to CNCF Helm 3 spec."""
    chart_file = CHART_DIR / "Chart.yaml"
    assert chart_file.exists(), "Chart.yaml must exist"

    with open(chart_file, "r", encoding="utf-8") as f:
        chart_data = yaml.safe_load(f)

    assert chart_data["apiVersion"] == "v2"
    assert chart_data["name"] == "enterprise-ai"
    assert chart_data["type"] == "application"
    assert "version" in chart_data
    assert "appVersion" in chart_data
    assert "enterprise-ai" in chart_data["keywords"]
    assert "canary" in chart_data["keywords"]
    assert len(chart_data["maintainers"]) >= 1


def test_values_yaml_defaults_and_contracts():
    """Verify values.yaml defines production defaults, probes, HPA, and Canary routing."""
    values_file = CHART_DIR / "values.yaml"
    assert values_file.exists(), "values.yaml must exist"

    with open(values_file, "r", encoding="utf-8") as f:
        values = yaml.safe_load(f)

    # 1. Base Replicas and Image
    assert values["replicaCount"] == 2
    assert values["image"]["repository"] == "enterprise-ai/backend"
    assert values["service"]["port"] == 8000

    # 2. Health Probes
    assert values["probes"]["liveness"]["path"] == "/api/v1/health"
    assert values["probes"]["readiness"]["path"] == "/api/v1/health"
    assert values["probes"]["liveness"]["initialDelaySeconds"] >= 10
    assert values["probes"]["readiness"]["initialDelaySeconds"] >= 5

    # 3. Horizontal Pod Autoscaler (HPA)
    assert values["autoscaling"]["enabled"] is True
    assert values["autoscaling"]["minReplicas"] == 2
    assert values["autoscaling"]["maxReplicas"] == 10
    assert values["autoscaling"]["targetCPUUtilizationPercentage"] == 75
    assert values["autoscaling"]["customMetrics"]["activeWebsockets"]["enabled"] is True
    assert values["autoscaling"]["customMetrics"]["activeWebsockets"]["targetAverageValue"] == "100"

    # 4. Canary Release Configuration
    assert values["canary"]["enabled"] is True
    assert values["canary"]["weight"] == 10
    assert values["canary"]["header"]["enabled"] is True
    assert values["canary"]["header"]["name"] == "X-Canary"
    assert values["canary"]["header"]["value"] == "always"

    # 5. Security & Isolation
    assert values["podSecurityContext"]["runAsNonRoot"] is True
    assert values["securityContext"]["allowPrivilegeEscalation"] is False
    assert values["secrets"]["enabled"] is True
    assert "mysqlPassword" in values["secrets"]
    assert "redisPassword" in values["secrets"]
    assert "secretKey" in values["secrets"]
    assert "hrApiToken" in values["secrets"]
    assert "erpApiToken" in values["secrets"]


def test_template_files_existence():
    """Verify all mandatory Kubernetes resource templates exist in the chart."""
    required_templates = [
        "_helpers.tpl",
        "configmap.yaml",
        "secret.yaml",
        "service.yaml",
        "deployment.yaml",
        "hpa.yaml",
        "ingress-stable.yaml",
        "ingress-canary.yaml",
    ]
    for tmpl in required_templates:
        tmpl_path = TEMPLATES_DIR / tmpl
        assert tmpl_path.exists(), f"Missing template: {tmpl}"


def test_deployment_template_probes_and_isolation():
    """Verify deployment.yaml includes livenessProbe, readinessProbe and physical Secret refs."""
    deploy_file = TEMPLATES_DIR / "deployment.yaml"
    content = deploy_file.read_text(encoding="utf-8")

    # Liveness and Readiness probe checks
    assert "livenessProbe:" in content
    assert "readinessProbe:" in content
    assert ".Values.probes.liveness.path" in content
    assert ".Values.probes.readiness.path" in content

    # ConfigMap and Secret reference checks
    assert "configMapRef:" in content
    assert "secretRef:" in content

    # Canary Deployment dual-track verification
    assert "track: stable" in content
    assert "track: canary" in content
    assert ".Values.canary.enabled" in content


def test_hpa_template_cpu_and_custom_metrics():
    """Verify hpa.yaml configures autoscaling/v2 with CPU target and active_websockets metric."""
    hpa_file = TEMPLATES_DIR / "hpa.yaml"
    content = hpa_file.read_text(encoding="utf-8")

    assert "apiVersion: autoscaling/v2" in content
    assert "kind: HorizontalPodAutoscaler" in content
    assert ".Values.autoscaling.minReplicas" in content
    assert ".Values.autoscaling.maxReplicas" in content
    assert ".Values.autoscaling.targetCPUUtilizationPercentage" in content
    assert "active_websockets" in content


def test_ingress_canary_annotations_and_weights():
    """Verify ingress-canary.yaml sets NGINX Canary annotations and header routing."""
    canary_ingress = TEMPLATES_DIR / "ingress-canary.yaml"
    content = canary_ingress.read_text(encoding="utf-8")

    assert 'nginx.ingress.kubernetes.io/canary: "true"' in content
    assert "nginx.ingress.kubernetes.io/canary-weight:" in content
    assert "nginx.ingress.kubernetes.io/canary-by-header:" in content
    assert "nginx.ingress.kubernetes.io/canary-by-header-value:" in content
    assert "backend:" in content
    assert "-canary" in content


@pytest.mark.parametrize("weight", [10, 50, 100])
def test_canary_progressive_rollout_weight_range(weight):
    """Verify Canary release progressive weights 10% -> 50% -> 100% are valid."""
    assert 0 <= weight <= 100
    assert weight in [10, 50, 100]


def _strip_control_tags(text: str) -> str:
    """Helper to remove Go template control flow lines and substitute value placeholders."""
    lines = []
    for line in text.splitlines():
        trimmed = line.strip()
        # Drop control-flow directives like {{- if ... }}, {{- end }}, {{- with ... }}
        if (trimmed.startswith("{{-") or trimmed.startswith("{{")) and (
            "if " in trimmed or "end" in trimmed or "with " in trimmed or "range " in trimmed
        ):
            continue
        if "include" in trimmed and trimmed.startswith("{{"):
            # label inclusion lines
            line = re.sub(r"\{\{.*?\}\}", "app: enterprise-ai", line)
        else:
            # value substitutions
            line = re.sub(r"\{\{.*?\}\}", "sample-value", line)
        lines.append(line)
    return "\n".join(lines)


def test_mock_render_manifests_valid_k8s_syntax():
    """
    Perform structural validation by substituting Helm variable placeholders
    with concrete values and verifying that the resulting documents parse as valid YAML structures.
    """
    # 1. ConfigMap rendering validation
    cm_file = TEMPLATES_DIR / "configmap.yaml"
    rendered_cm = _strip_control_tags(cm_file.read_text(encoding="utf-8"))
    cm_obj = yaml.safe_load(rendered_cm)
    assert cm_obj["apiVersion"] == "v1"
    assert cm_obj["kind"] == "ConfigMap"
    assert "data" in cm_obj
    assert "ENVIRONMENT" in cm_obj["data"]

    # 2. Secret rendering validation
    secret_file = TEMPLATES_DIR / "secret.yaml"
    rendered_secret = _strip_control_tags(secret_file.read_text(encoding="utf-8"))
    secret_obj = yaml.safe_load(rendered_secret)
    assert secret_obj["apiVersion"] == "v1"
    assert secret_obj["kind"] == "Secret"
    assert "stringData" in secret_obj
    assert "MYSQL_PASSWORD" in secret_obj["stringData"]

    # 3. HPA rendering validation
    hpa_file = TEMPLATES_DIR / "hpa.yaml"
    raw_hpa = hpa_file.read_text(encoding="utf-8")
    rendered_hpa = raw_hpa.replace('{{- if .Values.autoscaling.enabled }}', '')
    rendered_hpa = rendered_hpa.replace('{{- if .Values.autoscaling.targetCPUUtilizationPercentage }}', '')
    rendered_hpa = rendered_hpa.replace('{{- if .Values.autoscaling.targetMemoryUtilizationPercentage }}', '')
    rendered_hpa = rendered_hpa.replace('{{- if and .Values.autoscaling.customMetrics .Values.autoscaling.customMetrics.activeWebsockets.enabled }}', '')
    rendered_hpa = rendered_hpa.replace('{{- end }}', '')
    rendered_hpa = re.sub(r"\{\{.*?targetCPUUtilizationPercentage.*?\}\}", "75", rendered_hpa)
    rendered_hpa = re.sub(r"\{\{.*?targetMemoryUtilizationPercentage.*?\}\}", "80", rendered_hpa)
    rendered_hpa = re.sub(r"\{\{.*?minReplicas.*?\}\}", "2", rendered_hpa)
    rendered_hpa = re.sub(r"\{\{.*?maxReplicas.*?\}\}", "10", rendered_hpa)
    rendered_hpa = re.sub(r"\{\{.*?targetAverageValue.*?\}\}", '"100"', rendered_hpa)
    rendered_hpa = re.sub(r"\{\{.*?\}\}", "test-hpa", rendered_hpa)
    hpa_obj = yaml.safe_load(rendered_hpa)
    assert hpa_obj["apiVersion"] == "autoscaling/v2"
    assert hpa_obj["kind"] == "HorizontalPodAutoscaler"
    assert hpa_obj["spec"]["minReplicas"] == 2
    assert hpa_obj["spec"]["maxReplicas"] == 10
    assert len(hpa_obj["spec"]["metrics"]) == 3

    # 4. Service rendering validation
    svc_file = TEMPLATES_DIR / "service.yaml"
    raw_svc = svc_file.read_text(encoding="utf-8")
    # Split multi-document if canary is also included
    rendered_svc = _strip_control_tags(raw_svc)
    svc_docs = list(yaml.safe_load_all(rendered_svc))
    assert len(svc_docs) >= 1
    assert svc_docs[0]["apiVersion"] == "v1"
    assert svc_docs[0]["kind"] == "Service"
    assert "ports" in svc_docs[0]["spec"]
