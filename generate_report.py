import os
from datetime import datetime, timedelta
from data_loader import get_all_data
from data_processor import process_macro_data
from email_utils import send_daily_report
from agents import (
    generate_strategic_report, 
    analyze_chart_interbank, 
    analyze_chart_omo, 
    analyze_chart_yield, 
    analyze_chart_fx
)
import app  # import để dùng các hàm vẽ biểu đồ
import jinja2
import pdfkit

def main():
    print("Bắt đầu tiến trình tạo báo cáo Vĩ mô tự động...")
    os.makedirs("temp", exist_ok=True)
    
    # 1. Tải toàn bộ dữ liệu mới nhất
    print("Đang tải dữ liệu từ Google Sheets/Drive...")
    data_dict = get_all_data()
    
    print("Đang tiền xử lý thống kê (Data Processor)...")
    data_context = process_macro_data(data_dict)
    
    # 2. Đọc file prompt
    prompt_path = "prompt.txt"
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_content = f.read()
    else:
        print("Lỗi: Không tìm thấy file prompt.txt")
        return
        
    # 3. Tạo báo cáo Tổng quan qua AI
    print("Đang chạy Economist AI để phân tích Tổng quan Chiến lược...")
    report_md = generate_strategic_report(prompt_content, data_context)
    
    # 4. Lưu biểu đồ thành ảnh
    print("Đang xuất các biểu đồ ra file ảnh...")
    start_date = datetime.now() - timedelta(days=180)
    end_date = datetime.now()
    
    # Gọi hàm plot (lưu ý hàm plot trả về fig, has_data, ...)
    fig_ib, _, _, _ = app.plot_interbank(data_dict.get('SBV_Interbank_Rate'), start_date, end_date, show_legend=True)
    fig_omo, _, _ = app.plot_omo(data_dict.get('SBV_OMO'), start_date, end_date, show_legend=True)
    fig_yc, _, _ = app.plot_yield_curve(data_dict.get('US_Yield_Curve'), data_dict.get('SBV_Yield_Curve'), show_legend=True)
    fig_fx, _, _ = app.plot_exchange_rate(data_dict.get('SBV_Exchange_Rate'), data_dict.get('US_Exchange_Rate'), start_date, end_date, show_legend=True)
    
    # Lưu ảnh bằng Kaleido
    # Đổi background trắng để hợp với Light Mode PDF
    for fig in [fig_ib, fig_omo, fig_yc, fig_fx]:
        fig.update_layout(template='plotly_white', paper_bgcolor='white', plot_bgcolor='white')
        
    fig_ib.write_image("temp/interbank.png", width=1200, height=600)
    fig_omo.write_image("temp/omo.png", width=1200, height=600)
    fig_yc.write_image("temp/yield.png", width=1200, height=600)
    fig_fx.write_image("temp/fx.png", width=1200, height=600)
    
    # 5. Chạy AI phân tích từng biểu đồ
    print("Đang chạy AI phân tích 4 biểu đồ chuyên sâu...")
    ib_analysis = analyze_chart_interbank(data_dict.get('SBV_Interbank_Rate'))
    omo_analysis = analyze_chart_omo(data_dict.get('SBV_OMO'))
    yc_analysis = analyze_chart_yield(data_dict.get('US_Yield_Curve'), data_dict.get('SBV_Yield_Curve'))
    fx_analysis = analyze_chart_fx(data_dict.get('SBV_Exchange_Rate'), data_dict.get('US_Exchange_Rate'))
    
    # 6. Render HTML Template bằng Jinja2
    print("Đang tạo file PDF...")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('.'))
    template = env.get_template('report_template.html')
    
    # Tách đoạn đầu của report_md cho drop-cap
    md_text = report_md.replace("```markdown", "").replace("```", "").strip()
    first_p = md_text[0] if len(md_text) > 0 else "T"
    rest_p = md_text[1:] if len(md_text) > 1 else ""
    import markdown
    md_html = markdown.markdown(rest_p, extensions=['tables'])

    html_out = template.render(
        report_date=datetime.now().strftime("%d THÁNG %m, %Y"),
        summary_content_first_paragraph=first_p,
        summary_content_rest=md_html,
        
        # Ảnh (sử dụng đường dẫn tuyệt đối cho pdfkit)
        interbank_img=os.path.abspath("temp/interbank.png"),
        omo_img=os.path.abspath("temp/omo.png"),
        yield_img=os.path.abspath("temp/yield.png"),
        fx_img=os.path.abspath("temp/fx.png"),
        
        # Text phân tích
        interbank_analysis=ib_analysis,
        omo_analysis=omo_analysis,
        yield_analysis=yc_analysis,
        fx_analysis=fx_analysis,
        
        # Các Data Factboxes (Có thể nâng cấp trích xuất tự động sau, tạm gán trống để AI tự phân tích trong text)
        ib_latest_rate="--", ib_latest_vol="--", ib_trend="AUTO",
        fx_central="--", fx_vcb="--", fx_black="--", fx_dxy="--"
    )
    
    pdf_path = "Macro_Report.pdf"
    
    options = {
        'page-size': 'A4',
        'margin-top': '0in',
        'margin-right': '0in',
        'margin-bottom': '0in',
        'margin-left': '0in',
        'encoding': "UTF-8",
        'enable-local-file-access': None,
        'no-outline': None,
    }
    
    pdfkit.from_string(html_out, pdf_path, options=options)
    
    # 7. Gửi email
    print("Đang định dạng HTML và gửi Email đính kèm PDF...")
    send_daily_report(report_md, pdf_path)
    print("Tiến trình hoàn thành!")

if __name__ == "__main__":
    main()
