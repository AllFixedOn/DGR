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
            f"Base ativa: {len(lista_pdfs)} documento(s) da Secção 2 + Variações SATA (SP/S4)."
        ]
    }

# --- BARRA DE PESQUISA NATIVA LIGADA AO BACKEND OPENAI ---
with st.container():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #091526 0%, #003366 65%, #006B3C 100%); padding: 14px 16px; border-bottom: 1px solid #1E293B; color: white; font-family: sans-serif;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-weight:700; font-size:1.05rem;">✈️ SATA DGR Ops <span style="font-size:0.7rem; background:#00A859; padding:2px 6px; border-radius:6px;">EFB v2.67</span></div>
                <div style="font-size:0.75rem; color:#94A3B8;">IATA 67ª Ed. (2026) • Prioridade SATA Ativa</div>
            </div>
            <div style="font-size:0.72rem; color:#10B981; font-weight:600;">● ONLINE</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
        aplicar_sata = st.toggle("Aplicar Variações SATA", value=True)
    with col_t2:
        if audio_data_uri:
            st.audio(audio_data_uri)

    pergunta = st.text_input(
        "Consulta DGR:",
        placeholder="Ex: baterias 50wh, POC lítio metálico, cadeira rodas 350Wh...",
        label_visibility="collapsed"
    )

    if st.button("🔍 Validar Transporte (IATA + SATA)", type="primary", use_container_width=True):
        if not texto_referencia.strip():
            st.error("Nenhum PDF carregado no GitHub.")
        elif pergunta.strip():
            client = OpenAI(api_key=OPENAI_API_KEY)
            bloco_sata = f"""
            HIERARQUIA OBRIGATÓRIA:
            1º Lugar: REGRAS ESPECÍFICAS DA SATA (prevalecem sempre sobre a IATA).
            2º Lugar: MANUAL IATA DGR SECÇÃO 2 (67ª Edição).
            REGRAS SATA ATIVAS:
            {regras_sata_base}
            """ if aplicar_sata else "Aplica apenas a regra geral IATA DGR."

            prompt_json = f"""
            És um Instrutor Certificado de IATA DGR (67ª Edição) na SATA.
            Analisa a pergunta com base em TODOS os documentos da Secção 2 e nas Regras Específicas da SATA fornecidos abaixo.

            REGRAS CRÍTICAS DE RIGOR REGULAMENTAR (NUNCA VIOLAR):
            1. DISTINÇÃO OBRIGATÓRIA: INSTALADA NO EQUIPAMENTO (PED) VS. SOLTA / SOBRESSALENTE / POWERBANK:
               - Sempre que o utilizador perguntar sobre baterias sem especificar se estão instaladas num equipamento ou soltas/sobressalentes (ex.: "baterias 50wh" ou "baterias de lítio"), É OBRIGATÓRIO apresentar AMBOS os cenários separadamente!
               - No cartão "bagagem_porao", se a bateria instalada puder ir no porão (YES) mas a bateria solta/sobressalente for proibida no porão (NO), escreve exatamente: "YES (PED) | NO (Solta)".
               - No cartão "bagagem_mao", escreve: "YES (PED & Solta)".
               - Nos "limites_exatos" e "condicoes_operacionais", separa explicitamente:
                 * CENÁRIO A — Instalada no equipamento (PED): limites (ex.: até 100 Wh sem aprovação; 100–160 Wh com aprovação; máx. 15 PEDs) e condições para porão (desligado, protegido contra ativação acidental).
                 * CENÁRIO B — Solta / Sobressalente / Powerbank: PROIBIDA no porão (NO), permitida apenas na cabine, proteção individual contra curto-circuito, e na SATA limitada a no MÁXIMO 2 unidades por passageiro transportadas junto ao passageiro (evitar rack superior).
            2. ESCALÕES E PATAMARES DE APROVAÇÃO: Discrimina sempre TODOS os patamares distintos (ex.: Lítio Metálico <= 2 g SEM aprovação vs > 2 g até 8 g COM aprovação; ou Iões de Lítio <= 100 Wh SEM aprovação vs > 100 Wh até 160 Wh COM aprovação). Preenche "aprovacao_operador" com o resumo dos escalões (ex.: "NO (<=100Wh) | YES (100-160Wh)").
            3. REGRAS SATA: Teto máximo de 300 Wh mesmo em baterias fixas de cadeiras de rodas, máx. 2 powerbanks/sobressalentes na cabine junto ao passageiro, NOTOC YES obrigatório para munições.

            Devolve EXCLUSIVAMENTE um JSON válido com estas chaves:
            {{
              "status_cor": "PROIBIDO" ou "CONDICIONADO" ou "PERMITIDO",
              "titulo_veredicto": "Frase curta e direta do veredicto (destacando a diferença PED vs Solta se aplicável)",
              "referencia_iata": "Subsecção/Tabela exata (ex: Tabela 2.3.A / 2.3.5.8)",
              "aprovacao_operador": "YES / NO ou resumo dos escalões",
              "bagagem_porao": "YES / NO ou YES (PED) | NO (Solta)",
              "bagagem_mao": "YES / NO / ON PERSON",
              "notoc": "YES ou NO",
              "limites_exatos": ["CENÁRIO A (Instalada PED): ...", "CENÁRIO B (Solta / Powerbank): ...", "Patamares e quantidades..."],
              "condicoes_operacionais": ["Condições práticas porão vs cabine e variações SATA..."]
            }}

            {bloco_sata}
            DOCUMENTAÇÃO IATA SECÇÃO 2:
            {texto_referencia}
            """

            with st.spinner("A consultar Secção 2 + Variações SATA..."):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        temperature=0.0,
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": prompt_json},
                            {"role": "user", "content": pergunta}
                        ]
                    )
                    st.session_state["ultima_resposta"] = json.loads(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"Erro na API: {e}")

# --- RENDERIZAÇÃO DO PAINEL EFB INTERATIVO ---
resp_json = json.dumps(st.session_state["ultima_resposta"], ensure_ascii=False)
regras_json = json.dumps(regras_sata_base, ensure_ascii=False)
pdfs_json = json.dumps(lista_pdfs, ensure_ascii=False)

html_efb = f"""
<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  html, body {{ overscroll-behavior-y: contain; touch-action: pan-x pan-y; background: #060D1A; color: #F8FAFC; padding: 12px 14px 80px 14px; }}
  .tabs {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; background: #0F172A; padding: 5px; border-radius: 12px; border: 1px solid #1E293B; margin-bottom: 14px; }}
  .tab-btn {{ background: transparent; border: none; color: #94A3B8; padding: 8px 4px; border-radius: 8px; font-size: 0.74rem; font-weight: 600; cursor: pointer; }}
  .tab-btn.active {{ background: #005580; color: #FFFFFF; }}
  .section {{ display: none; }}
  .section.active {{ display: block; }}

  .card {{ background: #0F172A; border: 1px solid #1E293B; border-radius: 14px; padding: 14px; margin-bottom: 12px; }}
  .verdict {{ border-left: 5px solid #F59E0B; background: rgba(245, 158, 11, 0.1); }}
  .verdict.PROIBIDO {{ border-left-color: #
