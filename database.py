# database.py
import sqlite3

DB_NAME = "ballet_stock.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        create table if not exists track_list(
            id integer primary key autoincrement,
            target_url text, 
            mall_type text,
            product_name text,
            target_color text,
            target_size text,
            category text dafault '미분류',
            is_active integer default 1
        )
    """)
    conn.commit()
    conn.close()


# DB에 새로운 상품을 저장
def insert_track(url, mall_type, product_name, color, size, category):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            insert into track_list (target_url, mall_type, product_name, target_color, target_size, category)
            values(?, ?, ?, ?, ?, ?)
        """, (url, mall_type, product_name, color, size, category))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB 에러: {e}")
        return False
    finally:
        conn.close()


# DB에 저장된 상품을 꺼내와서 품절여부 파악
def fetch_all_tracks():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("select * from track_list")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# DB에 저장된 상품의 알람 여부 설정 (켬, 끔)
def update_track_status(item_id, is_active):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("update track_list set is_active = ? where id = ?", (is_active, item_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB 에러: {e}")
        return False
    finally:
        conn.close()


# DB에 저장된 상품을 삭제
def delete_track(item_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM track_list WHERE id = ?", (item_id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"DB 삭제 에러: {e}")
        return False
    finally:
        conn.close()