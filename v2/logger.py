"""
SOW Generator v2 — Structured Generation Logger
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from config import LOGS_DIR


class GenerationLogger:
    """Logs every generation run with full metadata."""

    def __init__(self, opportunity_name="unknown", pm="unknown", trigger="skill"):
        self.run_id = f"sow_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{opportunity_name.replace(' ', '_')[:20]}"
        self.start_time = time.time()
        self.log = {
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger": trigger,
            "pm": pm,
            "opportunity": {},
            "pipeline": {
                "stage_1_input": {},
                "stage_2_context": {},
                "stage_3_requirements": {},
                "stage_4_generation": {"sections": [], "total_tokens": 0, "total_cost_usd": 0.0},
                "stage_5_validation": {},
                "stage_6_output": {},
            },
            "regenerations": [],
            "final_quality_score": 0,
            "pm_feedback": None,
        }

    def log_stage(self, stage_name, data):
        if stage_name in self.log["pipeline"]:
            self.log["pipeline"][stage_name].update(data)

    def log_section(self, section_id, model, tokens_in, tokens_out, duration_ms, status="ok", error=None):
        entry = {
            "id": section_id,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "duration_ms": duration_ms,
            "status": status,
        }
        if error:
            entry["error"] = str(error)
        self.log["pipeline"]["stage_4_generation"]["sections"].append(entry)
        self.log["pipeline"]["stage_4_generation"]["total_tokens"] += tokens_in + tokens_out

    def log_regeneration(self, section_id, reason):
        self.log["regenerations"].append({
            "section_id": section_id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def set_quality_score(self, score):
        self.log["final_quality_score"] = score

    def set_opportunity(self, opp_data):
        self.log["opportunity"] = {
            "id": opp_data.get("Id", ""),
            "name": opp_data.get("Name", ""),
            "account": opp_data.get("Account", {}).get("Name", "") if isinstance(opp_data.get("Account"), dict) else "",
        }

    def estimate_cost(self):
        """Estimate generation cost based on token usage (Claude pricing)."""
        total = 0.0
        for s in self.log["pipeline"]["stage_4_generation"]["sections"]:
            model = s.get("model") or ""
            if model in ("fast", "sonnet") or "sonnet" in model:
                # Claude Sonnet: $3/M in, $15/M out
                total += s.get("tokens_in", 0) * 3.0 / 1_000_000
                total += s.get("tokens_out", 0) * 15.0 / 1_000_000
            elif model in ("strong", "opus") or "opus" in model:
                # Claude Opus: $15/M in, $75/M out
                total += s.get("tokens_in", 0) * 15.0 / 1_000_000
                total += s.get("tokens_out", 0) * 75.0 / 1_000_000
            # template sections have model=None, cost=0
        self.log["pipeline"]["stage_4_generation"]["total_cost_usd"] = round(total, 4)
        return total

    def save(self):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        path = LOGS_DIR / f"{self.run_id}.json"
        self.log["total_duration_ms"] = int((time.time() - self.start_time) * 1000)
        self.estimate_cost()
        with open(path, "w") as f:
            json.dump(self.log, f, indent=2, default=str)
        return str(path)
