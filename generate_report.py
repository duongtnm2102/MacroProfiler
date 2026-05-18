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
    fig_yc, _ = app.plot_yield_curve(data_dict.get('US_Yield_Curve'), data_dict.get('SBV_Yield_Curve'), show_legend=True)
    fig_fx, _, _ = app.plot_exchange_rate(data_dict.get('SBV_Exchange_Rate'), data_dict.get('US_Exchange_Rate'), start_date, end_date, show_legend=True)
    
    # Lưu ảnh bằng Kaleido (Không chuyển sang nền trắng, giữ nguyên Dark Mode cho dễ thấy line neon)
    fig_ib.write_image("temp/interbank.png", width=1400, height=450)
    fig_omo.write_image("temp/omo.png", width=1400, height=450)
    fig_yc.write_image("temp/yield.png", width=1400, height=450)
    fig_fx.write_image("temp/fx.png", width=1400, height=450)
    
    # 5. Chạy AI phân tích từng biểu đồ
    print("Đang chạy AI phân tích 4 biểu đồ chuyên sâu (5 API Keys chạy song song độc lập)...")
    ib_analysis = analyze_chart_interbank(data_dict.get('SBV_Interbank_Rate'))
    omo_analysis = analyze_chart_omo(data_dict.get('SBV_OMO'))
    yc_analysis = analyze_chart_yield(data_dict.get('US_Yield_Curve'), data_dict.get('SBV_Yield_Curve'))
    fx_analysis = analyze_chart_fx(data_dict.get('SBV_Exchange_Rate'), data_dict.get('US_Exchange_Rate'))
    
    # --- TRÍCH XUẤT SỐ LIỆU CHO FACTBOXES ---
    import pandas as pd
    ib_rate, ib_vol, ib_trend = "--", "--", "NEUTRAL"
    df_ib = data_dict.get('SBV_Interbank_Rate')
    if df_ib is not None and not df_ib.empty:
        try:
            # Lọc riêng kỳ hạn Qua đêm cho Factbox
            on_mask = df_ib['Term'].astype(str).str.contains('Qua đêm|ON|O/N|OVERNIGHT', na=False, case=False, regex=True)
            df_ib_clean = df_ib[on_mask].copy()
            df_ib_clean = df_ib_clean[df_ib_clean['Rate'].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce') > 0]
            if not df_ib_clean.empty:
                ib_rate = f"{df_ib_clean.iloc[-1]['Rate']}"
                ib_vol = f"{df_ib_clean.iloc[-1]['Volume']}"
        except: pass

    fx_c, fx_v, fx_b, fx_d = "--", "--", "--", "--"
    df_fx = data_dict.get('SBV_Exchange_Rate')
    if df_fx is not None and not df_fx.empty:
        try:
            df_fx_clean = df_fx.dropna(subset=['USD_VND_Rate'])
            if not df_fx_clean.empty:
                fx_c = f"{df_fx_clean.iloc[-1].get('USD_VND_Rate', '--')}"
                fx_v = f"{df_fx_clean.iloc[-1].get('VCB_rate', '--')}"
                fx_b = f"{df_fx_clean.iloc[-1].get('Black_Market_rate', '--')}"
        except: pass
        
    df_us_fx = data_dict.get('US_Exchange_Rate')
    if df_us_fx is not None and not df_us_fx.empty:
        try:
            dxy_col = [c for c in df_us_fx.columns if c != 'Date'][0]
            df_dxy_clean = df_us_fx.dropna(subset=[dxy_col])
            if not df_dxy_clean.empty:
                fx_d = f"{float(df_dxy_clean.iloc[-1][dxy_col]):.2f}"
        except: pass

    import re
    bullets = re.findall(r'-\s*(.+)', report_md)
    cover_high = "<ul>" + "".join([f"<li style='margin-bottom: 8px;'>{b.replace('**','').strip()}</li>" for b in bullets[:3]]) + "</ul>" if len(bullets) >= 2 else "<p>Biến động thanh khoản, tỷ giá và lợi suất tiếp tục chịu ảnh hưởng từ các cú sốc vĩ mô toàn cầu.</p>"
    exec_insights = "<ul>" + "".join([f"<li style='margin-bottom: 12px; font-family: Lato, sans-serif; font-size: 12.5px; color: #D1D5DB;'>{b.replace('**','').strip()}</li>" for b in bullets[2:6]]) + "</ul>" if len(bullets) >= 4 else cover_high

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
        cover_highlights=cover_high,
        summary_content_first_paragraph=first_p,
        summary_content_rest=md_html,
        executive_insights_list=exec_insights,
        
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
        
        # Các Data Factboxes
        ib_latest_rate=ib_rate, ib_latest_vol=ib_vol, ib_trend=ib_trend,
        fx_central=fx_c, fx_vcb=fx_v, fx_black=fx_b, fx_dxy=fx_d
    )
    
    pdf_path = "Macro_Report.pdf"
    
    options = {
        'page-size': 'A4',
        'orientation': 'Landscape',
        'margin-top': '0in',
        'margin-right': '0in',
        'margin-bottom': '0in',
        'margin-left': '0in',
        'encoding': "UTF-8",
        'enable-local-file-access': None,
        'no-outline': None,
    }
    
    # Tạm tắt theo yêu cầu:
    # pdfkit.from_string(html_out, pdf_path, options=options)
    
    # 7. Gửi email
    # print("Đang định dạng HTML và gửi Email đính kèm PDF...")
    # send_daily_report(report_md, pdf_path)
    print("Tiến trình phân tích hoàn thành! (Tính năng xuất PDF và gửi Email đang được tạm tắt)")

if __name__ == "__main__":
    main()
