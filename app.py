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

st.set_page_config(page_title="Macro Watch", page_icon="📈", layout="wide")

# CSS Phong cách Bloomberg
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

st.title("📈 Macro Watch")

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
        
    output = redirected_output.getvalue()
    return output, error_msg

def plot_yield_curve(df_us_yc, df_vn_yc, target_date=None, title="Yield Curve"):
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
            fig.add_trace(go.Scatter(x=terms_us_avail, y=rates_us, mode='lines+markers+text', name='US Yield Curve',
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
                fig.add_trace(go.Scatter(x=terms_vn_mapped, y=rates_vn, mode='lines+markers+text', name='VN Yield Curve',
                                          text=[f"{r:.2f}%" if pd.notnull(r) else "" for r in rates_vn], textposition="bottom center", line=dict(color='#FFFF00')))

    fig.update_layout(template='plotly_dark', plot_bgcolor='#000000', paper_bgcolor='#000000', margin=dict(l=0, r=0, t=30, b=0), title=title)
    fig.update_xaxes(categoryorder='array', categoryarray=std_order)
    return fig, has_data

tab_dash, tab_chat = st.tabs(["📺 DASHBOARD MẶC ĐỊNH", "💬 AI VĨ MÔ"])

with tab_dash:
    st.markdown("### 📊 MARKET DATA TERMINAL")
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
        
        st.markdown("---")
        st.markdown("#### 📅 Lọc Thời Gian Chung (Biểu đồ 1, 2, 4)")
        col_st, col_en = st.columns(2)
        with col_st:
            global_start = st.date_input("Từ ngày", pd.to_datetime("2025-01-01"))
        with col_en:
            global_end = st.date_input("Đến ngày", pd.to_datetime("today"))
        
        global_start = pd.to_datetime(global_start)
        global_end = pd.to_datetime(global_end)

        # Biểu đồ 1: Interbank ON
        st.markdown("#### 1. Interbank ON Rate & Volume")
        if not df_ib.empty:
            df1 = df_ib.copy()
            df1['Date'] = safe_to_datetime(df1['Date'])
            df1['Term_Clean'] = df1['Term'].astype(str).str.strip().str.upper()
            
            on_terms = [t for t in df1['Term_Clean'].unique() if t in ['ON', 'O/N', 'QUA ĐÊM', 'QUA DEM', 'OVERNIGHT']]
            target_term = on_terms[0] if on_terms else 'ON'
            
            df1 = df1[(df1['Date'] >= global_start) & (df1['Date'] <= global_end) & (df1['Term_Clean'] == target_term)].sort_values('Date')
            if not df1.empty:
                df1['Volume'] = pd.to_numeric(df1['Volume'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                df1['Rate'] = pd.to_numeric(df1['Rate'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                
                fig1 = make_subplots(specs=[[{"secondary_y": True}]])
                fig1.add_trace(go.Bar(x=df1['Date'], y=df1['Volume'], name='Volume', marker_color='rgba(0, 100, 255, 0.5)'), secondary_y=False)
                fig1.add_trace(go.Scatter(x=df1['Date'], y=df1['Rate'], name='ON Rate', mode='lines', connectgaps=True, line=dict(color='#00FF00', width=2)), secondary_y=True)
                fig1.update_layout(template='plotly_dark', plot_bgcolor='#000000', paper_bgcolor='#000000', margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info(f"Không có dữ liệu Interbank kỳ hạn '{target_term}' trong khoảng thời gian này. Các kỳ hạn trong data: {', '.join(df_ib['Term'].unique()[:10])}")

        # Biểu đồ 2: OMO
        st.markdown("#### 2. Cumulative Net OMO Injection")
        if not df_omo.empty:
            df2 = df_omo.copy()
            df2['Ngày'] = safe_to_datetime(df2['Ngày'])
            df2 = df2[(df2['Ngày'] >= global_start) & (df2['Ngày'] <= global_end)].sort_values('Ngày')
            if not df2.empty:
                df2['Giá trị bơm ròng'] = pd.to_numeric(df2['Giá trị bơm ròng'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                df2['Cumulative'] = df2['Giá trị bơm ròng'].cumsum()
                
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=df2['Ngày'], y=df2['Cumulative'], mode='lines', name='Cumulative OMO', connectgaps=True, line=dict(color='#FF00FF', width=2)))
                fig2.update_layout(template='plotly_dark', plot_bgcolor='#000000', paper_bgcolor='#000000', margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig2, use_container_width=True)

        # Biểu đồ 3: Yield Curve
        st.markdown("#### 3. Yield Curve")
        tab_latest, tab_compare = st.tabs(["🔥 Mới nhất", "⚖️ So sánh theo ngày"])
        
        with tab_latest:
            fig3, has_data3 = plot_yield_curve(df_us_yc, df_vn_yc, target_date=None, title="")
            if has_data3:
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("Không có dữ liệu Yield Curve.")
                
        with tab_compare:
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                date_1 = st.date_input("Chọn ngày 1", pd.to_datetime("today") - pd.Timedelta(days=30), key="yc1")
                fig_c1, h1 = plot_yield_curve(df_us_yc, df_vn_yc, target_date=pd.to_datetime(date_1), title=f"Đến ngày {date_1.strftime('%d/%m/%Y')}")
                if h1: st.plotly_chart(fig_c1, use_container_width=True)
            with col_c2:
                date_2 = st.date_input("Chọn ngày 2", pd.to_datetime("today"), key="yc2")
                fig_c2, h2 = plot_yield_curve(df_us_yc, df_vn_yc, target_date=pd.to_datetime(date_2), title=f"Đến ngày {date_2.strftime('%d/%m/%Y')}")
                if h2: st.plotly_chart(fig_c2, use_container_width=True)

        # Biểu đồ 4: Exchange Rates
        st.markdown("#### 4. Exchange Rates")
        if not df_fx.empty:
            df4 = df_fx.copy()
            df4['Date'] = safe_to_datetime(df4['Date'])
            if not df4.empty:
                df4_filter = df4[(df4['Date'] >= global_start) & (df4['Date'] <= global_end)].sort_values('Date')
                
                for col in ['USD_VND_Rate', 'VCB_rate', 'Black_Market_rate']:
                    if col in df4_filter.columns:
                        df4_filter[col] = pd.to_numeric(df4_filter[col].astype(str).str.replace(',', ''), errors='coerce')
                
                fig4 = go.Figure()
                if 'USD_VND_Rate' in df4_filter.columns:
                    fig4.add_trace(go.Scatter(x=df4_filter['Date'], y=df4_filter['USD_VND_Rate'], mode='lines', name='Central Rate', connectgaps=True, line=dict(color='white')))
                if 'VCB_rate' in df4_filter.columns:
                    fig4.add_trace(go.Scatter(x=df4_filter['Date'], y=df4_filter['VCB_rate'], mode='lines', name='VCB Rate', connectgaps=True, line=dict(color='lime')))
                if 'Black_Market_rate' in df4_filter.columns:
                    fig4.add_trace(go.Scatter(x=df4_filter['Date'], y=df4_filter['Black_Market_rate'], mode='lines', name='Black Market', connectgaps=True, line=dict(color='red')))
                    
                fig4.update_layout(template='plotly_dark', plot_bgcolor='#000000', paper_bgcolor='#000000', margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig4, use_container_width=True)
                
                st.dataframe(df4_filter.sort_values('Date', ascending=False), use_container_width=True)

        # Bảng 5: FedWatch
        st.markdown("#### 5. FedWatch Probabilities")
        if not df_fed.empty:
            def highlight_prob(val):
                try:
                    v = float(str(val).replace('%', '').strip())
                    if v == 0: 
                        return 'color: #333333;'
                    alpha = max(0.2, v / 100)
                    return f'background-color: rgba(0, 255, 0, {alpha}); color: white;'
                except:
                    return ''
                    
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
