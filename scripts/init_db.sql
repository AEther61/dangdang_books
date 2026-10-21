-- 创建项目数据库（MySQL 8.0+）
--
-- 这个脚本只负责“建库”，不建表、不插数据：
--   1. 建表：python manage.py migrate
--   2. 样例数据：python manage.py seed_data
--   3. 爬虫数据：python manage.py import_books data/books.jsonl
CREATE DATABASE IF NOT EXISTS dangdang_books
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;
