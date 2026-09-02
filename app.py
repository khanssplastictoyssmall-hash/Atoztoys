
import os, re, json, secrets
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, session

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None
    dict_row = None

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-me-in-render")
ROOT = os.path.dirname(os.path.abspath(__file__))

def db():
    if not psycopg:
        raise RuntimeError("psycopg is not installed")
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)

def slugify(s):
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", s or "").strip().lower()
    return re.sub(r"[-\s]+", "-", s) or secrets.token_hex(4)

def init_db():
    with db() as con:
        with con.cursor() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS atoz_store_settings(
                id INT PRIMARY KEY, data JSONB NOT NULL)""")
            c.execute("""CREATE TABLE IF NOT EXISTS categories(
                id SERIAL PRIMARY KEY, parent_id INT REFERENCES categories(id) ON DELETE CASCADE,
                name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE, icon TEXT DEFAULT '🧸',
                sort_order INT DEFAULT 0)""")

            # Safe schema migration for databases created by older AtoZ Toys versions.
            # CREATE TABLE IF NOT EXISTS does not alter an existing table, so add any
            # columns required by the current app without deleting existing data.
            c.execute("ALTER TABLE categories ADD COLUMN IF NOT EXISTS parent_id INT")
            c.execute("ALTER TABLE categories ADD COLUMN IF NOT EXISTS slug TEXT")
            c.execute("ALTER TABLE categories ADD COLUMN IF NOT EXISTS icon TEXT DEFAULT '🧸'")
            c.execute("ALTER TABLE categories ADD COLUMN IF NOT EXISTS sort_order INT DEFAULT 0")
            c.execute("UPDATE categories SET icon='🧸' WHERE icon IS NULL")
            c.execute("UPDATE categories SET sort_order=0 WHERE sort_order IS NULL")

            # Back-fill missing slugs, keeping them unique even when old category
            # names are duplicated.
            c.execute("SELECT id,name,slug FROM categories ORDER BY id")
            existing = c.fetchall()
            used = set()
            for cat in existing:
                raw = (cat["slug"] or "").strip()
                base = slugify(raw or cat["name"])
                candidate = base
                n = 2
                while candidate in used:
                    candidate = f"{base}-{n}"
                    n += 1
                used.add(candidate)
                if raw != candidate:
                    c.execute("UPDATE categories SET slug=%s WHERE id=%s", (candidate, cat["id"]))
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS categories_slug_uq ON categories(slug)")
            c.execute("""CREATE TABLE IF NOT EXISTS products(
                id SERIAL PRIMARY KEY, category_id INT REFERENCES categories(id) ON DELETE SET NULL,
                name TEXT NOT NULL, description TEXT DEFAULT '', price NUMERIC(12,2) DEFAULT 0,
                old_price NUMERIC(12,2) DEFAULT 0, stock INT DEFAULT 0,
                image_url TEXT DEFAULT '', badge TEXT DEFAULT '', featured BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW())""")
            c.execute("""CREATE TABLE IF NOT EXISTS ads(
                id SERIAL PRIMARY KEY, title TEXT DEFAULT '', subtitle TEXT DEFAULT '',
                image_url TEXT DEFAULT '', position TEXT DEFAULT 'home',
                sort_order INT DEFAULT 0, active BOOLEAN DEFAULT TRUE)""")
            c.execute("""CREATE TABLE IF NOT EXISTS orders(
                id SERIAL PRIMARY KEY, order_no TEXT UNIQUE NOT NULL, customer_name TEXT NOT NULL,
                phone TEXT NOT NULL, address TEXT NOT NULL, items JSONB NOT NULL,
                total NUMERIC(12,2) NOT NULL, status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT NOW())""")
            c.execute("SELECT COUNT(*) AS n FROM atoz_store_settings")
            if c.fetchone()["n"] == 0:
                settings = {
                    "store_name":"AtoZ Toys & Keychain",
                    "tagline":"Play. Learn. Grow.",
                    "logo":"ATOZ","logo_url":"logo.svg",
                    "phone":"+91 90000 00000",
                    "email":"hello@atoztoys.in",
                    "address":"Your City, India",
                    "footer_about":"A joyful one-stop shop for toys, gifts and keychains for every little adventure.",
                    "copyright":"© 2026 AtoZ Toys & Keychain. All Rights Reserved.",
                    "facebook":"#","instagram":"#","youtube":"#","whatsapp":"#"
                }
                c.execute("INSERT INTO atoz_store_settings(id,data) VALUES(1,%s)", (json.dumps(settings),))
            c.execute("SELECT COUNT(*) AS n FROM categories")
            if c.fetchone()["n"] == 0:
                seeds = [
                    ("Action Figures",None,"🦸"),("Baby Toys",None,"🧸"),("Building Blocks",None,"🧱"),
                    ("Dolls & Accessories",None,"👗"),("Remote Control",None,"🚗"),("Outdoor Toys",None,"🛴"),
                    ("Puzzles",None,"🧩"),("Vehicles",None,"🏎️"),("Games",None,"🎮"),
                    ("Soft Toys",None,"🐻"),("Learning & Education",None,"📚"),("Musical Toys",None,"🎵"),
                    ("Party & Gifting",None,"🎁"),("Keychains",None,"🔑")
                ]
                ids={}
                for name,parent,icon in seeds:
                    c.execute("INSERT INTO categories(name,parent_id,slug,icon) VALUES(%s,%s,%s,%s) RETURNING id",
                              (name,parent,slugify(name),icon))
                    ids[name]=c.fetchone()["id"]
                nested=[("Cars",ids["Vehicles"],"🚘"),("Trucks",ids["Vehicles"],"🚚"),
                        ("Building Blocks Sets",ids["Building Blocks"],"🧱"),
                        ("Dolls",ids["Dolls & Accessories"],"👧"),
                        ("Teddy Bears",ids["Soft Toys"],"🧸"),
                        ("Educational Puzzles",ids["Puzzles"],"🧩"),
                        ("Premium Keychains",ids["Keychains"],"🔑"),
                        ("Character Keychains",ids["Keychains"],"⭐"),
                        ("Mini Cars",None,"🏎️")]
                for name,parent,icon in nested:
                    if name=="Mini Cars":
                        parent=ids["Vehicles"]
                    c.execute("INSERT INTO categories(name,parent_id,slug,icon) VALUES(%s,%s,%s,%s)",
                              (name,parent,slugify(name),icon))
            c.execute("SELECT COUNT(*) AS n FROM products")
            if c.fetchone()["n"] == 0:
                c.execute("SELECT id,name FROM categories ORDER BY id LIMIT 8")
                cats=c.fetchall()
                seed_products=[
                    ("Super Racer Car","Fast little racer for indoor play.",799,999,25,"toy-car.svg","20% OFF",True),
                    ("Rainbow Building Blocks","Creative colorful blocks for endless builds.",849,999,30,"blocks.svg","15% OFF",True),
                    ("Baby Stacking Ring","Bright stacking toy for early learning.",449,699,40,"stacking.svg","10% OFF",True),
                    ("Soft Teddy Bear","Cuddly plush friend for little ones.",899,1299,18,"teddy.svg","30% OFF",True),
                    ("Princess Doll Set","Dress-up doll with accessories.",699,999,20,"doll.svg","25% OFF",True),
                    ("Puzzle Set 100 Pcs","Fun brain-building puzzle set.",299,399,35,"puzzle.svg","20% OFF",True),
                    ("Monster Truck","Big wheels and adventurous play.",999,1299,15,"truck.svg","15% OFF",False),
                    ("Cute Keychain","Pocket-size collectible keychain.",199,299,60,"keychain.svg","NEW",False)
                ]
                for i,p in enumerate(seed_products):
                    cat_id=cats[i % len(cats)]["id"]
                    c.execute("""INSERT INTO products(category_id,name,description,price,old_price,stock,image_url,badge,featured)
                                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(cat_id,*p))
            c.execute("SELECT COUNT(*) AS n FROM ads")
            if c.fetchone()["n"] == 0:
                ads=[
                    ("UP TO 40% OFF","Action toys for little heroes","banner-action.svg","home",1),
                    ("MEGA BLOCK SALE","Build big. Dream bigger.","banner-blocks.svg","home",2),
                    ("EXTRA 10% OFF","First order special","banner-gift.svg","home",3),
                    ("TOY BONANZA","Best toys at unbelievable prices","banner-bonanza.svg","after-products",1),
                    ("NEW COLLECTION","Fresh arrivals are here","banner-new.svg","after-products",2)
                ]
                for a in ads:
                    c.execute("""INSERT INTO ads(title,subtitle,image_url,position,sort_order,active)
                                 VALUES(%s,%s,%s,%s,%s,TRUE)""",a)
        con.commit()

@app.before_request
def boot():
    if not hasattr(app, "_db_ready"):
        try:
            init_db()
            app._db_ready=True
        except Exception as e:
            app._db_error=str(e)

def rows(sql, params=()):
    with db() as con:
        with con.cursor() as c:
            c.execute(sql, params); return c.fetchall()

def one(sql, params=()):
    r=rows(sql,params); return r[0] if r else None

def ok(data=None, **kw):
    x={"ok":True}
    if data is not None: x["data"]=data
    x.update(kw); return jsonify(x)

@app.get("/")
def home(): return send_from_directory(ROOT,"index.html")
@app.get("/admin")
def admin(): return send_from_directory(ROOT,"admin.html")
@app.get("/<path:name>")
def static_root(name):
    if os.path.isfile(os.path.join(ROOT,name)): return send_from_directory(ROOT,name)
    return jsonify({"ok":False,"error":"Not found"}),404

@app.get("/api/store")
def store():
    s=one("SELECT data FROM atoz_store_settings WHERE id=1")
    return ok(settings=s["data"] if s else {})

@app.get("/api/categories")
def categories():
    return ok(categories=rows("SELECT id,parent_id,name,slug,icon,sort_order FROM categories ORDER BY sort_order,name"))

@app.get("/api/products")
def products():
    q=request.args.get("q","").strip()
    cid=request.args.get("category_id")
    featured=request.args.get("featured")
    sql="""SELECT p.*, c.name AS category_name FROM products p
           LEFT JOIN categories c ON c.id=p.category_id WHERE 1=1"""
    params=[]
    if q:
        sql+=" AND (LOWER(p.name) LIKE LOWER(%s) OR LOWER(p.description) LIKE LOWER(%s))"
        params += [f"%{q}%",f"%{q}%"]
    if cid:
        sql+=" AND p.category_id=%s"; params.append(int(cid))
    if featured=="1": sql+=" AND p.featured=TRUE"
    sql+=" ORDER BY p.created_at DESC"
    return ok(products=rows(sql,params))

@app.get("/api/products/<int:pid>")
def product(pid):
    p=one("SELECT p.*,c.name AS category_name FROM products p LEFT JOIN categories c ON c.id=p.category_id WHERE p.id=%s",(pid,))
    return ok(product=p) if p else (jsonify({"ok":False,"error":"Product not found"}),404)

@app.get("/api/ads")
def ads():
    pos=request.args.get("position")
    sql="SELECT * FROM ads WHERE active=TRUE"
    params=[]
    if pos: sql+=" AND position=%s"; params.append(pos)
    sql+=" ORDER BY sort_order,id"
    return ok(ads=rows(sql,params))

def auth():
    return session.get("admin")==True

@app.post("/api/admin/login")
def login():
    data=request.get_json() or {}
    if data.get("username")==os.getenv("ADMIN_USER","admin") and data.get("password")==os.getenv("ADMIN_PASSWORD","admin123"):
        session["admin"]=True; return ok(message="Logged in")
    return jsonify({"ok":False,"error":"Invalid login"}),401

@app.post("/api/admin/logout")
def logout():
    session.clear(); return ok()

@app.get("/api/admin/status")
def status(): return ok(logged_in=auth())

@app.put("/api/admin/settings")
def update_settings():
    if not auth(): return jsonify({"ok":False,"error":"Unauthorized"}),401
    data=request.get_json() or {}
    with db() as con:
        with con.cursor() as c:
            c.execute("UPDATE atoz_store_settings SET data=%s WHERE id=1",(json.dumps(data),))
        con.commit()
    return ok()

@app.post("/api/admin/categories")
def add_cat():
    if not auth(): return jsonify({"ok":False,"error":"Unauthorized"}),401
    d=request.get_json() or {}
    name=d.get("name","").strip()
    if not name: return jsonify({"ok":False,"error":"Name required"}),400
    with db() as con:
        with con.cursor() as c:
            c.execute("""INSERT INTO categories(parent_id,name,slug,icon,sort_order)
                         VALUES(%s,%s,%s,%s,%s) RETURNING *""",
                      (d.get("parent_id") or None,name,slugify(name),d.get("icon","🧸"),d.get("sort_order",0)))
            r=c.fetchone()
        con.commit()
    return ok(category=r)

@app.put("/api/admin/categories/<int:cid>")
def edit_cat(cid):
    if not auth(): return jsonify({"ok":False,"error":"Unauthorized"}),401
    d=request.get_json() or {}
    parent_id = d.get("parent_id") or None
    if parent_id is not None and int(parent_id) == cid:
        return jsonify({"ok":False,"error":"A category cannot be its own parent"}),400
    if parent_id is not None:
        chain=int(parent_id); seen=set()
        while chain and chain not in seen:
            seen.add(chain)
            r=one("SELECT parent_id FROM categories WHERE id=%s",(chain,))
            if not r or r["parent_id"] is None: break
            if int(r["parent_id"]) == cid:
                return jsonify({"ok":False,"error":"Cannot move a category inside its own child"}),400
            chain=int(r["parent_id"])
    with db() as con:
        with con.cursor() as c:
            c.execute("""UPDATE categories SET parent_id=%s,name=%s,icon=%s,sort_order=%s WHERE id=%s RETURNING *""",
                      (parent_id,d.get("name",""),d.get("icon","🧸"),d.get("sort_order",0),cid))
            r=c.fetchone()
        con.commit()
    return ok(category=r)

@app.delete("/api/admin/categories/<int:cid>")
def del_cat(cid):
    if not auth(): return jsonify({"ok":False,"error":"Unauthorized"}),401
    with db() as con:
        with con.cursor() as c: c.execute("DELETE FROM categories WHERE id=%s",(cid,))
        con.commit()
    return ok()

@app.post("/api/admin/products")
def add_product():
    if not auth(): return jsonify({"ok":False,"error":"Unauthorized"}),401
    d=request.get_json() or {}
    with db() as con:
        with con.cursor() as c:
            c.execute("""INSERT INTO products(category_id,name,description,price,old_price,stock,image_url,badge,featured)
                         VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                      (d.get("category_id") or None,d.get("name",""),d.get("description",""),
                       d.get("price",0),d.get("old_price",0),d.get("stock",0),d.get("image_url",""),
                       d.get("badge",""),bool(d.get("featured"))))
            r=c.fetchone()
        con.commit()
    return ok(product=r)

@app.put("/api/admin/products/<int:pid>")
def edit_product(pid):
    if not auth(): return jsonify({"ok":False,"error":"Unauthorized"}),401
    d=request.get_json() or {}
    fields=["category_id","name","description","price","old_price","stock","image_url","badge","featured"]
    vals=[d.get(f) for f in fields]
    with db() as con:
        with con.cursor() as c:
            c.execute("""UPDATE products SET category_id=%s,name=%s,description=%s,price=%s,old_price=%s,
                         stock=%s,image_url=%s,badge=%s,featured=%s WHERE id=%s RETURNING *""",(*vals,pid))
            r=c.fetchone()
        con.commit()
    return ok(product=r)

@app.delete("/api/admin/products/<int:pid>")
def del_product(pid):
    if not auth(): return jsonify({"ok":False,"error":"Unauthorized"}),401
    with db() as con:
        with con.cursor() as c: c.execute("DELETE FROM products WHERE id=%s",(pid,))
        con.commit()
    return ok()

@app.post("/api/admin/ads")
def add_ad():
    if not auth(): return jsonify({"ok":False,"error":"Unauthorized"}),401
    d=request.get_json() or {}
    with db() as con:
        with con.cursor() as c:
            c.execute("""INSERT INTO ads(title,subtitle,image_url,position,sort_order,active)
                         VALUES(%s,%s,%s,%s,%s,%s) RETURNING *""",
                      (d.get("title",""),d.get("subtitle",""),d.get("image_url",""),
                       d.get("position","home"),d.get("sort_order",0),bool(d.get("active",True))))
            r=c.fetchone()
        con.commit()
    return ok(ad=r)

@app.put("/api/admin/ads/<int:aid>")
def edit_ad(aid):
    if not auth(): return jsonify({"ok":False,"error":"Unauthorized"}),401
    d=request.get_json() or {}
    with db() as con:
        with con.cursor() as c:
            c.execute("""UPDATE ads SET title=%s,subtitle=%s,image_url=%s,position=%s,sort_order=%s,active=%s
                         WHERE id=%s RETURNING *""",
                      (d.get("title",""),d.get("subtitle",""),d.get("image_url",""),d.get("position","home"),
                       d.get("sort_order",0),bool(d.get("active",True)),aid))
            r=c.fetchone()
        con.commit()
    return ok(ad=r)

@app.delete("/api/admin/ads/<int:aid>")
def del_ad(aid):
    if not auth(): return jsonify({"ok":False,"error":"Unauthorized"}),401
    with db() as con:
        with con.cursor() as c: c.execute("DELETE FROM ads WHERE id=%s",(aid,))
        con.commit()
    return ok()

@app.post("/api/orders")
def create_order():
    d=request.get_json() or {}
    if not d.get("customer_name") or not d.get("phone") or not d.get("address") or not d.get("items"):
        return jsonify({"ok":False,"error":"Name, phone, address and items are required"}),400
    total=float(d.get("total",0))
    order_no="ATOZ-"+datetime.now().strftime("%y%m%d%H%M%S")+secrets.token_hex(2).upper()
    with db() as con:
        with con.cursor() as c:
            c.execute("""INSERT INTO orders(order_no,customer_name,phone,address,items,total)
                         VALUES(%s,%s,%s,%s,%s,%s) RETURNING id,order_no,status""",
                      (order_no,d["customer_name"],d["phone"],d["address"],json.dumps(d["items"]),total))
            r=c.fetchone()
        con.commit()
    return ok(order=r)

@app.get("/api/orders/<order_no>")
def track(order_no):
    o=one("SELECT order_no,customer_name,total,status,created_at FROM orders WHERE order_no=%s",(order_no,))
    return ok(order=o) if o else (jsonify({"ok":False,"error":"Order not found"}),404)

@app.get("/api/admin/orders")
def admin_orders():
    if not auth(): return jsonify({"ok":False,"error":"Unauthorized"}),401
    return ok(orders=rows("SELECT * FROM orders ORDER BY created_at DESC LIMIT 200"))

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
