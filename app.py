import streamlit as st
import re
import os
import io
import sys
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_loader import get_all_data
from email_utils import send_daily_report
from agents import generate_strategic_report, data_analyst_agent
from data_processor import process_macro_data
from streamlit_javascript import st_javascript

st.set_page_config(page_title="VN McWatch", page_icon="🇻🇳", layout="wide")

# CSS Phong cách Bloomberg & Tối ưu khoảng trống
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    @media (max-width: 768px) {
        h1 {
            font-size: 2.5rem !important;
            white-space: nowrap;
        }
        h4 {
            font-size: 1.1rem !important;
            white-space: nowrap;
        }
    }
    /* Đồng bộ khoảng trống toàn hệ thống */
    div[data-baseweb="tab-list"] {
        margin-bottom: 0rem !important;
    }
    div[data-baseweb="tab-panel"] {
        padding-top: 1.5rem !important;
    }
    hr {
        margin-top: 1.5rem !important;
        margin-bottom: 1.5rem !important;
    }
    div[data-testid="stMarkdownContainer"] h4 {
        margin-top: 0rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style='display: flex; align-items: center;'>
    <img src="https://upload.wikimedia.org/wikipedia/commons/2/21/Flag_of_Vietnam.svg" width="55" style="margin-right: 15px; border-radius: 4px; box-shadow: 0px 0px 5px rgba(255,255,255,0.2);" /> 
    VN McWatch
</h1>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Cài đặt Dữ liệu")
    if st.button("Làm mới Dữ liệu (Reload CSV)"):
        with st.spinner("Đang tải dữ liệu từ Google Drive/Sheets..."):
            st.session_state.data_dict = get_all_data()
        st.success("Tải dữ liệu thành công!")

if "data_dict" not in st.session_state:
    st.session_state.data_dict = get_all_data()

def safe_to_datetime(series):
    return pd.to_datetime(series, dayfirst=True, errors='coerce')

def safe_date_range(label, key_prefix, default_start, default_end, min_date=None):
    res = st.date_input(label, value=(default_start, default_end), min_value=min_date, key=key_prefix)
    if isinstance(res, tuple):
        if len(res) == 2:
            return pd.to_datetime(res[0]), pd.to_datetime(res[1])
        elif len(res) == 1:
            return pd.to_datetime(res[0]), pd.to_datetime(res[0])
    elif res is not None:
        return pd.to_datetime(res), pd.to_datetime(res)
    return pd.to_datetime(default_start), pd.to_datetime(default_end)

def execute_python_code(code: str, data_dict: dict):
    match = re.search(r"```python\n(.*?)\n```", code, re.DOTALL)
    script = match.group(1) if match else code
        
    exec_globals = {
        'data_dict': data_dict,
        'st': st,
        'pd': pd,
        'plt': __import__('matplotlib.pyplot'),
        'np': __import__('numpy'),
        '__builtins__': __builtins__
    }
    
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    error_msg = None
    try:
        exec(script, exec_globals)
    except Exception as e:
        error_msg = f"Lỗi thực thi code: {str(e)}"
    finally:
        sys.stdout = old_stdout
    return redirected_output.getvalue(), error_msg

def plot_interbank(df_ib, start_date, end_date, show_legend=True):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    has_data = False
    target_term = 'ON'
    
    if not df_ib.empty:
        df1 = df_ib.copy()
        df1['Date'] = safe_to_datetime(df1['Date'])
        df1['Term_Clean'] = df1['Term'].astype(str).str.strip().str.upper()
        on_terms = [t for t in df1['Term_Clean'].unique() if t in ['ON', 'O/N', 'QUA ĐÊM', 'QUA DEM', 'OVERNIGHT']]
        target_term = on_terms[0] if on_terms else 'ON'
        
        df1 = df1[(df1['Date'] >= start_date) & (df1['Date'] <= end_date) & (df1['Term_Clean'] == target_term)].sort_values('Date')
        if not df1.empty:
            has_data = True
            df1['Volume'] = pd.to_numeric(df1['Volume'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df1['Rate'] = pd.to_numeric(df1['Rate'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            # --- LOẠI BỎ CÁC NGÀY KHÔNG CÓ DỮ LIỆU ---
            df1 = df1[(df1['Volume'] > 0) & (df1['Rate'] > 0)]
            
            df1['Date_Str'] = df1['Date'].dt.strftime('%d/%m/%Y')
            
            fig.add_trace(go.Bar(x=df1['Date_Str'], y=df1['Volume'], name='Volume', marker_color='rgba(0, 100, 255, 0.5)', showlegend=show_legend), secondary_y=False)
            fig.add_trace(go.Scatter(x=df1['Date_Str'], y=df1['Rate'], name='ON Rate', mode='lines', connectgaps=True, line=dict(color='#00FF00', width=2), showlegend=show_legend), secondary_y=True)
            
    fig.update_layout(
        template='plotly_dark', plot_bgcolor='#000000', paper_bgcolor='#000000', margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99, bgcolor="rgba(0,0,0,0.5)") if show_legend else None
    )
    fig.update_xaxes(type='category', nticks=15)
    return fig, has_data, target_term

def plot_omo(df_omo, start_date, end_date, show_legend=True):
    fig = go.Figure()
    has_data = False
    if not df_omo.empty:
        df2 = df_omo.copy()
        df2['Ngày'] = safe_to_datetime(df2['Ngày'])
        df2 = df2[(df2['Ngày'] >= start_date) & (df2['Ngày'] <= end_date)].sort_values('Ngày')
        if not df2.empty:
            has_data = True
            df2['Giá trị bơm ròng'] = pd.to_numeric(df2['Giá trị bơm ròng'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df2['Cumulative'] = df2['Giá trị bơm ròng'].cumsum()
            df2['Date_Str'] = df2['Ngày'].dt.strftime('%d/%m/%Y')
            fig.add_trace(go.Scatter(x=df2['Date_Str'], y=df2['Cumulative'], mode='lines', name='Cumulative OMO', connectgaps=True, line=dict(color='#FF00FF', width=2), showlegend=show_legend))
            
    fig.update_layout(
        template='plotly_dark', plot_bgcolor='#000000', paper_bgcolor='#000000', margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99, bgcolor="rgba(0,0,0,0.5)") if show_legend else None
    )
    fig.update_xaxes(type='category', nticks=15)
    return fig, has_data

def plot_yield_curve(df_us_yc, df_vn_yc, target_date=None, title="Yield Curve", show_legend=True):
    fig = go.Figure()
    vn_term_map = {
        '1 tháng': '1M', '3 tháng': '3M', '6 tháng': '6M', '9 tháng': '9M',
        '1 năm': '1Y', '2 năm': '2Y', '3 năm': '3Y', '5 năm': '5Y',
        '7 năm': '7Y', '10 năm': '10Y', '15 năm': '15Y', '20 năm': '20Y', '30 năm': '30Y'
    }
    std_order = ['1M', '3M', '6M', '9M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '15Y', '20Y', '30Y']
    has_data = False

    if not df_us_yc.empty:
        df3_us = df_us_yc.copy()
        df3_us['Date'] = safe_to_datetime(df3_us['Date'])
        if target_date:
            df3_us = df3_us[df3_us['Date'] <= target_date]
        if not df3_us.empty:
            has_data = True
            latest_us = df3_us.loc[df3_us['Date'].idxmax()]
            terms_us_avail = [t for t in std_order if t in latest_us.index]
            rates_us = [pd.to_numeric(latest_us[t], errors='coerce') for t in terms_us_avail]
            fig.add_trace(go.Scatter(x=terms_us_avail, y=rates_us, mode='lines+markers+text', name='US Yield Curve', showlegend=show_legend,
                                      text=[f"{r:.2f}%" if pd.notnull(r) else "" for r in rates_us], textposition="top center", line=dict(color='#00FFFF')))

    if not df_vn_yc.empty:
        df3_vn = df_vn_yc.copy()
        df3_vn['Date'] = safe_to_datetime(df3_vn['Date'])
        if target_date:
            df3_vn = df3_vn[df3_vn['Date'] <= target_date]
        if not df3_vn.empty:
            has_data = True
            latest_date_vn = df3_vn['Date'].max()
            latest_vn_df = df3_vn[df3_vn['Date'] == latest_date_vn].copy()
            terms_vn_raw = latest_vn_df['Term'].astype(str).str.strip().str.lower().tolist()
            terms_vn_mapped = [vn_term_map.get(t, t.upper()) for t in terms_vn_raw]
            
            if 'Spot_Rate_Annual_Pct' in latest_vn_df.columns:
                rates_vn = pd.to_numeric(latest_vn_df['Spot_Rate_Annual_Pct'].astype(str).str.replace(',', ''), errors='coerce').tolist()
            elif 'Par_Yield_Pct' in latest_vn_df.columns:
                rates_vn = pd.to_numeric(latest_vn_df['Par_Yield_Pct'].astype(str).str.replace(',', ''), errors='coerce').tolist()
            else:
                rates_vn = []
                
            if rates_vn:
                fig.add_trace(go.Scatter(x=terms_vn_mapped, y=rates_vn, mode='lines+markers+text', name='VN Yield Curve', showlegend=show_legend,
                                          text=[f"{r:.2f}%" if pd.notnull(r) else "" for r in rates_vn], textposition="bottom center", line=dict(color='#FFFF00')))

    fig.update_layout(
        template='plotly_dark', plot_bgcolor='#000000', paper_bgcolor='#000000', margin=dict(l=0, r=0, t=30, b=0), title=title,
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99, bgcolor="rgba(0,0,0,0.5)") if show_legend else None
    )
    fig.update_xaxes(categoryorder='array', categoryarray=std_order)
    return fig, has_data

def plot_exchange_rate(df_fx, start_date, end_date, show_legend=True):
    fig = go.Figure()
    has_data = False
    df_out = pd.DataFrame()
    if not df_fx.empty:
        df4 = df_fx.copy()
        df4['Date'] = safe_to_datetime(df4['Date'])
        if not df4.empty:
            df4_filter = df4[(df4['Date'] >= start_date) & (df4['Date'] <= end_date)].sort_values('Date')
            if not df4_filter.empty:
                has_data = True
                df_out = df4_filter.copy()
                for col in ['USD_VND_Rate', 'VCB_rate', 'Black_Market_rate']:
                    if col in df4_filter.columns:
                        df4_filter[col] = pd.to_numeric(df4_filter[col].astype(str).str.replace(',', ''), errors='coerce')
                
                df4_filter['Date_Str'] = df4_filter['Date'].dt.strftime('%d/%m/%Y')
                
                if 'USD_VND_Rate' in df4_filter.columns:
                    fig.add_trace(go.Scatter(x=df4_filter['Date_Str'], y=df4_filter['USD_VND_Rate'], mode='lines', name='Central Rate', connectgaps=True, line=dict(color='white'), showlegend=show_legend))
                if 'VCB_rate' in df4_filter.columns:
                    fig.add_trace(go.Scatter(x=df4_filter['Date_Str'], y=df4_filter['VCB_rate'], mode='lines', name='VCB Rate', connectgaps=True, line=dict(color='lime'), showlegend=show_legend))
                if 'Black_Market_rate' in df4_filter.columns:
                    fig.add_trace(go.Scatter(x=df4_filter['Date_Str'], y=df4_filter['Black_Market_rate'], mode='lines', name='Black Market', connectgaps=True, line=dict(color='red'), showlegend=show_legend))
                    
    fig.update_layout(
        template='plotly_dark', plot_bgcolor='#000000', paper_bgcolor='#000000', margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99, bgcolor="rgba(0,0,0,0.5)") if show_legend else None
    )
    fig.update_xaxes(type='category', nticks=15)
    return fig, has_data, df_out

# --- ĐO KÍCH THƯỚC MÀN HÌNH ĐỂ NHẬN DIỆN MOBILE ---
ui_width = st_javascript("window.innerWidth")
is_mobile = ui_width > 0 and ui_width <= 768

tab_dash, tab_chat = st.tabs(["📺 DASHBOARD MẶC ĐỊNH", "💬 AI VĨ MÔ"])

with tab_dash:

    data_dict = st.session_state.data_dict
    if not data_dict:
        st.warning("Đang tải dữ liệu...")
    else:
        df_ib = data_dict.get('SBV_Interbank_Rate', pd.DataFrame())
        df_omo = data_dict.get('SBV_OMO', pd.DataFrame())
        df_us_yc = data_dict.get('US_Yield_Curve', pd.DataFrame())
        df_vn_yc = data_dict.get('SBV_Yield_Curve', pd.DataFrame())
        df_fx = data_dict.get('SBV_Exchange_Rate', pd.DataFrame())
        df_fed = data_dict.get('FedWatch_Probabilities', pd.DataFrame())

        def highlight_prob(val):
            try:
                v = float(str(val).replace('%', '').strip())
                if v == 0: 
                    return 'color: #333333;'
                alpha = max(0.2, v / 100)
                return f'background-color: rgba(0, 255, 0, {alpha}); color: white;'
            except:
                return ''

        if is_mobile:
            # GIAO DIỆN MOBILE
            st.markdown("#### 1. Interbank ON Rate & Volume")
            f1, h1, _ = plot_interbank(df_ib, pd.to_datetime("2025-01-01"), pd.to_datetime("today"), show_legend=True)
            if h1: st.plotly_chart(f1, use_container_width=True, key="m_ib_chart")
            else: st.info("Không có dữ liệu.")
            
            st.markdown("---")
            st.markdown("#### 2. Cumulative Net OMO Injection")
            f2, h2 = plot_omo(df_omo, pd.to_datetime("2025-01-01"), pd.to_datetime("today"), show_legend=True)
            if h2: st.plotly_chart(f2, use_container_width=True, key="m_omo_chart")
            else: st.info("Không có dữ liệu.")
            
            st.markdown("---")
            st.markdown("#### 3. Yield Curve")
            fig3, has_data3 = plot_yield_curve(df_us_yc, df_vn_yc, target_date=None, title="", show_legend=True)
            if has_data3: st.plotly_chart(fig3, use_container_width=True, key="m_yc_chart")
            else: st.info("Không có dữ liệu Yield Curve.")
            
            st.markdown("---")
            st.markdown("#### 4. Exchange Rates")
            f4, h4, df_out4 = plot_exchange_rate(df_fx, pd.to_datetime("2025-01-01"), pd.to_datetime("today"), show_legend=True)
            if h4: 
                st.plotly_chart(f4, use_container_width=True, key="m_fx_chart")
                st.dataframe(df_out4.sort_values('Date', ascending=False), use_container_width=True)
            else: st.info("Không có dữ liệu.")
            
            st.markdown("---")
            st.markdown("#### 5. FedWatch Probabilities")
            if not df_fed.empty:
                try:
                    styled_fed = df_fed.style.applymap(highlight_prob, subset=df_fed.columns[1:])
                    st.dataframe(styled_fed, use_container_width=True)
                except AttributeError:
                    styled_fed = df_fed.style.map(highlight_prob, subset=df_fed.columns[1:])
                    st.dataframe(styled_fed, use_container_width=True)

        else:
            # GIAO DIỆN DESKTOP
            st.markdown("#### 1. Interbank ON Rate & Volume")
            t1_single, t1_compare = st.tabs(["🔥 Khung Thời Gian Đơn", "⚖️ So sánh 2 Khung Thời Gian"])
            with t1_single:
                d1_st, d1_en = safe_date_range("Chọn khoảng thời gian", 'ib_single', pd.to_datetime("2025-01-01"), pd.to_datetime("today"), min_date=pd.to_datetime("2004-07-12"))
                f1, h1, term1 = plot_interbank(df_ib, d1_st, d1_en, show_legend=True)
                if h1: st.plotly_chart(f1, use_container_width=True, key="ib_single_chart")
                else: st.info("Không có dữ liệu.")
                
            with t1_compare:
                c1_1, c1_2 = st.columns(2)
                with c1_1:
                    st_1, en_1 = safe_date_range("Khung thời gian 1", 'ib_c1', pd.to_datetime("2004-07-12"), pd.to_datetime("2024-12-31"), min_date=pd.to_datetime("2004-07-12"))
                    f1_c1, h1_c1, _ = plot_interbank(df_ib, st_1, en_1, show_legend=False)
                    if h1_c1: st.plotly_chart(f1_c1, use_container_width=True, key="ib_c1_chart")
                with c1_2:
                    st_2, en_2 = safe_date_range("Khung thời gian 2", 'ib_c2', pd.to_datetime("2025-01-01"), pd.to_datetime("today"), min_date=pd.to_datetime("2004-07-12"))
                    f1_c2, h1_c2, _ = plot_interbank(df_ib, st_2, en_2, show_legend=True)
                    if h1_c2: st.plotly_chart(f1_c2, use_container_width=True, key="ib_c2_chart")

            st.markdown("---")
            st.markdown("#### 2. Cumulative Net OMO Injection")
            t2_single, t2_compare = st.tabs(["🔥 Khung Thời Gian Đơn", "⚖️ So sánh 2 Khung Thời Gian"])
            with t2_single:
                d2_st, d2_en = safe_date_range("Chọn khoảng thời gian", 'omo_single', pd.to_datetime("2025-01-01"), pd.to_datetime("today"), min_date=pd.to_datetime("2010-10-14"))
                f2, h2 = plot_omo(df_omo, d2_st, d2_en, show_legend=True)
                if h2: st.plotly_chart(f2, use_container_width=True, key="omo_single_chart")
                else: st.info("Không có dữ liệu.")
                
            with t2_compare:
                c2_1, c2_2 = st.columns(2)
                with c2_1:
                    st_21, en_21 = safe_date_range("Khung thời gian 1", 'omo_c1', pd.to_datetime("2010-10-14"), pd.to_datetime("2024-12-31"), min_date=pd.to_datetime("2010-10-14"))
                    f2_c1, h2_c1 = plot_omo(df_omo, st_21, en_21, show_legend=False)
                    if h2_c1: st.plotly_chart(f2_c1, use_container_width=True, key="omo_c1_chart")
                with c2_2:
                    st_22, en_22 = safe_date_range("Khung thời gian 2", 'omo_c2', pd.to_datetime("2025-01-01"), pd.to_datetime("today"), min_date=pd.to_datetime("2010-10-14"))
                    f2_c2, h2_c2 = plot_omo(df_omo, st_22, en_22, show_legend=True)
                    if h2_c2: st.plotly_chart(f2_c2, use_container_width=True, key="omo_c2_chart")

            st.markdown("---")
            st.markdown("#### 3. Yield Curve")
            tab_latest, tab_compare = st.tabs(["🔥 Mới nhất", "⚖️ So sánh theo ngày"])
            
            with tab_latest:
                fig3, has_data3 = plot_yield_curve(df_us_yc, df_vn_yc, target_date=None, title="", show_legend=True)
                if has_data3:
                    st.plotly_chart(fig3, use_container_width=True, key="yc_single_chart")
                else:
                    st.info("Không có dữ liệu Yield Curve.")
                    
            with tab_compare:
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    date_1 = st.date_input("Chọn ngày 1", pd.to_datetime("today") - pd.Timedelta(days=30), min_value=pd.to_datetime("2013-03-19"), key="yc1")
                    fig_c1, h1 = plot_yield_curve(df_us_yc, df_vn_yc, target_date=pd.to_datetime(date_1), title=f"Đến ngày {date_1.strftime('%d/%m/%Y')}", show_legend=False)
                    if h1: st.plotly_chart(fig_c1, use_container_width=True, key="yc_c1_chart")
                with col_c2:
                    date_2 = st.date_input("Chọn ngày 2", pd.to_datetime("today"), min_value=pd.to_datetime("2013-03-19"), key="yc2")
                    fig_c2, h2 = plot_yield_curve(df_us_yc, df_vn_yc, target_date=pd.to_datetime(date_2), title=f"Đến ngày {date_2.strftime('%d/%m/%Y')}", show_legend=True)
                    if h2: st.plotly_chart(fig_c2, use_container_width=True, key="yc_c2_chart")

            st.markdown("---")
            st.markdown("#### 4. Exchange Rates")
            t4_single, t4_compare = st.tabs(["🔥 Khung Thời Gian Đơn", "⚖️ So sánh 2 Khung Thời Gian"])
            with t4_single:
                d4_st, d4_en = safe_date_range("Chọn khoảng thời gian", 'fx_single', pd.to_datetime("2025-01-01"), pd.to_datetime("today"), min_date=pd.to_datetime("2004-04-27"))
                f4, h4, df_out4 = plot_exchange_rate(df_fx, d4_st, d4_en, show_legend=True)
                if h4: 
                    st.plotly_chart(f4, use_container_width=True, key="fx_single_chart")
                    st.dataframe(df_out4.sort_values('Date', ascending=False), use_container_width=True)
                else: st.info("Không có dữ liệu.")
                
            with t4_compare:
                c4_1, c4_2 = st.columns(2)
                with c4_1:
                    st_41, en_41 = safe_date_range("Khung thời gian 1", 'fx_c1', pd.to_datetime("2004-04-27"), pd.to_datetime("2024-12-31"), min_date=pd.to_datetime("2004-04-27"))
                    f4_c1, h4_c1, _ = plot_exchange_rate(df_fx, st_41, en_41, show_legend=False)
                    if h4_c1: st.plotly_chart(f4_c1, use_container_width=True, key="fx_c1_chart")
                with c4_2:
                    st_42, en_42 = safe_date_range("Khung thời gian 2", 'fx_c2', pd.to_datetime("2025-01-01"), pd.to_datetime("today"), min_date=pd.to_datetime("2004-04-27"))
                    f4_c2, h4_c2, _ = plot_exchange_rate(df_fx, st_42, en_42, show_legend=True)
                    if h4_c2: st.plotly_chart(f4_c2, use_container_width=True, key="fx_c2_chart")

            st.markdown("---")
            st.markdown("#### 5. FedWatch Probabilities")
            if not df_fed.empty:
                try:
                    styled_fed = df_fed.style.applymap(highlight_prob, subset=df_fed.columns[1:])
                    st.dataframe(styled_fed, use_container_width=True)
                except AttributeError:
                    styled_fed = df_fed.style.map(highlight_prob, subset=df_fed.columns[1:])
                    st.dataframe(styled_fed, use_container_width=True)

with tab_chat:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Nhập lệnh (VD: Cập nhật, Thống kê tỷ giá OMO...)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            is_report = bool(re.search(r'(cập nhật|báo cáo)', prompt.lower()))
                
            if is_report:
                message_placeholder.markdown("🔄 Đang xử lý dữ liệu và tạo báo cáo vĩ mô (có thể mất 1-2 phút)...")
                data_context = process_macro_data(st.session_state.data_dict)
                
                prompt_path = "prompt.txt"
                if os.path.exists(prompt_path):
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        prompt_content = f.read()
                else:
                    prompt_content = "Vui lòng upload file prompt.txt."
                    
                report_md = generate_strategic_report(prompt_content, data_context)
                message_placeholder.markdown(report_md)
                
                with st.spinner("Đang gửi báo cáo qua email..."):
                    if send_daily_report(report_md):
                        st.success("Đã gửi báo cáo qua Email thành công!")
                    else:
                        st.error("Chưa thể gửi email (kiểm tra cấu hình SMTP).")
                        
                st.session_state.messages.append({"role": "assistant", "content": report_md})
                
            else:
                chat_context = ""
                for msg in st.session_state.messages:
                    role_name = "USER" if msg["role"] == "user" else "ASSISTANT"
                    chat_context += f"\n{role_name}: {msg['content']}"
                    
                MAX_LOOPS = 3
                current_loop = 0
                
                with st.spinner("AI đang tư duy và phân tích..."):
                    while current_loop < MAX_LOOPS:
                        response = data_analyst_agent(chat_context)
                        match = re.search(r"```python\n(.*?)\n```", response, re.DOTALL)
                        
                        if match:
                            code_block = match.group(0)
                            script = match.group(1)
                            text_part = response.replace(code_block, "").strip()
                            if text_part:
                                st.markdown(text_part)
                                
                            st.markdown("🧑‍💻 **Đang chạy code trích xuất dữ liệu:**")
                            st.code(script, language="python")
                            
                            output, err = execute_python_code(script, st.session_state.data_dict)
                            obs = f"\nKẾT QUẢ CHẠY MÃ HỆ THỐNG:\nOutput:\n{output}\nError:\n{err}"
                            
                            chat_context += f"\nASSISTANT (Sinh code):\n{code_block}\nSYSTEM (Observation): {obs}"
                            
                            if err:
                                st.error(f"Lỗi khi chạy code: {err}")
                            if output:
                                with st.expander("Xem dữ liệu thô"):
                                    st.text(output)
                                    
                            current_loop += 1
                            continue
                        else:
                            message_placeholder.markdown(response)
                            st.session_state.messages.append({"role": "assistant", "content": response})
                            break
