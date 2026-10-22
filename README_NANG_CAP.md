# SmartClass AI – bản nâng cấp giao diện và quản lý lớp

## Nội dung
- Trang tổng quan xanh–tím lấy cảm hứng từ ảnh tham chiếu, không sao chép logo, tên thương hiệu khác.
- Ngân hàng câu hỏi, tạo/trộn đề, chấm trắc nghiệm, game, Gemini giữ nguyên API của phiên bản trước.
- Thêm lớp, thêm/xóa học sinh, nhập và xuất Excel .xlsx; điểm danh theo ngày.
- Nút “Tạo dữ liệu minh họa cuộc thi”: tạo 2 lớp, 8 hồ sơ mẫu, điểm danh mẫu, 8 câu hỏi, 1 đề và 1 game. Tên dữ liệu được ghi rõ MINH HỌA, không phải hồ sơ hay kết quả chấm thật.
- Chân trang: Bản quyền thuộc về Nguyễn Việt Hà.

## Cập nhật GitHub
Repository: https://github.com/thienhaktvn-gif/smartclass-ai-web-
Tải tất cả các tệp vào THƯ MỤC GỐC, thay thế app.py, app.js, style.css, index.html, render.yaml, README.md (nếu muốn) và thêm requirements.txt. KHÔNG tải lên tệp database .db, file .env, khóa Gemini hoặc mật khẩu.

## CỰC KỲ QUAN TRỌNG – cấu hình Render
Dịch vụ Render đã tạo thủ công có thể giữ buildCommand cũ, không tự dùng render.yaml. Mở dịch vụ SmartClassAI > Settings > Build & Deploy > Build Command và đặt:
    pip install -r requirements.txt && python -m py_compile app.py
Start Command:
    python app.py
Giữ gói Free. Không sửa dịch vụ HSG Tin học AI.

## Kiểm thử sau cập nhật
1. Render deploy Live; trang chủ tải được và tên bản quyền chính xác.
2. Đăng nhập giáo viên, vào “Quản lý lớp học”, bấm “Tạo dữ liệu minh họa cuộc thi” một lần.
3. Xem 2 lớp, 8 học sinh. Thử xuất Excel, nhập 1 học sinh (mã mới), rồi xóa lại.
4. Vào “Điểm danh học sinh”, chọn lớp/ngày, lưu và tải lại để xác nhận dữ liệu.
5. Vào ngân hàng câu hỏi, tạo/trộn đề, game. Thử đề luyện tập bằng câu trả lời thực để tạo kết quả chấm thật.
6. Gemini chỉ hoạt động khi GEMINI_API_KEY lưu trong Render Environment và có hạn mức sử dụng.

## Giới hạn cần lưu ý
- SQLite, hình ảnh trên Render Free là dữ liệu tạm thời, có thể mất khi redeploy/restart. Không lưu dữ liệu thật của học sinh trước khi chuyển sang cơ sở dữ liệu bền vững.
- Không có chấm tự luận bằng Gemini, không tạo video MP4 thực tế. Các kết quả trắc nghiệm được chấm bằng đáp án đã lưu.
- Demo chỉ phù hợp trình diễn, cần bảo vệ thông tin học sinh và bảo mật trước khi vận hành thật.
