# item_popup.py
"""
Item Popup feature (modular)
- Tabela com campos específicos de ITEM + bordas customizáveis
- Editor em sidebar dentro de expander (admin) com preview (renderizado via components.html)
- Render via components.html com altura dinâmica (evita corte)
- Resiliência: erros no editor aparecem no sidebar (traceback) em vez de quebrar app
"""

import os
import sqlite3
import base64
from datetime import datetime
from contextlib import contextmanager
import traceback

import streamlit as st

DB_PATH = os.path.join(os.path.dirname(__file__), "rpg.db")


def _now_iso():
    return datetime.utcnow().isoformat()


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


SCHEMA_POPUP_BASE = """
CREATE TABLE IF NOT EXISTS item_popup (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_user_id INTEGER,
  target_item_id INTEGER,
  target_user_id INTEGER,
  title TEXT DEFAULT '',
  icon_filename TEXT DEFAULT '',
  icon_blob BLOB,
  rank TEXT DEFAULT '',
  classificacao TEXT DEFAULT '',
  tipo TEXT DEFAULT '',
  usos TEXT DEFAULT '',
  requisitos TEXT DEFAULT '',
  efeito_passivo TEXT DEFAULT '',
  bonus_equipamento TEXT DEFAULT '',
  descricao TEXT NOT NULL DEFAULT '',
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
  UNIQUE(target_item_id, target_user_id)
);
"""


def bootstrap():
    """Garante tabela item_popup com todas as colunas necessárias."""
    conn = get_conn()
    with conn:
        conn.executescript(SCHEMA_POPUP_BASE)
        try:
            existing_cols = {
                r["name"]
                for r in conn.execute("PRAGMA table_info(item_popup)").fetchall()
            }
        except Exception:
            existing_cols = set()

        desired_cols = {
            "icon_filename",
            "icon_blob",
            "rank",
            "classificacao",
            "tipo",
            "usos",
            "requisitos",
            "efeito_passivo",
            "bonus_equipamento",
            "descricao",
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
                    if col in {"icon_blob"}:
                        conn.execute(f"ALTER TABLE item_popup ADD COLUMN {col} BLOB")
                    elif col.endswith("_speed"):
                        conn.execute(
                            f"ALTER TABLE item_popup "
                            f"ADD COLUMN {col} REAL DEFAULT 1.0"
                        )
                    elif col in {"created_at", "updated_at"}:
                        conn.execute(
                            f"ALTER TABLE item_popup "
                            f"ADD COLUMN {col} TEXT NOT NULL DEFAULT ''"
                        )
                    else:
                        conn.execute(
                            f"ALTER TABLE item_popup "
                            f"ADD COLUMN {col} TEXT DEFAULT ''"
                        )
                except Exception:
                    # em migração, erros em ALTER TABLE são ignorados
                    pass


@contextmanager
def safe_modal(title: str):
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


def upsert_popup(
    owner_user_id,
    target_item_id,
    target_user_id,
    title,
    icon_filename,
    icon_blob,
    rank,
    classificacao,
    tipo,
    usos,
    requisitos,
    efeito_passivo,
    bonus_equipamento,
    descricao,
    card_border_type="none",
    card_border_color1="#ffffff",
    card_border_color2="#000000",
    card_border_speed=1.0,
    image_border_type="none",
    image_border_color1="#ffffff",
    image_border_color2="#000000",
    image_border_speed=1.0,
):
    now = _now_iso()
    conn = get_conn()
    with conn:
        cur = conn.execute(
            "SELECT id FROM item_popup "
            "WHERE target_item_id IS ? AND target_user_id IS ?",
            (target_item_id, target_user_id),
        )
        row = cur.fetchone()
        if row:
            conn.execute(
                """
                UPDATE item_popup SET
                    owner_user_id=?,
                    title=?,
                    icon_filename=?,
                    icon_blob=?,
                    rank=?,
                    classificacao=?,
                    tipo=?,
                    usos=?,
                    requisitos=?,
                    efeito_passivo=?,
                    bonus_equipamento=?,
                    descricao=?,
                    card_border_type=?,
                    card_border_color1=?,
                    card_border_color2=?,
                    card_border_speed=?,
                    image_border_type=?,
                    image_border_color1=?,
                    image_border_color2=?,
                    image_border_speed=?,
                    updated_at=?
                WHERE id=?
            """,
                (
                    owner_user_id,
                    title,
                    icon_filename,
                    icon_blob,
                    rank,
                    classificacao,
                    tipo,
                    usos,
                    requisitos,
                    efeito_passivo,
                    bonus_equipamento,
                    descricao,
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
            cur = conn.execute(
                """
                INSERT INTO item_popup(
                  owner_user_id, target_item_id, target_user_id,
                  title, icon_filename, icon_blob,
                  rank, classificacao, tipo, usos, requisitos,
                  efeito_passivo, bonus_equipamento, descricao,
                  card_border_type, card_border_color1, card_border_color2, card_border_speed,
                  image_border_type, image_border_color1, image_border_color2, image_border_speed,
                  created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
                (
                    owner_user_id,
                    target_item_id,
                    target_user_id,
                    title,
                    icon_filename,
                    icon_blob,
                    rank,
                    classificacao,
                    tipo,
                    usos,
                    requisitos,
                    efeito_passivo,
                    bonus_equipamento,
                    descricao,
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
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM item_popup WHERE id=?", (popup_id,))


def get_popup_for(item_id=None, user_id=None):
    """Busca popup com prioridade: (item+user) > (item global) > (user global) > global."""
    with get_conn() as conn:
        if item_id is not None and user_id is not None:
            r = conn.execute(
                "SELECT * FROM item_popup "
                "WHERE target_item_id=? AND target_user_id=? LIMIT 1",
                (item_id, user_id),
            ).fetchone()
            if r:
                return r
        if item_id is not None:
            r = conn.execute(
                "SELECT * FROM item_popup "
                "WHERE target_item_id=? AND target_user_id IS NULL LIMIT 1",
                (item_id,),
            ).fetchone()
            if r:
                return r
        if user_id is not None:
            r = conn.execute(
                "SELECT * FROM item_popup "
                "WHERE target_item_id IS NULL AND target_user_id=? LIMIT 1",
                (user_id,),
            ).fetchone()
            if r:
                return r
        r = conn.execute(
            "SELECT * FROM item_popup "
            "WHERE target_item_id IS NULL AND target_user_id IS NULL LIMIT 1"
        ).fetchone()
        return r


def _css_for_border(prefix, btype, c1, c2, speed, uid):
    """
    Produz CSS para borda que *não* cobre o interior (usa border/border-image).
    Retorna (inline_css, extra_css, class_name)

    Implementação idêntica à versão estável do skill_popup,
    com animação FLOW usando conic-gradient + variável CSS,
    para que APENAS as cores "girem" e não o card inteiro.
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
            "border: 6px solid transparent; border-radius:14px;"
            f"-webkit-border-image: linear-gradient(90deg,{safe(c1)},{safe(c2)}) 1;"
            f"border-image: linear-gradient(90deg,{safe(c1)},{safe(c2)}) 1;"
        )
    elif btype == "flow":
        # anima apenas o ÂNGULO do gradiente, não o card
        dur = max(0.6, 4.0 / float(max(0.1, speed)))
        extra = f"""
        @keyframes flow_{uid} {{
           0%   {{ --pos: 0deg;   }}
           100% {{ --pos: 360deg; }}
        }}
        .{cls} {{
           border: 6px solid transparent;
           border-radius:14px;
           --pos: 0deg;
           -webkit-border-image: conic-gradient(from var(--pos), {safe(c1)}, {safe(c2)}, {safe(c1)}) 1;
           border-image: conic-gradient(from var(--pos), {safe(c1)}, {safe(c2)}, {safe(c1)}) 1;
           animation: flow_{uid} {dur}s linear infinite;
        }}
        """
        inline = ""
    elif btype == "pulse":
        dur = max(0.6, 2.0 / float(max(0.1, speed)))
        inline = f"border: 4px solid {safe(c1)}; border-radius:14px;"
        extra = f"""
        @keyframes pulse_border_{uid} {{
           0%   {{ box-shadow: 0 0 0 0 rgba(0,0,0,0); }}
           50%  {{ box-shadow: 0 0 24px 8px {safe(c1)}66; }}
           100% {{ box-shadow: 0 0 0 0 rgba(0,0,0,0); }}
        }}
        .{cls} {{
           animation: pulse_border_{uid} {dur}s ease-in-out infinite;
        }}
        """
    elif btype == "changing":
        dur = max(0.6, 3.0 / float(max(0.1, speed)))
        inline = f"border: 6px solid {safe(c1)}; border-radius:14px;"
        extra = f"""
        @keyframes changing_border_{uid} {{
           0%   {{ border-color: {safe(c1)}; }}
           50%  {{ border-color: {safe(c2)}; }}
           100% {{ border-color: {safe(c1)}; }}
        }}
        .{cls} {{
           animation: changing_border_{uid} {dur}s linear infinite;
        }}
        """
    else:
        inline = f"border: 3px solid {safe(c1)}; border-radius:12px;"

    inline = "position:relative; box-sizing:border-box; " + inline
    return inline, extra, cls


def sidebar_item_popup_editor(current_user):
    """
    Editor de item popups (apenas admin). Só mostra itens da ficha selecionada.
    """
    try:
        if not current_user or not current_user.get("is_admin"):
            return

        cid = st.session_state.get("cid")
        if not cid:
            st.sidebar.info(
                "Selecione uma ficha antes de editar popups de item "
                "(use o seletor à esquerda)."
            )
            return

        with st.sidebar.expander("📦 Editor de Item Popups (Admin)", expanded=True):
            st.markdown(f"**Editando popups de ITEM para a ficha #{cid}**")

            # Lista apenas itens da ficha atual (inventory + items)
            with get_conn() as conn:
                try:
                    rows = conn.execute(
                        """
                        SELECT i.id, i.name
                        FROM inventory inv
                        JOIN items i ON i.id = inv.item_id
                        WHERE inv.character_id = ?
                        ORDER BY i.name
                        """,
                        (cid,),
                    ).fetchall()
                except Exception:
                    rows = []

            if not rows:
                st.info("Esta ficha não possui itens no inventário.")
                return

            options = [("— QUALQUER ITEM —", None)] + [
                (r["name"], r["id"]) for r in rows
            ]
            labels = [o[0] for o in options]

            sel_label = st.selectbox(
                "Escolha o item (alvo do popup)",
                labels,
                index=0,
                key=f"item_popup_select_item_{cid}",
            )
            sel_item_id = next(
                (o[1] for o in options if o[0] == sel_label), None
            )

            with get_conn() as conn:
                existing = conn.execute(
                    "SELECT * FROM item_popup "
                    "WHERE target_item_id IS ? AND target_user_id IS ?",
                    (sel_item_id, cid),
                ).fetchone()

            # -------- CAMPOS DO POPUP --------
            title = st.text_input(
                "Título (ex: <TESOURO DE [?]>)",
                value=row_field(existing, "title", ""),
                key=f"item_popup_title_{cid}_{sel_item_id}",
            )

            st.caption("Ícone (opcional)")
            upload_key = f"item_popup_icon_upload_{cid}_{sel_item_id}"
            uploaded = st.file_uploader(
                "Upload do ícone",
                type=["png", "jpg", "jpeg", "webp", "gif"],
                key=upload_key,
            )
            icon_blob = row_field(existing, "icon_blob", None)
            icon_filename = row_field(existing, "icon_filename", "")
            if uploaded:
                try:
                    icon_blob = uploaded.getvalue()
                    icon_filename = (
                        getattr(uploaded, "name", None)
                        or icon_filename
                        or "icon.png"
                    )
                    st.success("Ícone carregado (salvar para persistir).")
                except Exception as e:
                    st.error(f"Erro ao ler ícone: {e}")

            st.markdown("**Metadados (lado direito)**")
            cA, cB = st.columns(2)
            with cA:
                rank = st.text_input(
                    "Rank",
                    value=row_field(existing, "rank", "A"),
                    key=f"item_popup_rank_{cid}_{sel_item_id}",
                )
                classificacao = st.text_input(
                    "Classificação",
                    value=row_field(existing, "classificacao", "EQUIPAMENTO"),
                    key=f"item_popup_class_{cid}_{sel_item_id}",
                )
                tipo = st.text_input(
                    "Tipo",
                    value=row_field(existing, "tipo", "COLAR"),
                    key=f"item_popup_tipo_{cid}_{sel_item_id}",
                )
            with cB:
                usos = st.text_input(
                    "Usos",
                    value=row_field(existing, "usos", "1/1"),
                    key=f"item_popup_usos_{cid}_{sel_item_id}",
                )
                requisitos = st.text_input(
                    "Requisitos",
                    value=row_field(existing, "requisitos", "N/A"),
                    key=f"item_popup_req_{cid}_{sel_item_id}",
                )

            st.markdown("**EFEITO PASSIVO**")
            efeito_passivo = st.text_area(
                "Efeito passivo (uma linha por efeito)",
                value=row_field(existing, "efeito_passivo", ""),
                height=80,
                key=f"item_popup_eff_{cid}_{sel_item_id}",
            )

            st.markdown("**BÔNUS DE EQUIPAMENTO**")
            bonus_equip = st.text_area(
                "Bônus de equipamento (uma linha por bônus)",
                value=row_field(existing, "bonus_equipamento", ""),
                height=80,
                key=f"item_popup_bonus_{cid}_{sel_item_id}",
            )

            st.markdown("**DESCRIÇÃO**")
            descricao = st.text_area(
                "Descrição",
                value=row_field(existing, "descricao", ""),
                height=180,
                key=f"item_popup_desc_{cid}_{sel_item_id}",
            )

            st.markdown("---")
            st.markdown("### Bordas / Aparência")

            CARD_TYPES = ["none", "solid", "gradient", "flow", "pulse", "changing"]
            cur_card_type = row_field(existing, "card_border_type", "none")
            card_border_type = st.selectbox(
                "Tipo (card)",
                CARD_TYPES,
                index=(
                    CARD_TYPES.index(cur_card_type)
                    if cur_card_type in CARD_TYPES
                    else 0
                ),
                key=f"item_popup_card_type_{cid}_{sel_item_id}",
            )
            card_color1 = st.color_picker(
                "Cor primária (card)",
                value=row_field(existing, "card_border_color1", "#ffffff"),
                key=f"item_popup_card_color1_{cid}_{sel_item_id}",
            )
            card_color2 = st.color_picker(
                "Cor secundária (card)",
                value=row_field(existing, "card_border_color2", "#000000"),
                key=f"item_popup_card_color2_{cid}_{sel_item_id}",
            )
            card_speed = st.slider(
                "Velocidade / intensidade (card)",
                0.2,
                5.0,
                float(row_field(existing, "card_border_speed", 1.0)),
                0.1,
                key=f"item_popup_card_speed_{cid}_{sel_item_id}",
            )

            IMG_TYPES = ["none", "solid", "gradient", "flow", "pulse", "changing"]
            cur_img_type = row_field(existing, "image_border_type", "none")
            image_border_type = st.selectbox(
                "Tipo (imagem)",
                IMG_TYPES,
                index=(
                    IMG_TYPES.index(cur_img_type)
                    if cur_img_type in IMG_TYPES
                    else 0
                ),
                key=f"item_popup_img_type_{cid}_{sel_item_id}",
            )
            image_color1 = st.color_picker(
                "Cor primária (imagem)",
                value=row_field(existing, "image_border_color1", "#ffffff"),
                key=f"item_popup_img_color1_{cid}_{sel_item_id}",
            )
            image_color2 = st.color_picker(
                "Cor secundária (imagem)",
                value=row_field(existing, "image_border_color2", "#000000"),
                key=f"item_popup_img_color2_{cid}_{sel_item_id}",
            )
            image_speed = st.slider(
                "Velocidade / intensidade (imagem)",
                0.2,
                5.0,
                float(row_field(existing, "image_border_speed", 1.0)),
                0.1,
                key=f"item_popup_img_speed_{cid}_{sel_item_id}",
            )

            # -------- PREVIEWS --------
            import streamlit.components.v1 as components

            preview_card_css, preview_card_extra, preview_card_cls = _css_for_border(
                "preview_card",
                card_border_type,
                card_color1,
                card_color2,
                card_speed,
                f"item_cv{cid}",
            )
            preview_card_html = f"""
            <html><head><meta charset="utf-8"><style>
              .preview_card_box {{
                 width: 360px; height: 160px;
                 border-radius:16px;
                 background: linear-gradient(180deg,#2ca0ff,#005bd1);
                 position:relative; color:#eaf6ff;
                 padding:10px; box-shadow:0 10px 24px rgba(0,0,0,0.35);
                 box-sizing:border-box;
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
            components.html(preview_card_html, height=190, scrolling=False)

            preview_img_css, preview_img_extra, preview_img_cls = _css_for_border(
                "preview_img",
                image_border_type,
                image_color1,
                image_color2,
                image_speed,
                f"item_iv{cid}",
            )
            preview_img_html = f"""
            <html><head><meta charset="utf-8"><style>
              .preview_img_box {{
                width: 96px; height:96px;
                border-radius:8px; background:#1b6de0;
                display:inline-block; vertical-align:middle;
                box-sizing:border-box;
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
            components.html(preview_img_html, height=150, scrolling=False)

            # -------- AÇÕES --------
            st.markdown("---")
            c1, c2 = st.columns(2)
            if c1.button(
                "Salvar Popup",
                key=f"item_popup_save_{cid}_{sel_item_id}",
            ):
                try:
                    upsert_popup(
                        current_user["id"],
                        sel_item_id,
                        cid,
                        title,
                        icon_filename,
                        icon_blob,
                        rank or "",
                        classificacao or "",
                        tipo or "",
                        usos or "",
                        requisitos or "",
                        efeito_passivo or "",
                        bonus_equip or "",
                        descricao or "",
                        card_border_type=card_border_type,
                        card_border_color1=card_color1,
                        card_border_color2=card_color2,
                        card_border_speed=float(card_speed),
                        image_border_type=image_border_type,
                        image_border_color1=image_color1,
                        image_border_color2=image_color2,
                        image_border_speed=float(image_speed),
                    )
                    st.success("Popup de item salvo para esta ficha.")
                except Exception:
                    st.error("Erro ao salvar popup (veja traceback abaixo).")
                    st.code(traceback.format_exc())

            if c2.button(
                "Excluir Popup",
                key=f"item_popup_del_{cid}_{sel_item_id}",
            ):
                if existing and "id" in existing.keys():
                    try:
                        delete_popup(existing["id"])
                        st.success("Popup de item excluído.")
                    except Exception:
                        st.error("Erro ao excluir popup (veja traceback abaixo).")
                        st.code(traceback.format_exc())
                else:
                    st.warning(
                        "Nenhum popup existente para excluir "
                        "nesta combinação ficha/item."
                    )
    except Exception:
        tb = traceback.format_exc()
        try:
            st.sidebar.error(
                "Erro ao inicializar/mostrar editor de popups de item (veja traceback)."
            )
            st.sidebar.code(tb)
        except Exception:
            print("item_popup sidebar error:\n", tb)


def render_item_button(item_row, character_id, current_user):
    """
    Botão 🔍 para cada item do inventário.
    Usa a tabela item_popup para renderizar card customizado.
    """
    def _get(r, k, default=""):
        try:
            return r[k] if k in r.keys() else default
        except Exception:
            try:
                return r.get(k, default)
            except Exception:
                return default

    item_id = _get(item_row, "item_id", _get(item_row, "id", None))
    item_name = _get(item_row, "name", "Item")
    item_desc = _get(item_row, "description", "")

    btn_key = f"item_popup_btn_{item_id}_{character_id}"
    open_key = f"item_popup_open_{item_id}_{character_id}"
    if open_key not in st.session_state:
        st.session_state[open_key] = False

    if st.button(f"🔍 {item_name}", key=btn_key):
        st.session_state[open_key] = not st.session_state[open_key]

    if st.session_state.get(open_key):
        popup = get_popup_for(item_id=item_id, user_id=character_id)
        if popup:
            _render_item_template_popup(
                popup, item_name, item_desc, character_id, current_user
            )
        else:
            with safe_modal(item_name):
                st.markdown("**Descrição do catálogo:**")
                st.write(item_desc or "_(sem descrição)_")


def _render_item_template_popup(
    popup_row, item_name, item_desc, character_id, current_user
):
    import html as _html
    import textwrap
    import streamlit.components.v1 as components

    def _g(k):
        return row_field(popup_row, k, "")

    title = _g("title") or item_name
    icon_blob = _g("icon_blob")
    icon_filename = (_g("icon_filename") or "").strip()
    rank = _g("rank") or ""
    classificacao = _g("classificacao") or ""
    tipo = _g("tipo") or ""
    usos = _g("usos") or ""
    requisitos = _g("requisitos") or ""
    efeito_passivo = _g("efeito_passivo") or ""
    bonus_equip = _g("bonus_equipamento") or ""
    descricao = _g("descricao") or ""

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

    uid = f"{row_field(popup_row, 'id','x')}_{character_id}"

    # Ícone
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
                'style="width:160px;height:160px;object-fit:cover;'
                'border-radius:6px;display:block" />'
            )
        except Exception:
            icon_html_inner = (
                '<div style="width:160px;height:160px;border-radius:6px;'
                'background:rgba(0,0,0,0.25);display:flex;align-items:center;'
                'justify-content:center;color:#dff4ff;">ICON</div>'
            )
    else:
        icon_html_inner = (
            '<div style="width:160px;height:160px;border-radius:6px;'
            'background:rgba(0,0,0,0.25);display:flex;align-items:center;'
            'justify-content:center;color:#dff4ff;">ICON</div>'
        )

    # Bordas
    card_css_inline, card_extra, card_cls = _css_for_border(
        "card", card_border_type, card_border_color1, card_border_color2,
        card_border_speed, uid
    )
    img_css_inline, img_extra, img_cls = _css_for_border(
        "img", image_border_type, image_border_color1, image_border_color2,
        image_border_speed, uid
    )

    def esc_lines(text):
        if not text:
            return ""
        return "<br>".join(_html.escape(l) for l in str(text).splitlines())

    desc_esc = esc_lines(descricao or item_desc)
    efeito_esc = esc_lines(efeito_passivo)
    bonus_esc = esc_lines(bonus_equip)

    html = textwrap.dedent(
        f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <style>
        :root {{
          --bg1: #2ea8ff;
          --bg2: #0056d3;
          --headline: #ffffff;
          --body-text: #e4f4ff;
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
          box-sizing:border-box;
        }}
        .card {{
          width:960px;
          border-radius:20px;
          padding:20px;
          color:var(--body-text);
          position:relative;
          overflow:visible;
          box-sizing:border-box;
        }}
        .card-inner {{
          background: linear-gradient(180deg, var(--bg1) 0%, var(--bg2) 100%);
          border-radius:16px;
          padding:18px 26px 24px;
          box-sizing:border-box;
        }}
        .title-bar {{
          text-align:center;
          font-size:24px;
          font-weight:800;
          letter-spacing:1px;
          color:var(--headline);
          text-shadow:0 0 8px rgba(0,0,0,0.65);
          margin-bottom:12px;
        }}
        .top-icons {{
          position:absolute;
          right:32px; top:22px;
          display:flex;
          gap:4px;
        }}
        .top-icon-box {{
          width:18px; height:18px;
          border-radius:3px;
          border:1px solid rgba(255,255,255,0.75);
          background:rgba(0,0,0,0.12);
        }}
        .content-row {{
          display:flex;
          gap:22px;
          align-items:flex-start;
        }}
        .icon-col {{
          width:210px;
          flex:0 0 210px;
          text-align:center;
          position:relative;
        }}
        .icon-wrapper {{
          display:inline-block;
          padding:8px;
          border-radius:14px;
          box-sizing:border-box;
        }}
        .text-col {{
          flex:1;
          min-width:0;
          position:relative;
          color:var(--body-text);
        }}
        .item-name {{
          font-size:22px;
          font-weight:800;
          color:#ffffff;
          margin-bottom:4px;
          text-shadow:0 0 8px rgba(0,0,0,0.6);
        }}
        .meta-block {{
          font-size:14px;
          margin-bottom:10px;
          line-height:1.4;
        }}
        .meta-block div {{
          margin-bottom:2px;
        }}
        .section-title {{
          font-size:16px;
          font-weight:800;
          color:#ffffff;
          margin-top:10px;
          margin-bottom:4px;
        }}
        .section-text {{
          font-size:14px;
          line-height:1.4;
        }}
        .desc-block {{
          margin-top:12px;
          font-size:14px;
          line-height:1.45;
        }}
        .desc-label {{
          font-weight:800;
          margin-bottom:4px;
        }}
        .desc-box {{
          background:rgba(0,0,0,0.16);
          border-radius:10px;
          padding:10px;
        }}
        @media (max-width:980px) {{
          .card {{ width:100%; padding:16px; }}
          .content-row {{ flex-direction:column; }}
          .icon-col {{ width:100%; flex:unset; text-align:center; margin-bottom:14px; }}
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
            <div class="title-bar">&lt;INFORMAÇÕES DO ITEM&gt;</div>
            <div class="top-icons">
              <div class="top-icon-box"></div>
              <div class="top-icon-box"></div>
              <div class="top-icon-box"></div>
            </div>
            <div class="content-row">
              <div class="icon-col">
                <div class="icon-wrapper {img_cls}">
                  {icon_html_inner}
                </div>
              </div>
              <div class="text-col">
                <div class="item-name">&lt;{_html.escape(title)}&gt;</div>
                <div class="meta-block">
                  <div>[RANK: {_html.escape(rank)}]</div>
                  <div>[CLASSIFICAÇÃO: {_html.escape(classificacao)}]</div>
                  <div>[TIPO: {_html.escape(tipo)}] [USOS: {_html.escape(usos)}]</div>
                  <div>[REQUISITOS: {_html.escape(requisitos)}]</div>
                </div>

                <div class="section">
                  <div class="section-title">EFEITO PASSIVO:</div>
                  <div class="section-text">{efeito_esc}</div>
                </div>

                <div class="section">
                  <div class="section-title">BONUS DE EQUIPAMENTO:</div>
                  <div class="section-text">{bonus_esc}</div>
                </div>

                <div class="desc-block">
                  <div class="desc-label">DESCRIÇÃO:</div>
                  <div class="desc-box">{desc_esc}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </body>
    </html>
    """
    ).lstrip()

    # Altura dinâmica – base alta para evitar corte + ajuste por linhas
    num_lines = (
        (descricao or item_desc or "").count("\n")
        + efeito_passivo.count("\n")
        + bonus_equip.count("\n")
        + 6
    )
    approx_height = 720 + num_lines * 18
    approx_height = max(820, min(approx_height, 1400))

    components.html(html, height=approx_height, scrolling=False)
