import streamlit as st
import re
import os
import io
import sys
from data_loader import get_all_data
from email_utils import send_daily_report
from agents import orchestrator_agent, coder_agent, economist_agent
from data_processor import process_macro_data

st.set_page_config(page_title="Macro-Profiler AI", page_icon="📈", layout="wide")
st.title("📈 Longitudinal Strategic Macro-Profiler")

# Khởi tạo session state cho chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Nút tải dữ liệu ở sidebar
with st.sidebar:
    st.header("Cài đặt Dữ liệu")
    if st.button("Làm mới Dữ liệu (Reload CSV)"):
        with st.spinner("Đang tải dữ liệu từ Google Drive/Sheets..."):
            st.session_state.data_dict = get_all_data()
        st.success("Tải dữ liệu thành công!")

if "data_dict" not in st.session_state:
    st.session_state.data_dict = get_all_data()

# Hàm trích xuất và chạy Python code
def execute_python_code(code: str, data_dict: dict):
    # Trích xuất code trong block ```python ... ```
    match = re.search(r"```python\n(.*?)\n```", code, re.DOTALL)
    if not match:
        # Thử lấy toàn bộ nếu không có markdown block
        script = code
    else:
        script = match.group(1)
        
    # Tạo môi trường thực thi an toàn (chỉ bao gồm các biến cần thiết)
    local_vars = {
        'data_dict': data_dict,
        'st': st,
        'pd': __import__('pandas'),
        'plt': __import__('matplotlib.pyplot'),
        'np': __import__('numpy')
    }
    
    # Bắt stdout (print)
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    
    error_msg = None
    try:
        exec(script, globals(), local_vars)
    except Exception as e:
        error_msg = f"Lỗi thực thi code: {str(e)}"
    finally:
        sys.stdout = old_stdout
        
    output = redirected_output.getvalue()
    return output, error_msg

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Xử lý input từ user
if prompt := st.chat_input("Nhập lệnh (VD: Cập nhật, Thống kê tỷ giá OMO...)"):
    # Lưu vào lịch sử
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # 1. Gọi Orchestrator
        with st.spinner("Đang phân tích yêu cầu..."):
            intent = orchestrator_agent(prompt)
            
        if "UPDATE_REPORT" in intent:
            message_placeholder.markdown("🔄 Đang xử lý dữ liệu và tạo báo cáo vĩ mô (có thể mất 1-2 phút)...")
            # --- LUỒNG TẠO BÁO CÁO (UPDATE_REPORT) ---
            
            # (Phần này sẽ gọi Data Processor để tính toán thống kê)
            data_context = process_macro_data(st.session_state.data_dict)
            
            # Đọc prompt.txt
            prompt_path = "prompt.txt"
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt_content = f.read()
            else:
                prompt_content = "Vui lòng upload file prompt.txt."
                
            report_md = economist_agent(prompt_content, data_context)
            message_placeholder.markdown(report_md)
            
            # Gửi Email
            with st.spinner("Đang gửi báo cáo qua email..."):
                if send_daily_report(report_md):
                    st.success("Đã gửi báo cáo qua Email thành công!")
                else:
                    st.error("Chưa thể gửi email (kiểm tra cấu hình SMTP).")
                    
            st.session_state.messages.append({"role": "assistant", "content": report_md})
            
        elif "DATA_REQUEST" in intent:
            # --- LUỒNG THỐNG KÊ, BIỂU ĐỒ (AD-HOC) ---
            message_placeholder.markdown("🧑‍💻 Đang viết code xử lý dữ liệu...")
            code_response = coder_agent(prompt)
            
            st.markdown("### Code sinh ra:")
            st.code(code_response, language="python")
            
            st.markdown("### Kết quả thực thi:")
            output, err = execute_python_code(code_response, st.session_state.data_dict)
            
            if err:
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": f"Lỗi: {err}"})
            else:
                if output:
                    st.text(output)
                # Biểu đồ nếu có đã được render thông qua st.pyplot() trong code
                st.session_state.messages.append({"role": "assistant", "content": "Đã xử lý xong yêu cầu dữ liệu."})
        else:
            # Hội thoại thường
            message_placeholder.markdown(intent)
            st.session_state.messages.append({"role": "assistant", "content": intent})
