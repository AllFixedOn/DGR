import os
import glob
import json
import pdfplumber
import streamlit as st
from openai import OpenAI

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="DGR SATA Ops",
    page_icon="✈️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ESTILO VISUAL DE APP NATIVA (HEADER SATA + CARTÕES + LIMPEZA DE UI) ---
st.markdown("""
<style>
    header[data-testid="stHeader"] {visibility: hidden; height: 0px;}
    footer {visibility: hidden;}
    .block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 680px;}

    .sata-header {
        background: linear-gradient(135deg, #003366 0%, #005580 65%, #008751 100%);
        color: white;
        padding: 18px 20px;
        border-radius: 16px;
        margin-bottom: 16px;
        box-shadow: 0 4px 14px rgba(0, 51, 102, 0.18);
    }
    .sata-header h2 {
        margin: 0;
        font-size: 1.35rem;
        font-weight: 700;
        color: white;
        letter-spacing: 0.3px;
    }
    .sata-header p {
        margin: 4px 0 0 0;
        font-size: 0.85rem;
        opacity: 0.9;
        color: #E0F2FE;
    }

    .verdict-card {
        padding: 16px 18px;
        border-radius: 14px;
        margin: 12px 0;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .verdict-proibido {
        background-color: #FEF2F2;
        border-left: 6px solid #DC2626;
        color: #991B1B;
    }
    .verdict-condicionado {
        background-color: #FFFBEB;
        border-left: 6px solid #D97706;
        color: #92400E;
    }
    .verdict-permitido {
        background-color: #ECFDF5;
        border-left: 6px solid #059669;
        color: #065F46;
    }

    .status-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin: 12px 0;
    }
    .status-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
    }
    .status-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #64748B;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .status-val {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0F2942;
    }
</style>
""", unsafe_allow_html=True)

# --- PROTEÇÃO POR PASSWORD ---
def verificar_acesso():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.markdown("""
        <div class="sata-header">
            <h2>✈️ SATA DGR Assistant</h2>
            <p>Acesso Operacional Restrito • IATA 67ª Edição</p>
        </div>
        """, unsafe_allow_html=True)
        senha = st.text_input("Código de acesso:", type="password", placeholder="Introduz o PIN...")
        if st.button("Desbloquear App", type="primary", use_container_width=True):
            senha_correta = str(st.secrets.get("APP_PASSWORD", "")).strip()
            if senha.strip() == senha_correta and senha_correta != "":
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Código incorreto.")
        st.stop()

verificar_acesso()

OPENAI_API_KEY = str(st.secrets["OPENAI_API_KEY"]).strip()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CARREGAMENTO DE PDFs E REGRAS ---
@st.cache_data
def carregar_todos_pdfs(diretorio):
    padroes = [
        os.path.join(diretorio, "*.pdf"),
        os.path.join(diretorio, "manuais", "*.pdf")
    ]
    ficheiros = sorted(list(set(f for p in padroes for f in glob.glob(p))))
    blocos_texto, nomes_carregados = [], []

    for caminho in ficheiros:
        nome = os.path.basename(caminho)
        nomes_carregados.append(nome)
        paginas_doc = [f"=== DOCUMENTO: {nome} ==="]
        with pdfplumber.open(caminho) as pdf:
            for num_pag, page in enumerate(pdf.pages, start=1):
                texto_alinhado = page.extract_text(layout=True)
                if texto_alinhado:
                    paginas_doc.append(f"--- {nome} | PÁG. {num_pag} ---\n{texto_alinhado}")
        blocos_texto.append("\n\n".join(paginas_doc))

    return "\n\n========================================\n\n".join(blocos_texto), nomes_carregados

def carregar_regras_sata():
    caminho_txt = os.path.join(BASE_DIR, "regras_sata.txt")
    if os.path.exists(caminho_txt):
        with open(caminho_txt, "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
            if conteudo:
                return conteudo
    return "Regras SATA não encontradas no ficheiro regras_sata.txt."

texto_referencia, lista_pdfs = carregar_todos_pdfs(BASE_DIR)
regras_sata_base = carregar_regras_sata()

# --- CABEÇALHO DA APP ---
st.markdown("""
<div class="sata-header">
    <h2>✈️ SATA DGR • Check-in & Embarque</h2>
    <p>IATA DGR 67ª Ed. (2026) + Variações Operacionais SATA</p>
</div>
""", unsafe_allow_html=True)

# --- LEITOR OPCIONAL PARA ÁUDIO ---
audio_files = sorted(glob.glob(os.path.join(BASE_DIR, "*.mp3")) + glob.glob(os.path.join
