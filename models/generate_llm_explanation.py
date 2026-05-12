import os
import json
from groq import Groq
from build_explanation_payload import build_explanation_payload

# -----------------------------
# Safe Groq initialization
# -----------------------------
api_key = os.getenv("GROQ_API_KEY")

client = None
if api_key:
    try:
        api_key = api_key.strip().replace("\n", "").replace("\r", "")
        client = Groq(api_key=api_key)
    except:
        client = None


def generate_fallback_explanation(payload):
    team = payload["team"]
    opponent = payload["opponent"]
    venue = payload["venue"]
    prob = round(payload["predicted_win_probability"] * 100, 2)

    top_features = payload["top_features"]
    top_feature_names = [f["feature"] for f in top_features[:3]]

    return {
        "match_summary": f"{team} has an estimated win probability of {prob}% against {opponent}.",
        "feature_drivers": f"The strongest factors influencing this prediction are {', '.join(top_feature_names)}.",
        "venue_impact": f"The match is being played at {venue}, and venue-based historical trends are part of the prediction.",
        "final_explanation": f"Overall, the model gives {team} a {prob}% chance of winning based on recent team form, comparative performance, and venue conditions."
    }


def call_llm(payload):
    if not client:
        return None

    prompt = f"""
You are a professional cricket analyst.

Use ONLY the structured data provided below.
Do NOT invent any players, stats, or facts.
Explain the prediction in a clear, natural, cricket-analyst style.

Return ONLY valid JSON in this exact format:

{{
  "match_summary": "",
  "feature_drivers": "",
  "venue_impact": "",
  "final_explanation": ""
}}

Structured Prediction Data:
{json.dumps(payload, indent=2)}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional cricket analyst. Return strict JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3
        )

        output = response.choices[0].message.content.strip()

        if not output:
            return None

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return None

    except:
        return None


if __name__ == "__main__":
    payload = build_explanation_payload(sample_index=0)

    explanation = call_llm(payload)

    if explanation is None:
        explanation = generate_fallback_explanation(payload)
        print("Using fallback explanation.\n")

    print(json.dumps(explanation, indent=2))