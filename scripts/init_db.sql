-- 创建项目数据库（MySQL 8.0+）
--
-- 这个脚本只负责“建库”，不建表、不插数据。
-- 建库之后执行：
--   1. 建表 + 导入数据：python manage.py init_demo
-- 其中 init_demo 会读取 data/books.jsonl（仓库自带的 1016 条真实榜单数据）。
--
-- 只想单独导入数据时：
--   python manage.py import_books data/books.jsonl --source dangdang
CREATE DATABASE IF NOT EXISTS dangdang_books
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;
