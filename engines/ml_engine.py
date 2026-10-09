"""
Hybrid Recommendation Engine for SmartCompress AI.
Coordinates between the Random Forest ML model and the Rule-Based fallback engine.
Ensures transparent attribution of recommendations and provides calibrated explanations.
"""

from typing import Dict, Any

from engines.recommendation_engine import recommend_rule_based, ALL_ALGORITHMS, ALGORITHM_PROFILES
from model.predictor import ml_predictor


def get_recommendation(analysis: Dict[str, Any], preference: str = "balanced") -> Dict[str, Any]:
    """
    Generate algorithm recommendation using hybrid ML + Rule-based decision architecture.

    Logic:
    1. Check if file is extreme entropy (>= 7.6) or already compressed. In such cases,
       rule-based engine provides critical safety warnings and guidance.
    2. Attempt inference via Random Forest ML model if loaded and ready.
    3. If ML model succeeds, enhance recommendation with confidence score and model attribution.
    4. If ML model is missing or fails, seamlessly fall back to Rule-Based Engine.
    """
    entropy = analysis.get("entropy", 0.0)
    size_bytes = analysis.get("size_bytes", 0)
    category = analysis.get("category", "")
    extension = analysis.get("extension", "")

    # Always compute rule-based baseline for fallback and comparison
    rule_result = recommend_rule_based(analysis, preference)

    # If the file is a pure pre-compressed archive at the theoretical entropy ceiling (>= 7.92), prioritize rule-based safety notice
    if analysis.get("is_precompressed", False) and entropy >= 7.92:
        return rule_result

    # Try ML prediction
    ml_result = ml_predictor.predict(
        file_size=size_bytes,
        entropy=entropy,
        category=category,
        extension=extension,
        preference=preference
    )

    if ml_result and ml_result.get("recommended_algorithm"):
        algo = ml_result["recommended_algorithm"]
        confidence = ml_result["confidence"]
        conf_pct = ml_result["confidence_pct"]
        probabilities = ml_result.get("probabilities", {})

        # Formulate ML explanation
        explanation = (
            f"The Random Forest model recommends {algo} with {conf_pct}% ensemble voting confidence. "
            f"Based on experimental benchmarks of similar {category.lower()} files with entropy {entropy:.2f} bits/byte "
            f"and '{preference}' optimization preference, {algo} demonstrated superior performance."
        )

        # Ranked list with probability scores
        ranked_algos = []
        for a in ALL_ALGORITHMS:
            profile = ALGORITHM_PROFILES.get(a, {})
            score = probabilities.get(a, 0.0)
            ranked_algos.append({
                "algorithm": a,
                "name": profile.get("name", a),
                "strengths": profile.get("strengths", ""),
                "best_for": profile.get("best_for", ""),
                "is_recommended": (a == algo),
                "probability": round(score, 4),
                "probability_pct": round(score * 100, 1)
            })

        # Sort ranked algorithms by probability descending
        ranked_algos.sort(key=lambda x: x["probability"], reverse=True)

        return {
            "recommended_algorithm": algo,
            "explanation": explanation,
            "recommendation_source": "Random Forest ML",
            "model_confidence": confidence,
            "model_confidence_pct": conf_pct,
            "all_probabilities": probabilities,
            "ranked_algorithms": ranked_algos,
            "user_preference": preference,
            "warning": None,
            "model_accuracy": ml_result.get("model_accuracy")
        }

    # Fallback to rule-based engine
    return rule_result
