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
    import datetime
    val_start = pd.to_datetime(default_start).date()
    val_end = pd.to_datetime(default_end).date()
    min_val = pd.to_datetime(min_date).date() if min_date else None
    max_val = datetime.date.today()
    
    res = st.date_input(label, value=(val_start, val_end), min_value=min_val, max_value=max_val, key=key_prefix)
    if isinstance(res, tuple):
        if len(res) == 2:
            return pd.to_datetime(res[0]), pd.to_datetime(res[1])
        elif len(res) == 1:
            return pd.to_datetime(res[0]), pd.to_datetime(res[0])
    elif res is not None:
        return pd.to_datetime(res), pd.to_datetime(res)
    return pd.to_datetime(default_start), pd.to_datetime(default_end)

def get_term_days(term_str):
    if pd.isna(term_str):
        return 99999
    t = str(term_str).strip().lower()
    if t in ['qua đêm', 'on', 'o/n', 'overnight']: return 1
    if 'tuần' in t or 'week' in t:
        num = re.findall(r'\d+', t)
        return int(num[0]) * 7 if num else 7
    if 'năm' in t or 'year' in t or t.endswith('y'):
        num = re.findall(r'\d+', t)
        return int(num[0]) * 365 if num else 365
    if 'tháng' in t or 'month' in t or t.endswith('m'):
        num = re.findall(r'\d+', t)
        return int(num[0]) * 30 if num else 30
    return 99999

def sort_df_by_date_and_term(df):
    if 'Date' not in df.columns or 'Term' not in df.columns:
        return df
    df_sorted = df.copy()
    df_sorted['Term_Days'] = df_sorted['Term'].apply(get_term_days)
    df_sorted = df_sorted.sort_values(['Date', 'Term_Days'], ascending=[False, True])
    return df_sorted.drop(columns=['Term_Days'])

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
    df_out = pd.DataFrame()
    
    if not df_ib.empty:
        df1 = df_ib.copy()
        df1['Date'] = safe_to_datetime(df1['Date'])
        
        df_out = df1[(df1['Date'] >= start_date) & (df1['Date'] <= end_date)].copy()
        if 'Term_Clean' in df_out.columns:
            df_out = df_out.drop(columns=['Term_Clean'])
            
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
            
            latest_row = df1.dropna(subset=['Rate']).iloc[-1] if not df1.dropna(subset=['Rate']).empty else None
            if latest_row is not None:
                fig.add_annotation(x=latest_row['Date_Str'], y=latest_row['Rate'], text=f"{latest_row['Rate']:.2f}%", showarrow=True, arrowhead=1, yref="y2", ax=-20, ay=-30, font=dict(color="#00FF00", size=12))
            
    fig.update_layout(
        template='plotly_dark', plot_bgcolor='#000000', paper_bgcolor='#000000', margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99, bgcolor="rgba(0,0,0,0.5)") if show_legend else None
    )
    fig.update_xaxes(type='category', nticks=15)
    return fig, has_data, target_term, df_out

def plot_omo(df_omo, start_date, end_date, show_legend=True):
    fig = go.Figure()
    has_data = False
    df_out = pd.DataFrame()
    if not df_omo.empty:
        df2 = df_omo.copy()
        df2['Ngày'] = safe_to_datetime(df2['Ngày'])
        df2 = df2[(df2['Ngày'] >= start_date) & (df2['Ngày'] <= end_date)].sort_values('Ngày')
        if not df2.empty:
            has_data = True
            df2['Giá trị bơm ròng'] = pd.to_numeric(df2['Giá trị bơm ròng'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df2['Cumulative'] = df2['Giá trị bơm ròng'].cumsum()
            df_out = df2.copy()
            df2['Date_Str'] = df2['Ngày'].dt.strftime('%d/%m/%Y')
            fig.add_trace(go.Scatter(x=df2['Date_Str'], y=df2['Cumulative'], mode='lines', name='Cumulative OMO', connectgaps=True, line=dict(color='#FF00FF', width=2), showlegend=show_legend))
            
            latest_row = df2.iloc[-1] if not df2.empty else None
            if latest_row is not None:
                fig.add_annotation(x=latest_row['Date_Str'], y=latest_row['Cumulative'], text=f"{latest_row['Cumulative']:,.0f}", showarrow=True, arrowhead=1, ax=-20, ay=-30, font=dict(color="#FF00FF", size=12))
            
    fig.update_layout(
        template='plotly_dark', plot_bgcolor='#000000', paper_bgcolor='#000000', margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99, bgcolor="rgba(0,0,0,0.5)") if show_legend else None
    )
    fig.update_xaxes(type='category', nticks=15)
    return fig, has_data, df_out

def plot_yield_curve(df_us_yc, df_vn_yc, target_date=None, title="Yield Curve", show_legend=True):
    fig = go.Figure()
    vn_term_map = {
        '1 tháng': '1M', '3 tháng': '3M', '6 tháng': '6M', '9 tháng': '9M',
        '1 năm': '1Y', '2 năm': '2Y', '3 năm': '3Y', '5 năm': '5Y',
        '7 năm': '7Y', '10 năm': '10Y', '15 năm': '15Y', '20 năm': '20Y', '30 năm': '30Y'
    }
    std_order = ['1M', '3M', '6M', '9M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '15Y', '20Y', '30Y']
    has_data = False
    df_us_out = pd.DataFrame()
    df_vn_out = pd.DataFrame()

    if not df_us_yc.empty:
        df3_us = df_us_yc.copy()
        df3_us['Date'] = safe_to_datetime(df3_us['Date'])
        if target_date:
            df3_us = df3_us[df3_us['Date'] <= target_date]
        if not df3_us.empty:
            has_data = True
            latest_us = df3_us.loc[df3_us['Date'].idxmax()]
            df_us_out = latest_us.to_frame().T
            terms_us_avail = [t for t in std_order if t in latest_us.index]
            rates_us = [pd.to_numeric(latest_us[t], errors='coerce') for t in terms_us_avail]
            fig.add_trace(go.Scatter(x=terms_us_avail, y=rates_us, mode='lines+markers+text', name='US Yield Curve', showlegend=show_legend,
                                      text=[f"{r:.2f}%" if pd.notnull(r) else "" for r in rates_us], textposition="top center", line=dict(color='#00FFFF')))

    if not df_vn_yc.empty:
        df3_vn = df_vn_yc.copy()
        df3_vn['Date'] = safe_to_datetime(df3_vn['Date'])
        if target_date:
            df3_vn = df3_vn[df3_vn['Date'] <= target_date]
        if not df_vn_yc.empty:
            has_data = True
            latest_date_vn = df3_vn['Date'].max()
            latest_vn_df = df3_vn[df3_vn['Date'] == latest_date_vn].copy()
            df_vn_out = latest_vn_df.copy()
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

def plot_exchange_rate(df_fx, df_us_fx, start_date, end_date, show_legend=True):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    has_data = False
    df_out = pd.DataFrame()
    if not df_fx.empty:
        df4 = df_fx.copy()
        df4['Date'] = safe_to_datetime(df4['Date'])
        
        cols_to_keep_vn = ['Date'] + [c for c in ['USD_VND_Rate', 'VCB_rate', 'Black_Market_rate'] if c in df4.columns]
        df_merged = df4[cols_to_keep_vn].copy()
        for col in cols_to_keep_vn[1:]:
            df_merged[col] = pd.to_numeric(df_merged[col].astype(str).str.replace(',', ''), errors='coerce')
            
        if not df_us_fx.empty:
            df5 = df_us_fx.copy()
            df5['Date'] = safe_to_datetime(df5['Date'])
            
            dxy_col = None
            for c in df5.columns:
                if c != 'Date':
                    dxy_col = c
                    break
                    
            if dxy_col:
                df5[dxy_col] = pd.to_numeric(df5[dxy_col].astype(str).str.replace(',', ''), errors='coerce')
                df5_subset = df5[['Date', dxy_col]].rename(columns={dxy_col: 'DXY'})
                
                df_merged = pd.merge(df_merged, df5_subset, on='Date', how='outer').sort_values('Date')
                
                # Forward fill DXY
                df_merged['DXY'] = df_merged['DXY'].ffill()
                
        # Filter by date range
        df_filter = df_merged[(df_merged['Date'] >= start_date) & (df_merged['Date'] <= end_date)].sort_values('Date')
        
        if not df_filter.empty:
            has_data = True
            
            # Remove rows where all rates are NaN to clean up axis
            rate_cols = [c for c in ['USD_VND_Rate', 'VCB_rate', 'Black_Market_rate', 'DXY'] if c in df_filter.columns]
            df_filter = df_filter.dropna(subset=rate_cols, how='all')
            
            df_out = df_filter.copy()
            df_filter['Date_Str'] = df_filter['Date'].dt.strftime('%d/%m/%Y')
            
            if 'USD_VND_Rate' in df_filter.columns:
                fig.add_trace(go.Scatter(x=df_filter['Date_Str'], y=df_filter['USD_VND_Rate'], mode='lines', name='Central Rate', connectgaps=True, line=dict(color='white'), showlegend=show_legend), secondary_y=False)
                lr = df_filter.dropna(subset=['USD_VND_Rate']).iloc[-1] if not df_filter.dropna(subset=['USD_VND_Rate']).empty else None
                if lr is not None: fig.add_annotation(x=lr['Date_Str'], y=lr['USD_VND_Rate'], text=f"{lr['USD_VND_Rate']:,.0f}", showarrow=True, arrowhead=1, ax=-30, ay=10, font=dict(color="white", size=11), yref="y1")
            if 'VCB_rate' in df_filter.columns:
                fig.add_trace(go.Scatter(x=df_filter['Date_Str'], y=df_filter['VCB_rate'], mode='lines', name='VCB Rate', connectgaps=True, line=dict(color='lime'), showlegend=show_legend), secondary_y=False)
                lr = df_filter.dropna(subset=['VCB_rate']).iloc[-1] if not df_filter.dropna(subset=['VCB_rate']).empty else None
                if lr is not None: fig.add_annotation(x=lr['Date_Str'], y=lr['VCB_rate'], text=f"{lr['VCB_rate']:,.0f}", showarrow=True, arrowhead=1, ax=-30, ay=-10, font=dict(color="lime", size=11), yref="y1")
            if 'Black_Market_rate' in df_filter.columns:
                fig.add_trace(go.Scatter(x=df_filter['Date_Str'], y=df_filter['Black_Market_rate'], mode='lines', name='Black Market', connectgaps=True, line=dict(color='red'), showlegend=show_legend), secondary_y=False)
                lr = df_filter.dropna(subset=['Black_Market_rate']).iloc[-1] if not df_filter.dropna(subset=['Black_Market_rate']).empty else None
                if lr is not None: fig.add_annotation(x=lr['Date_Str'], y=lr['Black_Market_rate'], text=f"{lr['Black_Market_rate']:,.0f}", showarrow=True, arrowhead=1, ax=10, ay=-30, font=dict(color="red", size=11), yref="y1")
            if 'DXY' in df_filter.columns:
                fig.add_trace(go.Scatter(x=df_filter['Date_Str'], y=df_filter['DXY'], mode='lines', name='DXY', connectgaps=True, line=dict(color='orange', dash='dot'), showlegend=show_legend), secondary_y=True)
                lr = df_filter.dropna(subset=['DXY']).iloc[-1] if not df_filter.dropna(subset=['DXY']).empty else None
                if lr is not None: fig.add_annotation(x=lr['Date_Str'], y=lr['DXY'], text=f"{lr['DXY']:.2f}", showarrow=True, arrowhead=1, ax=10, ay=30, font=dict(color="orange", size=11), yref="y2")
                
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
        df_us_fx = data_dict.get('US_Exchange_Rate', pd.DataFrame())
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
            f1, h1, _, df_out1 = plot_interbank(df_ib, pd.to_datetime("2025-01-01"), pd.to_datetime("today"), show_legend=True)
            if h1: 
                st.plotly_chart(f1, width="stretch", key="m_ib_chart")
                st.dataframe(sort_df_by_date_and_term(df_out1), width="stretch")
            else: st.info("Không có dữ liệu.")
            
            st.markdown("---")
            st.markdown("#### 2. Cumulative Net OMO Injection")
            f2, h2, df_out2 = plot_omo(df_omo, pd.to_datetime("2025-01-01"), pd.to_datetime("today"), show_legend=True)
            if h2: 
                st.plotly_chart(f2, width="stretch", key="m_omo_chart")
                st.dataframe(df_out2.sort_values('Ngày', ascending=False), width="stretch")
            else: st.info("Không có dữ liệu.")
            
            st.markdown("---")
            st.markdown("#### 3. Yield Curve")
            fig3, has_data3 = plot_yield_curve(df_us_yc, df_vn_yc, target_date=None, title="", show_legend=True)
            if has_data3: 
                st.plotly_chart(fig3, width="stretch", key="m_yc_chart")
                st.markdown("**VN Yield Curve (Từ 01/01/2025 đến nay)**")
                if not df_vn_yc.empty:
                    df_vn_tbl = df_vn_yc.copy()
                    df_vn_tbl['Date'] = safe_to_datetime(df_vn_tbl['Date'])
                    df_vn_tbl = df_vn_tbl[df_vn_tbl['Date'] >= pd.to_datetime('2025-01-01')]
                    st.dataframe(sort_df_by_date_and_term(df_vn_tbl), width="stretch")
            else: st.info("Không có dữ liệu Yield Curve.")
            
            st.markdown("---")
            st.markdown("#### 4. Exchange Rates")
            f4, h4, df_out4 = plot_exchange_rate(df_fx, df_us_fx, pd.to_datetime("2025-01-01"), pd.to_datetime("today"), show_legend=True)
            if h4: 
                st.plotly_chart(f4, width="stretch", key="m_fx_chart")
                st.dataframe(df_out4.sort_values('Date', ascending=False), width="stretch")
            else: st.info("Không có dữ liệu.")
            
            st.markdown("---")
            st.markdown("#### 5. FedWatch Probabilities")
            if not df_fed.empty:
                try:
                    styled_fed = df_fed.style.applymap(highlight_prob, subset=df_fed.columns[1:])
                    st.dataframe(styled_fed, width="stretch")
                except AttributeError:
                    styled_fed = df_fed.style.map(highlight_prob, subset=df_fed.columns[1:])
                    st.dataframe(styled_fed, width="stretch")

        else:
            # GIAO DIỆN DESKTOP
            st.markdown("#### 1. Interbank ON Rate & Volume")
            t1_single, t1_compare = st.tabs(["🔥 Khung Thời Gian Đơn", "⚖️ So sánh 2 Khung Thời Gian"])
            with t1_single:
                d1_st, d1_en = safe_date_range("Chọn khoảng thời gian", 'ib_single', "2025-01-01", "today", min_date="2004-07-12")
                f1, h1, term1, df_out1 = plot_interbank(df_ib, d1_st, d1_en, show_legend=True)
                if h1: 
                    st.plotly_chart(f1, width="stretch", key="ib_single_chart")
                    st.dataframe(sort_df_by_date_and_term(df_out1), width="stretch")
                else: st.info("Không có dữ liệu.")
                
            with t1_compare:
                c1_1, c1_2 = st.columns(2)
                with c1_1:
                    st_1, en_1 = safe_date_range("Khung thời gian 1", 'ib_c1', "2024-01-01", "today", min_date="2004-07-12")
                    f1_c1, h1_c1, _, _ = plot_interbank(df_ib, st_1, en_1, show_legend=False)
                    if h1_c1: st.plotly_chart(f1_c1, width="stretch", key="ib_c1_chart")
                with c1_2:
                    st_2, en_2 = safe_date_range("Khung thời gian 2", 'ib_c2', "2025-01-01", "today", min_date="2004-07-12")
                    f1_c2, h1_c2, _, _ = plot_interbank(df_ib, st_2, en_2, show_legend=True)
                    if h1_c2: st.plotly_chart(f1_c2, width="stretch", key="ib_c2_chart")

            st.markdown("---")
            st.markdown("#### 2. Cumulative Net OMO Injection")
            t2_single, t2_compare = st.tabs(["🔥 Khung Thời Gian Đơn", "⚖️ So sánh 2 Khung Thời Gian"])
            with t2_single:
                d2_st, d2_en = safe_date_range("Chọn khoảng thời gian", 'omo_single', "2025-01-01", "today", min_date="2010-10-14")
                f2, h2, df_out2 = plot_omo(df_omo, d2_st, d2_en, show_legend=True)
                if h2: 
                    st.plotly_chart(f2, width="stretch", key="omo_single_chart")
                    st.dataframe(df_out2.sort_values('Ngày', ascending=False), width="stretch")
                else: st.info("Không có dữ liệu.")
                
            with t2_compare:
                c2_1, c2_2 = st.columns(2)
                with c2_1:
                    st_21, en_21 = safe_date_range("Khung thời gian 1", 'omo_c1', "2024-01-01", "today", min_date="2010-10-14")
                    f2_c1, h2_c1, _ = plot_omo(df_omo, st_21, en_21, show_legend=False)
                    if h2_c1: st.plotly_chart(f2_c1, width="stretch", key="omo_c1_chart")
                with c2_2:
                    st_22, en_22 = safe_date_range("Khung thời gian 2", 'omo_c2', "2025-01-01", "today", min_date="2010-10-14")
                    f2_c2, h2_c2, _ = plot_omo(df_omo, st_22, en_22, show_legend=True)
                    if h2_c2: st.plotly_chart(f2_c2, width="stretch", key="omo_c2_chart")

            st.markdown("---")
            st.markdown("#### 3. Yield Curve")
            tab_latest, tab_compare = st.tabs(["🔥 Mới nhất", "⚖️ So sánh theo ngày"])
            
            with tab_latest:
                fig3, has_data3 = plot_yield_curve(df_us_yc, df_vn_yc, target_date=None, title="", show_legend=True)
                if has_data3:
                    st.plotly_chart(fig3, width="stretch", key="yc_single_chart")
                    st.markdown("**VN Yield Curve (Từ 01/01/2025 đến nay)**")
                    if not df_vn_yc.empty:
                        df_vn_tbl = df_vn_yc.copy()
                        df_vn_tbl['Date'] = safe_to_datetime(df_vn_tbl['Date'])
                        df_vn_tbl = df_vn_tbl[df_vn_tbl['Date'] >= pd.to_datetime('2025-01-01')]
                        st.dataframe(sort_df_by_date_and_term(df_vn_tbl), width="stretch")
                else:
                    st.info("Không có dữ liệu Yield Curve.")
                    
            with tab_compare:
                col_c1, col_c2 = st.columns(2)
                import datetime
                with col_c1:
                    date_1 = st.date_input("Chọn ngày 1", pd.to_datetime("today").date() - pd.Timedelta(days=30), min_value=datetime.date(2013, 3, 19), max_value=datetime.date.today(), key="yc1")
                    fig_c1, h1 = plot_yield_curve(df_us_yc, df_vn_yc, target_date=pd.to_datetime(date_1), title=f"Đến ngày {date_1.strftime('%d/%m/%Y')}", show_legend=False)
                    if h1: st.plotly_chart(fig_c1, width="stretch", key="yc_c1_chart")
                with col_c2:
                    date_2 = st.date_input("Chọn ngày 2", pd.to_datetime("today").date(), min_value=datetime.date(2013, 3, 19), max_value=datetime.date.today(), key="yc2")
                    fig_c2, h2 = plot_yield_curve(df_us_yc, df_vn_yc, target_date=pd.to_datetime(date_2), title=f"Đến ngày {date_2.strftime('%d/%m/%Y')}", show_legend=True)
                    if h2: st.plotly_chart(fig_c2, width="stretch", key="yc_c2_chart")

            st.markdown("---")
            st.markdown("#### 4. Exchange Rates")
            t4_single, t4_compare = st.tabs(["🔥 Khung Thời Gian Đơn", "⚖️ So sánh 2 Khung Thời Gian"])
            with t4_single:
                d4_st, d4_en = safe_date_range("Chọn khoảng thời gian", 'fx_single', "2025-01-01", "today", min_date="2004-04-27")
                f4, h4, df_out4 = plot_exchange_rate(df_fx, df_us_fx, d4_st, d4_en, show_legend=True)
                if h4: 
                    st.plotly_chart(f4, width="stretch", key="fx_single_chart")
                    st.dataframe(df_out4.sort_values('Date', ascending=False), width="stretch")
                else: st.info("Không có dữ liệu.")
                
            with t4_compare:
                c4_1, c4_2 = st.columns(2)
                with c4_1:
                    st_41, en_41 = safe_date_range("Khung thời gian 1", 'fx_c1', "2024-01-01", "today", min_date="2004-04-27")
                    f4_c1, h4_c1, _ = plot_exchange_rate(df_fx, df_us_fx, st_41, en_41, show_legend=False)
                    if h4_c1: st.plotly_chart(f4_c1, width="stretch", key="fx_c1_chart")
                with c4_2:
                    st_42, en_42 = safe_date_range("Khung thời gian 2", 'fx_c2', "2025-01-01", "today", min_date="2004-04-27")
                    f4_c2, h4_c2, _ = plot_exchange_rate(df_fx, df_us_fx, st_42, en_42, show_legend=True)
                    if h4_c2: st.plotly_chart(f4_c2, width="stretch", key="fx_c2_chart")

            st.markdown("---")
            st.markdown("#### 5. FedWatch Probabilities")
            if not df_fed.empty:
                try:
                    styled_fed = df_fed.style.applymap(highlight_prob, subset=df_fed.columns[1:])
                    st.dataframe(styled_fed, width="stretch")
                except AttributeError:
                    styled_fed = df_fed.style.map(highlight_prob, subset=df_fed.columns[1:])
                    st.dataframe(styled_fed, width="stretch")

with tab_chat:
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("Nhập lệnh (VD: Cập nhật, Thống kê tỷ giá OMO...)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with chat_container:
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
                                    
                                # Ẩn phần hiển thị code
                                # st.markdown("🧑‍💻 **Đang chạy code trích xuất dữ liệu:**")
                                # st.code(script, language="python")
                                
                                output, err = execute_python_code(script, st.session_state.data_dict)
                                obs = f"\nKẾT QUẢ CHẠY MÃ HỆ THỐNG:\nOutput:\n{output}\nError:\n{err}"
                                
                                chat_context += f"\nASSISTANT (Sinh code):\n{code_block}\nSYSTEM (Observation): {obs}"
                                
                                # Ẩn phần hiển thị lỗi và dữ liệu thô
                                # if err:
                                #     st.error(f"Lỗi khi chạy code: {err}")
                                # if output:
                                #     with st.expander("Xem dữ liệu thô"):
                                #         st.text(output)
                                        
                                current_loop += 1
                                continue
                            else:
                                message_placeholder.markdown(response)
                                st.session_state.messages.append({"role": "assistant", "content": response})
                                break
