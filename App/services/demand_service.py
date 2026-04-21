import joblib
import pandas as pd
import random
import os

# 🔥 ALWAYS load model using absolute path (avoids path confusion)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "ml_model.pkl")

print("🔍 Loading model from:", MODEL_PATH)

model = joblib.load(MODEL_PATH)

print("✅ Model loaded successfully:", type(model))


# Feature names (STRICT ORDER — DO NOT CHANGE)
COLUMNS = [
    "predicted_demand",
    "extra_order",
    "month",
    "day_of_week",
    "day_of_month",
    "is_weekend"
]


def predict_demand(features):
    # Convert to DataFrame
    features_df = pd.DataFrame([features], columns=COLUMNS)

    # 🔥 DEBUG INPUT
    print("\n📥 INPUT FEATURES:", features)

    # Predict
    prediction = model.predict(features_df)[0]

    # 🔥 DEBUG RAW OUTPUT
    print("📤 RAW MODEL OUTPUT:", prediction)

    # Add small variation
    prediction = prediction + random.uniform(-2, 2)

    # Final output
    final_prediction = max(float(prediction), 0)

    # 🔥 DEBUG FINAL OUTPUT
    print("✅ FINAL DEMAND:", final_prediction)

    return final_prediction