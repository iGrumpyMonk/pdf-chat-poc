import pyodbc
from langchain_core.documents import Document

def db_connect(conn_str: str):
    return pyodbc.connect(conn_str, autocommit=True)

def current_max_ids(conn):
    cur = conn.cursor()
    def _mx(tbl, pk):
        try:
            cur.execute(f"SELECT MAX({pk}) FROM {tbl}")
            v = cur.fetchone()[0]
            return int(v) if v is not None else 0
        except Exception:
            return 0
    return {
        "Products": _mx("Products","product_id"),
        "Orders": _mx("Orders","order_id"),
        "OrderItems": _mx("OrderItems","order_item_id"),
    }

def fetch_new_db_docs(conn, last_ids):
    docs = []
    cur = conn.cursor()
    try:
        cur.execute("SELECT product_id, name, price FROM Products WHERE product_id > ?", last_ids["Products"])
        for pid, name, price in cur.fetchall():
            docs.append(Document(page_content=f"DB Product: id={pid}, name={name}, price={price}", metadata={"source":"db/Products","id":int(pid)}))
    except Exception:
        pass
    try:
        cur.execute("SELECT order_id, customer_name, order_date FROM Orders WHERE order_id > ?", last_ids["Orders"])
        for oid, cust, odate in cur.fetchall():
            docs.append(Document(page_content=f"DB Order: id={oid}, customer={cust}, order_date={odate}", metadata={"source":"db/Orders","id":int(oid)}))
    except Exception:
        pass
    try:
        cur.execute("""            SELECT oi.order_item_id, oi.order_id, oi.product_id, oi.quantity, p.name, oi.unit_price
            FROM OrderItems oi JOIN Products p ON p.product_id = oi.product_id
            WHERE oi.order_item_id > ?
        """, last_ids["OrderItems"])
        for oiid, oid, pid, qty, pname, unit_price in cur.fetchall():
            docs.append(Document(page_content=f"DB OrderItem: id={oiid}, order_id={oid}, product_id={pid}, qty={qty}, product={pname}, price_each={unit_price}", metadata={"source":"db/OrderItems","id":int(oiid)}))
    except Exception:
        pass
    return docs
