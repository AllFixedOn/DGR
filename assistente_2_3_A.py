import os
import glob
import json
import base64
import pdfplumber
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI

# --- CONFIGURAÇÃO DE ECRÃ TOTAL ---
st.set_page_config(
    page_title="SATA DGR Ops • EFB v2.67",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Remover margens, elementos padrão do Streamlit e bloquear Pull-to-Refresh no Android
st.markdown("""
<style>
    html, body, .stApp, [data-testid="stAppViewContainer"] {
        overscroll-behavior-y: contain !important;
        touch-action: pan-x pan-y !important;
        background-color: #060D1A !important;
    }
    header[data-testid="stHeader"] {display: none !important;}
    footer {display: none !important;}
    .block-container {
        padding: 0rem !important;
        margin: 0 auto !important;
        max-width: 540px !important;
    }
    iframe {
        border: none !important;
        width: 100% !important;
        overscroll-behavior-y: contain !important;
    }
</style>
""", unsafe_allow_html=True)

# --- PROTEÇÃO POR PASSWORD ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #003366, #008751); padding: 24px; border-radius: 16px; margin: 20px 16px; color: white; font-family: sans-serif;">
        <h2 style="margin:0; font-size:1.3rem;">✈️ SATA DGR Ops • EFB</h2>
        <p style="margin:4px 0 0 0; font-size:0.82rem; opacity:0.9;">Acesso Operacional Restrito • IATA 67ª Edição</p>
    </div>
    """, unsafe_allow_html=True)
    with st.container():
        senha = st.text_input("PIN de Acesso:", type="password", placeholder="Introduz o código...")
        if st.button("Desbloquear Sistema", type="primary", use_container_width=True):
            senha_correta = str(st.secrets.get("APP_PASSWORD", "")).strip()
            if senha.strip() == senha_correta and senha_correta != "":
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("PIN incorreto.")
    st.stop()

OPENAI_API_KEY = str(st.secrets["OPENAI_API_KEY"]).strip()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CARREGAMENTO DE PDFs E REGRAS SATA ---
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
    return "Regras SATA carregadas por defeito."

def carregar_audio_base64():
    audios = sorted(glob.glob(os.path.join(BASE_DIR, "*.mp3")) + glob.glob(os.path.join(BASE_DIR, "*.wav")))
    if audios:
        ext = "mp3" if audios[0].endswith(".mp3") else "wav"
        with open(audios[0], "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:audio/{ext};base64,{b64}", os.path.basename(audios[0])
    return "", ""

texto_referencia, lista_pdfs = carregar_todos_pdfs(BASE_DIR)
regras_sata_base = carregar_regras_sata()
audio_data_uri, audio_nome = carregar_audio_base64()

# --- ESTADO DA CONSULTA ---
if "ultima_resposta" not in st.session_state:
    st.session_state["ultima_resposta"] = {
        "status_cor": "CONDICIONADO",
        "titulo_veredicto": "Pronto para consulta operacional IATA + SATA",
        "referencia_iata": "Secção 2 • Tabela 2.3.A (67ª Ed. 2026)",
        "aprovacao_operador": "VARIA",
        "bagagem_porao": "VERIFICAR",
        "bagagem_mao": "VERIFICAR",
        "notoc": "VERIFICAR",
        "limites_exatos": [
            "Descreve o artigo do passageiro acima para validar limites exatos, patamares e distinção porão/cabine."
        ],
        "condicoes_operacionais": [
            f"Base ativa
