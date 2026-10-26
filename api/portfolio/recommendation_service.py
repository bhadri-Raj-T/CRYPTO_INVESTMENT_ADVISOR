from api.portfolio.personalized_service import get_personalized_analytics


def generate_recommendations(user_id, risk_tolerance):
    analytics = get_personalized_analytics(user_id, risk_tolerance)
    recommendations = []

    for asset in analytics["assets"]:
        symbol = asset["symbol"]
        prediction = asset.get("prediction") or {}
        risk = asset.get("risk") or {}
        anomaly = asset.get("anomaly") or {}

        reasons = []
        warnings = []
        recommendation = "HOLD"
        confidence = "LOW"

        direction = prediction.get("direction")
        p_up = prediction.get("probability_up")
        p_down = prediction.get("probability_down")
        model_status = prediction.get("status")

        if model_status not in (None, "OK") or direction is None:
            reasons.append("The experimental GRU V4 forecast is not ready for the latest record.")
            warnings.append("No directional recommendation is generated without a valid model output.")
        elif anomaly.get("is_anomaly") is True:
            probability = p_up if direction == "UP" else p_down
            if probability is not None:
                reasons.append(
                    f"GRU V4 direction is {direction} with {float(probability) * 100:.2f}% model probability."
                )
            if risk:
                reasons.append(
                    f"Current risk level is {risk.get('level')} with score {float(risk.get('score', 0)):.2f}."
                )
            reasons.append(f"User risk tolerance is {risk_tolerance}.")
            warnings.extend(
                [
                    "Anomaly detected in recent market behaviour.",
                    "Directional output is not promoted to an active bias while an anomaly is present.",
                ]
            )
        elif risk.get("level") == "HIGH":
            reasons.append(
                f"Current risk level is HIGH with score {float(risk.get('score', 0)):.2f}."
            )
            warnings.append("High market risk detected.")
        elif direction == "UP" and p_up is not None and float(p_up) >= 0.60:
            recommendation = "POSITIVE_BIAS"
            confidence = "MEDIUM"
            reasons.append(f"GRU V4 direction is UP with {float(p_up) * 100:.2f}% model probability.")
        elif direction == "DOWN" and p_down is not None and float(p_down) >= 0.60:
            recommendation = "NEGATIVE_BIAS"
            confidence = "MEDIUM"
            reasons.append(f"GRU V4 direction is DOWN with {float(p_down) * 100:.2f}% model probability.")
        else:
            if direction and p_up is not None and p_down is not None:
                probability = p_up if direction == "UP" else p_down
                reasons.append(
                    f"GRU V4 direction is {direction} with {float(probability) * 100:.2f}% model probability."
                )
            if risk:
                reasons.append(
                    f"Current risk level is {risk.get('level')} with score {float(risk.get('score', 0)):.2f}."
                )
            reasons.append(f"User risk tolerance is {risk_tolerance}.")

        warnings.append("GRU V4 is experimental and should not be treated as a guaranteed trading signal.")

        recommendations.append(
            {
                "symbol": symbol,
                "recommendation": recommendation,
                "confidence": confidence,
                "reasons": reasons,
                "warnings": warnings,
                "risk_tolerance": risk_tolerance,
                "model_version": "GRU_V4",
                "position_status": asset.get("position_status", "MARKET_WATCH"),
                "is_held": bool(asset.get("is_held", False)),
            }
        )

    return {
        "username": analytics.get("username"),
        "risk_tolerance": risk_tolerance,
        "recommendations": recommendations,
        "portfolio_summary": analytics["portfolio_summary"],
    }
