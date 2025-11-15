import asyncio
from plants.modules.pollination.prediction.train_pollination import train_model_for_probability_of_seed_production

if __name__ == "__main__":
    results, shap_values, df_preprocessed = asyncio.run(train_model_for_probability_of_seed_production())
    for key, value in results.items():
        print(f"{key}: {value}")
    a = 1