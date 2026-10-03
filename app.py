import streamlit as st
import pandas as pd
import libsql_client

# 1. Page Configuration
st.set_page_config(page_title="GridCast DE", page_icon="⚡", layout="wide")

st.title("⚡ GridCast DE: Day-Ahead Electricity Market Forecast")
st.markdown("Automated Machine Learning pipeline forecasting German power market conditions.")

# 2. Database Connection Settings
# Using HTTPS to bypass WebSocket/Firewall (Error 400) issues
TURSO_URL = "https://gridcast-db-maxrefaei.aws-us-east-1.turso.io"

# Fetching the token safely from Streamlit Secrets
try:
    raw_token = st.secrets["TURSO_AUTH_TOKEN"]
    # Clean up the token just in case there are invisible spaces or quotes
    TURSO_AUTH_TOKEN = raw_token.strip().strip("'").strip('"')
except FileNotFoundError:
    st.error("🚨 Secrets file not found. Please configure the token in Streamlit Cloud Advanced Settings.")
    st.stop()
except KeyError:
    st.error("🚨 `TURSO_AUTH_TOKEN` is missing in Streamlit Secrets. Please add it via Advanced Settings.")
    st.stop()

# 3. Data Fetching Function (Cached for performance)
@st.cache_data(ttl=3600)  # Cache data for 1 hour to reduce Turso database calls
def load_data():
    try:
        # Connect to Turso Cloud
        client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_AUTH_TOKEN)
        
        # Fetch the latest 7 days of forecasts (168 hours)
        result = client.execute("SELECT * FROM daily_forecasts ORDER BY target_date DESC, hour DESC LIMIT 168")
        
        if not result.rows:
            return pd.DataFrame() # Return empty DataFrame if no data exists

        # Parse data into Pandas
        columns = ["target_date", "hour", "load_mw", "solar_mw", "wind_mw", "price_eur"]
        data = [[row[0], row[1], row[2], row[3], row[4], row[5]] for row in result.rows]
        
        df = pd.DataFrame(data, columns=columns)
        
        # Create a proper datetime index for plotting
        df['datetime'] = pd.to_datetime(df['target_date']) + pd.to_timedelta(df['hour'], unit='h')
        df.set_index('datetime', inplace=True)
        df.sort_index(ascending=True, inplace=True) # Sort chronologically for line charts
        
        client.close()
        return df

    except Exception as e:
        st.error(f"🚨 Connection failed: {str(e)}")
        return None

# 4. Main Dashboard UI
with st.spinner("Fetching latest market forecasts from Turso Cloud..."):
    df = load_data()

if df is None:
    st.warning("⚠️ Failed to load data. Please verify your Turso URL and Auth Token.")
elif df.empty:
    st.info("🕒 Database is connected successfully, but no forecasts are available yet. Waiting for GitHub Actions...")
else:
    st.success("✅ Live data successfully synced with Turso Cloud!")
    
    # KPIs / Metrics Row
    st.subheader("📊 Market Overview (Latest Forecast)")
    latest_record = df.iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Predicted Price (EUR/MWh)", f"€ {latest_record['price_eur']:.2f}")
    col2.metric("Grid Load (MW)", f"{latest_record['load_mw']:,.0f} MW")
    col3.metric("Solar Generation (MW)", f"{latest_record['solar_mw']:,.0f} MW")

    st.divider()

    # Charts
    st.subheader("💶 Day-Ahead Price Forecast")
    st.line_chart(df['price_eur'], color="#ffaa00")

    st.divider()

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("🏭 Load Demand")
        st.line_chart(df['load_mw'], color="#ff2b2b")
    
    with chart_col2:
        st.subheader("☀️ Solar Injection")
        st.line_chart(df['solar_mw'], color="#00d4ff")

    st.divider()

    # Data Table
    st.subheader("📋 Raw Forecast Data")
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)
