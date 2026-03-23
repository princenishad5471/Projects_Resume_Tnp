"""
AI-Integrated CAD Design Validation Module
===========================================
Provides automated design validation against standard guidelines,
AI-based anomaly detection, and detailed validation report generation.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Design Standards
# ---------------------------------------------------------------------------

DESIGN_STANDARDS = {
    "tolerance": {
        "length_mm":    {"min": 0.1,  "max": 5000.0, "tolerance": 0.05},
        "width_mm":     {"min": 0.1,  "max": 2000.0, "tolerance": 0.05},
        "height_mm":    {"min": 0.1,  "max": 2000.0, "tolerance": 0.05},
        "wall_thickness_mm": {"min": 1.0, "max": 50.0,  "tolerance": 0.1},
        "hole_diameter_mm":  {"min": 0.5, "max": 200.0, "tolerance": 0.02},
        "fillet_radius_mm":  {"min": 0.2, "max": 25.0,  "tolerance": 0.05},
        "draft_angle_deg":   {"min": 0.5, "max": 10.0,  "tolerance": 0.1},
        "surface_roughness_um": {"min": 0.1, "max": 25.0, "tolerance": 0.5},
    },
    "material": {
        "allowed": ["Steel", "Aluminum", "Titanium", "ABS", "Nylon", "Carbon Fiber"],
        "min_yield_strength_mpa": 100,
        "max_density_g_cm3": 8.0,
    },
    "assembly": {
        "max_interference_mm": 0.05,
        "min_clearance_mm": 0.1,
        "max_components": 500,
    },
}

SEVERITY_LEVELS = {
    "CRITICAL": 4,
    "HIGH":     3,
    "MEDIUM":   2,
    "LOW":      1,
    "INFO":     0,
}

SEVERITY_COLOR = {
    "CRITICAL": "\033[91m",   # red
    "HIGH":     "\033[93m",   # yellow
    "MEDIUM":   "\033[94m",   # blue
    "LOW":      "\033[96m",   # cyan
    "INFO":     "\033[92m",   # green
    "RESET":    "\033[0m",
}


# ---------------------------------------------------------------------------
# Validation Issue
# ---------------------------------------------------------------------------

class ValidationIssue:
    """Represents a single design validation issue."""

    def __init__(self, rule_id, severity, component, parameter,
                 measured_value, expected_value, description, suggestion=""):
        self.rule_id       = rule_id
        self.severity      = severity
        self.component     = component
        self.parameter     = parameter
        self.measured_value = measured_value
        self.expected_value = expected_value
        self.description   = description
        self.suggestion    = suggestion
        self.timestamp     = datetime.now().isoformat()

    def to_dict(self):
        return {
            "rule_id":        self.rule_id,
            "severity":       self.severity,
            "component":      self.component,
            "parameter":      self.parameter,
            "measured_value": self.measured_value,
            "expected_value": self.expected_value,
            "description":    self.description,
            "suggestion":     self.suggestion,
            "timestamp":      self.timestamp,
        }

    def __repr__(self):
        c = SEVERITY_COLOR.get(self.severity, "")
        r = SEVERITY_COLOR["RESET"]
        return (
            f"{c}[{self.severity}]{r} {self.rule_id} | "
            f"{self.component}.{self.parameter} = {self.measured_value} "
            f"(expected {self.expected_value}): {self.description}"
        )


# ---------------------------------------------------------------------------
# Design Standards Checker
# ---------------------------------------------------------------------------

class DesignStandardsChecker:
    """Rule-based checker that validates design parameters against standards."""

    def __init__(self, standards=None):
        self.standards = standards or DESIGN_STANDARDS
        self.issues = []

    def _add_issue(self, rule_id, severity, component, parameter,
                   measured, expected, description, suggestion=""):
        self.issues.append(ValidationIssue(
            rule_id, severity, component, parameter,
            measured, expected, description, suggestion
        ))

    def check_dimensions(self, component_name, dimensions: dict):
        """Validate geometric dimensions against tolerance standards."""
        tol = self.standards["tolerance"]
        for param, value in dimensions.items():
            if param not in tol:
                continue
            rule = tol[param]
            if value < rule["min"]:
                self._add_issue(
                    f"DIM-{param.upper()}-MIN",
                    "HIGH",
                    component_name, param, value,
                    f">= {rule['min']}",
                    f"{param} is below minimum allowed value.",
                    f"Increase {param} to at least {rule['min']}."
                )
            elif value > rule["max"]:
                self._add_issue(
                    f"DIM-{param.upper()}-MAX",
                    "HIGH",
                    component_name, param, value,
                    f"<= {rule['max']}",
                    f"{param} exceeds maximum allowed value.",
                    f"Reduce {param} to at most {rule['max']}."
                )

    def check_material(self, component_name, material_props: dict):
        """Validate material properties against standards."""
        mat = self.standards["material"]
        material_name = material_props.get("name", "Unknown")

        if material_name not in mat["allowed"]:
            self._add_issue(
                "MAT-INVALID",
                "CRITICAL",
                component_name, "material", material_name,
                f"one of {mat['allowed']}",
                f"Material '{material_name}' is not in the approved list.",
                f"Use an approved material: {', '.join(mat['allowed'])}."
            )

        yield_strength = material_props.get("yield_strength_mpa", 0)
        if yield_strength < mat["min_yield_strength_mpa"]:
            self._add_issue(
                "MAT-YIELD-LOW",
                "HIGH",
                component_name, "yield_strength_mpa",
                yield_strength,
                f">= {mat['min_yield_strength_mpa']}",
                "Yield strength is below minimum requirement.",
                "Select a material with higher yield strength."
            )

        density = material_props.get("density_g_cm3", 0)
        if density > mat["max_density_g_cm3"]:
            self._add_issue(
                "MAT-DENSITY-HIGH",
                "MEDIUM",
                component_name, "density_g_cm3",
                density,
                f"<= {mat['max_density_g_cm3']}",
                "Material density exceeds design weight limit.",
                "Consider a lighter material to reduce component weight."
            )

    def check_assembly(self, assembly_props: dict):
        """Validate assembly-level constraints."""
        asm = self.standards["assembly"]

        interference = assembly_props.get("interference_mm", 0)
        if interference > asm["max_interference_mm"]:
            self._add_issue(
                "ASM-INTERFERENCE",
                "CRITICAL",
                "Assembly", "interference_mm",
                interference,
                f"<= {asm['max_interference_mm']}",
                "Component interference exceeds allowable limit.",
                "Review mating part dimensions and adjust to resolve interference."
            )

        clearance = assembly_props.get("clearance_mm", 999)
        if clearance < asm["min_clearance_mm"]:
            self._add_issue(
                "ASM-CLEARANCE",
                "HIGH",
                "Assembly", "clearance_mm",
                clearance,
                f">= {asm['min_clearance_mm']}",
                "Insufficient clearance between components.",
                f"Increase clearance to at least {asm['min_clearance_mm']} mm."
            )

        n_components = assembly_props.get("component_count", 0)
        if n_components > asm["max_components"]:
            self._add_issue(
                "ASM-COMPLEXITY",
                "MEDIUM",
                "Assembly", "component_count",
                n_components,
                f"<= {asm['max_components']}",
                "Assembly exceeds maximum component complexity limit.",
                "Consider modular sub-assemblies to reduce complexity."
            )

    def get_issues(self):
        return self.issues

    def reset(self):
        self.issues = []


# ---------------------------------------------------------------------------
# AI Anomaly Detector
# ---------------------------------------------------------------------------

class AIAnomalyDetector:
    """
    Uses Isolation Forest to detect anomalous design parameters
    that deviate from learned historical design patterns.
    """

    def __init__(self, contamination=0.05, random_state=42):
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100
        )
        self.scaler   = StandardScaler()
        self.features = []
        self._fitted  = False

    def train(self, historical_designs: pd.DataFrame):
        """Train anomaly detector on historical compliant design data."""
        self.features = historical_designs.select_dtypes(include=[np.number]).columns.tolist()
        X = historical_designs[self.features].dropna()
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self._fitted = True
        return self

    def detect(self, design: pd.DataFrame):
        """
        Detect anomalies in a new design.
        Returns a DataFrame with anomaly scores and labels.
        """
        if not self._fitted:
            raise RuntimeError("Detector not trained. Call train() first.")
        X = design[self.features].fillna(0)
        X_scaled = self.scaler.transform(X)
        scores  = self.model.decision_function(X_scaled)   # higher = more normal
        labels  = self.model.predict(X_scaled)              # -1 = anomaly, 1 = normal
        result  = design.copy()
        result["anomaly_score"] = np.round(scores, 4)
        result["anomaly_label"] = np.where(labels == -1, "ANOMALY", "NORMAL")
        return result

    def get_anomalous_features(self, design_row: dict):
        """
        Identify which features contributed most to an anomaly
        by comparing against the training distribution.
        """
        if not self._fitted:
            return []
        row_values = np.array([[design_row.get(f, 0) for f in self.features]])
        row_scaled = self.scaler.transform(row_values)
        mean_scaled = np.zeros(len(self.features))   # training mean after scaling
        deviations = np.abs(row_scaled[0] - mean_scaled)
        top_idx = np.argsort(deviations)[::-1][:3]
        return [(self.features[i], round(float(deviations[i]), 3)) for i in top_idx]


# ---------------------------------------------------------------------------
# Validation Engine
# ---------------------------------------------------------------------------

class CADValidationEngine:
    """
    Orchestrates design validation by combining rule-based checks
    and AI anomaly detection to produce a comprehensive validation result.
    """

    def __init__(self, standards=None, ai_detector=None):
        self.checker    = DesignStandardsChecker(standards)
        self.detector   = ai_detector   # optional AIAnomalyDetector
        self._results   = []
        self._ai_results = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_component(self, component_name, dimensions=None,
                           material_props=None, assembly_props=None):
        """Run all applicable rule checks for a single component."""
        self.checker.reset()
        if dimensions:
            self.checker.check_dimensions(component_name, dimensions)
        if material_props:
            self.checker.check_material(component_name, material_props)
        if assembly_props:
            self.checker.check_assembly(assembly_props)
        issues = self.checker.get_issues()
        self._results.extend(issues)
        return issues

    def validate_batch(self, designs_df: pd.DataFrame):
        """
        Run AI anomaly detection on a batch of designs.
        Requires a trained AIAnomalyDetector to be provided.
        """
        if self.detector is None:
            raise RuntimeError("No AI detector provided.")
        self._ai_results = self.detector.detect(designs_df)
        return self._ai_results

    def get_all_issues(self):
        return self._results

    def reset(self):
        self._results   = []
        self._ai_results = None
        self.checker.reset()

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    def summary(self):
        """Return a dict summarizing the validation run."""
        counts = {s: 0 for s in SEVERITY_LEVELS}
        for issue in self._results:
            counts[issue.severity] += 1
        total = len(self._results)
        passed = total == 0
        ai_anomalies = 0
        if self._ai_results is not None:
            ai_anomalies = int((self._ai_results["anomaly_label"] == "ANOMALY").sum())
        return {
            "total_issues":  total,
            "passed":        passed,
            "by_severity":   counts,
            "ai_anomalies":  ai_anomalies,
            "timestamp":     datetime.now().isoformat(),
        }

    def issues_dataframe(self):
        """Return all rule-based issues as a Pandas DataFrame."""
        return pd.DataFrame([i.to_dict() for i in self._results])


# ---------------------------------------------------------------------------
# Validation Report Generator
# ---------------------------------------------------------------------------

class ValidationReportGenerator:
    """Generates human-readable validation reports from engine results."""

    def __init__(self, engine: CADValidationEngine, project_name="Design Project"):
        self.engine       = engine
        self.project_name = project_name

    # ------------------------------------------------------------------

    def _header(self):
        width = 70
        lines = [
            "=" * width,
            "  AI-Integrated CAD Design Validation Report".center(width),
            f"  Project : {self.project_name}".center(width),
            f"  Date    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(width),
            "=" * width,
        ]
        return "\n".join(lines)

    def _summary_section(self, summary):
        status = "✅ PASSED" if summary["passed"] else "❌ FAILED"
        lines = [
            "",
            "VALIDATION SUMMARY",
            "-" * 40,
            f"  Status         : {status}",
            f"  Total Issues   : {summary['total_issues']}",
            f"  AI Anomalies   : {summary['ai_anomalies']}",
            "",
            "  Issues by Severity:",
        ]
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            count = summary["by_severity"].get(sev, 0)
            bar = "█" * count + "░" * max(0, 10 - count)
            lines.append(f"    {sev:<10} {bar}  ({count})")
        return "\n".join(lines)

    def _issues_section(self):
        issues = self.engine.get_all_issues()
        if not issues:
            return "\n✅ No rule violations detected."
        lines = ["", "DETAILED ISSUES", "-" * 40]
        for i, issue in enumerate(issues, 1):
            lines += [
                f"\n  [{i}] Rule     : {issue.rule_id}",
                f"      Severity  : {issue.severity}",
                f"      Component : {issue.component}",
                f"      Parameter : {issue.parameter}",
                f"      Measured  : {issue.measured_value}",
                f"      Expected  : {issue.expected_value}",
                f"      Detail    : {issue.description}",
                f"      Action    : {issue.suggestion}",
            ]
        return "\n".join(lines)

    def _ai_section(self):
        ai_results = self.engine._ai_results
        if ai_results is None:
            return ""
        anomalies = ai_results[ai_results["anomaly_label"] == "ANOMALY"]
        lines = [
            "",
            "AI ANOMALY DETECTION RESULTS",
            "-" * 40,
            f"  Total designs scanned : {len(ai_results)}",
            f"  Anomalies detected    : {len(anomalies)}",
        ]
        if not anomalies.empty:
            lines.append("\n  Anomalous Designs:")
            for _, row in anomalies.iterrows():
                lines.append(
                    f"    • Design ID {row.get('design_id', '?')}  "
                    f"Score: {row['anomaly_score']:.4f}"
                )
        return "\n".join(lines)

    def _footer(self):
        return "\n" + "=" * 70 + "\n  End of Report\n" + "=" * 70

    # ------------------------------------------------------------------

    def generate(self, print_report=True):
        """Generate and optionally print the full validation report."""
        summary = self.engine.summary()
        report  = "\n".join([
            self._header(),
            self._summary_section(summary),
            self._issues_section(),
            self._ai_section(),
            self._footer(),
        ])
        if print_report:
            print(report)
        return report

    def to_dataframe(self):
        """Return issues as a DataFrame for further analysis."""
        return self.engine.issues_dataframe()
