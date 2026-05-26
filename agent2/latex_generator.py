from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

import sys

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from shared_config import CONFIRMATION_THRESHOLD as _DEFAULT_CONFIDENCE
except Exception:
    _DEFAULT_CONFIDENCE = 0.85

try:
    from shared_config import AGENT2_LLM_PROVIDER, AGENT1_LLM_PROVIDER
except Exception:
    AGENT2_LLM_PROVIDER = "none"
    AGENT1_LLM_PROVIDER = "none"


class LaTeXEscaper:
    @staticmethod
    def escape(s: Optional[str]) -> str:
        if not s:
            return ""
        s = str(s)
        s = s.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
        s = re.sub(r" {2,}", " ", s).strip()
        s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
        s = re.sub(r"[^\x00-\x7F\u00C0-\u024F]", "", s)
        replacements = {
            "\\": "\\textbackslash{}",
            "&": "\\&",
            "%": "\\%",
            "$": "\\$",
            "_": "\\_",
            "{": "\\{",
            "}": "\\}",
            "~": "\\textasciitilde{}",
            "^": "\\textasciicircum{}",
            "->": "$\\rightarrow$",
            "<": "\\textless{}",
            ">": "\\textgreater{}",
            "#": "\\#",
            "[": "{[}",
            "]": "{]}",
            "|": "\\textbar{}",
        }
        for k, v in replacements.items():
            s = s.replace(k, v)
        return s


class BaseReportGenerator(ABC):
    def __init__(self):
        self.escaper = LaTeXEscaper()

    @abstractmethod
    def generate(self, report: dict, analysis: dict, timestamp: str) -> str:
        pass

    def _escape(self, text: Optional[str]) -> str:
        return self.escaper.escape(text)

    def _get_timestamp_ms(self, alert: dict) -> int:
        ts = alert.get("Timestamp_ms") or alert.get("timestamp_ms") or 0
        if not ts:
            ts_str = alert.get("Timestamp", alert.get("timestamp", ""))
            try:
                ts = int(
                    datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
                    * 1000
                )
            except Exception:
                ts = 0
        return ts

    def _build_list_items(self, items: List[str], default: Optional[str] = None) -> str:
        if not items:
            return f"  \\item {default or 'N/A'}"
        return "\n".join(f"  \\item {self._escape(item)}" for item in items)

    def _get_metadata_value(self, metadata: dict, *keys: str) -> str:
        for key in keys:
            value = metadata.get(key)
            if value is not None and value != "":
                return str(value)
        return ""

    def _hhmm(self, ms) -> str:
        if not ms:
            return "---"
        try:
            from datetime import timezone

            return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%H:%M")
        except Exception:
            return "---"

    def _clean_label(self, label: str) -> str:
        if not label:
            return ""
        if "  " in label:
            return label.split("  ", 1)[1].strip()
        if re.match(r"^[A-Z_]+\s+[A-Z]", label):
            parts = label.split(" ", 1)
            if "_" in parts[0] and len(parts) > 1:
                return parts[1].strip()
        return label

    def _get_confidence(self, report: dict, metadata: dict) -> str:
        _decision = report.get("decision", {})
        _sel = _decision.get("selected_hypothesis", {})
        prob = _sel.get("probability") if isinstance(_sel, dict) else None
        if prob is None:
            prob = metadata.get("primary_probability") or _DEFAULT_CONFIDENCE
        return f"{int(float(prob) * 100)}\\%"

    def _get_short_category(self, full_name: str) -> str:
        mapping = {
            "Ransomware": "Ransomware",
            "Data Exfiltration": "Exfiltration",
            "Advanced Persistent Threats": "APT",
            "Credential": "Credential",
            "Destructive": "Destructive",
            "Supply Chain": "Supply Chain",
            "DDoS": "DDoS",
            "Phishing": "Phishing",
            "Vulnerability": "Exploit",
            "Insider": "Insider",
            "Compliance": "Compliance",
            "Reconnaissance": "Recon",
            "Cryptojacking": "Cryptojacking",
            "Malware": "Malware Infra",
            "Others": "Others",
        }
        for key, badge in mapping.items():
            if key in full_name:
                return badge
        return full_name[:25]

    def _build_regulatory_rows(self, regulatory: dict) -> str:
        rows = []
        for key, value in regulatory.items():
            rows.append(
                f"  \\textbf{{{self._escape(key.upper())}}} & "
                f"{self._escape(str(value))} \\\\"
            )
        return "\n".join(rows) if rows else "  None & No regulatory impact \\\\"

    def _tier_cell(self, tier_str: str) -> str:
        return "\\mbox{" + self._escape(str(tier_str)) + "}"


# =============================================================================
# CISO REPORT GENERATOR
# =============================================================================


class CISOReportGenerator(BaseReportGenerator):
    def _analyst_block(self, text: str) -> str:
        """Fluent paragraph — Analyst Executive Assessment."""
        if not text:
            return ""
        return (
            "\\vspace{0.5ex}\n"
            "\\noindent \\textbf{Analyst Executive Assessment:} "
            "\\par\\smallskip\n"
            f"{self._escape(text)}\n"
            "\\vspace{0.8ex}\n\n"
        )

    def _criticality_block(self, bc: dict) -> str:
        """Business Criticality — Affected Services / Operational Risk / Blast Radius."""
        if not bc:
            return ""
        lines = []
        if bc.get("affected_services"):
            lines.append(
                f"\\noindent \\textbf{{Affected Services:}} "
                f"{self._escape(bc['affected_services'])}\n"
                "\\vspace{0.3ex}\n\n"
            )
        if bc.get("operational_risk"):
            lines.append(
                f"\\noindent \\textbf{{Operational Risk:}} "
                f"{self._escape(bc['operational_risk'])}\n"
                "\\vspace{0.3ex}\n\n"
            )
        if bc.get("blast_radius"):
            lines.append(
                f"\\noindent \\textbf{{Blast Radius:}} "
                f"{self._escape(bc['blast_radius'])}\n"
                "\\vspace{0.3ex}\n\n"
            )
        if not lines:
            return ""
        return "\\vspace{0.5ex}\n" + "".join(lines) + "\\vspace{0.3ex}\n"

    def generate(self, report: dict, analysis: dict, timestamp: str) -> str:
        metadata = report.get("metadata", {})
        ciso = report.get("ciso_report", {})

        # Window
        win_hhmm_start = self._hhmm(
            metadata.get("window_start_ms") or analysis.get("window_start_ms") or 0
        )
        win_hhmm_end = self._hhmm(
            metadata.get("window_end_ms") or analysis.get("window_end_ms") or 0
        )

        # Tier / Confidence
        tier = self._escape(
            analysis.get("top_risk_tier") or ciso.get("top_risk_tier", "HIGH")
        )
        confidence = self._get_confidence(report, metadata)

        # Raw label (unescaped) for fallback strings
        _raw_label = self._clean_label(
            analysis.get("attack_pattern", "")
            or report.get("label", "")
            or metadata.get("selected_hypothesis", "")
        )
        attack_pattern = self._escape(_raw_label) if _raw_label else "---"

        # Vector
        _phases = analysis.get("phases", [])
        initial_vector = self._escape(" -> ".join(_phases)) if _phases else "---"

        # LLM info
        _llm_used = metadata.get("llm_used", False)
        _model = str(metadata.get("model_used", "rule-based")).strip()
        llm_info = self._escape(f"{'Yes' if _llm_used else 'No'} ({_model})")

        risk_exp = self._escape(analysis.get("risk_explanation", "") or tier)

        # Executive Summary — mandatory
        exec_summary = self._escape(
            report.get("executive_summary", "") or ciso.get("executive_summary", "")
        )
        if not exec_summary:
            _what = self._escape(ciso.get("what_was_detected", ""))
            _why = self._escape(ciso.get("why_it_matters", ""))
            exec_summary = " ".join(filter(None, [_what, _why]))
        if not exec_summary:
            exec_summary = self._escape(
                f"{_raw_label} -- {tier} risk incident confirmed."
            )

        # Narrative fields
        business_impact = self._escape(
            ciso.get("business_impact", "")
            or "Critical operational risk affecting organizational assets."
        )

        why_it_matters = self._escape(ciso.get("why_it_matters", ""))
        if not why_it_matters:
            _n_phases = len(_phases)
            _phase_text = (
                f"{_n_phases} kill chain phase{'s' if _n_phases != 1 else ''} detected."
                if _n_phases > 0
                else "Kill chain phases pending analysis."
            )
            why_it_matters = self._escape(
                f"A {tier}-tier {_raw_label} poses immediate risk to business "
                f"operations and may trigger regulatory notification obligations. "
                f"{_phase_text}"
            )

        what_was_detected = self._escape(ciso.get("what_was_detected", ""))
        if not what_was_detected:
            _n = analysis.get("total_alerts", 0)
            _n_text = (
                f"{_n} security event{'s' if _n != 1 else ''}"
                if _n > 0
                else "Security events"
            )
            what_was_detected = self._escape(
                f"{_n_text} consistent with {_raw_label} behaviour "
                f"were observed in the monitoring window."
            )

        key_message = self._escape(ciso.get("key_message", ""))
        if not key_message:
            key_message = self._escape(
                f"{_raw_label} -- {tier} risk confirmed. "
                f"Immediate action required as per recommendations below."
            )

        # New blocks (Phases 1 & 2)
        _analyst = self._analyst_block(ciso.get("analyst_assessment", ""))
        _criticality = self._criticality_block(ciso.get("business_criticality", {}))

        # Immediate actions (from LLM containment_steps)
        immediate = (
            analysis.get("containment_steps")
            or report.get("soc_report", {}).get("containment_steps")
            or []
        )
        actions_block = ""
        if immediate:
            items = "\n".join(f"   \\item {self._escape(a)}" for a in immediate)
            actions_block = (
                "\\noindent \\textbf{Immediate Response Actions:}\n"
                "\\begin{itemize}\n" + items + "\n\\end{itemize}\n"
                "\\vspace{1ex}\n"
            )

        # Tables
        tl_rows = self._build_timeline_rows(analysis.get("timeline", []))
        cat_rows = self._build_category_rows(
            ciso.get("top_categories", analysis.get("top_categories", []))
        )
        recs_items = self._build_list_items(
            ciso.get("strategic_recommendations")
            or analysis.get("strategic_recommendations")
            or report.get("recommended_actions")
            or [],
            "See CISO recommendations.",
        )
        reg_rows = self._build_regulatory_rows(
            report.get("regulatory_impact", analysis.get("regulatory_impact", {}))
        )
        scope = self._build_scope_section(report, analysis)

        return (
            "\\documentclass[10pt,a4paper]{article}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage[T1]{fontenc}\n"
            "\\usepackage{geometry}\n"
            "\\usepackage{booktabs}\n"
            "\\usepackage{longtable}\n"
            "\\usepackage{array}\n"
            "\\usepackage{hyperref}\n"
            "\\usepackage{titlesec}\n"
            "\\usepackage{enumitem}\n"
            "\\geometry{margin=1.5cm,top=1.5cm,bottom=1.5cm,left=1.5cm,right=1.5cm}\n"
            "\\setlength{\\parskip}{0.3ex}\n"
            "\\setlength{\\parindent}{0pt}\n"
            "\\titlespacing*{\\section}{0pt}{0.5ex}{0.2ex}\n"
            "\\setlist{nosep,leftmargin=*}\n"
            "\\renewcommand{\\arraystretch}{1.1}\n"
            "\\pagestyle{empty}\n"
            "\\begin{document}\n"
            # Header
            "\\noindent\n"
            "\\begin{tabular}{@{}p{0.7\\linewidth} "
            ">{\\raggedleft\\arraybackslash}p{0.3\\linewidth}@{}}\n"
            f"  \\textbf{{\\Large CISO INCIDENT REPORT}} & "
            f"\\textbf{{Risk Tier: {tier}}} \\\\\n"
            "\\end{tabular}\n"
            "\\hrule\n\\vspace{1ex}\n"
            # Executive Summary
            f"\\noindent \\textbf{{Executive Summary:}} {exec_summary}\n"
            "\\vspace{1ex}\n"
            "\\hrule\n\\vspace{1ex}\n"
            # Status table
            "\\noindent\n"
            "\\begin{tabular}{@{}p{3.2cm} p{10.8cm}@{}}\n"
            f"  \\textbf{{Status:}}       & CONFIRMED"
            f" \\hfill \\textbf{{Confidence:}} {confidence} \\\\\n"
            f"  \\textbf{{Pattern:}}      & {attack_pattern} \\\\\n"
            f"  \\textbf{{Vector:}}       & {initial_vector} \\\\\n"
            f"  \\textbf{{Risk:}}         & {risk_exp} \\\\\n"
            f"  \\textbf{{LLM Enhanced:}} & {llm_info} \\\\\n"
            "\\end{tabular}\n"
            "\\vspace{1ex}\n\\hrule\n\\vspace{1ex}\n"
            # Narrative
            f"\\noindent \\textbf{{Business Impact:}} {business_impact}\n"
            "\\par\\vspace{0.8ex}\n"
            # Phase 1: Analyst Executive Assessment
            f"{_analyst}"
            # Phase 2: Business Criticality
            f"{_criticality}"
            f"\\noindent \\textbf{{Why It Matters:}} {why_it_matters}\n"
            "\\vspace{0.8ex}\n\n"
            f"\\noindent \\textbf{{What Was Detected:}} {what_was_detected}\n"
            "\\vspace{0.8ex}\n\n"
            f"{actions_block}"
            f"\\noindent \\underline{{\\textbf{{Key Message:}}}} {key_message}\n"
            "\\vspace{1.5ex}\n\n"
            # Window
            f"\\noindent \\textbf{{Window:}} {win_hhmm_start} -- {win_hhmm_end}\n\n"
            # Top Risk Categories
            "\\noindent \\textbf{Top Risk Categories:}\n"
            "\\begin{tabular}{@{}p{2.8cm} @{\\hspace{4pt}} p{7cm}"
            " @{\\hspace{4pt}} r@{}}\n"
            f"{cat_rows}\n"
            "\\end{tabular}\n"
            "\\vspace{0.5ex}\n\\hrule width 0.25\\textwidth\n\\vspace{1ex}\n"
            # Trigger Timeline (4 cols — CISO)
            "\\noindent \\textbf{Trigger Timeline:}\n\n"
            "{\\footnotesize\n"
            "\\begin{tabular}{@{}p{3.5cm} @{\\hspace{3pt}} p{1.5cm}"
            " @{\\hspace{3pt}} p{5.0cm} @{\\hspace{3pt}} p{2.0cm}@{}}\n"
            "\\toprule Timestamp & Alert ID & Category & Tier \\\\ \\midrule\n"
            f"{tl_rows}\n"
            "\\bottomrule\n\\end{tabular}}\n"
            "\\vspace{0.5ex}\n\\hrule width 0.25\\textwidth\n\\vspace{1ex}\n"
            # Strategic Recommendations
            "\\noindent \\textbf{Strategic Recommendations:}\n"
            "\\begin{itemize}\n"
            f"{recs_items}\n"
            "\\end{itemize}\n"
            "\\hrule\n\\vspace{1ex}\n"
            # Regulatory Impact
            "\\noindent \\textbf{Regulatory Impact:}\n\n"
            "\\begin{tabular}{@{}p{1.5cm} @{\\hspace{4pt}} p{12.5cm}@{}}\n"
            f"{reg_rows}\n"
            "\\end{tabular}\n"
            "\\vspace{1ex}\n\\hrule\n"
            f"{scope}\n"
            f"\\noindent \\textit{{Generated: {self._escape(timestamp)}}}\n"
            "\\end{document}\n"
        )

    def _build_timeline_rows(self, alerts: list) -> str:
        if not alerts:
            return r"No alerts recorded. & & & \\ \hline"
        rows = []
        for alert in sorted(alerts, key=lambda x: self._get_timestamp_ms(x)):
            ts = self._escape(alert.get("timestamp", alert.get("Timestamp", "---")))
            aid = self._escape(alert.get("id", alert.get("Alert ID", "---")))
            cat = self._escape(alert.get("category", alert.get("Category", "---")))
            tier = self._tier_cell(alert.get("tier", alert.get("Tier", "---")))
            rows.append(f"  {ts} & {aid} & {cat} & {tier} \\\\")
        return "\n".join(rows)

    def _build_category_rows(self, categories) -> str:
        if not categories:
            return "  --- & --- & --- \\\\"
        rows = []
        for entry in categories:
            if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                raw_label = str(entry[0])
                prob = entry[1]
            else:
                raw_label = str(entry)
                prob = 0.0
            # Protect double-space separator before escaping
            protected = raw_label.replace("  ", "\x00")
            if "\x00" in protected:
                parts = protected.split("\x00", 1)
                shortcode = self._escape(parts[0].strip())
                name = self._escape(parts[1].strip())
            else:
                shortcode = self._escape(self._get_short_category(raw_label))
                name = self._escape(self._clean_label(raw_label))
            prob_str = f"{float(prob):.2f}" if prob else "---"
            rows.append(f"  {shortcode} & {name} & {prob_str} \\\\[0.3ex]")
        return "\n".join(rows)

    def _build_scope_section(self, report: dict, analysis: dict = {}) -> str:
        meta = report.get("metadata", {})
        lines = []
        total = (
            meta.get("alert_count")
            or meta.get("total_alerts")
            or analysis.get("total_alerts", "")
        )
        if total:
            lines.append(f"  Total alerts & {total} \\\\")
        win_id = meta.get("window_id", "")
        if win_id:
            lines.append(f"  Window ID & {self._escape(str(win_id))} \\\\")
        if not lines:
            return ""
        return (
            "\\section*{Scope}\n"
            "\\begin{tabular}{ll}\n"
            + "\n".join(lines)
            + "\n\\end{tabular}\n\\vspace{1ex}\n"
        )


# =============================================================================
# SOC REPORT GENERATOR
# =============================================================================


class SOCReportGenerator(BaseReportGenerator):
    def _phased_response_block(self, pa: dict, fallback: list) -> str:
        """Phase 3: Priority Actions (0-1h / 1-4h / 4-24h)."""
        if pa:
            blocks = ""
            phases = [
                ("immediate_0_1h", "Priority Actions (0--1h):"),
                ("short_term_1_4h", "Priority Actions (1--4h):"),
                ("sustained_4_24h", "Priority Actions (4--24h):"),
            ]
            for key, label in phases:
                items = pa.get(key, [])
                if items:
                    rows = "\n".join(f"  \\item {self._escape(i)}" for i in items)
                    blocks += (
                        f"\\noindent \\textbf{{{label}}}\n"
                        f"\\begin{{itemize}}\n{rows}\n\\end{{itemize}}\n"
                        "\\vspace{0.3ex}\n"
                    )
            if blocks:
                return blocks
        # Fallback: flat containment list
        return (
            "\\noindent \\textbf{Containment Steps:}\n"
            "\\begin{itemize}\n"
            + self._build_list_items(fallback, "See SOC incident response playbook.")
            + "\n\\end{itemize}\n"
            "\\vspace{0.5ex}\n"
        )

    def generate(self, report: dict, analysis: dict, timestamp: str) -> str:
        metadata = report.get("metadata", {})
        ciso = report.get("ciso_report", {})
        soc = report.get("soc_report", {})

        # Window
        win_hhmm_start = self._hhmm(
            metadata.get("window_start_ms") or analysis.get("window_start_ms") or 0
        )
        win_hhmm_end = self._hhmm(
            metadata.get("window_end_ms") or analysis.get("window_end_ms") or 0
        )

        # Tier / Confidence
        tier = self._escape(
            analysis.get("top_risk_tier") or ciso.get("top_risk_tier", "HIGH")
        )
        confidence = self._get_confidence(report, metadata)

        # Label
        _raw_label = self._clean_label(
            analysis.get("label", "")
            or analysis.get("attack_pattern", "")
            or report.get("label", "")
            or metadata.get("selected_hypothesis", "")
        )
        label_esc = self._escape(_raw_label) if _raw_label else "Security Incident"

        # Technical summary
        _phases = analysis.get("phases", [])
        _phases_arrow = " $\\rightarrow$ ".join(_phases)
        tech_raw = analysis.get("technical_summary", "") or report.get(
            "executive_summary", ""
        )
        if not tech_raw or "Unclassified" in tech_raw:
            technical_summary = (
                f"{label_esc} confirmed with {confidence} confidence."
                + (f" Full kill chain: {_phases_arrow}." if _phases else "")
            )
        else:
            technical_summary = self._escape(tech_raw)

        # Threat classification
        _threat_raw = (
            analysis.get("threat_classification")
            or soc.get("threat_classification")
            or ""
        )
        if _threat_raw:
            _tc_esc = self._escape(_threat_raw)
            threat_class_line = (
                f"\\noindent \\textbf{{Threat Classification (LLM):}} {_tc_esc}\n"
                "\\vspace{0.8ex}\n\n"
            )
        else:
            threat_class_line = ""
        # Counts
        total_alerts = (
            analysis.get("total_alerts")
            or soc.get("total_alerts")
            or len(analysis.get("timeline", []))
        )
        triggers = len(report.get("confirmed_hypotheses", [report.get("label", "?")]))
        _llm_used = metadata.get("llm_used", False)
        _model = str(metadata.get("model_used", "rule-based"))
        llm_enhanced = self._escape(f"{'Yes' if _llm_used else 'No'} ({_model})")

        # Severity
        sev_data = (
            analysis.get("severity_breakdown") or report.get("severity_breakdown") or {}
        )
        sev_rows = self._build_severity_rows(sev_data)

        # Timeline
        soc_timeline = analysis.get("detailed_timeline") or analysis.get("timeline", [])
        tl_rows = self._build_timeline_rows(soc_timeline)

        # IoCs / Assets / CVEs
        ioc_list = analysis.get("iocs") or soc.get("ioc_bundle", {}).get(
            "ipv4_addresses", []
        ) + soc.get("ioc_bundle", {}).get("fqdns", []) + soc.get("ioc_bundle", {}).get(
            "executables", []
        )
        asset_list = analysis.get("affected_assets") or soc.get("affected_assets", [])
        cve_list = analysis.get("detected_cves") or soc.get("ioc_bundle", {}).get(
            "cve_ids", []
        )

        ioc_items = self._build_list_items(
            ioc_list, "No external IoCs extracted from this window."
        )
        asset_items = self._build_list_items(
            asset_list, "No affected assets extracted from this window."
        )
        cve_items = self._build_list_items(
            cve_list, "No CVEs referenced in this window."
        )

        # Phase 3: Phased response
        containment = (
            analysis.get("containment_steps") or soc.get("containment_steps") or []
        )
        pa = analysis.get("priority_actions") or soc.get("priority_actions") or {}
        phased_block = self._phased_response_block(pa, containment)

        # SIEM Queries
        queries = (
            analysis.get("investigation_queries")
            or soc.get("investigation_queries")
            or []
        )
        query_block = ""
        if queries:
            query_block = (
                "\\noindent \\textbf{SIEM/EDR Threat Hunting Queries:}\n"
                "\\vspace{0.5ex}\n"
                "\\begin{itemize}\n"
            )
            for q in queries:
                query_block += (
                    f"  \\item {{\\small\\parbox{{\\linewidth}}"
                    f"{{\\raggedright\\ttfamily {self._escape(q)}}}}}\n"
                )
            query_block += "\\end{itemize}\n\\vspace{0.8ex}\n"
        # Recommendations
        soc_recs = self._build_list_items(
            analysis.get("soc_recommendations", []),
            "See SOC incident response playbook.",
        )
        rec_actions = self._build_list_items(
            report.get("recommended_actions", []), "Activate incident response plan."
        )

        attack_vector = self._escape(" -> ".join(_phases)) if _phases else "---"

        return (
            "\\documentclass[10pt,a4paper]{article}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage[T1]{fontenc}\n"
            "\\usepackage{geometry}\n"
            "\\usepackage{booktabs}\n"
            "\\usepackage{longtable}\n"
            "\\usepackage{array}\n"
            "\\usepackage{hyperref}\n"
            "\\usepackage{titlesec}\n"
            "\\usepackage{enumitem}\n"
            "\\geometry{margin=1.5cm,top=1.5cm,bottom=1.5cm,left=1.5cm,right=1.5cm}\n"
            "\\setlength{\\parskip}{0.3ex}\n"
            "\\setlength{\\parindent}{0pt}\n"
            "\\titlespacing*{\\section}{0pt}{0.5ex}{0.2ex}\n"
            "\\setlist{nosep,leftmargin=*}\n"
            "\\renewcommand{\\arraystretch}{1.1}\n"
            "\\pagestyle{empty}\n"
            "\\begin{document}\n"
            # Header
            "\\noindent\n"
            "\\begin{tabular}{@{}p{0.6\\linewidth} p{0.4\\linewidth}@{}}\n"
            f"  \\textbf{{\\Large SOC INCIDENT REPORT}} &"
            f" \\hfill \\textbf{{Risk Tier: {tier}}} \\\\\n"
            "\\end{tabular}\n"
            "\\hrule\n\\vspace{1ex}\n"
            # Technical Summary
            f"\\noindent \\textbf{{Technical Summary:}} {technical_summary}\n"
            "\\vspace{1ex}\n\\hrule\n\\vspace{1ex}\n"
            # Counts
            "\\noindent\n"
            "\\begin{tabular}{@{}p{3.2cm} p{1.5cm} p{3.5cm} p{5.8cm}@{}}\n"
            f"  \\textbf{{Total Alerts:}} & {total_alerts} &"
            f" \\textbf{{Triggers:}} & {triggers} \\\\\n"
            f"  \\textbf{{LLM Enhanced:}} &"
            f" \\multicolumn{{3}}{{l}}{{{llm_enhanced}}} \\\\\n"
            "\\end{tabular}\n"
            "\\vspace{0.5ex}\n\n"
            f"{threat_class_line}"
            "\\hrule\n\\vspace{1ex}\n"
            # Phase 3: Phased response (replaces flat containment)
            f"{phased_block}"
            # SIEM Queries
            f"{query_block}"
            # Window
            f"\\noindent \\textbf{{Window:}} {win_hhmm_start} -- {win_hhmm_end}\n"
            "\\vspace{1ex}\n\\hrule\n\\vspace{1ex}\n"
            # Severity Breakdown
            "\\noindent \\textbf{Severity Breakdown:}\n\n"
            "\\begin{tabular}{@{}lr@{}}\n"
            "\\toprule Severity & Count \\\\ \\midrule\n"
            f"{sev_rows}\n"
            "\\bottomrule\n\\end{tabular}\n"
            "\\vspace{1.5ex}\n\n"
            # Trigger Timeline (5 cols — SOC)
            "\\noindent \\textbf{Trigger Timeline:}\n\n"
            "{\\footnotesize\n"
            "\\begin{tabular}{@{}p{3.2cm} @{\\hspace{3pt}} p{1.5cm}"
            " @{\\hspace{3pt}} p{4.0cm} @{\\hspace{3pt}} p{2.0cm}"
            " @{\\hspace{3pt}} p{2.2cm}@{}}\n"
            "\\toprule Timestamp & Alert ID & Category & Tier & Kill Chain"
            " \\\\ \\midrule\n"
            f"{tl_rows}\n"
            "\\bottomrule\n\\end{tabular}}\n"
            "\\vspace{0.5ex}\n\\hrule width 0.25\\textwidth\n\\vspace{1.5ex}\n"
            # IoCs
            "\\noindent \\textbf{Indicators of Compromise (external only):}\n"
            "\\begin{itemize}\n"
            f"{ioc_items}\n"
            "\\end{itemize}\n\\vspace{0.8ex}\n"
            # Assets
            "\\noindent \\textbf{Affected Assets:}\n"
            "\\begin{itemize}\n"
            f"{asset_items}\n"
            "\\end{itemize}\n\\vspace{0.8ex}\n"
            # CVEs
            "\\noindent \\textbf{Detected CVEs:}\n"
            "\\begin{itemize}\n"
            f"{cve_items}\n"
            "\\end{itemize}\n\\vspace{0.8ex}\n"
            "\\hrule\n\\vspace{1ex}\n"
            # SOC Recommendations
            "\\noindent \\textbf{SOC Recommendations:}\n"
            "\\begin{itemize}\n"
            f"{soc_recs}\n"
            "\\end{itemize}\n\\vspace{0.8ex}\n"
            # Recommended Actions
            "\\noindent \\textbf{Recommended Actions:}\n"
            "\\begin{itemize}\n"
            f"{rec_actions}\n"
            "\\end{itemize}\n"
            "\\hrule\n\\vspace{1ex}\n"
            # Attack Vector
            f"\\noindent \\textbf{{Attack Vector Analysis:}} {attack_vector}\n"
            "\\vspace{1ex}\n\\hrule\n"
            f"\\noindent \\textit{{Generated: {self._escape(timestamp)}}}\n"
            "\\end{document}\n"
        )

    def _build_timeline_rows(self, alerts: list) -> str:
        if not alerts:
            return r"No alerts recorded. & & & & \\ \hline"
        rows = []
        for alert in sorted(alerts, key=lambda x: self._get_timestamp_ms(x)):
            ts = self._escape(alert.get("timestamp", alert.get("Timestamp", "---")))
            aid = self._escape(alert.get("id", alert.get("Alert ID", "---")))
            cat = self._escape(alert.get("category", alert.get("Category", "---")))
            tier = self._tier_cell(alert.get("tier", alert.get("Tier", "---")))
            phase = self._tier_cell(
                (alert.get("kill_chain") or alert.get("Kill Chain") or "---").upper()
            )
            rows.append(f"  {ts} & {aid} & {cat} & {tier} & {phase} \\\\")
        return "\n".join(rows)

    def _build_severity_rows(self, severity_breakdown: dict) -> str:
        if not severity_breakdown:
            return "  No severity data & 0 \\\\"
        order = [
            "CRITICAL",
            "HIGH",
            "MEDIUM-HIGH",
            "MEDIUM",
            "LOW-MED",
            "LOW",
            "Unknown",
        ]
        rows = []
        for sev, count in sorted(
            severity_breakdown.items(),
            key=lambda x: order.index(x[0]) if x[0] in order else 99,
        ):
            rows.append(f"  {self._tier_cell(str(sev))} & {int(count)} \\\\")
        return "\n".join(rows)
