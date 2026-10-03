import streamlit as st
import pandas as pd
import libsql_client
import os
from datetime import datetime

# تنظیمات صفحه استریملیت
st.set_page_config(
    page_title="GridCast DE - German Power Market Forecast",
    page_icon="⚡",
    layout="wide"
)

# اتصال به دیتابیس Turso با پروتکل HTTPS
TURSO_URL = "https://gridcast-db-maxrefaei.aws-us-east-1.turso.io"
raw_token = os.getenv("TURSO_AUTH_TOKEN")

if not raw_token:
    # اگر توکن در Secrets گیت‌هاب نبود، می‌توانید به صورت موقت اینجا قرار دهید یا از Secrets استریملیت بخوانید
    TURSO_AUTH_TOKEN = st.secrets.get("TURSO_AUTH_TOKEN", "")
else:
    TURSO_AUTH_TOKEN = raw_token.strip().strip("'").strip('"')

@st.cache_data(ttl=600)
def load_data():
    if not TURSO_AUTH_TOKEN:
        return pd.DataFrame()
    
    client = libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_AUTH_TOKEN)
    try:
        result = client.execute("SELECT target_date, hour, load_mw, solar_mw, wind_mw, price_eur FROM daily_forecasts ORDER BY target_date DESC, hour ASC")
        rows = result.rows
        client.close()
        
        if not rows:
            return pd.DataFrame()
            
        df = pd.DataFrame(rows, columns=["target_date", "hour", "load_mw", "solar_mw", "wind_mw", "price_eur"])
        df['datetime'] = pd.to_datetime(df['target_date']) + pd.to_timedelta(df['hour'], unit='h')
        return df
    except Exception as e:
        client.close()
        st.error(f"خطا در اتصال به دیتابیس: {str(e)}")
        return pd.DataFrame()

# هдер اصلی سایت
st.title("⚡ GridCast DE: Day-Ahead Electricity Market Forecast")
st.markdown("Automated Machine Learning pipeline forecasting German power market conditions.")

# بارگذاری داده‌ها
df = load_data()

if df.empty:
    st.warning("⚠️ هیچ داده‌ای در دیتابیس یافت نشد یا ارتباط با Turso برقرار نشد.")
else:
    st.success("✅ Live data successfully synced with Turso Cloud!")
    
    # فیلتر کردن و پیدا کردن آخرین داده معتبر (برای جلوگیری از نمایش مقادیر صفر)
    valid_df = df[df['load_mw'] > 0]
    latest_record = valid_df.iloc[-1] if not valid_df.empty else df.iloc[-1]

    # بخش کارت‌های نمایشی بالا (Market Overview)
    st.subheader("📊 Market Overview (Latest Forecast)")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Predicted Price (EUR/MWh)", value=f"€ {latest_record['price_eur']:.2f}")
    with col2:
        st.metric(label="Grid Load (MW)", value=f"{int(latest_record['load_mw']):,} MW")
    with col3:
        st.metric(label="Solar Generation (MW)", value=f"{int(latest_record['solar_mw']):,} MW")

    st.markdown("---")

    # نمودار پیش‌بینی قیمت
    st.subheader("💶 Day-Ahead Price Forecast")
    st.line_chart(df.set_index('datetime')['price_eur'], color="#FF4B4B")

    # نمودار بار شبکه
    st.subheader("🏭 Load Demand")
    st.line_chart(df.set_index('datetime')['load_mw'], color="#FFA421")

    # نمودار تولید خورشیدی
    st.subheader("☀️ Solar Injection")
    st.line_chart(df.set_index('datetime')['solar_mw'], color="#00C0F2")

    # جدول داده‌های خام
    with st.expander("📋 Raw Forecast Data"):
        st.dataframe(df)
