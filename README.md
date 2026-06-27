# OtoKarar — Car Recommendation System

A multi-criteria car recommendation system for the Turkish market, built with Streamlit and the TOPSIS decision-making method.

## Features

- Weighted multi-criteria ranking based on price, fuel consumption, and performance
- Total Cost of Ownership (TCO) calculation for realistic comparison
- Radar chart visualization for side-by-side vehicle comparison
- Interactive sidebar filters (budget, fuel type, transmission)
- Dashboard-style UI with styled comparison cards

## Tech Stack

- **Framework:** Streamlit
- **Decision Method:** TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution)
- **Visualization:** Plotly
- **Data Handling:** Pandas, NumPy

## How It Works

The app scores and ranks vehicles using a weighted TOPSIS model across multiple criteria (price, fuel efficiency, performance), helping users find the option closest to their ideal trade-off rather than relying on a single metric.

## Setup

```bash
pip install -r requirements.txt
streamlit run oto/main.py
```

Optional: to enable live data enrichment via Car API (RapidAPI), copy `.env.example` to `.env` and add your own API key. The app runs without it, using the built-in dataset.

## Note

This was originally developed as a university course project and is being extended further.
