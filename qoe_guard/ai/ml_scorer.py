"""
ML-Based Risk Scoring for QoE-Guard.

Replaces hand-tuned heuristics with learned models:
- Train on historical QoE incidents
- Learn which changes actually caused issues
- Provide explainable predictions with SHAP

Libraries:
- xgboost/lightgbm: Gradient boosting
- shap: Explainable AI
- scikit-learn: Preprocessing, metrics
"""
from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path


@dataclass
class FeatureVector:
    """Feature vector for ML scoring."""
    # Structural features
    added_fields: int = 0
    removed_fields: int = 0
    type_changes: int = 0
    value_changes: int = 0
    array_length_changes: int = 0
    depth_changes: int = 0
    
    # Criticality features
    critical_path_changes: int = 0
    high_criticality_changes: int = 0
    medium_criticality_changes: int = 0
    low_criticality_changes: int = 0
    
    # Numeric features
    max_numeric_delta_pct: float = 0.0
    avg_numeric_delta_pct: float = 0.0
    
    # Runtime features
    latency_delta_pct: float = 0.0
    error_rate: float = 0.0
    
    # Schema features
    schema_violations: int = 0
    required_field_changes: int = 0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "added_fields": self.added_fields,
            "removed_fields": self.removed_fields,
            "type_changes": self.type_changes,
            "value_changes": self.value_changes,
            "array_length_changes": self.array_length_changes,
            "depth_changes": self.depth_changes,
            "critical_path_changes": self.critical_path_changes,
            "high_criticality_changes": self.high_criticality_changes,
            "medium_criticality_changes": self.medium_criticality_changes,
            "low_criticality_changes": self.low_criticality_changes,
            "max_numeric_delta_pct": self.max_numeric_delta_pct,
            "avg_numeric_delta_pct": self.avg_numeric_delta_pct,
            "latency_delta_pct": self.latency_delta_pct,
            "error_rate": self.error_rate,
            "schema_violations": self.schema_violations,
            "required_field_changes": self.required_field_changes,
        }
    
    def to_list(self) -> List[float]:
        """Convert to list for model input."""
        return list(self.to_dict().values())


@dataclass
class MLPrediction:
    """Result of ML risk prediction."""
    risk_score: float  # 0-1
    decision: str  # PASS/WARN/FAIL
    confidence: float
    feature_importances: Dict[str, float]
    top_contributors: List[Tuple[str, float, str]]  # (feature, value, direction)
    explanation: str


@dataclass
class SHAPExplanation:
    """SHAP-based explanation for a prediction."""
    base_value: float
    shap_values: Dict[str, float]
    top_positive: List[Tuple[str, float]]  # Pushing toward high risk
    top_negative: List[Tuple[str, float]]  # Pushing toward low risk
    force_plot_html: Optional[str] = None


class MLRiskScorer:
    """
    ML-based risk scorer using gradient boosting.
    
    Features:
    - Learns from historical validation data
    - Provides SHAP explanations
    - Supports model versioning
    - Auto-retraining capability
    """
    
    def __init__(
        self,
        model_type: str = "xgboost",  # xgboost, lightgbm, random_forest
        model_path: Optional[str] = None,
    ):
        """
        Initialize ML scorer.
        
        Args:
            model_type: Type of model to use
            model_path: Optional path to load pre-trained model
        """
        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.feature_names = list(FeatureVector().to_dict().keys())
        self.explainer = None
        self.thresholds = {"warn": 0.3, "fail": 0.7}
        
        if model_path:
            self.load(model_path)
        else:
            self._init_model()
    
    def _init_model(self):
        """Initialize the ML model."""
        try:
            from sklearn.preprocessing import StandardScaler
            self.scaler = StandardScaler()
            
            if self.model_type == "xgboost":
                import xgboost as xgb
                self.model = xgb.XGBClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    objective="binary:logistic",
                    random_state=42,
                    use_label_encoder=False,
                    eval_metric="logloss",
                )
            elif self.model_type == "lightgbm":
                import lightgbm as lgb
                self.model = lgb.LGBMClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=42,
                )
            else:
                from sklearn.ensemble import RandomForestClassifier
                self.model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=5,
                    random_state=42,
                )
        except ImportError as e:
            print(f"Warning: Could not initialize {self.model_type}: {e}")
            self.model = None
    
    @property
    def is_trained(self) -> bool:
        """Check if model is trained."""
        return self.model is not None and hasattr(self.model, "classes_")
    
    def train(
        self,
        features: List[FeatureVector],
        labels: List[int],  # 0 = no issue, 1 = issue
        validation_split: float = 0.2,
    ) -> Dict[str, float]:
        """
        Train the model on historical data.
        
        Args:
            features: List of feature vectors
            labels: Binary labels (0 = OK, 1 = caused issue)
            validation_split: Fraction for validation
        
        Returns:
            Training metrics
        """
        if not self.model:
            self._init_model()
            if not self.model:
                return {"error": "Model not available"}
        
        import numpy as np
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        # Prepare data
        X = np.array([f.to_list() for f in features])
        y = np.array(labels)
        
        # Split
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=42
        )
        
        # Scale
        self.scaler.fit(X_train)
        X_train_scaled = self.scaler.transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        # Train
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_val_scaled)
        
        # Initialize SHAP explainer
        try:
            import shap
            self.explainer = shap.TreeExplainer(self.model)
        except Exception:
            self.explainer = None
        
        return {
            "accuracy": accuracy_score(y_val, y_pred),
            "precision": precision_score(y_val, y_pred, zero_division=0),
            "recall": recall_score(y_val, y_pred, zero_division=0),
            "f1": f1_score(y_val, y_pred, zero_division=0),
            "train_size": len(X_train),
            "val_size": len(X_val),
        }
    
    def predict(self, features: FeatureVector) -> MLPrediction:
        """
        Predict risk score for given features.
        
        Args:
            features: Feature vector
        
        Returns:
            MLPrediction with score and explanation
        """
        if not self.is_trained:
            return self._fallback_predict(features)
        
        import numpy as np
        
        X = np.array([features.to_list()])
        X_scaled = self.scaler.transform(X)
        
        # Get probability
        prob = self.model.predict_proba(X_scaled)[0][1]
        
        # Get feature importances
        importances = self._get_feature_importances()
        
        # Determine decision
        if prob >= self.thresholds["fail"]:
            decision = "FAIL"
        elif prob >= self.thresholds["warn"]:
            decision = "WARN"
        else:
            decision = "PASS"
        
        # Get top contributors
        contributors = self._get_top_contributors(features, importances)
        
        return MLPrediction(
            risk_score=prob,
            decision=decision,
            confidence=abs(prob - 0.5) * 2,  # Higher confidence away from 0.5
            feature_importances=importances,
            top_contributors=contributors,
            explanation=self._generate_explanation(features, prob, contributors),
        )
    
    def explain(self, features: FeatureVector) -> SHAPExplanation:
        """
        Get SHAP explanation for prediction.
        
        Args:
            features: Feature vector
        
        Returns:
            SHAPExplanation with detailed breakdown
        """
        if not self.explainer:
            return SHAPExplanation(
                base_value=0.5,
                shap_values={},
                top_positive=[],
                top_negative=[],
            )
        
        import numpy as np
        
        X = np.array([features.to_list()])
        X_scaled = self.scaler.transform(X)
        
        shap_values = self.explainer.shap_values(X_scaled)
        
        # Handle different SHAP output formats
        if isinstance(shap_values, list):
            values = shap_values[1][0]  # Class 1 (issue)
        else:
            values = shap_values[0]
        
        # Create SHAP value dict
        shap_dict = {
            name: float(val) for name, val in zip(self.feature_names, values)
        }
        
        # Sort by absolute value
        sorted_shap = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)
        
        top_positive = [(k, v) for k, v in sorted_shap if v > 0][:5]
        top_negative = [(k, v) for k, v in sorted_shap if v < 0][:5]
        
        # Generate force plot HTML if possible
        force_html = None
        try:
            import shap
            force_plot = shap.force_plot(
                self.explainer.expected_value[1] if isinstance(self.explainer.expected_value, list) else self.explainer.expected_value,
                values,
                features.to_list(),
                feature_names=self.feature_names,
            )
            force_html = shap.getjs() + force_plot.html()
        except Exception:
            pass
        
        return SHAPExplanation(
            base_value=float(self.explainer.expected_value[1] if isinstance(self.explainer.expected_value, list) else self.explainer.expected_value),
            shap_values=shap_dict,
            top_positive=top_positive,
            top_negative=top_negative,
            force_plot_html=force_html,
        )
    
    def save(self, path: str):
        """Save model to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "scaler": self.scaler,
                "thresholds": self.thresholds,
                "feature_names": self.feature_names,
                "model_type": self.model_type,
            }, f)
    
    def load(self, path: str):
        """Load model from disk."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.thresholds = data["thresholds"]
        self.feature_names = data["feature_names"]
        self.model_type = data["model_type"]
        
        # Re-init SHAP explainer
        try:
            import shap
            self.explainer = shap.TreeExplainer(self.model)
        except Exception:
            self.explainer = None
    
    def _get_feature_importances(self) -> Dict[str, float]:
        """Get feature importances from model."""
        if hasattr(self.model, "feature_importances_"):
            importances = self.model.feature_importances_
            return {
                name: float(imp)
                for name, imp in zip(self.feature_names, importances)
            }
        return {name: 1.0 / len(self.feature_names) for name in self.feature_names}
    
    def _get_top_contributors(
        self,
        features: FeatureVector,
        importances: Dict[str, float],
    ) -> List[Tuple[str, float, str]]:
        """Get top contributing features."""
        feature_dict = features.to_dict()
        
        contributions = []
        for name, imp in importances.items():
            value = feature_dict.get(name, 0)
            if value != 0:
                direction = "↑" if value > 0 else "↓"
                contributions.append((name, value * imp, direction))
        
        contributions.sort(key=lambda x: abs(x[1]), reverse=True)
        return contributions[:5]
    
    def _generate_explanation(
        self,
        features: FeatureVector,
        prob: float,
        contributors: List[Tuple[str, float, str]],
    ) -> str:
        """Generate human-readable explanation."""
        if prob < 0.3:
            risk_level = "Low"
        elif prob < 0.7:
            risk_level = "Medium"
        else:
            risk_level = "High"
        
        parts = [f"{risk_level} risk ({prob:.0%})"]
        
        if contributors:
            top = contributors[0]
            parts.append(f"Top contributor: {top[0]}")
        
        return ". ".join(parts)
    
    def _fallback_predict(self, features: FeatureVector) -> MLPrediction:
        """Fallback prediction using heuristics."""
        # Simple weighted sum
        weights = {
            "removed_fields": 0.15,
            "type_changes": 0.15,
            "critical_path_changes": 0.20,
            "high_criticality_changes": 0.15,
            "schema_violations": 0.10,
            "required_field_changes": 0.10,
            "error_rate": 0.15,
        }
        
        feature_dict = features.to_dict()
        score = 0.0
        
        for name, weight in weights.items():
            value = feature_dict.get(name, 0)
            # Normalize value contribution
            if name == "error_rate":
                score += value * weight
            else:
                score += min(1.0, value / 5) * weight
        
        score = min(1.0, max(0.0, score))
        
        if score >= 0.7:
            decision = "FAIL"
        elif score >= 0.3:
            decision = "WARN"
        else:
            decision = "PASS"
        
        return MLPrediction(
            risk_score=score,
            decision=decision,
            confidence=0.5,  # Lower confidence for heuristic
            feature_importances=weights,
            top_contributors=[],
            explanation=f"Heuristic score: {score:.0%} ({decision})",
        )


# Feature extraction from changes
def extract_features_from_changes(
    changes: List[Dict[str, Any]],
    criticality_profiles: Optional[Dict[str, float]] = None,
    runtime_metrics: Optional[Dict[str, float]] = None,
) -> FeatureVector:
    """
    Extract ML features from detected changes.
    
    Args:
        changes: List of detected changes
        criticality_profiles: Path -> criticality mapping
        runtime_metrics: Optional runtime metrics
    
    Returns:
        FeatureVector for ML scoring
    """
    features = FeatureVector()
    criticality_profiles = criticality_profiles or {}
    
    numeric_deltas = []
    
    for change in changes:
        change_type = change.get("change_type", "")
        path = change.get("path", "")
        
        # Count by change type
        if change_type == "added":
            features.added_fields += 1
        elif change_type == "removed":
            features.removed_fields += 1
        elif change_type == "type_changed":
            features.type_changes += 1
        elif change_type == "value_changed":
            features.value_changes += 1
        elif change_type == "array_length_changed":
            features.array_length_changes += 1
        
        # Count by criticality
        criticality = _get_path_criticality(path, criticality_profiles)
        if criticality >= 0.9:
            features.critical_path_changes += 1
        elif criticality >= 0.7:
            features.high_criticality_changes += 1
        elif criticality >= 0.4:
            features.medium_criticality_changes += 1
        else:
            features.low_criticality_changes += 1
        
        # Track numeric deltas
        old_val = change.get("old_value")
        new_val = change.get("new_value")
        if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
            if old_val != 0:
                delta_pct = abs(new_val - old_val) / abs(old_val)
                numeric_deltas.append(delta_pct)
    
    # Numeric features
    if numeric_deltas:
        features.max_numeric_delta_pct = max(numeric_deltas)
        features.avg_numeric_delta_pct = sum(numeric_deltas) / len(numeric_deltas)
    
    # Runtime features
    if runtime_metrics:
        features.latency_delta_pct = runtime_metrics.get("latency_delta_pct", 0)
        features.error_rate = runtime_metrics.get("error_rate", 0)
    
    return features


def _get_path_criticality(path: str, profiles: Dict[str, float]) -> float:
    """Get criticality score for a JSON path."""
    # Direct match
    if path in profiles:
        return profiles[path]
    
    # Prefix match
    for profile_path, score in profiles.items():
        if path.startswith(profile_path):
            return score
    
    # Default based on path patterns
    path_lower = path.lower()
    if any(kw in path_lower for kw in ["playback", "manifest", "drm", "license"]):
        return 0.95
    if any(kw in path_lower for kw in ["entitlement", "auth", "token"]):
        return 0.85
    if any(kw in path_lower for kw in ["ad", "ads", "monetization"]):
        return 0.7
    if any(kw in path_lower for kw in ["analytics", "tracking", "beacon"]):
        return 0.3
    
    return 0.5


# Convenience functions
def train_risk_model(
    training_data: List[Tuple[FeatureVector, int]],
    model_type: str = "xgboost",
) -> Tuple[MLRiskScorer, Dict[str, float]]:
    """
    Train a new risk model.
    
    Args:
        training_data: List of (features, label) tuples
        model_type: Type of model
    
    Returns:
        (trained model, metrics)
    """
    features, labels = zip(*training_data)
    
    scorer = MLRiskScorer(model_type=model_type)
    metrics = scorer.train(list(features), list(labels))
    
    return scorer, metrics


def explain_prediction(
    features: FeatureVector,
    model_path: Optional[str] = None,
) -> SHAPExplanation:
    """
    Get SHAP explanation for features.
    
    Args:
        features: Feature vector
        model_path: Optional path to pre-trained model
    
    Returns:
        SHAPExplanation
    """
    scorer = MLRiskScorer(model_path=model_path)
    return scorer.explain(features)
