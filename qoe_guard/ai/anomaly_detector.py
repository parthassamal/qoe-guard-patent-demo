"""
Anomaly Detection for QoE-Guard.

Uses ML algorithms to detect unusual patterns in API behavior:
- Response time anomalies
- Schema violation patterns
- Unexpected value distributions
- Behavioral drift over time

Libraries:
- scikit-learn: Isolation Forest, One-Class SVM, LOF
- numpy: Numerical operations
- scipy: Statistical tests
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class AnomalyScore:
    """Result of anomaly detection for a single observation."""
    is_anomaly: bool
    score: float  # -1 to 1, higher = more anomalous
    confidence: float
    features_contribution: Dict[str, float]
    explanation: str


@dataclass
class RuntimeMetrics:
    """Runtime metrics for an API call."""
    latency_ms: float
    status_code: int
    response_size_bytes: int
    timestamp: datetime
    endpoint: str
    method: str
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyReport:
    """Complete anomaly detection report."""
    total_observations: int
    anomaly_count: int
    anomaly_rate: float
    top_anomalies: List[Tuple[RuntimeMetrics, AnomalyScore]]
    patterns_detected: List[str]
    summary: str


class AnomalyDetector:
    """
    Detect anomalies in API runtime behavior using ML.
    
    Supports multiple detection algorithms:
    - Isolation Forest: Good for general outlier detection
    - One-Class SVM: Good for novelty detection
    - Local Outlier Factor: Good for density-based outliers
    - Statistical: Z-score, IQR for simple cases
    """
    
    def __init__(
        self,
        algorithm: str = "isolation_forest",  # isolation_forest, one_class_svm, lof, statistical
        contamination: float = 0.1,  # Expected proportion of outliers
        n_estimators: int = 100,  # For Isolation Forest
    ):
        """
        Initialize anomaly detector.
        
        Args:
            algorithm: Detection algorithm to use
            contamination: Expected anomaly rate
            n_estimators: Number of trees for Isolation Forest
        """
        self.algorithm = algorithm
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.model = None
        self.scaler = None
        self.feature_names: List[str] = []
        self.training_stats: Dict[str, Dict[str, float]] = {}
        
        self._init_model()
    
    def _init_model(self):
        """Initialize the ML model."""
        try:
            from sklearn.ensemble import IsolationForest
            from sklearn.svm import OneClassSVM
            from sklearn.neighbors import LocalOutlierFactor
            from sklearn.preprocessing import StandardScaler
            
            self.scaler = StandardScaler()
            
            if self.algorithm == "isolation_forest":
                self.model = IsolationForest(
                    n_estimators=self.n_estimators,
                    contamination=self.contamination,
                    random_state=42,
                    n_jobs=-1,
                )
            elif self.algorithm == "one_class_svm":
                self.model = OneClassSVM(
                    kernel="rbf",
                    nu=self.contamination,
                )
            elif self.algorithm == "lof":
                self.model = LocalOutlierFactor(
                    n_neighbors=20,
                    contamination=self.contamination,
                    novelty=True,
                )
            # statistical doesn't need sklearn model
            
        except ImportError:
            print("Warning: scikit-learn not installed. Anomaly detection limited to statistical methods.")
            self.model = None
            self.algorithm = "statistical"
    
    @property
    def is_available(self) -> bool:
        """Check if ML-based detection is available."""
        return self.model is not None or self.algorithm == "statistical"
    
    def fit(self, metrics: List[RuntimeMetrics]) -> "AnomalyDetector":
        """
        Fit the model on historical metrics.
        
        Args:
            metrics: List of historical runtime metrics
        
        Returns:
            Self for method chaining
        """
        if not metrics:
            return self
        
        features, self.feature_names = self._extract_features(metrics)
        
        if self.algorithm == "statistical":
            self._fit_statistical(features)
        else:
            import numpy as np
            features_array = np.array(features)
            self.scaler.fit(features_array)
            scaled_features = self.scaler.transform(features_array)
            self.model.fit(scaled_features)
        
        return self
    
    def detect(self, metric: RuntimeMetrics) -> AnomalyScore:
        """
        Detect if a single metric is anomalous.
        
        Args:
            metric: Runtime metric to check
        
        Returns:
            AnomalyScore with detection result
        """
        features, _ = self._extract_features([metric])
        feature_vector = features[0]
        
        if self.algorithm == "statistical":
            return self._detect_statistical(feature_vector, metric)
        
        import numpy as np
        feature_array = np.array([feature_vector])
        
        try:
            scaled = self.scaler.transform(feature_array)
            
            # Get prediction (-1 = anomaly, 1 = normal)
            prediction = self.model.predict(scaled)[0]
            
            # Get anomaly score (higher = more anomalous)
            if hasattr(self.model, "score_samples"):
                raw_score = -self.model.score_samples(scaled)[0]
            else:
                raw_score = 0.5 if prediction == -1 else 0.0
            
            is_anomaly = prediction == -1
            
            # Compute feature contributions
            contributions = self._compute_contributions(feature_vector)
            
            return AnomalyScore(
                is_anomaly=is_anomaly,
                score=min(1.0, max(-1.0, raw_score)),
                confidence=0.8 if self.model else 0.5,
                features_contribution=contributions,
                explanation=self._generate_explanation(metric, contributions, is_anomaly),
            )
        except Exception as e:
            # Fallback to statistical
            return self._detect_statistical(feature_vector, metric)
    
    def detect_batch(self, metrics: List[RuntimeMetrics]) -> AnomalyReport:
        """
        Detect anomalies in a batch of metrics.
        
        Args:
            metrics: List of runtime metrics
        
        Returns:
            AnomalyReport with all findings
        """
        if not metrics:
            return AnomalyReport(
                total_observations=0,
                anomaly_count=0,
                anomaly_rate=0.0,
                top_anomalies=[],
                patterns_detected=[],
                summary="No metrics to analyze.",
            )
        
        results = [(m, self.detect(m)) for m in metrics]
        
        anomalies = [(m, s) for m, s in results if s.is_anomaly]
        anomaly_count = len(anomalies)
        anomaly_rate = anomaly_count / len(metrics)
        
        # Sort by score
        anomalies.sort(key=lambda x: x[1].score, reverse=True)
        top_anomalies = anomalies[:10]
        
        # Detect patterns
        patterns = self._detect_patterns(anomalies)
        
        return AnomalyReport(
            total_observations=len(metrics),
            anomaly_count=anomaly_count,
            anomaly_rate=anomaly_rate,
            top_anomalies=top_anomalies,
            patterns_detected=patterns,
            summary=self._generate_summary(anomaly_count, len(metrics), patterns),
        )
    
    def _extract_features(
        self,
        metrics: List[RuntimeMetrics],
    ) -> Tuple[List[List[float]], List[str]]:
        """Extract feature vectors from metrics."""
        feature_names = [
            "latency_ms",
            "status_code",
            "response_size_bytes",
            "hour_of_day",
            "is_error",
            "latency_normalized",
        ]
        
        features = []
        for m in metrics:
            hour = m.timestamp.hour if m.timestamp else 12
            is_error = 1.0 if m.status_code >= 400 else 0.0
            
            # Normalize latency (log scale)
            import math
            latency_norm = math.log1p(m.latency_ms)
            
            features.append([
                m.latency_ms,
                float(m.status_code),
                float(m.response_size_bytes),
                float(hour),
                is_error,
                latency_norm,
            ])
        
        return features, feature_names
    
    def _fit_statistical(self, features: List[List[float]]):
        """Fit statistical model (mean, std for each feature)."""
        import numpy as np
        features_array = np.array(features)
        
        for i, name in enumerate(self.feature_names):
            col = features_array[:, i]
            self.training_stats[name] = {
                "mean": float(np.mean(col)),
                "std": float(np.std(col)) + 1e-10,  # Avoid division by zero
                "min": float(np.min(col)),
                "max": float(np.max(col)),
                "q1": float(np.percentile(col, 25)),
                "q3": float(np.percentile(col, 75)),
            }
    
    def _detect_statistical(
        self,
        feature_vector: List[float],
        metric: RuntimeMetrics,
    ) -> AnomalyScore:
        """Statistical anomaly detection using Z-score and IQR."""
        if not self.training_stats:
            # No training data, use heuristics
            is_anomaly = (
                metric.latency_ms > 5000 or  # > 5s
                metric.status_code >= 500 or  # Server error
                metric.response_size_bytes > 10_000_000  # > 10MB
            )
            return AnomalyScore(
                is_anomaly=is_anomaly,
                score=0.8 if is_anomaly else 0.1,
                confidence=0.4,
                features_contribution={"latency_ms": 0.5, "status_code": 0.3, "size": 0.2},
                explanation="Heuristic detection (no training data)",
            )
        
        z_scores = {}
        contributions = {}
        max_z = 0
        
        for i, name in enumerate(self.feature_names):
            if name in self.training_stats:
                stats = self.training_stats[name]
                z = abs(feature_vector[i] - stats["mean"]) / stats["std"]
                z_scores[name] = z
                contributions[name] = min(1.0, z / 3)  # Normalize to 0-1
                max_z = max(max_z, z)
        
        # Anomaly if Z > 3 (99.7% of normal distribution)
        is_anomaly = max_z > 3
        score = min(1.0, max_z / 5)
        
        return AnomalyScore(
            is_anomaly=is_anomaly,
            score=score,
            confidence=0.7,
            features_contribution=contributions,
            explanation=self._generate_explanation(metric, contributions, is_anomaly),
        )
    
    def _compute_contributions(
        self,
        feature_vector: List[float],
    ) -> Dict[str, float]:
        """Compute feature contributions to anomaly score."""
        if not self.training_stats:
            return {name: 1.0 / len(self.feature_names) for name in self.feature_names}
        
        contributions = {}
        for i, name in enumerate(self.feature_names):
            if name in self.training_stats:
                stats = self.training_stats[name]
                z = abs(feature_vector[i] - stats["mean"]) / stats["std"]
                contributions[name] = min(1.0, z / 3)
        
        # Normalize
        total = sum(contributions.values()) or 1
        return {k: v / total for k, v in contributions.items()}
    
    def _detect_patterns(
        self,
        anomalies: List[Tuple[RuntimeMetrics, AnomalyScore]],
    ) -> List[str]:
        """Detect patterns in anomalies."""
        patterns = []
        
        if not anomalies:
            return patterns
        
        # Check for latency spikes
        high_latency = [m for m, s in anomalies if m.latency_ms > 1000]
        if len(high_latency) > 3:
            patterns.append(f"Latency spike pattern: {len(high_latency)} requests > 1s")
        
        # Check for error bursts
        errors = [m for m, s in anomalies if m.status_code >= 400]
        if len(errors) > 3:
            error_codes = defaultdict(int)
            for m in errors:
                error_codes[m.status_code] += 1
            patterns.append(f"Error burst: {dict(error_codes)}")
        
        # Check for endpoint concentration
        endpoints = defaultdict(int)
        for m, s in anomalies:
            endpoints[m.endpoint] += 1
        
        concentrated = [(e, c) for e, c in endpoints.items() if c >= 3]
        if concentrated:
            patterns.append(f"Endpoint concentration: {concentrated}")
        
        return patterns
    
    def _generate_explanation(
        self,
        metric: RuntimeMetrics,
        contributions: Dict[str, float],
        is_anomaly: bool,
    ) -> str:
        """Generate human-readable explanation."""
        if not is_anomaly:
            return "Metric is within normal bounds."
        
        # Find top contributors
        sorted_contrib = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        top = sorted_contrib[:3]
        
        parts = []
        for name, contrib in top:
            if contrib > 0.3:
                if name == "latency_ms":
                    parts.append(f"high latency ({metric.latency_ms:.0f}ms)")
                elif name == "status_code":
                    parts.append(f"unusual status ({metric.status_code})")
                elif name == "response_size_bytes":
                    parts.append(f"unusual size ({metric.response_size_bytes} bytes)")
                elif name == "is_error":
                    parts.append("error response")
        
        if parts:
            return f"Anomaly detected: {', '.join(parts)}"
        return "Anomaly detected based on overall pattern"
    
    def _generate_summary(
        self,
        anomaly_count: int,
        total: int,
        patterns: List[str],
    ) -> str:
        """Generate summary for report."""
        rate = anomaly_count / total if total else 0
        
        summary = f"Analyzed {total} metrics, found {anomaly_count} anomalies ({rate:.1%})."
        
        if patterns:
            summary += f" Detected patterns: {'; '.join(patterns)}"
        
        if rate > 0.2:
            summary += " WARNING: High anomaly rate indicates potential systemic issues."
        
        return summary


# Convenience function
def detect_runtime_anomalies(
    metrics: List[RuntimeMetrics],
    historical: Optional[List[RuntimeMetrics]] = None,
) -> AnomalyReport:
    """
    Quick function to detect runtime anomalies.
    
    Args:
        metrics: Metrics to check
        historical: Optional historical data for training
    """
    detector = AnomalyDetector()
    
    if historical:
        detector.fit(historical)
    
    return detector.detect_batch(metrics)


# Time series anomaly detection for trends
class TimeSeriesAnomalyDetector:
    """
    Detect anomalies in time series data.
    
    Uses rolling statistics and trend analysis.
    """
    
    def __init__(
        self,
        window_size: int = 20,
        z_threshold: float = 3.0,
    ):
        self.window_size = window_size
        self.z_threshold = z_threshold
    
    def detect_latency_trend(
        self,
        metrics: List[RuntimeMetrics],
    ) -> Dict[str, Any]:
        """
        Detect if latency is trending up/down anomalously.
        
        Returns trend analysis with confidence.
        """
        if len(metrics) < self.window_size:
            return {"trend": "insufficient_data", "confidence": 0.0}
        
        import numpy as np
        
        # Sort by timestamp
        sorted_metrics = sorted(metrics, key=lambda m: m.timestamp)
        latencies = [m.latency_ms for m in sorted_metrics]
        
        # Compute rolling mean
        latencies_array = np.array(latencies)
        rolling_mean = np.convolve(
            latencies_array,
            np.ones(self.window_size) / self.window_size,
            mode="valid",
        )
        
        # Compute trend using linear regression
        x = np.arange(len(rolling_mean))
        slope, intercept = np.polyfit(x, rolling_mean, 1)
        
        # Compute trend strength
        y_pred = slope * x + intercept
        ss_res = np.sum((rolling_mean - y_pred) ** 2)
        ss_tot = np.sum((rolling_mean - np.mean(rolling_mean)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Classify trend
        if abs(slope) < 1:
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"
        
        # Check if anomalous
        std = np.std(latencies)
        mean = np.mean(latencies)
        recent_mean = np.mean(latencies[-self.window_size:])
        
        z_score = (recent_mean - mean) / std if std > 0 else 0
        is_anomalous = abs(z_score) > self.z_threshold
        
        return {
            "trend": trend,
            "slope": float(slope),
            "r_squared": float(r_squared),
            "recent_mean": float(recent_mean),
            "overall_mean": float(mean),
            "z_score": float(z_score),
            "is_anomalous": is_anomalous,
            "confidence": min(1.0, abs(r_squared)),
        }
