import streamlit as st
import pandas as pd
import libsql_client
import plotly.graph_objects as go

# تنظیمات اصلی صفحه
st.set_page_config(page_title="GridCast DE | Energy ML", layout="wide")
st.title("⚡ GridCast DE: Day-Ahead Electricity Market Forecast")
st.markdown("Automated Machine Learning pipeline forecasting German power market conditions.")

@st.cache_data(ttl=3600)
def load_data():
    url = "libsql://gridcast-db-maxrefaei.aws-us-east-1.turso.io"
    
    # روش امن برای خواندن رمز: جلوگیری از کرش کردن اپلیکیشن
    token = st.secrets.get("TURSO_AUTH_TOKEN")
    
    if not token:
        st.error("⚠️ توکن دیتابیس پیدا نشد! لطفاً در تنظیمات استریملیت (بخش Advanced Settings -> Secrets) توکن را وارد کنید.")
        return pd.DataFrame()

    try:
        # اتصال به دیتابیس
        client = libsql_client.create_client_sync(url=url, auth_token=token)
        result = client.execute("SELECT * FROM daily_forecasts ORDER BY target_date DESC, hour ASC LIMIT 24")
        
        if not result.rows:
            return pd.DataFrame()
            
        # تبدیل خروجی به دیتام‌فریم
        df = pd.DataFrame(result.rows, columns=['id', 'target_date', 'hour', 'load_mw', 'solar_mw', 'wind_mw', 'price_eur', 'created_at'])
        df['datetime'] = pd.to_datetime(df['target_date']) + pd.to_timedelta(df['hour'], unit='h')
        return df
        
    except Exception as e:
        st.error(f"⚠️ اتصال به دیتابیس برقرار نشد: {e}")
        return pd.DataFrame()

# فراخوانی تابع
df = load_data()

# رسم نمودارها در صورت وجود دیتا
if df.empty:
    st.warning("داده‌ای برای نمایش وجود ندارد. منتظر اجرای پایپ‌لاین در گیت‌هاب اکشنز باشید.")
else:
    target_date = df['target_date'].iloc[0]
    st.subheader(f"Forecast for: **{target_date}**")
    
    # 1. چارت قیمت
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=df['datetime'], y=df['price_eur'], mode='lines+markers', name='Day-Ahead Price (€/MWh)', line=dict(color='firebrick', width=3)))
    fig_price.update_layout(title="Day-Ahead Price Forecast", xaxis_title="Time", yaxis_title="€ / MWh")
    st.plotly_chart(fig_price, use_container_width=True)
    
    # 2. چارت بار مصرفی و تولید خورشیدی
    fig_grid = go.Figure()
    fig_grid.add_trace(go.Scatter(x=df['datetime'], y=df['load_mw'], mode='lines', name='Load Forecast (MW)', fill='tonexty', line=dict(color='royalblue')))
    fig_grid.add_trace(go.Scatter(x=df['datetime'], y=df['solar_mw'], mode='lines', name='Solar Gen (MW)', fill='tozeroy', line=dict(color='orange')))
    fig_grid.update_layout(title="Load vs. Solar Generation", xaxis_title="Time", yaxis_title="MW")
    st.plotly_chart(fig_grid, use_container_width=True)

    # 3. جدول دیتای خام
    with st.expander("View Raw Data"):
        st.dataframe(df[['datetime', 'load_mw', 'solar_mw', 'price_eur']])
