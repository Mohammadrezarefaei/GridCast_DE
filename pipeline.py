import pandas as pd
import requests
import joblib
import libsql_client
from datetime import datetime, timedelta
import os

# 1. Fetch Weather Data (Tomorrow)
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

# 2. Load Models & Predict
model_load = joblib.load('models/xgb_load_model.pkl')
model_solar = joblib.load('models/xgb_solar_model.pkl')
model_price = joblib.load('models/xgb_price_model.pkl')

X_load = df_tomorrow[['temperature_2m', 'hour', 'dayofweek', 'month']]
df_tomorrow['Load_MW'] = model_load.predict(X_load)

X_solar = df_tomorrow[['solar_radiation', 'hour', 'month']]
df_tomorrow['Solar_Gen'] = model_solar.predict(X_solar)

X_price = df_tomorrow[['Load_MW', 'Solar_Gen', 'windspeed_10m', 'hour', 'dayofweek']]
df_tomorrow['Price_EUR'] = model_price.predict(X_price)

# 3. Batch Insert to Turso
TURSO_URL = "libsql://gridcast-db-maxrefaei.aws-us-east-1.turso.io"
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN") # فراخوانی امن توکن

if not TURSO_AUTH_TOKEN:
    raise ValueError("TURSO_AUTH_TOKEN environment variable is missing!")

client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_AUTH_TOKEN)

values_placeholders = []
args_list = []
for _, row in df_tomorrow.iterrows():
    values_placeholders.append("(?, ?, ?, ?, ?, ?)")
    args_list.extend([
        str(row['time'].date()),
        int(row['hour']),
        float(row['Load_MW']),
        float(row['Solar_Gen']),
        0.0,
        float(row['Price_EUR'])
    ])

insert_query = f"""
INSERT INTO daily_forecasts (target_date, hour, load_mw, solar_mw, wind_mw, price_eur)
VALUES {', '.join(values_placeholders)}
"""

client.execute(insert_query, args_list)
print(f"✅ Prediction for {tomorrow} saved to Turso Cloud!")
