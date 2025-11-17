# skill_popup.py
"""
Skill Popup feature (modular)
- Tabela com campos do SKILL TEMPLATE + bordas customizáveis
- Editor em sidebar dentro de expander (admin) com preview (renderizado via components.html)
- Render via components.html com altura dinâmica (evita corte)
- Resiliência: erros no editor aparecem no sidebar (traceback) em vez de quebrar app
- Bordas:
    - card_border_* controla a moldura do card
    - image_border_* controla a moldura da imagem/ícone
"""

import sqlite3
import os
import base64
from datetime import datetime
from contextlib import contextmanager
import traceback

import streamlit as st

DB_PATH = os.path.join(os.path.dirname(__file__), "rpg.db")


# ================== DB HELPERS ==================


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


SCHEMA_POPUP_BASE = """
CREATE TABLE IF NOT EXISTS skill_popup (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER,
  target_skill_id INTEGER,
  target_user_id INTEGER,
  title TEXT DEFAULT '',
  icon_filename TEXT DEFAULT '',
  icon_blob BLOB,
  alcance TEXT DEFAULT '',
  duracao TEXT DEFAULT '',
  tempo_uso TEXT DEFAULT '',
  acao TEXT DEFAULT '',
  area TEXT DEFAULT '',
  usos TEXT DEFAULT '',
  tipo TEXT DEFAULT '',
  rank TEXT DEFAULT '',
  descricao TEXT NOT NULL DEFAULT '',
  efeito_bonus TEXT DEFAULT '',
  card_border_type TEXT DEFAULT 'none',
  card_border_color1 TEXT DEFAULT '#ffffff',
  card_border_color2 TEXT DEFAULT '#000000',
  card_border_speed REAL DEFAULT 1.0,
  image_border_type TEXT DEFAULT 'none',
  image_border_color1 TEXT DEFAULT '#ffffff',
  image_border_color2 TEXT DEFAULT '#000000',
  image_border_speed REAL DEFAULT 1.0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(target_skill_id, target_user_id)
);
"""

# flag de bootstrap preguiçoso (lazy)
_BOOTSTRAPPED = False


def bootstrap():
    """Cria/atualiza a tabela skill_popup."""
    conn = get_conn()
    with conn:
        conn.executescript(SCHEMA_POPUP_BASE)
        try:
            existing_cols = {r["name"] for r in conn.execute("PRAGMA table_info(skill_popup)").fetchall()}
        except Exception:
            existing_cols = set()

        desired_cols = {
            "icon_filename",
            "icon_blob",
            "alcance",
            "duracao",
            "tempo_uso",
            "acao",
            "area",
            "usos",
            "tipo",
            "rank",
            "descricao",
            "efeito_bonus",
            "card_border_type",
            "card_border_color1",
            "card_border_color2",
            "card_border_speed",
            "image_border_type",
            "image_border_color1",
            "image_border_color2",
            "image_border_speed",
            "created_at",
            "updated_at",
        }

        for col in desired_cols:
            if col not in existing_cols:
                try:
                    if col == "icon_blob":
                        conn.execute(f"ALTER TABLE skill_popup ADD COLUMN {col} BLOB")
                    elif col.endswith("_speed"):
                        conn.execute(f"ALTER TABLE skill_popup ADD COLUMN {col} REAL DEFAULT 1.0")
                    else:
                        conn.execute(f"ALTER TABLE skill_popup ADD COLUMN {col} TEXT DEFAULT ''")
                except Exception:
                    # em caso de corrida / erros, ignorar
                    pass


def _ensure_bootstrap():
    """Garante que bootstrap() foi rodado pelo menos uma vez."""
    global _BOOTSTRAPPED
    if not _BOOTSTRAPPED:
        try:
            bootstrap()
        except Exception:
            traceback.print_exc()
        _BOOTSTRAPPED = True


# ================== HELPERS DE UI ==================


@contextmanager
def safe_modal(title: str):
    """
    Usa st.modal quando disponível; caso contrário faz fallback inline.
    """
    if hasattr(st, "modal"):
        with st.modal(title):
            yield
    else:
        st.markdown(f"### {title}")
        with st.container():
            yield


def row_field(row, key, default=""):
    """Acessa sqlite3.Row ou dict de forma segura."""
    try:
        if row is None:
            return default
        if hasattr(row, "keys"):
            return row[key] if key in row.keys() and row[key] is not None else default
        return row.get(key, default)
    except Exception:
        return default


# ================== CRUD POPUPS ==================


def upsert_popup(
    owner_user_id,
    target_skill_id,
    target_user_id,
    title,
    icon_filename,
    icon_blob,
    alcance,
    duracao,
    tempo_uso,
    acao,
    area,
    usos,
    tipo,
    rank,
    descricao,
    efeito_bonus,
    card_border_type="none",
    card_border_color1="#ffffff",
    card_border_color2="#000000",
    card_border_speed=1.0,
    image_border_type="none",
    image_border_color1="#ffffff",
    image_border_color2="#000000",
    image_border_speed=1.0,
):
    """
    Cria ou atualiza popup para (target_skill_id, target_user_id).
    Total de 26 colunas (sem o id) => 26 valores.
    """
    _ensure_bootstrap()
    now = _now_iso()
    conn = get_conn()
    with conn:
        cur = conn.execute(
            "SELECT id FROM skill_popup WHERE target_skill_id IS ? AND target_user_id IS ?",
            (target_skill_id, target_user_id),
        )
        row = cur.fetchone()
        if row:
            conn.execute(
                """
                UPDATE skill_popup SET
                    owner_user_id=?, title=?, icon_filename=?, icon_blob=?,
                    alcance=?, duracao=?, tempo_uso=?, acao=?, area=?,
                    usos=?, tipo=?, rank=?, descricao=?, efeito_bonus=?,
                    card_border_type=?, card_border_color1=?, card_border_color2=?, card_border_speed=?,
                    image_border_type=?, image_border_color1=?, image_border_color2=?, image_border_speed=?,
                    updated_at=?
                WHERE id=?
                """,
                (
                    owner_user_id,
                    title,
                    icon_filename,
                    icon_blob,
                    alcance,
                    duracao,
                    tempo_uso,
                    acao,
                    area,
                    usos,
                    tipo,
                    rank,
                    descricao,
                    efeito_bonus,
                    card_border_type,
                    card_border_color1,
                    card_border_color2,
                    float(card_border_speed),
                    image_border_type,
                    image_border_color1,
                    image_border_color2,
                    float(image_border_speed),
                    now,
                    row["id"],
                ),
            )
            return row["id"]
        else:
            # 26 colunas (sem o id) => 26 placeholders
            cur = conn.execute(
                """
                INSERT INTO skill_popup(
                  owner_user_id, target_skill_id, target_user_id,
                  title, icon_filename, icon_blob,
                  alcance, duracao, tempo_uso, acao, area,
                  usos, tipo, rank, descricao, efeito_bonus,
                  card_border_type, card_border_color1, card_border_color2, card_border_speed,
                  image_border_type, image_border_color1, image_border_color2, image_border_speed,
                  created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    owner_user_id,
                    target_skill_id,
                    target_user_id,
                    title,
                    icon_filename,
                    icon_blob,
                    alcance,
                    duracao,
                    tempo_uso,
                    acao,
                    area,
                    usos,
                    tipo,
                    rank,
                    descricao,
                    efeito_bonus,
                    card_border_type,
                    card_border_color1,
                    card_border_color2,
                    float(card_border_speed),
                    image_border_type,
                    image_border_color1,
                    image_border_color2,
                    float(image_border_speed),
                    now,
                    now,
                ),
            )
            return cur.lastrowid


def delete_popup(popup_id):
    _ensure_bootstrap()
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM skill_popup WHERE id=?", (popup_id,))


def list_popups():
    _ensure_bootstrap()
    with get_conn() as conn:
        return conn.execute("SELECT * FROM skill_popup ORDER BY updated_at DESC").fetchall()


def get_popup_for(skill_id=None, user_id=None):
    """
    Busca SOMENTE popup específico daquela skill + personagem.
    Nada de fallback global (evita reaproveitar popup de outra skill).
    """
    _ensure_bootstrap()
    if skill_id is None or user_id is None:
        return None

    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM skill_popup WHERE target_skill_id=? AND target_user_id=? LIMIT 1",
            (skill_id, user_id),
        ).fetchone()


# ================== BORDAS (CSS) ==================


def _css_for_border(prefix, btype, c1, c2, speed, uid):
    """
    Produz CSS para borda que *não* cobre o interior (usa pseudo-elemento quando precisa).
    Retorna (inline_css, extra_css, class_name)
    """
    safe = lambda s: s.replace('"', "'")
    cls = f"{prefix}_border_{uid}"
    inline = ""
    extra = ""

    if not btype or btype == "none":
        inline = "border: none; border-radius:12px;"
    elif btype == "solid":
        inline = f"border: 4px solid {safe(c1)}; border-radius:12px;"
    elif btype == "gradient":
        inline = (
            "border: 6px solid transparent; border-radius:14px; "
            f"-webkit-border-image: linear-gradient(90deg, {safe(c1)}, {safe(c2)}) 1; "
            f"border-image: linear-gradient(90deg, {safe(c1)}, {safe(c2)}) 1;"
        )
    elif btype == "flow":
        # gradiente se movendo ao longo da borda (cores fluindo, card parado)
        dur = max(0.6, 4.0 / float(max(0.1, speed)))
        extra = f"""
        .{cls} {{
           position: relative;
           border-radius:14px;
        }}
        .{cls}::before {{
           content: "";
           position:absolute;
           inset:-3px;
           border-radius:inherit;
           padding:3px;
           background: linear-gradient(90deg, {safe(c1)}, {safe(c2)}, {safe(c1)});
           background-size: 300% 300%;
           -webkit-mask:
             linear-gradient(#000 0 0) content-box,
             linear-gradient(#000 0 0);
           -webkit-mask-composite: xor;
                   mask-composite: exclude;
           animation: flow_{uid} {dur}s linear infinite;
        }}
        @keyframes flow_{uid} {{
           0%   {{ background-position: 0% 50%;   }}
           100% {{ background-position: 200% 50%; }}
        }}
        """
        inline = "border-radius:14px;"
    elif btype == "pulse":
        dur = max(0.6, 2.0 / float(max(0.1, speed)))
        inline = f"border: 4px solid {safe(c1)}; border-radius:14px;"
        extra = f"""
        @keyframes pulse_border_{uid} {{
           0% {{ box-shadow: 0 0 0 0 rgba(0,0,0,0); }}
           50% {{ box-shadow: 0 0 24px 8px {safe(c1)}66; }}
           100% {{ box-shadow: 0 0 0 0 rgba(0,0,0,0); }}
        }}
        .{cls} {{ animation: pulse_border_{uid} {dur}s ease-in-out infinite; }}
        """
    elif btype == "changing":
        dur = max(0.6, 3.0 / float(max(0.1, speed)))
        inline = f"border: 6px solid {safe(c1)}; border-radius:14px;"
        extra = f"""
        @keyframes changing_border_{uid} {{
           0% {{ border-color: {safe(c1)}; }}
           50% {{ border-color: {safe(c2)}; }}
           100% {{ border-color: {safe(c1)}; }}
        }}
        .{cls} {{ animation: changing_border_{uid} {dur}s linear infinite; }}
        """
    else:
        inline = f"border: 3px solid {safe(c1)}; border-radius:12px;"

    # garante que o elemento não "empurre" o layout interno
    inline = "position:relative; box-sizing:border-box; " + inline
    return inline, extra, cls


# ================== EDITOR NA SIDEBAR ==================


def sidebar_skill_popup_editor(current_user):
    """Editor na sidebar (apenas admin)."""
    try:
        _ensure_bootstrap()

        if not current_user or not current_user.get("is_admin"):
            return

        cid = st.session_state.get("cid")
        if not cid:
            st.sidebar.info("Selecione uma ficha antes de editar popups (use o seletor à esquerda).")
            return

        with st.sidebar.expander("🛠 Editor de Skill Popups (Admin)", expanded=True):
            st.markdown(f"**Editando popups para a ficha #{cid}**")

            # skills APENAS da ficha atual (character_skills + skills)
            skills = []
            with get_conn() as conn:
                try:
                    skills = conn.execute(
                        """
                        SELECT s.id, s.name
                        FROM character_skills cs
                        JOIN skills s ON s.id = cs.skill_id
                        WHERE cs.character_id = ?
                        ORDER BY s.name
                        """,
                        (cid,),
                    ).fetchall()
                except Exception:
                    skills = []

            if not skills:
                st.warning("Nenhuma skill vinculada a esta ficha ainda.")
                return

            options = [(s["name"], s["id"]) for s in skills]
            labels = [o[0] for o in options]

            # key depende do cid -> quando troca de ficha, o widget é recriado
            sel_label = st.selectbox(
                "Escolha a habilidade (alvo do popup)",
                labels,
                index=0,
                key=f"skill_popup_skill_select_{cid}",
            )
            sel_skill_id = next((o[1] for o in options if o[0] == sel_label), None)

            if sel_skill_id is None:
                st.warning("Selecione uma habilidade válida para editar o popup.")
                return

            # carrega popup existente (se houver) para (skill, ficha)
            with get_conn() as conn:
                existing = conn.execute(
                    "SELECT * FROM skill_popup WHERE target_skill_id IS ? AND target_user_id IS ?",
                    (sel_skill_id, cid),
                ).fetchone()

            title = st.text_input(
                "Título (ex: <BRAÇO OFERECIDO>)",
                value=row_field(existing, "title", ""),
            )

            st.caption("Ícone (opcional)")
            uploaded = st.file_uploader(
                "Upload do ícone",
                type=["png", "jpg", "jpeg", "webp", "gif"],
                key=f"popup_icon_upload_{sel_skill_id}_{cid}",
            )
            icon_blob = row_field(existing, "icon_blob", None)
            icon_filename = row_field(existing, "icon_filename", "")
            if uploaded:
                try:
                    icon_blob = uploaded.getvalue()
                    icon_filename = getattr(uploaded, "name", icon_filename or "icon.png")
                    st.success("Ícone carregado (salvar para persistir).")
                except Exception as e:
                    st.error(f"Erro ao ler ícone: {e}")

            st.markdown("**Metadados (canto superior direito)**")
            ca, cb = st.columns(2)
            with ca:
                alcance = st.text_input(
                    "Alcance",
                    value=row_field(existing, "alcance", "PESSOAL"),
                )
                tempo_uso = st.text_input(
                    "Tempo de uso",
                    value=row_field(existing, "tempo_uso", "INST"),
                )
                usos = st.text_input(
                    "Usos (ex: USOS 5p/D)",
                    value=row_field(existing, "usos", "USOS 5p/D"),
                )
            with cb:
                duracao = st.text_input(
                    "Duração",
                    value=row_field(existing, "duracao", "5 TURNOS"),
                )
                acao = st.text_input(
                    "Ação",
                    value=row_field(existing, "acao", "5 BONUS"),
                )
                area = st.text_input(
                    "Área",
                    value=row_field(existing, "area", "PESSOAL"),
                )

            st.markdown("**Canto esquerdo (info rápida)**")
            tipo = st.text_input("Tipo", value=row_field(existing, "tipo", "FISICO"))
            rank = st.text_input("Rank", value=row_field(existing, "rank", "E"))

            st.markdown("**Descrição e Efeito**")
            descricao = st.text_area(
                "Descrição (Markdown permitido)",
                value=row_field(existing, "descricao", ""),
                height=160,
            )
            efeito_bonus = st.text_input(
                "Efeito/Bonus",
                value=row_field(existing, "efeito_bonus", ""),
            )

            st.markdown("---")
            st.markdown("### Bordas / Aparência")
            CARD_TYPES = ["none", "solid", "gradient", "flow", "pulse", "changing"]
            cur_card_type = row_field(existing, "card_border_type", "none")
            card_border_type = st.selectbox(
                "Tipo (card)",
                CARD_TYPES,
                index=CARD_TYPES.index(cur_card_type) if cur_card_type in CARD_TYPES else 0,
            )
            card_color1 = st.color_picker(
                "Cor primária (card)",
                value=row_field(existing, "card_border_color1", "#ffffff"),
            )
            card_color2 = st.color_picker(
                "Cor secundária (card)",
                value=row_field(existing, "card_border_color2", "#000000"),
            )
            card_speed = st.slider(
                "Velocidade / intensidade (card)",
                0.2,
                5.0,
                float(row_field(existing, "card_border_speed", 1.0)),
                0.1,
            )

            IMG_TYPES = ["none", "solid", "gradient", "flow", "pulse", "changing"]
            cur_img_type = row_field(existing, "image_border_type", "none")
            image_border_type = st.selectbox(
                "Tipo (imagem)",
                IMG_TYPES,
                index=IMG_TYPES.index(cur_img_type) if cur_img_type in IMG_TYPES else 0,
            )
            image_color1 = st.color_picker(
                "Cor primária (imagem)",
                value=row_field(existing, "image_border_color1", "#ffffff"),
            )
            image_color2 = st.color_picker(
                "Cor secundária (imagem)",
                value=row_field(existing, "image_border_color2", "#000000"),
            )
            image_speed = st.slider(
                "Velocidade / intensidade (imagem)",
                0.2,
                5.0,
                float(row_field(existing, "image_border_speed", 1.0)),
                0.1,
            )

            # Previews via components.html
            import streamlit.components.v1 as components

            preview_card_css, preview_card_extra, preview_card_cls = _css_for_border(
                "preview_card",
                card_border_type,
                card_color1,
                card_color2,
                card_speed,
                f"cv{cid}",
            )
            preview_card_html = f"""
            <html><head><meta charset="utf-8"><style>
              .preview_card_box {{
                width: 320px; height: 120px; border-radius:12px;
                background: linear-gradient(180deg,#0f66b3,#0a3d8a);
                position:relative; color:#eaf6ff; padding:10px;
                box-shadow:0 8px 20px rgba(0,0,0,0.25); box-sizing:border-box;
              }}
              .preview_card_box .inner {{ padding:6px; }}
              .{preview_card_cls} {{ {preview_card_css} }}
              {preview_card_extra}
            </style></head>
            <body>
              <div class="preview_card_box {preview_card_cls}">
                <div class="inner">Preview Card</div>
              </div>
            </body></html>
            """
            components.html(preview_card_html, height=140, scrolling=False)

            preview_img_css, preview_img_extra, preview_img_cls = _css_for_border(
                "preview_img",
                image_border_type,
                image_color1,
                image_color2,
                image_speed,
                f"iv{cid}",
            )
            preview_img_html = f"""
            <html><head><meta charset="utf-8"><style>
              .preview_img_box {{
                width: 96px; height:96px; border-radius:8px;
                background:#1b6de0; display:inline-block;
                vertical-align:middle; box-sizing:border-box;
              }}
              .{preview_img_cls} {{ {preview_img_css} }}
              {preview_img_extra}
            </style></head>
            <body>
              <div class="{preview_img_cls}" style="display:inline-block;padding:6px;border-radius:10px;">
                <div class="preview_img_box"></div>
              </div>
            </body></html>
            """
            components.html(preview_img_html, height=120, scrolling=False)

            st.markdown("---")
            c1, c2 = st.columns([1, 1])
            if c1.button("Salvar Popup"):
                try:
                    upsert_popup(
                        current_user["id"],
                        sel_skill_id,
                        cid,
                        title,
                        icon_filename,
                        icon_blob,
                        alcance or "",
                        duracao or "",
                        tempo_uso or "",
                        acao or "",
                        area or "",
                        usos or "",
                        tipo or "",
                        rank or "",
                        descricao or "",
                        efeito_bonus or "",
                        card_border_type=card_border_type,
                        card_border_color1=card_color1,
                        card_border_color2=card_color2,
                        card_border_speed=float(card_speed),
                        image_border_type=image_border_type,
                        image_border_color1=image_color1,
                        image_border_color2=image_color2,
                        image_border_speed=float(image_speed),
                    )
                    st.success("Popup salvo para esta ficha e habilidade.")
                except Exception:
                    st.error("Erro ao salvar popup (veja traceback abaixo).")
                    st.code(traceback.format_exc())

            if c2.button("Excluir Popup"):
                if existing and "id" in getattr(existing, "keys", lambda: [])():
                    try:
                        delete_popup(existing["id"])
                        st.success("Popup excluído.")
                    except Exception:
                        st.error("Erro ao excluir popup (veja traceback abaixo).")
                        st.code(traceback.format_exc())
                else:
                    st.warning("Nenhum popup existente para excluir nesta combinação.")
    except Exception:
        tb = traceback.format_exc()
        try:
            st.sidebar.error("Erro ao inicializar/mostrar editor de popups (veja traceback).")
            st.sidebar.code(tb)
        except Exception:
            print("skill_popup sidebar error:\n", tb)


# ================== RENDER NO CLICAR DA LUPA ==================


def get_popups_for_character(character_id):
    _ensure_bootstrap()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM skill_popup WHERE target_user_id=? ORDER BY updated_at DESC",
            (character_id,),
        ).fetchall()


def render_skill_button(skill_row, character_id, current_user):
    """
    Desenha o botão de lupa para uma habilidade.
    skill_row deve ter colunas: id, name, description
    """

    def _get(r, k, default=""):
        try:
            return r[k] if r and hasattr(r, "keys") and k in r.keys() else default
        except Exception:
            try:
                return r.get(k, default)
            except Exception:
                return default

    _ensure_bootstrap()

    skill_id = _get(skill_row, "id", "")
    skill_name = _get(skill_row, "name", "Habilidade")
    skill_desc = _get(skill_row, "description", "")

    btn_key = f"skill_popup_btn_{skill_id}_{character_id}"
    open_key = f"skill_popup_open_{skill_id}_{character_id}"
    if open_key not in st.session_state:
        st.session_state[open_key] = False

    if st.button(f"🔍 {skill_name}", key=btn_key):
        st.session_state[open_key] = not st.session_state[open_key]

    if st.session_state.get(open_key):
        popup = get_popup_for(skill_id=skill_id, user_id=character_id)
        if popup:
            _render_skill_template_popup(popup, skill_name, skill_desc, character_id, current_user)
        else:
            with safe_modal(skill_name):
                st.markdown("**Descrição (catálogo):**")
                st.write(skill_desc or "_(sem descrição)_")


def _render_skill_template_popup(popup_row, skill_name, skill_desc, character_id, current_user):
    import html as _html
    import textwrap
    import streamlit.components.v1 as components

    def _g(k):
        return row_field(popup_row, k, "")

    title = _g("title") or skill_name
    icon_blob = _g("icon_blob")
    icon_filename = (_g("icon_filename") or "").strip()
    alcance = _g("alcance") or ""
    duracao = _g("duracao") or ""
    tempo_uso = _g("tempo_uso") or ""
    acao = _g("acao") or ""
    area = _g("area") or ""
    usos = _g("usos") or ""
    tipo = _g("tipo") or ""
    rank = _g("rank") or ""
    descricao = _g("descricao") or ""
    efeito = _g("efeito_bonus") or ""

    card_border_type = _g("card_border_type") or "none"
    card_border_color1 = _g("card_border_color1") or "#ffffff"
    card_border_color2 = _g("card_border_color2") or "#000000"
    try:
        card_border_speed = float(_g("card_border_speed") or 1.0)
    except Exception:
        card_border_speed = 1.0

    image_border_type = _g("image_border_type") or "none"
    image_border_color1 = _g("image_border_color1") or "#ffffff"
    image_border_color2 = _g("image_border_color2") or "#000000"
    try:
        image_border_speed = float(_g("image_border_speed") or 1.0)
    except Exception:
        image_border_speed = 1.0

    uid = f"{row_field(popup_row, 'id', 'x')}_{character_id}"

    # monta data URI do ícone, se houver blob
    if icon_blob:
        try:
            b64 = base64.b64encode(icon_blob).decode()
            mime = "image/png"
            if icon_filename.lower().endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"
            elif icon_filename.lower().endswith(".gif"):
                mime = "image/gif"
            elif icon_filename.lower().endswith(".webp"):
                mime = "image/webp"
            data_uri = f"data:{mime};base64,{b64}"
            icon_html_inner = (
                f'<img src="{data_uri}" '
                'style="width:96px;height:96px;object-fit:cover;'
                'border-radius:6px;display:block" />'
            )
        except Exception:
            icon_html_inner = (
                '<div style="width:96px;height:96px;border-radius:6px;'
                "background:rgba(0,0,0,0.2);display:flex;align-items:center;"
                'justify-content:center;color:#dff4ff;">ICON</div>'
            )
    else:
        icon_html_inner = (
            '<div style="width:96px;height:96px;border-radius:6px;'
            "background:rgba(0,0,0,0.2);display:flex;align-items:center;"
            'justify-content:center;color:#dff4ff;">ICON</div>'
        )

    # CSS de bordas
    card_css_inline, card_extra, card_cls = _css_for_border(
        "card",
        card_border_type,
        card_border_color1,
        card_border_color2,
        card_border_speed,
        uid,
    )
    img_css_inline, img_extra, img_cls = _css_for_border(
        "img",
        image_border_type,
        image_border_color1,
        image_border_color2,
        image_border_speed,
        uid,
    )

    descricao_esc = _html.escape(descricao).replace("\n", "<br>") if descricao else ""
    efeito_esc = _html.escape(efeito).replace("\n", "<br>") if efeito else ""
    if not descricao_esc and skill_desc:
        descricao_esc = _html.escape(skill_desc).replace("\n", "<br>")

    html = textwrap.dedent(
        f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <style>
        :root {{
          --bg1: #0f66b3;
          --bg2: #0a3d8a;
          --accent: #f7d9d9;
          --desc-bg: rgba(0,0,0,0.12);
          --effect-green: #39ff7a;
          font-family: "Segoe UI", Roboto, Arial, sans-serif;
        }}
        body {{
          margin:0;
          background: transparent;
          -webkit-font-smoothing:antialiased;
        }}
        .outer {{
          width:100%;
          display:flex;
          justify-content:center;
          padding:8px 14px;
        }}
        .card {{
          width:920px;
          border-radius:18px;
          padding:18px;
          color:#eaf6ff;
          position:relative;
          overflow:visible;
          box-sizing:border-box;
        }}
        .card-inner {{
          background: linear-gradient(180deg, var(--bg1) 0%, var(--bg2) 100%);
          border-radius:14px;
          padding:12px;
          box-sizing:border-box;
        }}
        .row {{ display:flex; gap:18px; align-items:flex-start; }}
        .icon-col {{
          width:128px;
          flex:0 0 128px;
          text-align:center;
        }}
        .meta-col {{ flex:1; position:relative; min-width:0; }}
        .title {{
          font-size:22px;
          font-weight:800;
          margin-bottom:6px;
          color:#eaf6ff;
        }}
        .top-meta {{
          position:absolute;
          right:0;
          top:0;
          text-align:right;
          font-size:13px;
          color:#e6f6ff;
        }}
        .meta-line {{ margin-bottom:6px; }}
        .desc-box {{
          margin-top:64px;
          background: var(--desc-bg);
          padding:16px 20px;
          border-radius:12px;
          width:72%;
          box-sizing: border-box;
        }}
        .desc-label {{
          font-weight:800;
          margin-bottom:6px;
          font-size:14px;
        }}
        .desc-text {{
          color:#e8f9ff;
          line-height:1.4;
          font-size:13px;
          padding-right:4px;
          word-break: break-word;
        }}
        .type-rank {{
          margin-top:6px;
          font-size:13px;
          color:#eaf6ff;
        }}
        .effect {{
          margin-top:10px;
          color: var(--effect-green);
          font-weight:800;
        }}
        @media (max-width:980px) {{
          .card {{ width:100%; padding:14px; }}
          .desc-box {{ width:100%; margin-top:12px; }}
          .top-meta {{
            position:static;
            text-align:left;
            margin-top:6px;
          }}
        }}
        .card-inner.{card_cls} {{ {card_css_inline} }}
        .{img_cls} {{ {img_css_inline} }}
        {card_extra}
        {img_extra}
      </style>
    </head>
    <body>
      <div class="outer">
        <div class="card">
          <div class="card-inner {card_cls}">
            <div class="row">
              <div class="icon-col" style="display:flex;flex-direction:column;align-items:center;">
                <div class="{img_cls}" style="display:inline-block;padding:6px;border-radius:10px; box-sizing:border-box;">
                  <div style="width:96px;height:96px;display:flex;align-items:center;justify-content:center;">
                    {icon_html_inner}
                  </div>
                </div>

                <div style="height:8px;"></div>
                <div style="font-weight:700; font-size:13px;color:#eaf6ff;margin-top:8px">
                  {_html.escape(usos)}
                </div>
                <div class="type-rank">{_html.escape(tipo)}</div>
                <div class="type-rank">[RANK {_html.escape(rank)}]</div>
              </div>

              <div class="meta-col">
                <div class="title">&lt;{_html.escape(title)}&gt;</div>

                <div class="top-meta">
                  <div class="meta-line">[ALCANCE: <strong>{_html.escape(alcance)}</strong>]</div>
                  <div class="meta-line">[DURAÇÃO: <strong>{_html.escape(duracao)}</strong>]</div>
                  <div class="meta-line">[TEMPO DE USO: <strong>{_html.escape(tempo_uso)}</strong>]</div>
                  <div class="meta-line">[AÇÃO: <strong>{_html.escape(acao)}</strong>]</div>
                  <div class="meta-line">[ÁREA: <strong>{_html.escape(area)}</strong>]</div>
                </div>

                <div class="desc-box">
                  <div class="desc-label">DESCRIÇÃO:</div>
                  <div class="desc-text">{descricao_esc}</div>
                </div>

                <div class="effect">{efeito_esc}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </body>
        </html>
    """
    ).lstrip()

    # altura dinâmica aproximada (agora considera descrição + efeito)
        # ===== ALTURA DINÂMICA MAIS PRECISA =====

    desc_lines = descricao.count("\n") + 1 if descricao else 1
    effect_lines = efeito.count("\n") + 1 if efeito else 0

    # altura aproximada por linha
    line_height = 20

    # base maior para cards grandes
    base_height = 420

    approx_height = base_height + (desc_lines * line_height) + (effect_lines * line_height)

    # se tiver borda animada, acrescenta mais espaço no iframe
    if card_border_type != "none" or image_border_type != "none":
        approx_height += 70

    # margem extra se houver ícone
    if icon_blob:
        approx_height += 40

    # limite mínimo e máximo
    approx_height = min(max(approx_height, 500), 2000)

    components.html(html, height=approx_height, scrolling=False)


