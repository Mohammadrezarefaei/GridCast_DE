import streamlit as st
import pandas as pd
import libsql_client
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="GridCast DE | Energy ML", layout="wide")
st.title("⚡ GridCast DE: Day-Ahead Electricity Market Forecast")
st.markdown("Automated Machine Learning pipeline forecasting German power market conditions.")

# اتصال به دیتابیس و خواندن داده‌ها
@st.cache_data(ttl=3600)
def load_data():
    url = "libsql://gridcast-db-maxrefaei.aws-us-east-1.turso.io"
    # توکن از سکرت‌های استریملیت خوانده می‌شود
    token = st.secrets["TURSO_AUTH_TOKEN"] 
    client = libsql_client.create_client_sync(url=url, auth_token=token)
    
    # گرفتن آخرین دیتای پیش‌بینی شده
    result = client.execute("SELECT * FROM daily_forecasts ORDER BY target_date DESC, hour ASC LIMIT 24")
    
    if not result.rows:
        return pd.DataFrame()
        
    df = pd.DataFrame(result.rows, columns=['id', 'target_date', 'hour', 'load_mw', 'solar_mw', 'wind_mw', 'price_eur', 'created_at'])
    df['datetime'] = pd.to_datetime(df['target_date']) + pd.to_timedelta(df['hour'], unit='h')
    return df

df = load_data()

if df.empty:
    st.warning("No data found in the database. Awaiting pipeline execution.")
else:
    # نمایش تاریخ پیش‌بینی
    target_date = df['target_date'].iloc[0]
    st.subheader(f"Forecast for: **{target_date}**")
    
    # ساخت چارت قیمت
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=df['datetime'], y=df['price_eur'], mode='lines+markers', name='Day-Ahead Price (€/MWh)', line=dict(color='firebrick', width=3)))
    fig_price.update_layout(title="Day-Ahead Price Forecast", xaxis_title="Time", yaxis_title="€ / MWh")
    st.plotly_chart(fig_price, use_container_width=True)
    
    # ساخت چارت بار مصرفی و تولید خورشیدی
    fig_grid = go.Figure()
    fig_grid.add_trace(go.Scatter(x=df['datetime'], y=df['load_mw'], mode='lines', name='Load Forecast (MW)', fill='tonexty', line=dict(color='royalblue')))
    fig_grid.add_trace(go.Scatter(x=df['datetime'], y=df['solar_mw'], mode='lines', name='Solar Generation (MW)', fill='tozeroy', line=dict(color='orange')))
    fig_grid.update_layout(title="Load vs. Solar Generation Forecast", xaxis_title="Time", yaxis_title="MW")
    st.plotly_chart(fig_grid, use_container_width=True)

    # نمایش دیتای خام
    with st.expander("View Raw Data"):
        st.dataframe(df[['datetime', 'load_mw', 'solar_mw', 'price_eur']])
