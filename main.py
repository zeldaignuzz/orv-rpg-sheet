# main.py — ORV RPG Sheet (Streamlit + SQLite) com tema, ?char=ID
# Modificado para adicionar:
#  - feature skill_popup (editor admin na sidebar e popups por habilidade/usuário)
#  - feature item_popup (editor admin na sidebar e popups por item/usuário, usada no inventário)

import sqlite3, os, base64, inspect, traceback
from datetime import datetime
import streamlit as st
import bcrypt

# ===== módulos de features (devem existir na mesma pasta) =====
import skill_popup

try:
    print("skill_popup module file:", inspect.getsourcefile(skill_popup))
except Exception:
    pass

# item_popup é modular/opcional: se o arquivo ainda não existir, o app continua funcionando
try:
    import item_popup
    try:
        print("item_popup module file:", inspect.getsourcefile(item_popup))
    except Exception:
        pass
except Exception:
    item_popup = None

DB_PATH = "rpg.db"
CATEGORIES = ["Arma", "Equipamento", "Utilitários", "Materiais"]
IMAGE_TYPES = ["png", "jpg", "jpeg", "webp", "gif"]

# ================== ESTILO ORV ==================
def _image_to_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


def apply_orv_theme():
    st.set_page_config(page_title="Ficha ORV — Multiusuário", layout="wide")
    b64 = _image_to_base64("BOMBA STATUS.png")
    if b64:
        bg_css = f"url('data:image/png;base64,{b64}')"
        bg_size = "cover"
        bg_pos = "center 10%"
    else:
        bg_css = "linear-gradient(180deg, #3bb2ff 0%, #1e8bff 40%, #0466c8 100%)"
        bg_size = "auto"
        bg_pos = "center"

    st.markdown(
        f"""
    <style>
      .stApp {{ background: {bg_css}; background-size: {bg_size}; background-position: {bg_pos}; }}
      .block-container {{
        max-width: 1200px; padding-top: 2rem; padding-bottom: 3rem; position: relative; border-radius: 18px;
        background: rgba(0, 58, 110, 0.35);
        box-shadow: 0 0 0 2px rgba(122,211,255,.5), 0 0 20px rgba(122,211,255,.3) inset; backdrop-filter: blur(4px);
      }}
      h1, h2, h3, h4, .stMarkdown p, label {{ color: #eaf6ff !important; text-shadow: 0 0 6px rgba(255,255,255,.15); }}
      .stTextInput input, .stNumberInput input, textarea, .stSelectbox input {{
        background: rgba(255,255,255,.08); color:#eaf6ff !important; border:1px solid rgba(122,211,255,.35); border-radius:10px;
      }}
      .stButton>button {{ border-radius: 12px !important; border:1px solid rgba(122,211,255,.6)!important; box-shadow:0 0 8px rgba(122,211,255,.35); }}
      .stTabs [data-baseweb="tab"] {{ background: rgba(0,0,0,.25); border-radius: 12px; padding:.4rem .9rem; border:1px solid rgba(122,211,255,.35); }}
      .pv-box {{
        margin-top:.25rem; padding:.4rem .7rem; display:inline-block; border-radius:10px;
        border:1px solid rgba(122,211,255,.5); background:rgba(0,0,0,.25);
        font-weight:600;
      }}
      .inv-cat-title {{
        margin-top:.75rem; font-weight:700; letter-spacing:.3px;
        border-left:4px solid rgba(122,211,255,.6); padding-left:.5rem;
      }}
      .appearance-card {{
        border:1px solid rgba(122,211,255,.5);
        background:rgba(0,0,0,.25);
        padding:.7rem; border-radius:12px;
      }}
      .appearance-card img {{
        border-radius:10px; border:1px solid rgba(122,211,255,.35);
        display:block; margin: 0 auto;
        max-width: 280px;
      }}
    </style>
    """,
        unsafe_allow_html=True,
    )


apply_orv_theme()

# ================== BANCO / SCHEMA ==================
SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash BLOB NOT NULL,
  is_admin INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS characters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  title TEXT,
  age INTEGER,
  sponsor TEXT,
  celestial_mark TEXT,
  innate_talent TEXT,
  coins INTEGER NOT NULL DEFAULT 0,
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stats (
  character_id INTEGER PRIMARY KEY,
  con INTEGER NOT NULL DEFAULT 0,
  dex INTEGER NOT NULL DEFAULT 0,
  cha INTEGER NOT NULL DEFAULT 0,
  str INTEGER NOT NULL DEFAULT 0,
  int INTEGER NOT NULL DEFAULT 0,
  wis INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS combat (
  character_id INTEGER PRIMARY KEY,
  hp_max INTEGER NOT NULL DEFAULT 0,
  hp_current INTEGER NOT NULL DEFAULT 0,
  hp_temp INTEGER NOT NULL DEFAULT 0,
  ac INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE
);

/* ===== ITENS (por usuário, com categoria) ===== */
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER, -- NULL = item global (admin)
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL DEFAULT 'Utilitários' CHECK(category IN ('Arma','Equipamento','Utilitários','Materiais')),
  UNIQUE(owner_user_id, name),
  FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS inventory (
  character_id INTEGER NOT NULL,
  item_id INTEGER NOT NULL,
  qty INTEGER NOT NULL DEFAULT 0,
  coins INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(character_id, item_id),
  FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE,
  FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS descriptions (
  key TEXT PRIMARY KEY,
  text TEXT NOT NULL DEFAULT ''
);

/* ===== HABILIDADES (skills por usuário) ===== */
CREATE TABLE IF NOT EXISTS skills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER, -- NULL = habilidade global (admin)
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  UNIQUE(owner_user_id, name),
  FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS character_skills (
  character_id INTEGER NOT NULL,
  skill_id INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('unique','generic','innate')),
  uses_max INTEGER NOT NULL DEFAULT 0,
  uses_current INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(character_id, skill_id),
  FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE,
  FOREIGN KEY(skill_id) REFERENCES skills(id) ON DELETE CASCADE
);

/* ===== IMAGENS (Aparência) ===== */
CREATE TABLE IF NOT EXISTS user_images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER NOT NULL,
  filename TEXT NOT NULL,
  mime TEXT NOT NULL,
  data BLOB NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS character_appearances (
  character_id INTEGER PRIMARY KEY,
  image_id INTEGER NOT NULL,
  FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE,
  FOREIGN KEY(image_id) REFERENCES user_images(id) ON DELETE CASCADE
);
"""

DEFAULT_DESCRIPTIONS = {
    "BASICO:NOME": "Nome do jogador/personagem.",
    "BASICO:TITULO": "Título/Honra.",
    "BASICO:IDADE": "Idade em anos.",
    "BASICO:PATROCINADOR": "Patrocinador.",
    "BASICO:MARCA_CELESTIAL": "Marca celestial.",
    "BASICO:TALENTO_INATO": "Talento inato.",
    "STATUS:CON": "Constituição.",
    "STATUS:DEX": "Destreza.",
    "STATUS:CHA": "Carisma.",
    "STATUS:STR": "Força.",
    "STATUS:INT": "Inteligência.",
    "STATUS:WIS": "Sabedoria.",
    "COMBATE:HP_MAX": "Vida máxima.",
    "COMBATE:HP_CURRENT": "Vida atual.",
    "COMBATE:HP_TEMP": "Vida temporária.",
    "COMBATE:AC": "Classe de Armadura.",
    "HAB:UNIQUE": "Habilidades Únicas — características exclusivas do personagem.",
    "HAB:GENERIC": "Habilidades Genéricas — truques/perícias comuns.",
    "HAB:INNATE": "Talento Inato — habilidade/benção nuclear do personagem.",
}

# ================== DB HELPERS ==================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(table: str, col: str) -> bool:
    with get_conn() as c:
        cols = [r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()]
        return col in cols


def _table_sql(name: str) -> str:
    with get_conn() as c:
        row = c.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        return row["sql"] if row and row["sql"] else ""


def bootstrap():
    conn = get_conn()
    with conn:
        conn.executescript(SCHEMA)

        # garante coluna 'wis' em stats em bancos antigos
        try:
            cur_cols = [r["name"] for r in conn.execute("PRAGMA table_info(stats)").fetchall()]
            if "wis" not in cur_cols:
                conn.execute("ALTER TABLE stats ADD COLUMN wis INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

        # garante coluna 'coins' em inventory em bancos antigos
        try:
            inv_cols = [r["name"] for r in conn.execute("PRAGMA table_info(inventory)").fetchall()]
            if "coins" not in inv_cols:
                conn.execute("ALTER TABLE inventory ADD COLUMN coins INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

        # garante colunas 'notes' e 'coins' em characters em bancos antigos
        try:
            char_cols = [r["name"] for r in conn.execute("PRAGMA table_info(characters)").fetchall()]
            if "notes" not in char_cols:
                conn.execute("ALTER TABLE characters ADD COLUMN notes TEXT NOT NULL DEFAULT ''")
            if "coins" not in char_cols:
                conn.execute("ALTER TABLE characters ADD COLUMN coins INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

        
        # garante colunas de usos em character_skills em bancos antigos
        try:
            cs_cols = [r["name"] for r in conn.execute("PRAGMA table_info(character_skills)").fetchall()]
            if "uses_max" not in cs_cols:
                conn.execute("ALTER TABLE character_skills ADD COLUMN uses_max INTEGER NOT NULL DEFAULT 0")
            if "uses_current" not in cs_cols:
                conn.execute("ALTER TABLE character_skills ADD COLUMN uses_current INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

# (Migrações antigas/extra podem ser recolocadas aqui se você tiver no projeto original.)

        # --- admin inicial
        if conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] == 0:
            conn.execute(
                "INSERT INTO users (username,password_hash,is_admin) VALUES (?,?,1)",
                ("admin", bcrypt.hashpw(b"admin", bcrypt.gensalt())),
            )
        # descrições padrão
        for k, v in DEFAULT_DESCRIPTIONS.items():
            conn.execute(
                "INSERT OR IGNORE INTO descriptions(key,text) VALUES(?,?)", (k, v)
            )


# ================== UTIL / COMPAT (safe modal) ==================
from contextlib import contextmanager


@contextmanager
def safe_modal(title: str):
    """
    Usa st.modal quando disponível; caso contrário faz um fallback inline (cabeçalho).
    Use:
       with safe_modal("Título"):
           st.markdown("...")
    """
    if hasattr(st, "modal"):
        with st.modal(title):
            yield
    else:
        st.markdown(f"### {title}")
        yield


# ================== HELPERS da aplicação ==================
def now():
    return datetime.utcnow().isoformat()


def verify_password(pw, hashed):
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed)
    except Exception:
        return False


def get_user(username):
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()


def create_character(owner_id: int, name="Novo", title=None):
    with get_conn() as c, c:
        cur = c.execute(
            """INSERT INTO characters
            (owner_user_id,name,title,age,sponsor,celestial_mark,innate_talent,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?, ?, ?)""",
            (owner_id, name, title, None, None, None, None, now(), now()),
        )
        cid = cur.lastrowid
        c.execute("INSERT INTO stats (character_id) VALUES (?)", (cid,))
        c.execute("INSERT INTO combat (character_id) VALUES (?)", (cid,))
        return cid


def list_characters(user):
    with get_conn() as c:
        if user["is_admin"]:
            return c.execute(
                "SELECT * FROM characters ORDER BY updated_at DESC"
            ).fetchall()
        return c.execute(
            "SELECT * FROM characters WHERE owner_user_id=? ORDER BY updated_at DESC",
            (user["id"],),
        ).fetchall()


def load_character(cid):
    with get_conn() as c:
        ch = c.execute("SELECT * FROM characters WHERE id=?", (cid,)).fetchone()
        stt = c.execute("SELECT * FROM stats WHERE character_id=?", (cid,)).fetchone()
        cmb = c.execute(
            "SELECT * FROM combat WHERE character_id=?", (cid,)
        ).fetchone()
        inv = c.execute(
            """
            SELECT inventory.qty,
                   inventory.coins,
                   items.id   AS item_id,
                   items.name AS name,
                   items.description AS description,
                   items.category AS category
            FROM inventory
            JOIN items ON items.id = inventory.item_id
            WHERE inventory.character_id = ?
            ORDER BY CASE items.category
                       WHEN 'Arma' THEN 1
                       WHEN 'Equipamento' THEN 2
                       WHEN 'Utilitários' THEN 3
                       WHEN 'Materiais' THEN 4
                       ELSE 5
                     END,
                     items.name
        """,
            (cid,),
        ).fetchall()
        return ch, stt, cmb, inv


def save_character_basic(cid, data):
    with get_conn() as c, c:
        c.execute(
            """UPDATE characters SET name=?, title=?, age=?, sponsor=?, celestial_mark=?, innate_talent=?, updated_at=? WHERE id=?""",
            (
                data["name"],
                data["title"],
                data["age"],
                data["sponsor"],
                data["celestial_mark"],
                data["innate_talent"],
                now(),
                cid,
            ),
        )


def save_stats(cid, d):
    with get_conn() as c, c:
        c.execute(
            "UPDATE stats SET con=?, dex=?, cha=?, str=?, int=?, wis=? WHERE character_id=?",
            (d["con"], d["dex"], d["cha"], d["str"], d["int"], d["wis"], cid),
        )
        c.execute("UPDATE characters SET updated_at=? WHERE id=?", (now(), cid))


def save_combat(cid, d):
    with get_conn() as c, c:
        c.execute(
            "UPDATE combat SET hp_max=?, hp_current=?, hp_temp=?, ac=? WHERE character_id=?",
            (d["hp_max"], d["hp_current"], d["hp_temp"], d["ac"], cid),
        )
        c.execute("UPDATE characters SET updated_at=? WHERE id=?", (now(), cid))


# ================== APARÊNCIA (imagens) ==================
def get_current_appearance(cid):
    with get_conn() as c:
        r = c.execute(
            """
            SELECT ui.id, ui.mime, ui.data, ui.filename, ui.created_at
            FROM character_appearances ca
            JOIN user_images ui ON ui.id = ca.image_id
            WHERE ca.character_id = ?
        """,
            (cid,),
        ).fetchone()
        return r


def save_uploaded_appearance(user_id: int, cid: int, uploaded_file):
    raw = uploaded_file.getvalue()
    filename = getattr(uploaded_file, "name", f"upload_{cid}")
    mime = uploaded_file.type or "application/octet-stream"
    with get_conn() as c, c:
        cur = c.execute(
            """
            INSERT INTO user_images(owner_user_id, filename, mime, data, created_at)
            VALUES (?,?,?,?,?)
        """,
            (user_id, filename, mime, raw, now()),
        )
        img_id = cur.lastrowid
        c.execute(
            """INSERT INTO character_appearances(character_id, image_id)
                     VALUES(?,?)
                     ON CONFLICT(character_id) DO UPDATE SET image_id=excluded.image_id
                  """,
            (cid, img_id),
        )
        c.execute("UPDATE characters SET updated_at=? WHERE id=?", (now(), cid))
    return img_id


# ================== ITENS por usuário (com categoria) ==================
def upsert_user_item(user_id: int, name: str, description: str, category: str) -> int:
    name = name.strip()
    category = category if category in CATEGORIES else "Utilitários"
    with get_conn() as c, c:
        c.execute(
            """
            INSERT INTO items(owner_user_id,name,description,category)
            VALUES(?,?,?,?)
            ON CONFLICT(owner_user_id,name) DO UPDATE SET
                description=COALESCE(NULLIF(?,''), description),
                category=excluded.category
        """,
            (user_id, name, description, category, description),
        )
    with get_conn() as c:
        rid = c.execute(
            "SELECT id FROM items WHERE owner_user_id=? AND name=?",
            (user_id, name),
        ).fetchone()["id"]
    return rid


def set_inv_qty(cid, item_id, qty):
    with get_conn() as c, c:
        if qty <= 0:
            c.execute(
                "DELETE FROM inventory WHERE character_id=? AND item_id=?",
                (cid, item_id),
            )
        else:
            c.execute(
                """INSERT INTO inventory(character_id,item_id,qty,coins) VALUES(?,?,?,COALESCE((SELECT coins FROM inventory WHERE character_id=? AND item_id=?),0))
                         ON CONFLICT(character_id,item_id) DO UPDATE SET qty=excluded.qty""",
                (cid, item_id, qty, cid, item_id),
            )
        c.execute("UPDATE characters SET updated_at=? WHERE id=?", (now(), cid))


def set_inv_coins(cid, item_id, coins):
    with get_conn() as c, c:
        c.execute(
            """INSERT INTO inventory(character_id,item_id,qty,coins) VALUES(?,?,0,?)
                     ON CONFLICT(character_id,item_id) DO UPDATE SET coins=excluded.coins""",
            (cid, item_id, coins),
        )
        c.execute("UPDATE characters SET updated_at=? WHERE id=?", (now(), cid))


def get_desc(key):
    with get_conn() as c:
        r = c.execute("SELECT text FROM descriptions WHERE key=?", (key,)).fetchone()
        return r["text"] if r else ""


def set_desc(key, text):
    with get_conn() as c, c:
        c.execute(
            """INSERT INTO descriptions(key,text) VALUES(?,?)
                     ON CONFLICT(key) DO UPDATE SET text=excluded.text""",
            (key, text),
        )


# ================== HABILIDADES por usuário ==================
def upsert_user_skill(user_id: int, name: str, description: str = "") -> int:
    name = name.strip()
    with get_conn() as c, c:
        c.execute(
            """INSERT INTO skills(owner_user_id,name,description) VALUES(?,?,?)
                     ON CONFLICT(owner_user_id,name) DO UPDATE SET description=COALESCE(NULLIF(?,''), description)""",
            (user_id, name, description, description),
        )
    with get_conn() as c:
        rid = c.execute(
            "SELECT id FROM skills WHERE owner_user_id=? AND name=?",
            (user_id, name),
        ).fetchone()["id"]
    return rid


def link_skill_to_char(cid: int, skill_id: int, kind: str):
    with get_conn() as c, c:
        c.execute(
            """INSERT INTO character_skills(character_id,skill_id,kind) VALUES(?,?,?)
                     ON CONFLICT(character_id,skill_id) DO UPDATE SET kind=excluded.kind""",
            (cid, skill_id, kind),
        )
        c.execute("UPDATE characters SET updated_at=? WHERE id=?", (now(), cid))


def unlink_skill_from_char(cid: int, skill_id: int):
    with get_conn() as c, c:
        c.execute(
            "DELETE FROM character_skills WHERE character_id=? AND skill_id=?",
            (cid, skill_id),
        )
        c.execute("UPDATE characters SET updated_at=? WHERE id=?", (now(), cid))


def list_skills_for_char(cid: int, kind: str):
    with get_conn() as c:
        return c.execute(
            """SELECT s.id,
                          s.name,
                          s.description,
                          s.owner_user_id,
                          cs.uses_max,
                          cs.uses_current
                   FROM character_skills cs
                   JOIN skills s ON s.id = cs.skill_id
                   WHERE cs.character_id = ? AND cs.kind = ?
                   ORDER BY s.name""",
            (cid, kind),
        ).fetchall()


def update_skill_description_if_owner(skill_id: int, owner_user_id: int, text: str):
    with get_conn() as c, c:
        c.execute(
            "UPDATE skills SET description=? WHERE id=? AND owner_user_id=?",
            (text, skill_id, owner_user_id),
        )


def delete_skill_if_owner_and_unreferenced(skill_id: int, owner_user_id: int) -> bool:
    """
    Deleta o registro em `skills` apenas se:
      - a skill existir e tiver owner_user_id == owner_user_id
      - e não houver mais linhas em character_skills referenciando essa skill
    Retorna True se o registro foi deletado, False caso não tenha sido (ou não tinha permissão).
    """
    with get_conn() as c, c:
        row = c.execute(
            "SELECT owner_user_id FROM skills WHERE id=?", (skill_id,)
        ).fetchone()
        if not row:
            return False
        if row["owner_user_id"] != owner_user_id:
            return False
        refs = c.execute(
            "SELECT COUNT(*) AS c FROM character_skills WHERE skill_id=?",
            (skill_id,),
        ).fetchone()["c"]
        if refs == 0:
            c.execute("DELETE FROM skills WHERE id=?", (skill_id,))
            return True
        return False


def update_skill_uses(cid: int, skill_id: int, uses_max: int | None = None, uses_current: int | None = None):
    """Atualiza os campos de uso para uma habilidade específica da ficha."""
    with get_conn() as c, c:
        row = c.execute(
            "SELECT uses_max, uses_current FROM character_skills WHERE character_id=? AND skill_id=?",
            (cid, skill_id),
        ).fetchone()
        if not row:
            return
        cur_max = row["uses_max"]
        cur_current = row["uses_current"]
        if uses_max is None:
            uses_max = cur_max
        if uses_current is None:
            uses_current = cur_current
        uses_max = max(0, int(uses_max))
        uses_current = max(0, min(int(uses_current), uses_max))
        c.execute(
            "UPDATE character_skills SET uses_max=?, uses_current=? WHERE character_id=? AND skill_id=?",
            (uses_max, uses_current, cid, skill_id),
        )


def reset_all_skill_uses(cid: int):
    """Restaura uses_current = uses_max para todas as habilidades da ficha."""
    with get_conn() as c, c:
        c.execute(
            "UPDATE character_skills SET uses_current = uses_max WHERE character_id=?",
            (cid,),
        )


# ================== UI BASE ==================
def header():
    mid = st.columns([1, 3, 1])[1]
    with mid:
        st.title("⟨INFORMAÇÃO DE JOGADOR⟩ — ORV")
        st.caption(
            "Multiusuário | Pop-ups | Hub do Admin | Habilidades por usuário | Inventário categorizado | Aparência com upload"
        )


def popup_desc(key, label, is_admin=False):
    if st.button(f"🔍 {label}", key=f"desc-{key}"):
        # usa safe_modal para compatibilidade com versões antigas do Streamlit
        with safe_modal(label):
            txt = st.text_area(
                "Descrição", get_desc(key), height=200, key=f"dta-{key}"
            )
            if is_admin and st.button(
                "Salvar descrição", key=f"save-desc-{key}"
            ):
                set_desc(key, txt)
                st.success("Descrição salva.")


def login_box():
    st.subheader("Entrar")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    if st.button("Login"):
        urow = get_user(u)
        if not urow or not verify_password(p, urow["password_hash"]):
            st.error("Usuário/senha inválidos.")
        else:
            # converte sqlite Row pra dict para armazenar no session_state
            st.session_state.user = dict(urow)
            st.rerun()

    st.divider()
    st.caption("Novo por aqui?")
    nu = st.text_input("Criar usuário")
    np = st.text_input("Criar senha", type="password")
    if st.button("Registrar"):
        if not nu or not np:
            st.warning("Preencha usuário e senha.")
        else:
            try:
                hashed = bcrypt.hashpw(np.encode("utf-8"), bcrypt.gensalt())
                with get_conn() as c, c:
                    c.execute(
                        "INSERT INTO users(username,password_hash) VALUES(?,?)",
                        (nu, hashed),
                    )
                st.success("Usuário criado! Faça login.")
            except sqlite3.IntegrityError:
                st.error("Usuário já existe.")


def sidebar_char_selector(user):
    st.sidebar.header("Fichas" if user["is_admin"] else "Suas fichas")
    if st.sidebar.button("➕ Nova ficha"):
        cid = create_character(user["id"], name="Novo")
        st.session_state.cid = cid
        params = dict(st.query_params)
        params["char"] = [str(cid)]
        st.query_params = params
        st.rerun()

    rows = list_characters(user)
    if not rows:
        st.sidebar.info("Nenhuma ficha. Crie uma.")
        return

    options = {
        f'#{r["id"]} — {r["name"]} (atualizado {r["updated_at"][:19]}Z)': r["id"]
        for r in rows
    }

    params = st.query_params
    if "char" in params and "cid" not in st.session_state:
        try:
            char_val = params.get("char")
            if isinstance(char_val, (list, tuple)) and char_val:
                st.session_state.cid = int(char_val[0])
            elif isinstance(char_val, str) and char_val:
                st.session_state.cid = int(char_val)
        except Exception:
            pass

    current_id = st.session_state.get("cid", list(options.values())[0])
    labels = list(options.keys())
    values = list(options.values())
    try:
        idx = values.index(current_id)
    except ValueError:
        idx = 0

    sel_label = st.sidebar.selectbox("Selecionar", labels, index=idx)
    st.session_state.cid = options[sel_label]

    params = dict(st.query_params)
    params["char"] = [str(st.session_state.cid)]
    st.query_params = params

    st.sidebar.caption("Compartilhe este URL para abrir direto nesta ficha.")


# =============== SESSÕES ===============
def section_basic(ch, is_admin, cid, user_id):
    st.subheader("Informações básicas")
    left, right = st.columns([3, 2], gap="large")

    # --- Coluna Direita: Aparência (cartão fixo) ---
    with right:
        st.markdown("#### Aparência")
        with st.container():
            st.markdown("<div class='appearance-card'>", unsafe_allow_html=True)
            cur = get_current_appearance(cid)
            if cur:
                st.image(
                    cur["data"],
                    caption=f"{cur['filename']} (atualizada {cur['created_at'][:19]}Z)",
                )
            else:
                st.caption("Nenhuma imagem definida ainda.")
            up = st.file_uploader(
                "Selecionar imagem", type=IMAGE_TYPES, key=f"ap-upload-{cid}"
            )
            save_col1, save_col2 = st.columns([1, 3])
            with save_col1:
                disabled_btn = up is None
                if st.button(
                    "💾 Salvar", key=f"ap-save-{cid}", disabled=disabled_btn
                ):
                    try:
                        save_uploaded_appearance(user_id, cid, up)
                        st.success("Aparência salva!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
            with save_col2:
                st.caption("PNG, JPG, WEBP, GIF")
            st.markdown("</div>", unsafe_allow_html=True)

    # --- Coluna Esquerda: Campos básicos (3 subcolunas) ---
    with left:
        cols = st.columns(3)
        with cols[0]:
            name = st.text_input("Nome", ch["name"] or "")
            title = st.text_input("Título", ch["title"] or "")
        with cols[1]:
            age = st.number_input("Idade", 0, 300, int(ch["age"] or 0))
            sponsor = st.text_input("Patrocinador", ch["sponsor"] or "")
        with cols[2]:
            celestial_mark = st.text_input(
                "Marca Celestial", ch["celestial_mark"] or ""
            )
            innate = st.text_input("Talento Inato", ch["innate_talent"] or "")

        if st.button("💾 Salvar básicos"):
            save_character_basic(
                ch["id"],
                dict(
                    name=name,
                    title=title,
                    age=age,
                    sponsor=sponsor,
                    celestial_mark=celestial_mark,
                    innate_talent=innate,
                ),
            )
            st.success("Básicos salvos.")


def section_status(stt, cid, is_admin):
    st.subheader("Status")
    cols = st.columns(6)
    with cols[0]:
        con = st.number_input("CON", 0, 999, int(stt["con"] or 0))
    with cols[1]:
        dex = st.number_input("DEX", 0, 999, int(stt["dex"] or 0))
    with cols[2]:
        cha = st.number_input("CHA", 0, 999, int(stt["cha"] or 0))
    with cols[3]:
        str_ = st.number_input("STR", 0, 999, int(stt["str"] or 0))
    with cols[4]:
        int_ = st.number_input("INT", 0, 999, int(stt["int"] or 0))
    with cols[5]:
        wis = st.number_input("SABEDORIA", 0, 999, int(stt["wis"] or 0))
    if st.button("💾 Salvar status"):
        save_stats(
            cid, dict(con=con, dex=dex, cha=cha, str=str_, int=int_, wis=wis)
        )
        st.success("Status salvos.")


def section_combat(cmb, cid, is_admin):
    st.subheader("Dados de combate")
    c1, c2, c3, c4 = st.columns(4)
    with c1:        hp_max = st.number_input(
            "Vida Máxima", 0, 9999, int(cmb["hp_max"] or 0), key="hp_max"
        )
    with c2:        hp_current = st.number_input(
            "Vida Atual", 0, 9999, int(cmb["hp_current"] or 0), key="hp_current"
        )
    with c3:        hp_temp = st.number_input(
            "Vida Temporária", 0, 9999, int(cmb["hp_temp"] or 0), key="hp_temp"
        )
    with c4:        ac = st.number_input(
            "Classe de Armadura", 0, 1000, int(cmb["ac"] or 0), key="ac"
        )

    temp_nonneg = max(0, int(hp_temp))
    pv_efetivo = int(hp_current) + temp_nonneg
    st.markdown(
        f"<div class='pv-box'>PV: {pv_efetivo}/{int(hp_max)}</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "PV Efetivo = Vida Atual + Vida Temporária (pode exceder o máximo)."
    )

    if st.button("💾 Salvar combate"):
        save_combat(
            cid,
            dict(
                hp_max=int(hp_max),
                hp_current=int(hp_current),
                hp_temp=int(hp_temp),
                ac=int(ac),
            ),
        )
        st.success("Combate salvo.")


# ================== INVENTÁRIO (por usuário, com categoria) ==================
def section_inventory(ch, inv, cid, is_admin, user_id):
    st.subheader("Inventário")
    st.caption(
        "Cada usuário tem seu próprio catálogo. Se o item não existir, será criado com a categoria escolhida."
    )

    cA, cB, cC, cD = st.columns([2, 1, 1, 1])
    with cA:
        item_name = st.text_input("Nome do item")
    with cB:
        qty_add = st.number_input("Qtde", 1, 9999, 1)
    with cC:
        category = st.selectbox("Categoria", CATEGORIES, index=0)
    with cD:
        desc_new = st.text_input("Descrição (opcional)")

    if st.button("➕ Adicionar/Atualizar no inventário"):
        if item_name.strip():
            item_id = upsert_user_item(
                user_id, item_name.strip(), desc_new.strip(), category
            )
            set_inv_qty(cid, item_id, qty_add)
            st.success("Inventário atualizado.")
            st.rerun()
        else:
            st.warning("Informe o nome do item.")

    if inv:
        st.write("### Itens desta ficha")
        by_cat = {cat: [] for cat in CATEGORIES}
        for r in inv:
            by_cat.get(r["category"], []).append(r)

        for cat in CATEGORIES:
            rows = by_cat.get(cat, [])
            if not rows:
                continue
            st.markdown(f"**{cat}**")
            st.caption(f"Itens da categoria {cat}")
            for row in rows:
                i1, i2, i3, i4, i5 = st.columns([3, 1, 1, 1, 1])
                with i1:
                    # Integração modular com item_popup:
                    # se existir item_popup.render_item_button, ele cuida da abertura do popup.
                    if item_popup and hasattr(
                        item_popup, "render_item_button"
                    ):
                        try:
                            item_popup.render_item_button(
                                row, cid, st.session_state.user
                            )
                        except Exception:
                            st.error(
                                "Erro ao renderizar popup de item (veja traceback no console)."
                            )
                    else:
                        # Fallback antigo: editor simples via safe_modal
                        if st.button(
                            f"🔍 {row['name']}",
                            key=f"inv-pop-{row['item_id']}",
                        ):
                            with safe_modal(
                                f"{row['name']} — {row['category']}"
                            ):
                                st.markdown("**Descrição**")
                                txt = st.text_area(
                                    " ",
                                    row["description"],
                                    height=180,
                                    key=f"inv-desc-{row['item_id']}",
                                )
                                new_cat = st.selectbox(
                                    "Categoria do catálogo",
                                    CATEGORIES,
                                    index=CATEGORIES.index(
                                        row["category"]
                                    )
                                    if row["category"] in CATEGORIES
                                    else 2,
                                    key=f"inv-cat-{row['item_id']}",
                                )
                                if st.button(
                                    "Salvar no catálogo",
                                    key=f"inv-desc-save-{row['item_id']}",
                                ):
                                    with get_conn() as c, c:
                                        c.execute(
                                            """UPDATE items
                                                 SET description=COALESCE(?, description),
                                                     category=?
                                                 WHERE id=? AND owner_user_id=?""",
                                            (
                                                txt
                                                if txt.strip()
                                                else None,
                                                new_cat,
                                                row["item_id"],
                                                user_id,
                                            ),
                                        )
                                    st.success(
                                        "Catálogo atualizado (se o item for seu)."
                                    )
                with i2:
                    newq = st.number_input(
                        "Qtd",
                        0,
                        9999,
                        int(row["qty"]),
                        key=f"qty-{row['item_id']}",
                    )
                with i3:
                    if st.button("💾", key=f"save-{row['item_id']}"):
                        set_inv_qty(
                            cid, row["item_id"], newq
                        )
                        st.success("Quantidade salva.")
                with i4:
                    if st.button("🗑️", key=f"del-{row['item_id']}"):
                        set_inv_qty(cid, row["item_id"], 0)
                        st.warning("Item removido.")
                        st.rerun()
                with i5:
                    st.caption(row["category"])
    else:
        st.info("Nenhum item neste inventário ainda.")
    st.markdown("---")
    st.markdown("### Moedas")
    # usa coluna 'coins' na tabela characters
    try:
        current_coins = int(ch["coins"]) if "coins" in ch.keys() and ch["coins"] is not None else 0
    except Exception:
        current_coins = 0
    novas_moedas = st.number_input(
        "Quantidade de moedas",
        0,
        10_000_000,
        current_coins,
        key=f"coins-char-{cid}",
    )
    if st.button("💾 Salvar moedas"):
        with get_conn() as c, c:
            c.execute(
                "UPDATE characters SET coins=?, updated_at=? WHERE id=?",
                (int(novas_moedas), now(), cid),
            )
        st.success("Moedas salvas.")




# ================== HABILIDADES ==================
def _skill_field(r, key, default=""):
    # suporte sqlite3.Row ou dict
    try:
        if hasattr(r, "get"):
            return r.get(key, default)
    except Exception:
        pass
    try:
        return r[key]
    except Exception:
        return default



def section_skills(cid: int, user_id: int):
    st.subheader("Habilidades")

    # botão global para restaurar todos os usos
    if st.button("🔄 Restaurar TODOS os usos de todas as habilidades", key=f"reset_all_uses_{cid}"):
        reset_all_skill_uses(cid)
        st.success("Todos os usos de habilidades desta ficha foram restaurados.")
        st.rerun()

    # unified add box (single input + category selector)
    st.markdown("### Adicionar / Reutilizar habilidade")
    add_row = st.columns([6, 2, 2])
    with add_row[0]:
        add_name = st.text_input("Nome da habilidade", key=f"add_skill_name_{cid}")
    with add_row[1]:
        kind_map = {
            "Única": "unique",
            "Genérica": "generic",
            "Talento Inato": "innate",
        }
        kind_label = st.selectbox(
            "Categoria", list(kind_map.keys()), index=0, key=f"add_skill_kind_{cid}"
        )
    with add_row[2]:
        add_desc = st.text_input(
            "Descrição (opcional)", key=f"add_skill_desc_{cid}"
        )
    if st.button("➕ Adicionar Habilidade", key=f"add_skill_btn_{cid}"):
        if add_name.strip():
            try:
                sid = upsert_user_skill(
                    user_id, add_name.strip(), (add_desc or "").strip()
                )
                link_skill_to_char(
                    cid, sid, kind_map.get(kind_label, "unique")
                )
                st.success(
                    f"Habilidade '{add_name.strip()}' adicionada à ficha como {kind_label}."
                )
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao adicionar habilidade: {e}")
        else:
            st.warning("Informe um nome para a habilidade.")

    st.markdown("---")

    def render_skill_row(s, kind_label_internal: str):
        # columns: popup, usos, delete
        col_popup, col_uses, col_del = st.columns([5, 4, 1])

        skill_id = s["id"]
        # --- coluna popup ---
        with col_popup:
            if hasattr(skill_popup, "render_skill_button"):
                skill_popup.render_skill_button(
                    s, cid, st.session_state.user
                )
            else:
                if st.button(
                    f"🔍 {_skill_field(s,'name')}",
                    key=f"fallback-{kind_label_internal}-{skill_id}-{cid}",
                ):
                    with safe_modal(_skill_field(s, "name")):
                        st.text_area(
                            "Descrição",
                            _skill_field(s, "description"),
                            height=220,
                        )

        # --- coluna de usos ---
        with col_uses:
            # valores atuais do banco
            try:
                max_db = int(s["uses_max"]) if "uses_max" in s.keys() and s["uses_max"] is not None else 0
            except Exception:
                max_db = 0
            try:
                cur_db = int(s["uses_current"]) if "uses_current" in s.keys() and s["uses_current"] is not None else max_db
            except Exception:
                cur_db = max_db

            usos_max = st.number_input(
                "Usos",
                0,
                999,
                max_db,
                key=f"uses_max_{cid}_{skill_id}_{kind_label_internal}",
            )
            st.markdown(f"Usos restantes: **{cur_db}**")

            cols_btn = st.columns(2)
            with cols_btn[0]:
                if st.button(
                    "− Gastar 1 uso",
                    key=f"dec_use_{cid}_{skill_id}_{kind_label_internal}",
                ):
                    novo_atual = max(0, cur_db - 1)
                    update_skill_uses(cid, skill_id, usos_max, novo_atual)
                    st.rerun()
            with cols_btn[1]:
                if st.button(
                    "Restaurar",
                    key=f"reset_use_{cid}_{skill_id}_{kind_label_internal}",
                ):
                    update_skill_uses(cid, skill_id, usos_max, usos_max)
                    st.rerun()

        # --- coluna deletar ---
        with col_del:
            if st.button("🗑️", key=f"skill-del-{kind_label_internal}-{skill_id}-{cid}"):
                try:
                    unlink_skill_from_char(cid, skill_id)
                    deleted = delete_skill_if_owner_and_unreferenced(
                        skill_id, user_id
                    )
                    if deleted:
                        st.success(
                            "Habilidade desvinculada e excluída do catálogo."
                        )
                    else:
                        st.warning(
                            "Habilidade desvinculada da ficha. (Registro mantido no catálogo se pertence a outro usuário ou ainda referenciado.)"
                        )
                except Exception as e:
                    st.error(f"Erro ao remover habilidade: {e}")
                st.rerun()

    # Únicas
    st.markdown("##### Únicas")
    uniques = list_skills_for_char(cid, "unique")
    for s in uniques:
        render_skill_row(s, "unique")

    st.markdown("---")

    # Genéricas
    st.markdown("##### Genéricas")
    generics = list_skills_for_char(cid, "generic")
    for s in generics:
        render_skill_row(s, "generic")

    st.markdown("---")

    # Talento Inato
    st.markdown("##### Talento Inato")
    innate = list_skills_for_char(cid, "innate")
    for s in innate:
        render_skill_row(s, "innate")
# ================== ANOTAÇÕES ==================
def section_notes(ch, cid):
    st.subheader("Anotações")
    try:
        current = ch["notes"] if "notes" in ch.keys() and ch["notes"] is not None else ""
    except Exception:
        # fallback se ch não for Row padrão
        try:
            current = ch.get("notes", "")
        except Exception:
            current = ""
    notas = st.text_area("Anotações da ficha", current, height=220)
    if st.button("💾 Salvar anotações"):
        with get_conn() as c, c:
            c.execute(
                "UPDATE characters SET notes=?, updated_at=? WHERE id=?",
                (notas, now(), cid),
            )
        st.success("Anotações salvas.")
# ================== ADMIN HUB ==================
def admin_hub(user):
    st.header("Hub do Administrador")
    st.info(
        "Edite fichas, descrições e catálogos globais. Altere sua senha aqui."
    )
    with get_conn() as c:
        users = c.execute(
            "SELECT id, username, is_admin FROM users ORDER BY username"
        ).fetchall()
    st.table([dict(u) for u in users])

    st.subheader("Alterar senha (admin logado)")
    np = st.text_input("Nova senha", type="password")
    if st.button("Salvar senha"):
        if np:
            hashed = bcrypt.hashpw(np.encode("utf-8"), bcrypt.gensalt())
            with get_conn() as c, c:
                c.execute(
                    "UPDATE users SET password_hash=? WHERE id=?",
                    (hashed, user["id"]),
                )
            st.success("Senha alterada.")
        else:
            st.warning("Senha não pode ser vazia.")

    st.subheader("Editar/Inserir descrição de campo (popups)")
    k = st.text_input("Chave (ex.: STATUS:CON)")
    t = st.text_area("Texto", height=150)
    c1, c2 = st.columns(2)
    if c1.button("Salvar descrição"):
        if k:
            set_desc(k, t)
            st.success("Descrição salva.")
        else:
            st.warning("Informe a chave.")
    if c2.button("Ver descrição atual"):
        if k:
            st.info(get_desc(k) or "(vazia)")
        else:
            st.warning("Informe a chave.")

    st.subheader("Itens globais (opcional)")
    iname = st.text_input("Nome do item global")
    icat = st.selectbox("Categoria do item global", CATEGORIES, index=2)
    idesc = st.text_area("Descrição do item global", height=120)
    if st.button("Salvar item global"):
        with get_conn() as c, c:
            c.execute(
                """INSERT INTO items(owner_user_id,name,description,category)
                         VALUES(NULL,?,?,?)
                         ON CONFLICT(owner_user_id,name) DO UPDATE SET
                           description=excluded.description,
                           category=excluded.category
                      """,
                (iname, idesc, icat),
            )
        st.success("Item global salvo.")

    st.subheader("Habilidades globais (opcional)")
    sname = st.text_input("Nome da habilidade global")
    sdesc = st.text_area("Descrição da habilidade global", height=120)
    if st.button("Salvar habilidade global"):
        with get_conn() as c, c:
            c.execute(
                """INSERT INTO skills(owner_user_id,name,description) VALUES(NULL,?,?)
                         ON CONFLICT(owner_user_id,name) DO UPDATE SET description=excluded.description""",
                (sname, sdesc),
            )
        st.success("Habilidade global salva.")


# ================== APLICATIVO ==================
def header_and_login():
    header()
    if "user" not in st.session_state:
        login_box()
        st.stop()
    user = st.session_state.user
    st.success(
        f"Logado como **{user['username']}** {'(admin)' if user['is_admin'] else ''}"
    )
    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()
    return user


def main():
    # bootstrap geral do app (cria tabelas principais)
    bootstrap()

    # bootstrap das features modulares (garante tabelas antes de qualquer SELECT)
    try:
        if hasattr(skill_popup, "bootstrap"):
            skill_popup.bootstrap()
    except Exception:
        traceback.print_exc()

    if item_popup:
        try:
            if hasattr(item_popup, "bootstrap"):
                item_popup.bootstrap()
        except Exception:
            traceback.print_exc()

    # login / usuário logado
    user = header_and_login()

    # seletor de ficha (define st.session_state.cid)
    sidebar_char_selector(user)
    if "cid" not in st.session_state:
        st.stop()

    cid = st.session_state.cid

    # editores na sidebar (após cid definido, para filtragem correta por ficha)
    if user.get("is_admin"):
        # editor de skill popups
        try:
            if hasattr(skill_popup, "sidebar_skill_popup_editor"):
                skill_popup.sidebar_skill_popup_editor(user)
        except Exception:
            st.sidebar.error(
                "Erro ao inicializar editor de popups de habilidade (verifique skill_popup.py)."
            )

        # editor de item popups (modular)
        if item_popup and hasattr(item_popup, "sidebar_item_popup_editor"):
            try:
                item_popup.sidebar_item_popup_editor(user)
            except Exception:
                st.sidebar.error(
                    "Erro ao inicializar editor de popups de item (verifique item_popup.py)."
                )

    ch, stt, cmb, inv = load_character(cid)

    # --- (opcional) refresh para estados de popup de skill, se skill_popup usar essa flag ---
    refresh_key = f"skill_popup_needs_refresh_{cid}"
    if st.session_state.get(refresh_key):
        for k in list(st.session_state.keys()):
            if (
                isinstance(k, str)
                and k.startswith("skill_popup_open_")
                and k.endswith(f"_{cid}")
            ):
                try:
                    st.session_state[k] = False
                except Exception:
                    try:
                        del st.session_state[k]
                    except Exception:
                        pass
        try:
            del st.session_state[refresh_key]
        except Exception:
            pass
        try:
            st.rerun()
        except Exception:
            pass

    tab1, tab2, tabSkills, tab3, tab4, tabNotes = st.tabs(
        ["Básico", "Status", "Habilidades", "Combate", "Inventário", "Anotações"]
    )
    with tab1:
        section_basic(ch, bool(user["is_admin"]), cid, user_id=user["id"])
    with tab2:
        section_status(stt, cid, bool(user["is_admin"]))
    with tabSkills:
        section_skills(cid, user_id=user["id"])
    with tab3:
        section_combat(cmb, cid, bool(user["is_admin"]))
    with tab4:
        section_inventory(ch, inv, cid, bool(user["is_admin"]), user_id=user["id"])
    with tabNotes:
        section_notes(ch, cid)

    st.divider()
    if user["is_admin"]:
        admin_hub(user)


if __name__ == "__main__":
    main()
