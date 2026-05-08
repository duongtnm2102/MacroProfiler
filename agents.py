import os
from groq import Groq
from dotenv import load_dotenv

# Load env variables (for local testing)
load_dotenv()

# Khởi tạo Groq Client
# Cần cấu hình GROQ_API_KEY trong .env hoặc Streamlit Secrets
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def call_groq(messages, model="llama-3.1-8b-instant", temperature=0.6, max_tokens=None):
    """
    Hàm gọi API chung cho các Agents
    """
    try:
        kwargs = {
            "messages": messages,
            "model": model,
            "temperature": temperature
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
            
        response = groq_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    except Exception as e:
        return f"Lỗi gọi Groq API: {e}"

def get_search_context():
    """
    Dùng thư viện duckduckgo_search để lấy thông tin mới nhất từ internet.
    Hỗ trợ cho AI không có quyền truy cập internet (để không bịa data).
    """
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        queries = [
            "Chỉ đạo tín dụng ngân hàng nhà nước thủ tướng mới nhất", 
            "US CPI YoY inflation rate latest", 
            "Federal Reserve FOMC minutes latest"
        ]
        search_text = "\n--- THÔNG TIN CẬP NHẬT TỪ INTERNET (DÙNG ĐỂ PHÂN TÍCH SOFT DATA) ---\n"
        search_text += "Lưu ý: TUYỆT ĐỐI dùng thông tin dưới đây để viết báo cáo. NẾU KHÔNG CÓ, HÃY GHI LÀ 'KHÔNG CÓ THÔNG TIN', CẤM BỊA ĐẶT PHÁT BIỂU CHÍNH TRỊ.\n\n"
        
        for q in queries:
            search_text += f"Kết quả tìm kiếm cho '{q}':\n"
            results = ddgs.text(q, max_results=2)
            for r in results:
                search_text += f"- {r.get('title', '')}: {r.get('body', '')}\n"
        return search_text
    except Exception as e:
        return f"\n--- THÔNG TIN INTERNET ---\nKhông thể truy cập internet. Tác vụ tính Real Rate hãy dùng CPI = 2.4%. Về chính trị: Xin ghi 'Không có dữ liệu mới cập nhật', tuyệt đối không tự bịa.\n"

def orchestrator_agent(user_input):
    """
    Quyết định luồng xử lý:
    1. Trả về "UPDATE_REPORT" nếu người dùng gõ "Cập nhật", "Làm báo cáo"...
    2. Trả về "DATA_REQUEST" nếu người dùng hỏi biểu đồ, thống kê.
    3. Trả về câu trả lời bình thường nếu chỉ là hội thoại.
    """
    system_msg = """Bạn là hệ thống phân loại ý định.
QUY TẮC TỐI THƯỢNG:
1. Nếu User gõ các từ như "cập nhật", "báo cáo", "làm báo cáo": BẠN PHẢI TRẢ LỜI CÓ CHỨA CHUỖI "UPDATE_REPORT". Ví dụ: "UPDATE_REPORT: Đang cập nhật báo cáo."
2. Nếu User gõ "vẽ", "thống kê", "biểu đồ": BẠN PHẢI TRẢ LỜI CÓ CHỨA CHUỖI "DATA_REQUEST".
3. Nếu User chỉ chào hỏi: Trả lời giao tiếp bình thường."""
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_input}
    ]
    # Nâng cấp lên model 70B để hiểu đúng intent dù chỉ 1 từ "Cập nhật"
    return call_groq(messages, model="llama-3.3-70b-versatile")

def coder_agent(task_description):
    """
    Sinh code Python dựa trên yêu cầu biểu đồ/thống kê.
    """
    system_msg = '''Bạn là Coder AI chuyên về Data Science (Python, Pandas, Matplotlib).
Nhiệm vụ: Dựa vào yêu cầu, hãy viết script Python.
Luôn đặt code của bạn trong markdown ```python ... ```.
Để hiển thị biểu đồ trên Streamlit, HÃY DÙNG `st.pyplot(fig)` thay vì `plt.show()` hoặc `plt.savefig()`.
Các file CSV đã được load sẵn thành một dictionary tên là `data_dict`. 
Keys và Cấu trúc cột của từng file (để bạn không phải tốn token gọi df.head()):
1. 'SBV_Exchange_Rate': Date, USD_VND_Rate, Black_Market_rate, VCB_rate
2. 'SBV_Interbank_Rate': Date, Term, Rate, Volume
3. 'SBV_OMO': Ngày, Loại hình giao dịch, Kỳ hạn, Số TV tham gia, Số TV trúng thầu, Khối lượng mua trúng thầu, Lãi suất trúng thầu bên mua, Khối lượng mua đáo hạn, Khối lượng bán trúng thầu, Lãi suất trúng thầu bên bán, Khối lượng bán đáo hạn, Tổng bơm, Tổng hút, Giá trị bơm ròng
4. 'SBV_Yield_Curve': Date, Term, Spot_Rate_Continuous_Pct, Par_Yield_Pct, Spot_Rate_Annual_Pct
5. 'SBV_Policy_Rates': Loại lãi suất, Giá trị, Văn bản quyết định, Ngày có hiệu lực
6. 'US_Exchange_Rate': Date, Broad Trade-Weighted Dollar Index
7. 'US_Interbank_Rates': Date, EFFR, OBFR, SOFR
8. 'US_OMO': Ngày, Loại hình giao dịch, Kỳ hạn, Số TV tham gia, Số TV trúng thầu, Khối lượng mua trúng thầu, Lãi suất trúng thầu bên mua, Khối lượng mua đáo hạn, Khối lượng bán trúng thầu, Lãi suất trúng thầu bên bán, Khối lượng bán đáo hạn, Tổng bơm, Tổng hút, Giá trị bơm ròng
9. 'US_Policy_Rates': Date, Fed Funds Rate, Bank Prime Loan
10. 'US_Yield_Curve': Date, 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y
11. 'FedWatch_Probabilities': MEETING DATE, 275-300, 300-325, 325-350, 350-375, 375-400, 400-425, 425-450, 450-475, 475-500, 500-525
Bạn có thể gọi df = data_dict['Tên_Key'] để xử lý.
Biến `st` (streamlit) đã được import sẵn. Hãy print() các thống kê nếu có.'''
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": task_description}
    ]
    # Dùng GPT-OSS-120B cho việc sinh code (Giới hạn max_tokens=2000 để tránh lỗi TPM 8000)
    return call_groq(messages, model="openai/gpt-oss-120b", temperature=0.6, max_tokens=2000)

def economist_agent(prompt_content, data_context):
    """
    Dựa vào data và system prompt (prompt.txt) để viết Báo cáo.
    """
    system_msg = f"""Bạn là Chuyên gia Phân tích Chiến lược Vĩ mô.
Dưới đây là bộ chỉ dẫn (System Instructions) của bạn:
{prompt_content}

---
BÁO CÁO PHẢI TUÂN THỦ NGHIÊM NGẶT FORMAT VÀ NỘI DUNG ĐƯỢC YÊU CẦU TRONG CHỈ DẪN TRÊN.
Hãy sử dụng Markdown để trình bày báo cáo rõ ràng, dễ đọc. TUYỆT ĐỐI KHÔNG bịa đặt trích dẫn chính trị.
"""
    search_context = get_search_context()
    full_context = f"Đây là số liệu thô và thống kê mới nhất được lấy từ cơ sở dữ liệu:\n{data_context}\n{search_context}\n\nHãy viết bản báo cáo vĩ mô đầy đủ theo đúng hướng dẫn."
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": full_context}
    ]
    # Trả về Qwen 32B cho Economist Agent, temp mặc định 0.6
    return call_groq(messages, model="qwen/qwen3-32b", temperature=0.6)
