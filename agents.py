import os
from groq import Groq
from dotenv import load_dotenv

# Load env variables (for local testing)
load_dotenv()

# Khởi tạo Groq Client
# Cần cấu hình GROQ_API_KEY trong .env hoặc Streamlit Secrets
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def call_groq(messages, model="llama3-8b-8192", temperature=0.2):
    """
    Hàm gọi API chung cho các Agents
    """
    try:
        response = groq_client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Lỗi gọi Groq API: {e}"

def orchestrator_agent(user_input):
    """
    Quyết định luồng xử lý:
    1. Trả về "UPDATE_REPORT" nếu người dùng gõ "Cập nhật", "Làm báo cáo"...
    2. Trả về "DATA_REQUEST" nếu người dùng hỏi biểu đồ, thống kê.
    3. Trả về câu trả lời bình thường nếu chỉ là hội thoại.
    """
    system_msg = "Bạn là người điều phối (Orchestrator). Trả lời bằng tiếng Việt. Nếu người dùng muốn tạo bản báo cáo vĩ mô hoặc cập nhật dữ liệu hàng ngày, hãy trả về CHÍNH XÁC chuỗi: UPDATE_REPORT. Nếu người dùng muốn thống kê dữ liệu, vẽ biểu đồ cụ thể, trả về CHÍNH XÁC chuỗi: DATA_REQUEST. Nếu chỉ là giao tiếp thông thường, hãy trả lời bình thường ngắn gọn."
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_input}
    ]
    return call_groq(messages, model="llama3-8b-8192")

def coder_agent(task_description):
    """
    Sinh code Python dựa trên yêu cầu biểu đồ/thống kê.
    """
    system_msg = '''Bạn là Coder AI chuyên về Data Science (Python, Pandas, Matplotlib).
Nhiệm vụ: Dựa vào yêu cầu, hãy viết script Python.
Luôn đặt code của bạn trong markdown ```python ... ```.
Để hiển thị biểu đồ trên Streamlit, HÃY DÙNG `st.pyplot(fig)` thay vì `plt.show()` hoặc `plt.savefig()`.
Các file CSV đã được load sẵn thành một dictionary tên là `data_dict`. 
Keys gồm: 'SBV_OMO', 'SBV_Interbank_Rate', 'SBV_Exchange_Rate', 'SBV_Policy_and_FedWatch', 'SBV_Yield_Curve', 'US_Policy_Rates', 'US_OMO', 'US_Yield_Curve'.
Bạn có thể gọi df = data_dict['Tên_Key'] để xử lý.
Biến `st` (streamlit) đã được import sẵn. Hãy print() các thống kê nếu có.'''
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": task_description}
    ]
    # Dùng model mạnh hơn cho code
    return call_groq(messages, model="llama3-70b-8192", temperature=0.1)

def economist_agent(prompt_content, data_context):
    """
    Dựa vào data và system prompt (prompt.txt) để viết Báo cáo.
    """
    system_msg = f"""Bạn là Chuyên gia Phân tích Chiến lược Vĩ mô.
Dưới đây là bộ chỉ dẫn (System Instructions) của bạn:
{prompt_content}

---
BÁO CÁO PHẢI TUÂN THỦ NGHIÊM NGẶT FORMAT VÀ NỘI DUNG ĐƯỢC YÊU CẦU TRONG CHỈ DẪN TRÊN.
Hãy sử dụng Markdown để trình bày báo cáo rõ ràng, dễ đọc.
"""
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"Đây là số liệu thô và thống kê mới nhất được lấy từ cơ sở dữ liệu:\n{data_context}\n\nHãy viết bản báo cáo vĩ mô đầy đủ theo đúng hướng dẫn."}
    ]
    # Dùng model 70b để viết phân tích sâu sắc
    return call_groq(messages, model="llama3-70b-8192", temperature=0.3)
