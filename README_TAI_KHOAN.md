# SmartClass AI – đăng ký giáo viên và cách ly dữ liệu

- Bản này thêm API `POST /api/register`, giao diện đăng ký giáo viên, giới hạn tần suất đăng ký/đăng nhập, mật khẩu băm PBKDF2, cookie HttpOnly và CSRF hiện có.
- Mặc định **đóng đăng ký** (`SMARTCLASS_ALLOW_REGISTRATION=0`). Chỉ đặt `1` khi đã có ổ đĩa bền vững và chính sách bảo vệ dữ liệu phù hợp.
- Mỗi giáo viên mới có một tệp SQLite tách biệt trong thư mục `smartclass_teachers`; tài khoản quản trị cũ dùng DB cũ. Cần backup **cả DB chính lẫn thư mục DB giáo viên**.
- **Chưa hoàn thiện:** public exams/games vẫn đọc kho công bố cũ; giáo viên mới chưa có liên kết chia sẻ đề riêng cho học sinh. Chưa có xác minh email, đặt lại mật khẩu, đồng bộ giáo án trên server, hoặc đảm bảo dữ liệu không mất trên Render Free.
- Không đưa dữ liệu học sinh thật hoặc bật đăng ký công khai trên Render Free. Triển khai sản phẩm thật cần PostgreSQL/Persistent Disk, migrations và kiểm thử an ninh trước.
- Không đổi các biến GEMINI_API_KEY và GEMINI_MODEL.
