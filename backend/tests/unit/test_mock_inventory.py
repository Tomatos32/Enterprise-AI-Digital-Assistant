"""Unit Tests for Global Mock Inventory Audit & Production Cutover Configuration."""

from pathlib import Path
from backend.core.config import Settings, settings


def test_mock_inventory_document_exists():
    """Verifies that the mock inventory documentation exists and contains all required sections."""
    doc_path = Path("docs/MOCK_INVENTORY.md")
    assert doc_path.exists(), "docs/MOCK_INVENTORY.md must exist in repository root"
    content = doc_path.read_text(encoding="utf-8")
    assert "HR 员工信息查询" in content
    assert "ERP 物料库存查询" in content
    assert "ERP 采购订单创建" in content
    assert "OA 故障工单流转" in content
    assert "企业微信 Bot 通知" in content
    assert "n8n / Dify 事件联动" in content
    assert "E2E 演示数据库" in content
    assert "冷启动知识库文档" in content
    assert "LLM 网关与降级" in content
    assert "USE_MOCK_SYSTEMS" in content


def test_default_development_settings():
    """Verifies default settings in development mode."""
    assert settings.ENVIRONMENT == "development"
    assert settings.USE_MOCK_SYSTEMS is True
    assert settings.PROJECT_NAME == "Enterprise AI Digital Assistant"


def test_production_settings_override():
    """Verifies that settings properly load production environment switches and URLs."""
    prod_env = {
        "ENVIRONMENT": "production",
        "USE_MOCK_SYSTEMS": "false",
        "HR_BASE_URL": "https://hr.enterprise.internal/api/v1",
        "HR_API_TOKEN": "token_hr_123",
        "ERP_BASE_URL": "https://erp.enterprise.internal/api/v1",
        "ERP_API_TOKEN": "token_erp_456",
        "OA_BASE_URL": "https://oa.enterprise.internal/api/v1",
        "OA_API_TOKEN": "token_oa_789",
        "WECOM_WEBHOOK_URL": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=prod-key",
        "DIFY_API_BASE": "https://dify.enterprise.internal/v1",
        "DIFY_API_KEY": "app-prod-key",
        "N8N_WEBHOOK_URL": "https://n8n.enterprise.internal/webhook/prod-approval",
    }
    prod_settings = Settings(**prod_env)
    assert prod_settings.ENVIRONMENT == "production"
    assert prod_settings.USE_MOCK_SYSTEMS is False
    assert prod_settings.HR_BASE_URL == "https://hr.enterprise.internal/api/v1"
    assert prod_settings.HR_API_TOKEN == "token_hr_123"
    assert prod_settings.ERP_BASE_URL == "https://erp.enterprise.internal/api/v1"
    assert prod_settings.ERP_API_TOKEN == "token_erp_456"
    assert prod_settings.OA_BASE_URL == "https://oa.enterprise.internal/api/v1"
    assert prod_settings.OA_API_TOKEN == "token_oa_789"
    assert prod_settings.WECOM_WEBHOOK_URL == "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=prod-key"
    assert prod_settings.DIFY_API_BASE == "https://dify.enterprise.internal/v1"
    assert prod_settings.DIFY_API_KEY == "app-prod-key"
    assert prod_settings.N8N_WEBHOOK_URL == "https://n8n.enterprise.internal/webhook/prod-approval"
