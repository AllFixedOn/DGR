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
    /* Esconder barra superior e rodapé padrão do Streamlit */
    header[data-testid="stHeader"] {visibility: hidden; height: 0px;}
    footer {visibility: hidden;}
    .block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 680px;}

    /* Banner Superior Estilo App SATA */
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

    /* Cartões de Veredicto Semáforo */
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

    /* Grelha 2x2 para Status Operacional */
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

    /* Cartão de Detalhes */
    .info-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 16px;
        margin-top: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
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

# --- LEITOR OPCIONAL PARA A TUA SPLASH / BACKGROUND MUSIC ---
audio_files = sorted(glob.glob(os.path.join(BASE_DIR, "*.mp3")) + glob.glob(os.path.join(BASE_DIR, "*.wav")))
if audio_files:
    with st.expander("🎵 Áudio da App (Splash / Background)", expanded=False):
        for af in audio_files:
            st.caption(os.path.basename(af))
            st.audio(af)

# --- NAVEGAÇÃO POR SEPARADORES (ESTILO APP MÓVEL) ---
tab_consulta, tab_rapido, tab_regras = st.tabs(["🔍 Consulta IA", "🚦 Guia Rápido", "📋 Regras SATA"])

with tab_consulta:
    aplicar_sata = st.toggle("Prioridade Regras SATA (SP / S4)", value=True)

    # Pills / Botões rápidos
    if "query_input" not in st.session_state:
        st.session_state["query_input"] = ""

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔋 Powerbanks (Máx. 2)", use_container_width=True):
            st.session_state["query_input"] = "Quais os limites, quantidade e localização a bordo para powerbanks na SATA?"
        if st.button("♿ Cadeira Rodas (300Wh)", use_container_width=True):
            st.session_state["query_input"] = "Passageiro com cadeira de rodas elétrica com bateria de lítio fixa. Qual o limite na SATA?"
    with c2:
        if st.button("🧯 CO2 vs Camping Gas", use_container_width=True):
            st.session_state["query_input"] = "Passageiro com cartuchos de CO2 para colete salva-vidas vs camping gas. Limites e regras?"
        if st.button("🔫 Munições & NOTOC", use_container_width=True):
            st.session_state["query_input"] = "Quais as regras, peso máximo e exigência de NOTOC para munições na SATA?"

    pergunta = st.text_area(
        "Artigo ou cenário do passageiro:",
        value=st.session_state["query_input"],
        placeholder="Ex: Passageiro leva 2 baterias de 120 Wh ou desumidificador...",
        height=95,
        label_visibility="collapsed"
    )

    if st.button("Validar Transporte", type="primary", use_container_width=True):
        if not texto_referencia.strip():
            st.error("Nenhum PDF carregado no repositório.")
        elif not pergunta.strip():
            st.warning("Escreve o artigo ou dúvida primeiro.")
        else:
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
            Analisa a pergunta com base na documentação fornecida e devolve EXCLUSIVAMENTE um objeto JSON válido com estas chaves exatas:
            {{
              "status_cor": "PROIBIDO" ou "CONDICIONADO" ou "PERMITIDO",
              "titulo_veredicto": "Frase curta e direta do veredicto na SATA (ex: PROIBIDO NA SATA - Excede 300 Wh)",
              "referencia_iata": "Subsecção/Tabela exata (ex: Tabela 2.3.A / 2.3.2.4)",
              "aprovacao_operador": "YES" ou "NO" ou "N/A",
              "bagagem_porao": "YES" ou "NO",
              "bagagem_mao": "YES" ou "NO" ou "ON PERSON",
              "notoc": "YES" ou "NO",
              "limites_exatos": ["Lista de strings com TODOS os limites numéricos: Wh, mL, L, g, kg, máx. unidades"],
              "condicoes_operacionais": ["Lista de strings com as condições práticas de check-in/embarque e variações SATA"]
            }}

            {bloco_sata}

            DOCUMENTAÇÃO IATA SECÇÃO 2:
            {texto_referencia}
            """

            with st.spinner("A analisar regulamentação IATA + SATA..."):
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
                    dados = json.loads(response.choices[0].message.content)

                    # Renderizar Cartão Semáforo
                    cor = dados.get("status_cor", "CONDICIONADO").upper()
                    classe_css = "verdict-condicionado"
                    icone = "⚠️"
                    if "PROIBIDO" in cor:
                        classe_css = "verdict-proibido"
                        icone = "⛔"
                    elif "PERMITIDO" in cor:
                        classe_css = "verdict-permitido"
                        icone = "✅"

                    st.markdown(f"""
                    <div class="verdict-card {classe_css}">
                        <div style="font-size: 1.1rem;">{icone} {dados.get('titulo_veredicto', '')}</div>
                        <div style="font-size: 0.82rem; margin-top: 4px; opacity: 0.85;">Ref: {dados.get('referencia_iata', '')}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Renderizar Grelha 2x2
                    st.markdown(f"""
                    <div class="status-grid">
                        <div class="status-box">
                            <div class="status-label">Aprovação Operador</div>
                            <div class="status-val">{dados.get('aprovacao_operador', '-')}</div>
                        </div>
                        <div class="status-box">
                            <div class="status-label">Informar Cmdt (NOTOC)</div>
                            <div class="status-val">{dados.get('notoc', '-')}</div>
                        </div>
                        <div class="status-box">
                            <div class="status-label">Bagagem de Porão</div>
                            <div class="status-val">{dados.get('bagagem_porao', '-')}</div>
                        </div>
                        <div class="status-box">
                            <div class="status-label">Bagagem de Mão</div>
                            <div class="status-val">{dados.get('bagagem_mao', '-')}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Renderizar Limites e Condições
                    st.markdown("#### 📏 Limites Quantitativos Exatos")
                    for lim in dados.get("limites_exatos", []):
                        st.markdown(f"- **{lim}**")

                    st.markdown("#### 📝 Condições Operacionais & SATA")
                    for cond in dados.get("condicoes_operacionais", []):
                        st.markdown(f"- {cond}")

                except Exception as e:
                    st.error(f"Erro ao processar resposta: {e}")

with tab_rapido:
    st.markdown("#### 🚦 Resumo Rápido de Balcão (SATA)")
    st.error("⛔ **PROIBIDOS (Porão e Cabine):** Trotinetes/hoverboards/bicicletas elétricas, desumidificadores, tinteiros/toners, latas de tinta/sprays técnicos, camping gas/gás inflamável (Div. 2.1), cadeiras de rodas com bateria fixa **> 300 Wh**.")
    st.warning("⚠️ **RESTRIÇÕES ESPECÍFICAS SATA:**\n- **Cadeiras de Rodas Elétricas:** Máx. **300 Wh** mesmo em baterias fixas.\n- **Powerbanks:** Máx. **2 unidades** por passageiro, só na cabine e **junto ao passageiro** (evitar rack superior).\n- **Munições (1.4S):** Máx. **5 kg** porão + **NOTOC obrigatório (YES)**.")
    st.success("✅ **PERMITIDOS (DENTRO DOS LIMITES IATA):** Cartuchos de **CO2** (Div. 2.2 — não inflamáveis), artigos de higiene/medicinais (2.3.5.1), eletrónicos portáteis com baterias até 100 Wh.")

with tab_regras:
    st.markdown(f"#### 📚 Base Documental Ativa ({len(lista_pdfs)} PDFs)")
    for pdf_nome in lista_pdfs:
        st.caption(f"📄 {pdf_nome}")
    st.divider()
    st.markdown("#### 📋 Ficheiro `regras_sata.txt` em vigor")
    st.text_area("Regras atuais:", value=regras_sata_base, height=350, disabled=True)
