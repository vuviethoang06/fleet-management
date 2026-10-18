# Đề 30 – Hệ thống Quản lý Đội xe (Fleet Management) - Vũ Việt Hoàng - DTC245200750

Website quản lý **xe, bảo dưỡng, lịch trình, tài xế**, triển khai hoàn toàn bằng **Docker Compose**.

| Thành phần | Công nghệ | Truy cập |
|---|---|---|
| Web app | Python Flask + Gunicorn | https://localhost/ |
| Database | PostgreSQL 16 | (mạng nội bộ `backend`) |
| DB tool | pgAdmin 4 | https://localhost/pgadmin/ |
| Reverse proxy | Nginx (HTTPS tự ký, security headers) | cổng 80 → 443 |
| Giám sát | Prometheus + Grafana (+ cAdvisor, nginx/postgres exporter) | https://localhost/grafana/ |
| Log tập trung | Loki + Promtail (LogQL) | Grafana → Explore → Loki |

## Chạy hệ thống
```bash
git clone <URL_REPO> && cd fleet
cp .env.example .env        # ĐỔI toàn bộ mật khẩu trong .env
docker compose up -d --build
docker compose ps           # tất cả service phải Up / healthy
```
Mở https://localhost (trình duyệt cảnh báo chứng chỉ tự ký → chọn tiếp tục).
- pgAdmin: đăng nhập bằng `PGADMIN_EMAIL`/`PGADMIN_PASSWORD`; server "Fleet DB" đã khai báo sẵn, nhập mật khẩu `POSTGRES_PASSWORD` khi kết nối.
- Grafana: `GRAFANA_USER`/`GRAFANA_PASSWORD` → dashboard **Fleet - Giám sát tổng quan** (đã provisioning).
- Dừng: `docker compose down` (thêm `-v` để xóa dữ liệu).

## Lịch sử commit (theo yêu cầu đề)
1. **Commit 1** – App + PostgreSQL + pgAdmin + Nginx reverse proxy (HTTPS, security headers)
2. **Commit 2** – Prometheus + Grafana (container / web server / database)
3. **Commit 3** – Loki + Promtail + truy vấn LogQL (`docs/logql-queries.md`)
4. **Commit 4** – Hardening, kiểm thử, hoàn thiện README

## Hardening đã áp dụng
- Container ứng dụng chạy **non-root** (UID 10001), Nginx dùng image `nginx-unprivileged`, Prometheus/Grafana/Loki chạy user thường
- `cap_drop: ALL`, `no-new-privileges`, `read_only` filesystem cho app và nginx
- **Network isolation**: `backend` và `monitoring` là mạng `internal`; DB không publish cổng ra host; chỉ Nginx mở cổng 80/443
- Mật khẩu mạnh, đặt trong `.env` (không commit); PostgreSQL dùng `scram-sha-256`
- **Hạn chế quyền DB**: app dùng role `fleet_app` (chỉ SELECT/INSERT/UPDATE/DELETE), exporter dùng `fleet_monitor` (`pg_monitor`), không dùng superuser
- Nginx: `server_tokens off`, HSTS, X-Frame-Options, X-Content-Type-Options, CSP, Referrer-Policy, Permissions-Policy, TLS ≥ 1.2, rate limiting, chặn `/metrics` từ ngoài

## Kiểm tra nhanh
```bash
curl -kI https://localhost/                      # xem security headers
curl -sI http://localhost/ | head -3             # 301 → HTTPS
docker compose exec app id                       # uid=10001 (non-root)
docker compose exec nginx id                     # uid=101 (non-root)
docker compose exec db psql -U fleet_admin -d fleetdb -c '\du'
```

## Cấu trúc thư mục
```
app/ (Flask, Dockerfile, templates)   nginx/ (Dockerfile, default.conf, security-headers.conf)
postgres/ (init.sh, servers.json)     prometheus/  loki/  promtail/
grafana/ (provisioning, dashboards)   docs/        docker-compose.yml  .env.example
```
