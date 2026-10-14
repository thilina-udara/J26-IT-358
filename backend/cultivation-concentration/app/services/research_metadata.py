"""Frozen public contract/benchmark metadata; no model/data imports or access."""

FEATURES = [
    "District",
    "Crop",
    "Season",
    "Land_Size_Acres",
    "Planting_Month",
    "Harvest_Month",
    "Overlap_Plan_Count",
    "Own_Expected_Production_kg",
    "Past_Window_Count",
    "Past_Mean_Window_Acres",
    "Past_Mean_Window_Production_kg",
    "Previous_Year_Window_Mean_Acres",
    "Previous_Year_Window_Median_Acres",
    "Previous_Year_Window_Std_Acres",
    "Previous_Year_Mean_Plan_Acres",
]

LABELS = ["Low", "Medium", "High"]

BENCHMARKS = {
    "XGBoost": {
        "pooled_accuracy": 0.8430,
        "pooled_macro_f1": 0.7182,
        "2023": {"accuracy": 0.9124, "macro_f1": 0.8035, "medium_recall": 0.9296, "high_recall": 0.4970},
        "2024": {"accuracy": 0.8906, "macro_f1": 0.7620, "medium_recall": 0.3905, "high_recall": 0.9003},
        "2025": {"accuracy": 0.7557, "macro_f1": 0.6295, "medium_recall": 0.2239, "high_recall": 0.9541},
    },
    "CatBoost": {
        "pooled_accuracy": 0.8441,
        "pooled_macro_f1": 0.7088,
        "2023": {"accuracy": 0.9169, "macro_f1": 0.8313, "medium_recall": 0.8486, "high_recall": 0.6000},
        "2024": {"accuracy": 0.8827, "macro_f1": 0.7207, "medium_recall": 0.2664, "high_recall": 0.9003},
        "2025": {"accuracy": 0.7617, "macro_f1": 0.6228, "medium_recall": 0.1944, "high_recall": 0.9490},
    },
    "Random Forest": {
        "pooled_accuracy": 0.7767,
        "pooled_macro_f1": 0.6012,
        "2023": {"accuracy": 0.8624, "macro_f1": 0.5585, "medium_recall": 0.8380, "high_recall": 0.0182},
        "2024": {"accuracy": 0.7309, "macro_f1": 0.4218, "medium_recall": 0.4307, "high_recall": 0.0233},
        "2025": {"accuracy": 0.7530, "macro_f1": 0.6198, "medium_recall": 0.1988, "high_recall": 0.9566},
    },
    "LinearSVC": {
        "pooled_accuracy": 0.7904,
        "pooled_macro_f1": 0.6064,
        "2023": {"accuracy": 0.9096, "macro_f1": 0.8283, "medium_recall": 0.5493, "high_recall": 0.8000},
        "2024": {"accuracy": 0.7422, "macro_f1": 0.3974, "medium_recall": 0.3394, "high_recall": 0.0000},
        "2025": {"accuracy": 0.7451, "macro_f1": 0.5810, "medium_recall": 0.1163, "high_recall": 0.9541},
    },
    "RBF SVC": {
        "pooled_accuracy": 0.7943,
        "pooled_macro_f1": 0.6200,
        "2023": {"accuracy": 0.8512, "macro_f1": 0.5245, "medium_recall": 0.6796, "high_recall": 0.0000},
        "2024": {"accuracy": 0.8339, "macro_f1": 0.6359, "medium_recall": 0.0730, "high_recall": 0.8538},
        "2025": {"accuracy": 0.7225, "macro_f1": 0.5543, "medium_recall": 0.0825, "high_recall": 0.9541},
    },
}
