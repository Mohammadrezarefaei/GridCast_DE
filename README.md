# ⚡ GridCast DE: Day-Ahead Electricity Market Forecast

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-Cloud-red?style=for-the-badge&logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/Turso-Cloud-purple?style=for-the-badge&logo=turso&logoColor=white" />
  <img src="https://img.shields.io/badge/XGBoost-Models-orange?style=for-the-badge&logo=xgboost&logoColor=white" />
  <img src="https://img.shields.io/badge/GitHub-Actions-20232A?style=for-the-badge&logo=githubactions&logoColor=white" />
</p>

An automated, end-to-end Machine Learning pipeline designed to forecast German day-ahead electricity market conditions (Load Demand, Solar Generation, and Market Clearing Prices). The system fetches real-time meteorological forecasts, runs optimized XGBoost regressors via GitHub Actions, persists predictions to Turso Cloud (libSQL), and visualizes live insights through an interactive Streamlit dashboard.

🌐 **Live Streamlit App:** [GridCast DE Dashboard](https://gridcastde-skgkueczogrjzjamfa8gru.streamlit.app/)

---

## 🏗️ Architecture & Workflow

```text
┌─────────────────┐       ┌──────────────────────┐       ┌─────────────────┐
│  Open-Meteo API │──────▶│    GitHub Actions    │──────▶│   Turso Cloud   │
│(Weather Forecast│       │ (XGBoost Prediction  │       │  (libSQL DB)    │
│  & Meteorological Data) │       │      Pipeline)       │       └────────T────────┘
└─────────────────┘       └──────────────────────┘                │
                                                                  ▼
                                                          ┌─────────────────┐
                                                          │Streamlit Dashboard│
                                                          │ (Live Analytics)│
                                                          └─────────────────┘
