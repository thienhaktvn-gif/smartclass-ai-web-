# SmartClass AI – Gemini & Games (Web Edition)

Phiên bản web độc lập, giao diện xanh–tím lấy cảm hứng HSG Tin học AI. Bao gồm: ngân hàng câu hỏi, tạo/trộn đề, làm bài trắc nghiệm và chấm theo đáp án, phản hồi theo từng câu, trò chơi tương tác từ câu hỏi ngân hàng, Gemini đề xuất câu hỏi, Gemini tạo ảnh minh họa (nếu model/tài khoản được cấp phép), Gemini xây dựng kịch bản phân cảnh video (không tạo MP4).

## Chạy nội bộ

Python 3.10+ không cần cài gói ngoài. Đặt biến `SMARTCLASS_SECRET` và `SMARTCLASS_ADMIN_PASSWORD` bằng giá trị riêng đủ mạnh, rồi chạy `python app.py`. Mặc định web lắng nghe cổng 10000. Đặt `SMARTCLASS_DEMO=1` nếu muốn khởi tạo sáu câu hỏi ví dụ trên cơ sở dữ liệu mới.

## Gemini

Đặt `GEMINI_API_KEY` ở **Render Environment**, không thêm key vào tệp hoặc GitHub. Model văn bản mặc định `GEMINI_MODEL=gemini-2.5-flash`; model ảnh mặc định `GEMINI_IMAGE_MODEL=gemini-2.5-flash-image`. Quyền truy cập, hạn mức miễn phí và chi phí tùy gói/tài khoản Google; không mặc định miễn phí. Giáo viên phải xác minh nội dung AI. **Không gửi dữ liệu cá nhân học sinh tới AI.** Tạo video hiện chỉ làm kịch bản phân cảnh, chưa xuất video thật.

## Triển khai Internet

Tạo repository riêng cho SmartClassAI (đừng ghi đè ứng dụng HSG Tin học AI đang hoạt động). Chép các file ở thư mục này vào gốc repo, tạo Render Web Service với `rootDir` là gốc repo, `buildCommand=python -m py_compile app.py`, `startCommand=python app.py`. Đặt `SMARTCLASS_ADMIN_USER`, `SMARTCLASS_ADMIN_PASSWORD`, `SMARTCLASS_SECRET` và nếu cần `GEMINI_API_KEY`. Hệ thống dùng SQLite và bộ nhớ phiên; **Render Free không bảo đảm dữ liệu bền vững**. Không dùng để thu dữ liệu học sinh thật cho đến khi nâng cấp DB ngoài, phiên bền vững, xác thực học sinh và giới hạn truy cập. Tệp ảnh tạo ra lưu cục bộ và sẽ mất khi Render thay instance. Mã dự thi phiên bản này là khóa trộn đề, **chưa xác thực danh tính hoặc chống nộp lại**. Gói này là bản thử nghiệm chức năng, không phải hệ thống thi chính thức.

## Bảo mật

Không công khai mật khẩu/API key. Đặt hạn mức ngân sách ở dịch vụ Gemini. Tránh để lộ đề thi chưa công bố. Endpoint game chỉ trả câu hỏi không kèm đáp án và kiểm tra đáp án trên server, nhưng game là luyện tập (không chống gian lận). AI tạo video thực cần API video có quyền và kiểm soát chi phí.
