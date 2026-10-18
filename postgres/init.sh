#!/bin/bash
# Tạo schema + role ứng dụng quyền tối thiểu (không phải superuser)
set -e
psql -v ON_ERROR_STOP=1 -v apppw="$DB_APP_PASSWORD" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
CREATE ROLE fleet_app LOGIN PASSWORD :'apppw' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE fleet_monitor LOGIN PASSWORD :'apppw' NOSUPERUSER;
GRANT pg_monitor TO fleet_monitor;

CREATE TABLE vehicles(
  id SERIAL PRIMARY KEY, plate VARCHAR(20) UNIQUE NOT NULL, model VARCHAR(80) NOT NULL,
  year INT NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'active');
CREATE TABLE drivers(
  id SERIAL PRIMARY KEY, name VARCHAR(80) NOT NULL, license_no VARCHAR(30) UNIQUE NOT NULL, phone VARCHAR(20));
CREATE TABLE maintenance(
  id SERIAL PRIMARY KEY, vehicle_id INT NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
  description TEXT NOT NULL, due_date DATE NOT NULL, done BOOLEAN NOT NULL DEFAULT false);
CREATE TABLE trips(
  id SERIAL PRIMARY KEY, vehicle_id INT NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
  driver_id INT NOT NULL REFERENCES drivers(id), origin VARCHAR(100) NOT NULL, destination VARCHAR(100) NOT NULL,
  depart_at TIMESTAMP NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'planned');

INSERT INTO vehicles(plate,model,year) VALUES ('29A-123.45','Hyundai Solati',2021),('30F-678.90','Toyota Hiace',2020),('15C-111.22','Isuzu QKR',2022);
INSERT INTO drivers(name,license_no,phone) VALUES ('Nguyễn Văn An','B2-001122','0901000001'),('Trần Minh Bình','D-003344','0901000002');
INSERT INTO maintenance(vehicle_id,description,due_date) VALUES (1,'Thay dầu động cơ',CURRENT_DATE+10),(2,'Kiểm tra phanh',CURRENT_DATE+25);
INSERT INTO trips(vehicle_id,driver_id,origin,destination,depart_at) VALUES (1,1,'Hà Nội','Hải Phòng',now()+interval '1 day');

-- Hardening: chỉ cấp quyền DML trên bảng cần thiết, thu hồi quyền mặc định
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO fleet_app;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO fleet_app;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO fleet_app;
SQL
