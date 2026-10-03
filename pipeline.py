import pandas as pd
import requests
import xgboost as xgb
import libsql_client
from datetime import datetime, timedelta
import os

# 1. Fetch Weather Data (Tomorrow)
print("🌤️ Fetching weather data from Open-Meteo...")
url = "https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m,direct_radiation,windspeed_10m&timezone=Europe%2FBerlin&forecast_days=2"
response = requests.get(url)
data = response.json()

df_future = pd.DataFrame({
    "time": pd.to_datetime(data["hourly"]["time"]),
    "temperature_2m": data["hourly"]["temperature_2m"],
    "solar_radiation": data["hourly"]["direct_radiation"],
    "windspeed_10m": data["hourly"]["windspeed_10m"]
})

tomorrow = (datetime.now() + timedelta(days=1)).date()
df_tomorrow = df_future[df_future['time'].dt.date == tomorrow].copy()

df_tomorrow['hour'] = df_tomorrow['time'].dt.hour
df_tomorrow['dayofweek'] = df_tomorrow['time'].dt.dayofweek
df_tomorrow['month'] = df_tomorrow['time'].dt.month

# 2. Load Models & Predict (Using XGBoost JSON natively)
print("🧠 Loading XGBoost models from JSON files...")
model_load = xgb.XGBRegressor()
model_load.load_model('models/xgb_load_model.json')

model_solar = xgb.XGBRegressor()
model_solar.load_model('models/xgb_solar_model.json')

model_price = xgb.XGBRegressor()
model_price.load_model('models/xgb_price_model.json')

print("🔮 Generating predictions...")
X_load = df_tomorrow[['temperature_2m', 'hour', 'dayofweek', 'month']]
df_tomorrow['Load_MW'] = model_load.predict(X_load)

X_solar = df_tomorrow[['solar_radiation', 'hour', 'month']]
df_tomorrow['Solar_Gen'] = model_solar.predict(X_solar)

X_price = df_tomorrow[['Load_MW', 'Solar_Gen', 'windspeed_10m', 'hour', 'dayofweek']]
df_tomorrow['Price_EUR'] = model_price.predict(X_price)

# 3. Batch Insert to Turso
# Using HTTPS to bypass GitHub Action WebSocket/Firewall (Error 400)
TURSO_URL = "https://gridcast-db-maxrefaei.aws-us-east-1.turso.io"
raw_token = os.getenv("TURSO_AUTH_TOKEN")

if not raw_token:
    raise ValueError("🚨 TURSO_AUTH_TOKEN is missing in GitHub Secrets!")

TURSO_AUTH_TOKEN = raw_token.strip().strip("'").strip('"')

print("🔄 Connecting to Turso Database via HTTPS...")
client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_AUTH_TOKEN)

try:
    print("🛠️ Checking/Creating Table...")
    # Ensures the table exists so we don't get 'KeyError: result'
    client.execute("""
    CREATE TABLE IF NOT EXISTS daily_forecasts (
        target_date TEXT,
        hour INTEGER,
        load_mw REAL,
        solar_mw REAL,
        wind_mw REAL,
        price_eur REAL
    )
    """)

    print("📝 Preparing data for insertion...")
    values_placeholders = []
    args_list = []
    for _, row in df_tomorrow.iterrows():
        values_placeholders.append("(?, ?, ?, ?, ?, ?)")
        args_list.extend([
            str(row['time'].date()),
            int(row['hour']),
            float(row['Load_MW']),
            float(row['Solar_Gen']),
            float(row['windspeed_10m']),
            float(row['Price_EUR'])
        ])

    insert_query = f"""
    INSERT INTO daily_forecasts (target_date, hour, load_mw, solar_mw, wind_mw, price_eur)
    VALUES {', '.join(values_placeholders)}
    """

    print("🚀 Sending data to Turso...")
    client.execute(insert_query, args_list)
    print(f"✅ Prediction for {tomorrow} successfully saved to Turso Cloud!")
    
    # Crucial: Closes the connection so GitHub Action finishes cleanly
    client.close()

except Exception as e:
    print(f"❌ 🚨 PYTHON ERROR: {str(e)}")
    # Force close connection even if an error occurs
    client.close()
    raise e
