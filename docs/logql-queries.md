# Truy vấn LogQL (chạy trong Grafana -> Explore -> Loki)

1. Log truy cập Nginx — chỉ các request tới trang xe:
   `{service="nginx"} |= "/vehicles"`
2. Tốc độ request/giây của Nginx trong 1 phút:
   `sum(rate({service="nginx"}[1m]))`
3. Log JSON của ứng dụng, lọc mức ERROR:
   `{service="app"} | json | level="ERROR"`
4. Hoạt động nghiệp vụ — sự kiện tạo xe mới:
   `{service="app"} |= "vehicle created"`
5. Lỗi/cảnh báo từ PostgreSQL:
   `{service="db"} |~ "ERROR|FATAL|WARNING"`
6. Đếm số request theo mã trạng thái 4xx/5xx (Nginx):
   `sum(count_over_time({service="nginx"} |~ "\" (4|5)[0-9]{2} " [5m]))`
