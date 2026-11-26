import os
import io
import glob
import json
import base64
import pdfplumber
from PIL import Image
import streamlit as st
from openai import OpenAI

# --- CONFIGURAÇÃO DE ECRÃ TOTAL ---
st.set_page_config(
    page_title="SATA DGR Ops • EFB v2.67",
    page_icon="✈️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ESTILO NATIVO SEM BLOQUEIO DE SCROLL ---
st.markdown("""
<style>
    html, body, .stApp {
        background-color: #060D1A !important;
        color: #F8FAFC !important;
        overscroll-behavior-y: contain;
    }
    header[data-testid="stHeader"] {display: none !important;}
    footer {display: none !important;}
    .block-container {
        padding: 0.6rem 0.9rem 3rem 0.9rem !important;
        max-width: 540px !important;
    }

    /* Cabeçalho SATA EFB */
    .sata-banner {
        background: linear-gradient(135deg, #091526 0%, #003366 65%, #006B3C 100%);
        padding: 14px 16px;
        border-radius: 14px;
        border: 1px solid #1E293B;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .sata-title { font-weight: 700; font-size: 1.05rem; color: #FFFFFF; }
    .sata-badge { font-size: 0.68rem; background: #00A859; color: white; padding: 2px 6px; border-radius: 6px; margin-left: 4px; }
    .sata-sub { font-size: 0.74rem; color: #94A3B8; margin-top: 2px; }

    /* Cartão Veredicto Semáforo */
    .verdict-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-left: 5px solid #F59E0B;
        border-radius: 14px;
        padding: 14px;
        margin: 10px 0;
    }
    .verdict-PROIBIDO { border-left-color: #EF4444; background: rgba(239, 68, 68, 0.14); }
    .verdict-PERMITIDO { border-left-color: #10B981; background: rgba(16, 185, 129, 0.14); }
    .v-title { font-size: 0.98rem; font-weight: 700; color: #F8FAFC; }
    .v-ref { font-size: 0.75rem; color: #94A3B8; font-family: monospace; margin-top: 4px; }

    /* Grelha 2x2 */
    .grid2 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin: 10px 0;
    }
    .stat-box {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 10px;
        text-align: center;
    }
    .stat-lbl { font-size: 0.66rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.4px; }
    .stat-val { font-size: 0.85rem; font-weight: 700; color: #38BDF8; font-family: monospace; margin-top: 4px; }

    /* Cartões de Detalhe */
    .detail-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 14px;
        padding: 14px;
        margin-top: 10px;
        font-size: 0.86rem;
        line-height: 1.45;
        color: #E2E8F0;
    }
    .detail-card h4 {
        font-size: 0.78rem;
        color: #94A3B8;
        text-transform: uppercase;
        margin: 0 0 8px 0;
    }
    .detail-card ul { padding-left: 18px; margin: 0; }
    .detail-card li { margin-bottom: 6px; }

    /* Inputs escuros */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
        border-color: #334155 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- PROTEÇÃO POR PASSWORD ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.markdown("""
    <div class="sata-banner">
        <div>
            <div class="sata-title">✈️ SATA DGR Ops <span class="sata-badge">EFB v2.67</span></div>
            <div class="sata-sub">Acesso Operacional Restrito • IATA 67ª Edição</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
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

def processar_imagem_para_base64(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail((1280, 1280))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

texto_referencia, lista_pdfs = carregar_todos_pdfs(BASE_DIR)
regras_sata_base = carregar_regras_sata()

# --- CABEÇALHO ---
st.markdown("""
<div class="sata-banner">
    <div>
        <div class="sata-title">✈️ SATA DGR Ops <span class="sata-badge">EFB v2.67</span></div>
        <div class="sata-sub">IATA 67ª Ed. (2026) • Texto + Câmara IA</div>
    </div>
    <div style="font-size:0.72rem; color:#10B981; font-weight:700;">● ONLINE</div>
</div>
""", unsafe_allow_html=True)

# --- CONTROLO RÁPIDO DE ÁUDIO (LIGAR / DESLIGAR) ---
audios = sorted(glob.glob(os.path.join(BASE_DIR, "*.mp3")) + glob.glob(os.path.join(BASE_DIR, "*.wav")))
if audios:
    col_som1, col_som2 = st.columns([2, 3])
    with col_som1:
        musica_ativa = st.toggle("🔊 Música", value=False)
    with col_som2:
        if musica_ativa:
            st.audio(audios[0], autoplay=True)

# --- NAVEGAÇÃO NATIVA POR SEPARADORES (SEM IFRAME PRESO) ---
tab_ia, tab_calc, tab_guia, tab_docs = st.tabs(["🤖 Consulta IA", "🔋 Calc. Wh/g", "🚦 Guia SATA", "📋 Regras"])

with tab_ia:
    aplicar_sata = st.toggle("Aplicar Variações SATA (SP / S4)", value=True)

    pergunta = st.text_input(
        "Consulta DGR:",
        placeholder="Escreve o artigo ou tira foto abaixo...",
        label_visibility="collapsed"
    )

    # --- SELETOR DIRETO CÂMARA VS GALERIA ---
    modo_foto = st.radio(
        "Anexar imagem:",
        ["Sem foto", "📷 Câmara (Tirar Foto)", "🖼️ Galeria (Upload)"],
        horizontal=True,
        label_visibility="collapsed"
    )

    foto_artigo = None
    if modo_foto == "📷 Câmara (Tirar Foto)":
        foto_artigo = st.camera_input("Aponta à etiqueta ou artigo", label_visibility="collapsed")
    elif modo_foto == "🖼️ Galeria (Upload)":
        foto_artigo = st.file_uploader("Escolher imagem", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed")

    if st.button("🔍 Validar Transporte (IATA + SATA)", type="primary", use_container_width=True):
        if not texto_referencia.strip():
            st.error("Nenhum PDF carregado no GitHub.")
        elif not pergunta.strip() and foto_artigo is None:
            st.warning("Escreve o artigo ou tira uma foto primeiro.")
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
            Analisa a pergunta e/ou a IMAGEM fornecida com base em TODOS os documentos da Secção 2 e nas Regras Específicas da SATA.

            REGRAS DE ANÁLISE VISUAL (QUANDO HOUVER IMAGEM):
            - Lê atentamente todas as especificações técnicas visíveis na etiqueta ou produto: Volts (V), mAh, Watt-hora (Wh), gramas de lítio, símbolos de inflamabilidade/gás comprimido/corrosivo, códigos UN, marca/tipo de equipamento (ex.: powerbank, bateria de ferramenta, spray, desumidificador, cadeira de rodas).
            - Se na etiqueta estiverem apenas Volts (V) e mAh (sem Wh), calcula automaticamente Wh = (V * mAh) / 1000 e indica o cálculo exato na resposta.

            REGRAS CRÍTICAS DE RIGOR REGULAMENTAR (NUNCA VIOLAR):
            1. CLASSIFICAÇÃO DE POWERBANKS:
               - Um POWERBANK é SEMPRE considerado uma bateria sobressalente (spare battery) e NUNCA uma bateria instalada num equipamento (PED).
               - Quando o artigo for um POWERBANK, responde EXCLUSIVAMENTE sobre powerbanks: proibidos no porão, na SATA têm teto máximo de 100 Wh (>100 Wh é PROIBIDO na SATA), máx. 2 unidades na cabine e recomendação de transporte junto ao passageiro.
            2. PERGUNTAS GENÉRICAS SOBRE BATERIAS (sem especificar PED, sobressalente ou powerbank):
               - Apenas nestes casos genéricos, discrimina separadamente: Instalada (PED), Bateria Solta/Sobressalente normal (até 100 Wh: máx. 20 unidades; 100–160 Wh: máx. 2 com aprovação), e Powerbank SATA (até 100 Wh: máx. 2 unidades; >100 Wh proibido).
            3. ESCALÕES E PATAMARES DE APROVAÇÃO: Discrimina sempre todos os patamares existentes (ex.: Lítio Metálico <= 2 g SEM aprovação vs > 2 g até 8 g COM aprovação).
            4. REGRAS SATA: Teto máximo de 300 Wh mesmo em baterias fixas de cadeiras de rodas, máx. 2 powerbanks até 100 Wh (>100 Wh proibidos) na cabine junto ao passageiro, NOTOC YES obrigatório para munições.

            Devolve EXCLUSIVAMENTE um JSON válido com estas chaves:
            {{
              "status_cor": "PROIBIDO" ou "CONDICIONADO" ou "PERMITIDO",
              "titulo_veredicto": "Frase curta e direta do veredicto (identificando o artigo da foto se houver imagem)",
              "referencia_iata": "Subsecção/Tabela exata (ex: Tabela 2.3.A / 2.3.5.8)",
              "aprovacao_operador": "YES / NO ou N/A (se proibido) ou resumo dos escalões",
              "bagagem_porao": "YES ou NO",
              "bagagem_mao": "YES ou NO ou ON PERSON",
              "notoc": "YES ou NO",
              "limites_exatos": [
                "Valores lidos na etiqueta/imagem (se aplicável) e limites/patamares regulamentares"
              ],
              "condicoes_operacionais": [
                "Condições práticas, motivos de proibição ou requisitos SATA aplicáveis"
              ]
            }}

            {bloco_sata}
            DOCUMENTAÇÃO IATA SECÇÃO 2:
            {texto_referencia}
            """

            texto_utilizador = pergunta.strip() if pergunta.strip() else "Identifica este artigo/etiqueta na imagem e indica se pode ser transportado na SATA (porão e/ou cabine) e em que condições."

            if foto_artigo is not None:
                img_b64 = processar_imagem_para_base64(foto_artigo)
                user_content = [
                    {"type": "text", "text": texto_utilizador},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_b64}",
                            "detail": "high"
                        }
                    }
                ]
            else:
                user_content = texto_utilizador

            with st.spinner("A analisar imagem e regulamentação IATA + SATA..."):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        temperature=0.0,
                        response_format={"type": "json_object"},
                        messages=[
                            {"role": "system", "content": prompt_json},
                            {"role": "user", "content": user_content}
                        ]
                    )
                    st.session_state["ultima_resposta"] = json.loads(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"Erro na API: {e}")

    # --- RENDERIZAÇÃO NATIVA DO RESULTADO ---
    if "ultima_resposta" in st.session_state:
        dados = st.session_state["ultima_resposta"]
        cor = dados.get("status_cor", "CONDICIONADO").upper()
        classe = "verdict-CONDICIONADO"
        icone = "⚠️"
        if "PROIBIDO" in cor:
            classe = "verdict-PROIBIDO"
            icone = "⛔"
        elif "PERMITIDO" in cor:
            classe = "verdict-PERMITIDO"
            icone = "✅"

        st.markdown(f"""
        <div class="verdict-card {classe}">
            <div class="v-title">{icone} {dados.get('titulo_veredicto', '')}</div>
            <div class="v-ref">REF: {dados.get('referencia_iata', '')}</div>
        </div>
        <div class="grid2">
            <div class="stat-box"><div class="stat-lbl">Aprovação Operador</div><div class="stat-val">{dados.get('aprovacao_operador', '-')}</div></div>
            <div class="stat-box"><div class="stat-lbl">Informar Cmdt (NOTOC)</div><div class="stat-val">{dados.get('notoc', '-')}</div></div>
            <div class="stat-box"><div class="stat-lbl">Bagagem de Porão</div><div class="stat-val">{dados.get('bagagem_porao', '-')}</div></div>
            <div class="stat-box"><div class="stat-lbl">Bagagem de Mão</div><div class="stat-val">{dados.get('bagagem_mao', '-')}</div></div>
        </div>
        """, unsafe_allow_html=True)

        limites_html = "".join(f"<li>{item}</li>" for item in dados.get("limites_exatos", []))
        cond_html = "".join(f"<li>{item}</li>" for item in dados.get("condicoes_operacionais", []))

        st.markdown(f"""
        <div class="detail-card">
            <h4>📏 Limites & Patamares Exatos</h4>
            <ul>{limites_html}</ul>
        </div>
        <div class="detail-card">
            <h4>📝 Condições Operacionais & SATA</h4>
            <ul>{cond_html}</ul>
        </div>
        """, unsafe_allow_html=True)

with tab_calc:
    st.markdown("#### ⚡ Calculadora Rápida de Baterias (IATA + SATA)")
    tipo_calc = st.selectbox(
        "Tipo de Aplicação:",
        [
            "Eletrónico Portátil / Bateria Sobressalente (Iões Lítio)",
            "Powerbank (Regra SATA: Máx. 100 Wh / Máx. 2 un.)",
            "Cadeira de Rodas Elétrica (Teto SATA 300 Wh Fixa)",
            "Lítio Metálico (mAh → Gramas de Lítio)"
        ]
    )
    col_v, col_m = st.columns(2)
    with col_v:
        volts = st.number_input("Tensão (Volts - V):", min_value=0.0, value=14.8, step=0.1)
    with col_m:
        mah = st.number_input("Capacidade (mAh):", min_value=0.0, value=10000.0, step=100.0)

    if "Lítio Metálico" in tipo_calc:
        gramas = (mah / 1000.0) * 0.3
        st.metric("Conteúdo Estimado de Lítio", f"{gramas:.2f} g")
        if gramas <= 2:
            st.success("✅ ≤ 2 g: Permitido SEM aprovação (Solta: só cabine, máx. 20 sobressalentes).")
        elif gramas <= 8:
            st.warning("⚠️ > 2 g até 8 g (POC/Médico): Requer APROVAÇÃO do operador (YES), máx. 2 sobressalentes.")
        else:
            st.error("⛔ > 8 g: PROIBIDO em bagagem de passageiro.")
    else:
        wh = (volts * mah) / 1000.0
        st.metric("Energia Calculada", f"{wh:.1f} Wh")
        if "Cadeira de Rodas" in tipo_calc:
            if wh <= 300:
                st.success("✅ ≤ 300 Wh: Aceite na SATA (sujeito a aprovação e proteção de terminais).")
            else:
                st.error("⛔ > 300 Wh: PROIBIDO NA SATA (teto máximo de 300 Wh mesmo para baterias fixas).")
        elif "Powerbank" in tipo_calc:
            if wh <= 100:
                st.success("✅ ≤ 100 Wh: Permitido na SATA (SÓ CABINE, máx. 2 powerbanks junto ao passageiro, sem aprovação).")
            else:
                st.error("⛔ > 100 Wh: POWERBANK PROIBIDO NA SATA (não é permitida a faixa 100–160 Wh para powerbanks).")
        else:
            if wh <= 100:
                st.success("✅ ≤ 100 Wh (Sem aprovação): Instalada PED (Porão/Cabine) | Solta normal: SÓ CABINE (máx. 20 sobressalentes).")
            elif wh <= 160:
                st.warning("⚠️ 100–160 Wh: Requer APROVAÇÃO SATA (YES). Solta normal: SÓ CABINE (máx. 2 unidades).")
            else:
                st.error("⛔ > 160 Wh: PROIBIDO em bagagem de passageiro.")

with tab_guia:
    st.error("⛔ **PROIBIDOS NA SATA (Porão & Cabine):**\n- **Powerbanks > 100 Wh**\n- Trotinetes elétricas, hoverboards, segways, bicicletas elétricas\n- Cadeiras de rodas com bateria fixa **> 300 Wh**\n- Desumidificadores, tinteiros e toners de impressão\n- Latas de tinta e sprays técnicos/inflamáveis\n- Camping gas, botijas gás inflamável (Div. 2.1) e recipientes combustível")
    st.warning("⚠️ **REGRAS ESPECÍFICAS SATA:**\n- **Baterias Sobressalentes (≤ 100 Wh):** Só cabine. Mantém limite IATA de **máx. 20 unidades** (100–160 Wh: máx. 2 com aprovação).\n- **Powerbanks:** Só cabine, **máx. 100 Wh** e **máx. 2 powerbanks** por passageiro; levar **junto ao passageiro** (evitar rack superior).\n- **Munições (1.4S):** Máx. 5 kg porão + **NOTOC obrigatório (YES)**.\n- **Cartuchos CO2 (Div. 2.2):** Permitidos dentro dos limites IATA (não inflamáveis).")

with tab_docs:
    st.markdown(f"**📚 Manuais Carregados ({len(lista_pdfs)} PDFs):**")
    for p in lista_pdfs:
        st.caption(f"📄 {p}")
    st.divider()
    st.markdown("**📋 Regras SATA Ativas (`regras_sata.txt`):**")
    st.text_area("Regras atuais:", value=regras_sata_base, height=340, disabled=True)
