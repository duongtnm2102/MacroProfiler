import streamlit as st
import re
import os
import io
import sys
from data_loader import get_all_data
from email_utils import send_daily_report
from agents import generate_strategic_report, data_analyst_agent
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
    match = re.search(r"```python\n(.*?)\n```", code, re.DOTALL)
    script = match.group(1) if match else code
        
    # Tạo môi trường thực thi an toàn và nạp sẵn vào bộ nhớ toàn cục (globals)
    # Khắc phục lỗi name 'data_dict' is not defined trong hàm con
    exec_globals = {
        'data_dict': data_dict,
        'st': st,
        'pd': __import__('pandas'),
        'plt': __import__('matplotlib.pyplot'),
        'np': __import__('numpy'),
        '__builtins__': __builtins__
    }
    
    # Bắt stdout (print)
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    
    error_msg = None
    try:
        # Thực thi với globals
        exec(script, exec_globals)
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
        
        # Nhận diện lệnh bằng Keyword (không dùng AI nữa)
        is_report = bool(re.search(r'(cập nhật|báo cáo)', prompt.lower()))
            
        if is_report:
            message_placeholder.markdown("🔄 Đang xử lý dữ liệu và tạo báo cáo vĩ mô (có thể mất 1-2 phút)...")
            # --- LUỒNG TẠO BÁO CÁO (CHỨC NĂNG CỐ ĐỊNH) ---
            data_context = process_macro_data(st.session_state.data_dict)
            
            prompt_path = "prompt.txt"
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt_content = f.read()
            else:
                prompt_content = "Vui lòng upload file prompt.txt."
                
            report_md = generate_strategic_report(prompt_content, data_context)
            message_placeholder.markdown(report_md)
            
            # Gửi Email
            with st.spinner("Đang gửi báo cáo qua email..."):
                if send_daily_report(report_md):
                    st.success("Đã gửi báo cáo qua Email thành công!")
                else:
                    st.error("Chưa thể gửi email (kiểm tra cấu hình SMTP).")
                    
            st.session_state.messages.append({"role": "assistant", "content": report_md})
            
        else:
            # --- LUỒNG CHAT PHÂN TÍCH (ReAct LOOP) ---
            chat_context = ""
            for msg in st.session_state.messages:
                role_name = "USER" if msg["role"] == "user" else "ASSISTANT"
                chat_context += f"\n{role_name}: {msg['content']}"
                
            MAX_LOOPS = 3
            current_loop = 0
            
            with st.spinner("AI đang tư duy và phân tích..."):
                while current_loop < MAX_LOOPS:
                    response = data_analyst_agent(chat_context)
                    
                    # AI có sinh code không?
                    match = re.search(r"```python\n(.*?)\n```", response, re.DOTALL)
                    
                    if match:
                        code_block = match.group(0)
                        script = match.group(1)
                        # In phần văn bản (kế hoạch) trước khi in code
                        text_part = response.replace(code_block, "").strip()
                        if text_part:
                            st.markdown(text_part)
                            
                        st.markdown("🧑‍💻 **Đang chạy code trích xuất dữ liệu:**")
                        st.code(script, language="python")
                        
                        output, err = execute_python_code(script, st.session_state.data_dict)
                        obs = f"\nKẾT QUẢ CHẠY MÃ HỆ THỐNG:\nOutput:\n{output}\nError:\n{err}"
                        
                        # Cập nhật context cho vòng lặp tiếp theo
                        chat_context += f"\nASSISTANT (Sinh code):\n{code_block}\nSYSTEM (Observation): {obs}"
                        
                        if err:
                            st.error(f"Lỗi khi chạy code: {err}")
                        if output:
                            with st.expander("Xem dữ liệu thô"):
                                st.text(output)
                                
                        current_loop += 1
                        # Lặp lại vòng lặp để AI đọc "obs"
                        continue
                    else:
                        # Không sinh code -> Câu trả lời cuối cùng
                        message_placeholder.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        break
