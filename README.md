# JackTeamVN Bot

## 1) Bot này dùng để làm gì
Bot Telegram nội bộ để quản lý danh sách sản phẩm đã chuẩn hóa, tìm kiếm nhanh, chỉnh sửa, xuất dữ liệu và sao lưu SQLite.

## 2) Tính năng chính
- Quản lý sản phẩm: thêm, sửa, xóa theo ID
- Tìm kiếm và phân trang danh sách
- Chuẩn hóa dữ liệu đồng loạt
- Xuất TXT/CSV
- Sao lưu DB có retention
- FSM cho luồng nhiều bước (memory hoặc Redis)
- Chế độ bot riêng tư theo admin

## 3) Cấu trúc thư mục ngắn gọn
- `bot.py`: entrypoint chạy bot
- `config.py`: đọc/validate biến môi trường
- `handlers/commands.py`: router chính, gom đăng ký command modules
- `handlers/command_handlers/`: tách command theo nhóm (general, admin actions, product flows)
- `handlers/filters.py`, `handlers/states.py`: phân quyền và FSM state
- `database/`: kết nối SQLite, schema, repository
- `services/`: normalize, formatter, export
- `utils/`: logger, FSM storage, healthcheck
- `data/`, `exports/`, `logs/`, `storage/`: dữ liệu runtime

## 4) Cách tạo bot với BotFather
1. Mở Telegram, chat với `@BotFather`.
2. Dùng `/newbot` và làm theo hướng dẫn.
3. Lấy token và gán vào `BOT_TOKEN` trong `.env`.

## 5) Cách cấu hình .env
Tạo file `.env` từ mẫu:

```bash
cp .env.example .env
```

Các biến quan trọng:
- `BOT_TOKEN`: token bot
- `ADMIN_IDS`: ví dụ `123456789,987654321`
- `PRIVATE_BOT_MODE=true`: chỉ admin mới dùng được bot
- `DB_NAME=data/jackteamvn.db`
- `FSM_BACKEND=memory|redis`
- `REDIS_URL=redis://redis:6379/0`
- `BACKUP_RETENTION_DAYS=7`

## 6) Cách chạy local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

## 7) Cách chạy Docker
```bash
docker compose up -d --build
```

Xem log:
```bash
docker compose logs -f jackteamvn_bot
```

## 8) Giải thích FSM backend
- `FSM_BACKEND=memory`: lưu state trong RAM (đơn giản, mất state khi restart)
- `FSM_BACKEND=redis`: lưu state bền hơn qua Redis
- Bot sẽ tự thử Redis nếu cấu hình `FSM_BACKEND=redis` hoặc có `REDIS_URL`; nếu Redis không sẵn sàng sẽ fallback sang memory

## 9) Giải thích dữ liệu lưu bằng SQLite
- File DB mặc định: `data/jackteamvn.db`
- Bảng chính: `products`
- Audit ghi thay đổi qua `audit_log`
- Backup đặt trong `storage/backups/`

## 10) Cách backup / export
- `/backup`: tạo bản sao DB, tự dọn backup cũ theo `BACKUP_RETENTION_DAYS`
- `/export`: xuất dữ liệu ra TXT và CSV trong thư mục `exports/`

## 11) Danh sách command
- `/start` - Khởi động bot
- `/help` - Hướng dẫn sử dụng
- `/list` - Danh sách sản phẩm
- `/find` - Tìm sản phẩm
- `/add` - Thêm sản phẩm
- `/edit` - Sửa sản phẩm
- `/delete` - Xóa sản phẩm
- `/export` - Xuất dữ liệu
- `/stats` - Thống kê
- `/normalize` - Chuẩn hóa dữ liệu
- `/backup` - Sao lưu dữ liệu
- `/cancel` - Hủy thao tác

## 12) Lưu ý bảo mật
- Đây là bot nội bộ, không nên public token và file `.env`
- Khi `PRIVATE_BOT_MODE=true`, chỉ `ADMIN_IDS` mới được truy cập bot
- Các thao tác ghi dữ liệu (`/add`, `/edit`, `/delete`, `/backup`, `/normalize`, `/export`) yêu cầu quyền admin
