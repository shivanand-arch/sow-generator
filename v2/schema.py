"""
SOW Generator v2 — RequirementsSpec Schema & Module Matcher
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from config import MODULE_CATALOG_PATH


# ============================================================
# RequirementsSpec — the central data structure
# ============================================================

@dataclass
class CustomerInfo:
    name: str = ""
    industry: str = ""
    country: str = ""
    region: str = ""
    project_id: str = ""
    deal_value: str = ""
    mrr: str = ""

@dataclass
class DeploymentInfo:
    type: str = "cloud"  # cloud | on-premise | hybrid | emerge
    infrastructure: str = ""
    platform: str = "ECC"
    sip_integration: str = ""

@dataclass
class LicenseComponent:
    component: str = ""
    count: int = 0
    type: str = ""
    retention_days: int = 0

@dataclass
class IvrMenu:
    did: str = ""
    levels: int = 1
    options: list = field(default_factory=list)
    sub_menus: list = field(default_factory=list)

@dataclass
class IvrSpec:
    complexity: str = "medium"  # low | medium | high | custom
    inbound_dids: list = field(default_factory=list)
    languages: list = field(default_factory=lambda: ["English"])
    menus: list = field(default_factory=list)
    csat: bool = False
    callback: bool = False
    vip_routing: bool = False
    custom_description: str = ""

@dataclass
class IntegrationSpec:
    type: str = ""
    system: str = ""
    direction: str = "bidirectional"
    features: list = field(default_factory=list)

@dataclass
class SimilarSow:
    doc_id: str = ""
    customer: str = ""
    industry: str = ""
    score: float = 0.0
    modules: list = field(default_factory=list)
    text_excerpt: str = ""  # relevant section text for few-shot

@dataclass
class RequirementsSpec:
    customer: CustomerInfo = field(default_factory=CustomerInfo)
    deployment: DeploymentInfo = field(default_factory=DeploymentInfo)
    licenses: list = field(default_factory=list)  # List[LicenseComponent]
    modules: dict = field(default_factory=dict)  # {"ivr": ["IVR-001"], "integration": [...], ...}
    ivr_spec: IvrSpec = field(default_factory=IvrSpec)
    integrations: list = field(default_factory=list)  # List[IntegrationSpec]
    similar_sows: list = field(default_factory=list)  # List[SimilarSow]
    use_case_type: str = "Inbound Voice"
    additional_requirements: str = ""
    sf_opportunity: dict = field(default_factory=dict)  # Raw SF data for reference

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_dict(cls, data):
        spec = cls()
        if "customer" in data:
            spec.customer = CustomerInfo(**{k: v for k, v in data["customer"].items() if k in CustomerInfo.__dataclass_fields__})
        if "deployment" in data:
            spec.deployment = DeploymentInfo(**{k: v for k, v in data["deployment"].items() if k in DeploymentInfo.__dataclass_fields__})
        if "licenses" in data:
            spec.licenses = [LicenseComponent(**lc) if isinstance(lc, dict) else lc for lc in data["licenses"]]
        if "modules" in data:
            spec.modules = data["modules"]
        if "ivr_spec" in data:
            spec.ivr_spec = IvrSpec(**{k: v for k, v in data["ivr_spec"].items() if k in IvrSpec.__dataclass_fields__})
        if "integrations" in data:
            spec.integrations = [IntegrationSpec(**ig) if isinstance(ig, dict) else ig for ig in data["integrations"]]
        if "similar_sows" in data:
            spec.similar_sows = [SimilarSow(**ss) if isinstance(ss, dict) else ss for ss in data["similar_sows"]]
        for key in ("use_case_type", "additional_requirements"):
            if key in data:
                setattr(spec, key, data[key])
        if "sf_opportunity" in data:
            spec.sf_opportunity = data["sf_opportunity"]
        return spec


# ============================================================
# Module Catalog & Matcher
# ============================================================

class ModuleCatalog:
    """Loads and queries the 152-module ECC catalog."""

    def __init__(self, catalog_path=None):
        path = Path(catalog_path) if catalog_path else MODULE_CATALOG_PATH
        with open(path) as f:
            self.catalog = json.load(f)
        self._flat = {}
        for top_category, modules in self.catalog.items():
            for mod_id, mod_info in modules.items():
                info = mod_info if isinstance(mod_info, dict) else {"name": mod_info}
                self._flat[mod_id] = {
                    "id": mod_id,
                    "top_category": top_category,  # IVR, Integration, Blaster, Queue, Data
                    "sub_category": info.get("category", ""),
                    **info,
                }

    def get_module(self, module_id):
        return self._flat.get(module_id)

    def get_category(self, category):
        return self.catalog.get(category, {})

    def all_module_ids(self):
        return list(self._flat.keys())

    def match_from_products(self, products_text, description_text=""):
        """Match SF Products__c and Description to module IDs."""
        text = f"{products_text} {description_text}".lower()
        matched = {}

        # Keyword → module category/ID mapping rules
        rules = [
            # IVR
            (["ivr", "interactive voice"], ["IVR-001", "IVR-003", "IVR-029", "IVR-030", "IVR-031"]),
            (["language selection", "multi-language", "bilingual"], ["IVR-002"]),
            (["dtmf", "keypad"], ["IVR-007"]),
            (["csat", "satisfaction"], ["IVR-018"]),
            (["nps", "net promoter"], ["IVR-017"]),
            (["callback", "call back"], ["IVR-023"]),
            (["time-based routing", "business hours", "after hours"], ["IVR-029", "IVR-005"]),
            (["otp", "one time"], ["IVR-011"]),
            (["pin verification", "pin"], ["IVR-010"]),
            (["speech recognition", "voice input"], ["IVR-008"]),
            (["self-service", "balance inquiry"], ["IVR-019"]),
            (["order status", "ticket status"], ["IVR-020"]),
            (["vip", "priority caller", "whitelist"], ["IVR-013"]),
            (["blacklist", "block"], ["IVR-012"]),
            (["consent"], ["IVR-015"]),
            (["recording announcement"], ["IVR-014"]),
            (["multi-level", "nested menu", "sub menu"], ["IVR-028", "IVR-004"]),
            (["emergency bypass"], ["IVR-033"]),
            (["skill-based menu"], ["IVR-034"]),
            (["geographic routing"], ["IVR-035"]),
            (["tts", "text-to-speech"], ["IVR-026"]),

            # Integration
            (["salesforce", "sfdc"], ["INT-004"]),
            (["freshdesk"], ["INT-005"]),
            (["zendesk"], ["INT-006"]),
            (["zoho"], ["INT-007"]),
            (["hubspot"], ["INT-008"]),
            (["leadsquared"], ["INT-009"]),
            (["custom crm", "url-based crm", "proprietary crm"], ["INT-010"]),
            (["rest api"], ["INT-001"]),
            (["webhook"], ["INT-002"]),
            (["soap"], ["INT-003"]),
            (["screen pop"], ["INT-021"]),
            (["click to dial", "click-to-dial", "c2d"], ["INT-022"]),
            (["post-call", "post call data push"], ["INT-023"]),
            (["database lookup", "db lookup"], ["INT-011"]),
            (["sms gateway"], ["INT-014"]),
            (["whatsapp"], ["INT-015"]),
            (["payment gateway"], ["INT-013"]),
            (["crm", "integration"], ["INT-001", "INT-002"]),

            # Blaster
            (["blaster", "outbound campaign", "auto dialer"], ["BLA-002", "BLA-003"]),
            (["click to dial", "click-to-dial"], ["BLA-007"]),
            (["progressive dialer"], ["BLA-010"]),
            (["predictive dialer"], ["BLA-011"]),
            (["collections"], ["BLA-004"]),
            (["retry logic"], ["BLA-018"]),

            # Queue
            (["queue", "acd"], ["QUE-001"]),
            (["skill-based routing", "skill based"], ["QUE-002"]),
            (["priority routing", "priority queue"], ["QUE-003"]),
            (["overflow", "failover"], ["QUE-005"]),
            (["sticky agent"], ["QUE-006"]),
            (["queue callback"], ["QUE-007"]),

            # Data/Reporting
            (["reporting", "reports", "analytics"], ["DAT-001"]),
            (["cdr", "call detail"], ["DAT-002"]),
            (["dashboard"], ["DAT-003"]),
            (["voice logger", "call recording"], ["DAT-007"]),
            (["custom report"], ["DAT-009"]),
            (["wallboard"], ["DAT-005"]),
            (["cqa", "quality assurance", "quality audit"], ["DAT-010"]),
        ]

        for keywords, module_ids in rules:
            if any(kw in text for kw in keywords):
                for mid in module_ids:
                    mod = self.get_module(mid)
                    if mod:
                        cat = mod["top_category"]  # Use top-level: IVR, Integration, etc.
                        if cat not in matched:
                            matched[cat] = []
                        if mid not in matched[cat]:
                            matched[cat].append(mid)

        return matched

    def get_modules_detail(self, module_ids_by_category):
        """Get full module details for a set of module IDs grouped by category."""
        details = {}
        for category, ids in module_ids_by_category.items():
            details[category] = []
            for mid in ids:
                mod = self.get_module(mid)
                if mod:
                    details[category].append(mod)
        return details
