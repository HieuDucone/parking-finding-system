from flask import Flask, jsonify, render_template
import sqlite3
import os
from datetime import datetime
import random
import threading
import time

app = Flask(__name__)
DB_PATH = 'parking.db'

# ==================== DATABASE INITIALIZATION ====================
def init_database():
    """Khởi tạo database mới với thông tin real-time"""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE parking_lots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        capacity INTEGER NOT NULL,
        current_free INTEGER DEFAULT 0,
        occupied INTEGER DEFAULT 0,
        hourly_rate INTEGER DEFAULT 10000,
        is_24h BOOLEAN DEFAULT 1,
        phone TEXT,
        description TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE realtime_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parking_id INTEGER,
        update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        event_type TEXT,
        event_description TEXT,
        FOREIGN KEY (parking_id) REFERENCES parking_lots(id)
    )
    ''')
    
    # DỮ LIỆU MỚI - 8 BÃI XE CẬP NHẬT (THÊM BÃI TRƯỜNG CAO ĐẲNG Y TẾ BẠCH MAI)
    parking_data = [
        # 1. Bãi Đỗ Xe Ô Tô 33 P. Lý Thường Kiệt
        ("Bãi Đỗ Xe Ô Tô 33 P. Lý Thường Kiệt", 
         "33 P. Lý Thường Kiệt, Hàng Bài, Hoàn Kiếm, Hà Nội",
         21.022275813069978, 105.85292348664028, 45, 32, 13, 20000, 1,
         "024 3826 7890", "Bãi xe ô tô trung tâm phố cổ, gần Hồ Gươm"),
        
        # 2. Bãi gửi xe C1 
        ("Bãi gửi xe C1", 
         "Trần Đại Nghĩa, Bách Khoa, Hai Bà Trưng, Hà Nội",
         21.007289, 105.842975, 40, 28, 12, 15000, 1,
         "024 3869 4242", "Bãi xe rộng rãi, an ninh 24/7"),
        
        # 3. Điểm trông giữ xe số 3 
        ("Điểm trông giữ xe số 3", 
         "Đồng Tâm, Hai Bà Trưng, Hà Nội",
         20.999625, 105.845767, 25, 18, 7, 10000, 1,
         "024 3862 1234", "Bãi xe nhỏ, giá rẻ"),
        
        # 4. Bãi xe Bệnh viện Bạch Mai 
        ("Bãi đỗ xe Bệnh viện Bạch Mai", 
         "2R3Q+6V9, Phương Mai, Đống Đa, Hà Nội",
         21.002755407552762, 105.83978625095475, 60, 42, 18, 12000, 1,
         "024 3869 3731", "Bãi xe bệnh viện, ưu tiên bệnh nhân"),
        
        # 5. Bãi đỗ xe Đại học Xây dựng 
        ("Bãi đỗ xe Đại học Xây dựng", 
         "Đường Giải Phóng, Hai Bà Trưng, Hà Nội",
         21.003476021583086, 105.84265323445536, 35, 25, 10, 8000, 0,
         "024 3869 0511", "Bãi xe trong trường đại học"),
        
        ("Bãi đỗ xe NEU", 
         "Số 207 Đường Giải Phóng, Hai Bà Trưng, Hà Nội",
         21.000580494737033, 105.84255627094294, 30, 22, 8, 10000, 0,
         "024 3868 2169", "Bãi xe trường Đại học Kinh tế Quốc dân"),
        
        ("Bãi xe Hai Bà Trưng", 
         "Khu vực Hai Bà Trưng, Hà Nội",
         21.0120, 105.8550, 32, 24, 8, 13000, 1,
         "024 3865 4321", "Bãi xe khu vực Hai Bà Trưng"),
        
        ("Bãi đỗ xe Trường Cao đẳng Y tế Bạch Mai", 
         "Khu vực Trường Cao đẳng Y tế Bạch Mai, Đống Đa, Hà Nội",
         21.00091567973603, 105.83884308253705, 28, 20, 8, 9000, 0,
         "024 3868 5678", "Bãi xe dành cho cán bộ, sinh viên và khách thăm quan trường")
    ]
    
    cursor.executemany('''
        INSERT INTO parking_lots 
        (name, address, lat, lng, capacity, current_free, occupied, hourly_rate, is_24h, phone, description) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', parking_data)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Đã tạo database với {len(parking_data)} bãi xe")
    
    # HIỂN THỊ DANH SÁCH BÃI XE
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT name, capacity, current_free, occupied FROM parking_lots ORDER BY id')
    lots = cursor.fetchall()
    
    print("\n📋 DANH SÁCH 8 BÃI XE CẬP NHẬT:")
    print("=" * 90)
    total_capacity = 0
    total_free = 0
    
    for i, lot in enumerate(lots, 1):
        free_percent = (lot[2] / lot[1]) * 100 if lot[1] > 0 else 0
        status = "🟢 Nhiều chỗ" if free_percent > 60 else "🟡 Vừa" if free_percent > 30 else "🔴 Sắp đầy"
        print(f"{i:2d}. {lot[0]:45} | 📊 {lot[2]:2d}/{lot[1]:2d} chỗ ({free_percent:.0f}%) | {status}")
        total_capacity += lot[1]
        total_free += lot[2]
    
    conn.close()
    
    print("=" * 90)
    print(f"📈 TỔNG QUAN: {total_free}/{total_capacity} chỗ trống ({total_free/total_capacity*100:.1f}%)")
    print("\n🎯 ĐÃ CẬP NHẬT:")
    print("   ✓ Sửa tọa độ Bãi Lý Thường Kiệt")
    print("   ✓ Thêm 3 bãi xe mới: BV Bạch Mai, ĐH Xây dựng, NEU")
    print("   ✓ Thêm bãi mới: Trường Cao đẳng Y tế Bạch Mai")
    print("   ✗ Bỏ 2 bãi: CV Thống Nhất, Võ Thị Sáu")

# ==================== REAL-TIME UPDATE THREAD ====================
def update_parking_status():
    """Thread cập nhật số chỗ trống ngẫu nhiên"""
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, capacity, current_free FROM parking_lots')
            parking_lots = cursor.fetchall()
            
            for lot_id, capacity, current_free in parking_lots:
                change = random.randint(-3, 3)
                new_free = max(0, min(capacity, current_free + change))
                new_occupied = capacity - new_free
                
                cursor.execute('''
                    UPDATE parking_lots 
                    SET current_free = ?, occupied = ?, last_updated = ?
                    WHERE id = ?
                ''', (new_free, new_occupied, datetime.now(), lot_id))
                
                if change != 0:
                    event_desc = f"{abs(change)} xe {'vào' if change < 0 else 'ra'} bãi"
                    cursor.execute('''
                        INSERT INTO realtime_updates (parking_id, update_time, event_type, event_description)
                        VALUES (?, ?, 'UPDATE', ?)
                    ''', (lot_id, datetime.now(), event_desc))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Lỗi cập nhật: {e}")
        
        time.sleep(30)

# ==================== DATABASE CONNECTION ====================
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== ROUTES ====================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/parking')
def get_parking():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM parking_lots ORDER BY id')
        data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/parking/realtime')
def get_parking_realtime():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, address, lat, lng, capacity, 
                   current_free, occupied, hourly_rate,
                   is_24h, phone, description,
                   strftime('%H:%M', last_updated) as updated_time
            FROM parking_lots 
            ORDER BY current_free DESC
        ''')
        data = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/parking/<int:parking_id>')
def get_parking_detail(parking_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, address, lat, lng, capacity, 
                   current_free, occupied, hourly_rate,
                   is_24h, phone, description,
                   strftime('%H:%M', last_updated) as updated_time
            FROM parking_lots 
            WHERE id = ?
        ''', (parking_id,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Bãi xe không tồn tại"}), 404
            
        parking = dict(row)
        
        cursor.execute('''
            SELECT event_description, strftime('%H:%M', update_time) as time
            FROM realtime_updates 
            WHERE parking_id = ?
            ORDER BY update_time DESC
            LIMIT 5
        ''', (parking_id,))
        
        updates = cursor.fetchall()
        parking['recent_updates'] = [
            {"description": row[0], "time": row[1]} 
            for row in updates
        ]
        
        conn.close()
        return jsonify(parking)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats')
def get_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total_lots,
                SUM(capacity) as total_capacity,
                SUM(current_free) as total_free,
                SUM(occupied) as total_occupied,
                ROUND(AVG(hourly_rate), 0) as avg_price
            FROM parking_lots
        ''')
        stats = dict(cursor.fetchone())
        conn.close()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    print("=" * 80)
    print("🚀 SMART PARKING FINDER - REAL-TIME SYSTEM")
    print("=" * 80)
    
    init_database()
    
    print("\n🔄 Bật cập nhật real-time (30 giây/lần)...")
    update_thread = threading.Thread(target=update_parking_status, daemon=True)
    update_thread.start()
    
    print("\n🌐 SERVER THÔNG TIN:")
    print("   Web:     http://localhost:5000")
    print("   API:     http://localhost:5000/api/parking")
    print("   Realtime:http://localhost:5000/api/parking/realtime")
    print("   Stats:   http://localhost:5000/api/stats")
    print("=" * 80)
    print("⚡ Server đang chạy... Nhấn Ctrl+C để dừng")
    print("=" * 80)
    
    app.run(debug=True, port=5000)