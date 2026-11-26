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

# Remover margens e elementos padrão do Streamlit para aspeto 100% App Nativa
st.markdown("""
<style>
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
    }
    body, .stApp {
        background-color: #060D1A !important;
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
            "Seleciona um atalho abaixo ou descreve o artigo do passageiro para validar limites exatos e patamares."
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
        placeholder="Ex: POC lítio metálico, cadeira rodas 350Wh, 2 powerbanks...",
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

            REGRAS CRÍTICAS DE RIGOR REGULAMENTAR:
            1. ESCALÕES E PATAMARES DE APROVAÇÃO: Discrimina sempre TODOS os patamares distintos (ex.: Lítio Metálico <= 2 g SEM aprovação vs > 2 g até 8 g COM aprovação; ou Iões de Lítio <= 100 Wh SEM aprovação vs > 100 Wh até 160 Wh COM aprovação).
            2. Preenche "aprovacao_operador" com o resumo exato dos escalões quando aplicável (ex.: "NO (<=2g) | YES (>2g-8g)").
            3. Indica sempre limites numéricos exatos (Wh, g, mL, L, kg, máx. unidades) e regras SATA (ex.: teto 300 Wh mesmo em baterias fixas de cadeiras de rodas, máx. 2 powerbanks junto ao passageiro, NOTOC YES para munições).

            Devolve EXCLUSIVAMENTE um JSON válido com estas chaves:
            {{
              "status_cor": "PROIBIDO" ou "CONDICIONADO" ou "PERMITIDO",
              "titulo_veredicto": "Frase curta e direta do veredicto",
              "referencia_iata": "Subsecção/Tabela exata (ex: Tabela 2.3.A / 2.3.3.2)",
              "aprovacao_operador": "YES / NO ou resumo dos escalões",
              "bagagem_porao": "YES ou NO",
              "bagagem_mao": "YES ou NO ou ON PERSON",
              "notoc": "YES ou NO",
              "limites_exatos": ["Patamar 1...", "Patamar 2...", "Máximo unidades..."],
              "condicoes_operacionais": ["Condições práticas e variações SATA..."]
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

# --- RENDERIZAÇÃO DO PAINEL EFB INTERATIVO (CARTÕES + CALCULADORA + GUIA) ---
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
  body {{ background: #060D1A; color: #F8FAFC; padding: 12px 14px 80px 14px; }}
  .tabs {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; background: #0F172A; padding: 5px; border-radius: 12px; border: 1px solid #1E293B; margin-bottom: 14px; }}
  .tab-btn {{ background: transparent; border: none; color: #94A3B8; padding: 8px 4px; border-radius: 8px; font-size: 0.74rem; font-weight: 600; cursor: pointer; }}
  .tab-btn.active {{ background: #005580; color: #FFFFFF; }}
  .section {{ display: none; }}
  .section.active {{ display: block; }}

  .card {{ background: #0F172A; border: 1px solid #1E293B; border-radius: 14px; padding: 14px; margin-bottom: 12px; }}
  .verdict {{ border-left: 5px solid #F59E0B; background: rgba(245, 158, 11, 0.1); }}
  .verdict.PROIBIDO {{ border-left-color: #EF4444; background: rgba(239, 68, 68, 0.12); }}
  .verdict.PERMITIDO {{ border-left-color: #10B981; background: rgba(16, 185, 129, 0.12); }}
  .v-title {{ font-size: 0.98rem; font-weight: 700; margin-bottom: 4px; }}
  .v-ref {{ font-size: 0.76rem; color: #94A3B8; font-family: monospace; }}

  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }}
  .box {{ background: #0F172A; border: 1px solid #1E293B; border-radius: 12px; padding: 10px; text-align: center; }}
  .box-lbl {{ font-size: 0.68rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
  .box-val {{ font-size: 0.88rem; font-weight: 700; color: #38BDF8; font-family: monospace; }}

  h4 {{ font-size: 0.82rem; color: #94A3B8; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.4px; }}
  ul {{ padding-left: 16px; font-size: 0.85rem; line-height: 1.45; color: #E2E8F0; }}
  li {{ margin-bottom: 6px; }}

  /* Calculadora */
  label {{ display: block; font-size: 0.78rem; color: #94A3B8; margin-bottom: 4px; margin-top: 8px; }}
  input, select {{ width: 100%; background: #060D1A; border: 1px solid #334155; color: white; padding: 10px; border-radius: 10px; font-size: 0.95rem; }}
  .calc-res {{ margin-top: 12px; padding: 14px; border-radius: 12px; background: #1E293B; text-align: center; }}
  .calc-num {{ font-size: 1.6rem; font-weight: 800; color: #10B981; font-family: monospace; }}
  pre {{ white-space: pre-wrap; font-size: 0.8rem; color: #CBD5E1; line-height: 1.45; }}
</style>
</head>
<body>

<div class="tabs">
  <button class="tab-btn active" onclick="showTab('ia', this)">🤖 Resultado IA</button>
  <button class="tab-btn" onclick="showTab('calc', this)">🔋 Calc. Wh/g</button>
  <button class="tab-btn" onclick="showTab('guia', this)">🚦 Guia SATA</button>
  <button class="tab-btn" onclick="showTab('docs', this)">📋 Regras</button>
</div>

<div id="tab-ia" class="section active">
  <div id="verdict-card" class="card verdict">
    <div id="v-title" class="v-title"></div>
    <div id="v-ref" class="v-ref"></div>
  </div>
  <div class="grid2">
    <div class="box"><div class="box-lbl">Aprovação Operador</div><div id="b-aprov" class="box-val"></div></div>
    <div class="box"><div class="box-lbl">Informar Cmdt (NOTOC)</div><div id="b-notoc" class="box-val"></div></div>
    <div class="box"><div class="box-lbl">Bagagem de Porão</div><div id="b-porao" class="box-val"></div></div>
    <div class="box"><div class="box-lbl">Bagagem de Mão</div><div id="b-mao" class="box-val"></div></div>
  </div>
  <div class="card">
    <h4>📏 Limites & Patamares Exatos</h4>
    <ul id="list-limites"></ul>
  </div>
  <div class="card">
    <h4>📝 Condições Operacionais & SATA</h4>
    <ul id="list-cond"></ul>
  </div>
</div>

<div id="tab-calc" class="section">
  <div class="card">
    <h4>⚡ Calculadora Rápida de Baterias (IATA + SATA)</h4>
    <label>Tipo de Aplicação:</label>
    <select id="tipo-uso" onchange="calcularWh()">
      <option value="ped">Eletrónico Portátil / Powerbank (Iões Lítio)</option>
      <option value="wheelchair">Cadeira de Rodas Elétrica (Teto SATA 300 Wh Fixa)</option>
      <option value="metal">Lítio Metálico (mAh → Gramas de Lítio)</option>
    </select>
    <label>Tensão Nominal (Volts - V):</label>
    <input type="number" id="volts" value="14.8" step="0.1" oninput="calcularWh()">
    <label>Capacidade (mAh):</label>
    <input type="number" id="mah" value="10000" step="100" oninput="calcularWh()">
    <div class="calc-res">
      <div id="calc-num" class="calc-num">148.0 Wh</div>
      <div id="calc-msg" style="font-size:0.82rem; margin-top:6px; color:#FBBF24;"></div>
    </div>
  </div>
</div>

<div id="tab-guia" class="section">
  <div class="card" style="border-left:4px solid #EF4444;">
    <h4>⛔ Proibidos na SATA (Porão & Cabine)</h4>
    <ul>
      <li>Trotinetes elétricas, hoverboards, segways, bicicletas elétricas.</li>
      <li>Cadeiras de rodas com bateria fixa superior a <strong>300 Wh</strong>.</li>
      <li>Desumidificadores, tinteiros e toners de impressão.</li>
      <li>Latas de tinta e sprays técnicos/inflamáveis.</li>
      <li>Camping gas, botijas gás inflamável (Div. 2.1) e recipientes combustível (cheios ou vazios).</li>
    </ul>
  </div>
  <div class="card" style="border-left:4px solid #F59E0B;">
    <h4>⚠️ Regras Específicas SATA</h4>
    <ul>
      <li><strong>Powerbanks:</strong> Máx. <strong>2 unidades</strong> na cabine; recomendação SATA: transportar <strong>junto ao passageiro</strong> (evitar rack superior).</li>
      <li><strong>Munições (1.4S):</strong> Máx. 5 kg porão + <strong>NOTOC obrigatório (YES)</strong>.</li>
      <li><strong>Cartuchos CO2 (Div. 2.2):</strong> Permitidos dentro dos limites IATA (não inflamáveis).</li>
    </ul>
  </div>
</div>

<div id="tab-docs" class="section">
  <div class="card">
    <h4>📚 Manuais Carregados</h4>
    <ul id="list-pdfs"></ul>
  </div>
  <div class="card">
    <h4>📋 Regras SATA Ativas (regras_sata.txt)</h4>
    <pre id="txt-regras"></pre>
  </div>
</div>

<script>
  const dados = {resp_json};
  const regrasTxt = {regras_json};
  const pdfsList = {pdfs_json};

  function showTab(id, btn) {{
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + id).classList.add('active');
    btn.classList.add('active');
  }}

  // Preencher Resultado IA
  const vCard = document.getElementById('verdict-card');
  const cor = (dados.status_cor || '').toUpperCase();
  if (cor.includes('PROIBIDO')) vCard.classList.add('PROIBIDO');
  else if (cor.includes('PERMITIDO')) vCard.classList.add('PERMITIDO');

  document.getElementById('v-title').textContent = (cor.includes('PROIBIDO') ? '⛔ ' : cor.includes('PERMITIDO') ? '✅ ' : '⚠️ ') + dados.titulo_veredicto;
  document.getElementById('v-ref').textContent = 'REF: ' + dados.referencia_iata;
  document.getElementById('b-aprov').textContent = dados.aprovacao_operador;
  document.getElementById('b-notoc').textContent = dados.notoc;
  document.getElementById('b-porao').textContent = dados.bagagem_porao;
  document.getElementById('b-mao').textContent = dados.bagagem_mao;

  const ulLim = document.getElementById('list-limites');
  (dados.limites_exatos || []).forEach(l => {{
    const li = document.createElement('li'); li.textContent = l; ulLim.appendChild(li);
  }});
  const ulCond = document.getElementById('list-cond');
  (dados.condicoes_operacionais || []).forEach(c => {{
    const li = document.createElement('li'); li.textContent = c; ulCond.appendChild(li);
  }});

  // Preencher Docs
  const ulPdfs = document.getElementById('list-pdfs');
  pdfsList.forEach(p => {{
    const li = document.createElement('li'); li.textContent = p; ulPdfs.appendChild(li);
  }});
  document.getElementById('txt-regras').textContent = regrasTxt;

  // Calculadora
  function calcularWh() {{
    const tipo = document.getElementById('tipo-uso').value;
    const v = parseFloat(document.getElementById('volts').value) || 0;
    const mah = parseFloat(document.getElementById('mah').value) || 0;
    const numEl = document.getElementById('calc-num');
    const msgEl = document.getElementById('calc-msg');

    if (tipo === 'metal') {{
      const gramas = (mah / 1000) * 0.3;
      numEl.textContent = gramas.toFixed(2) + ' g Lítio';
      if (gramas <= 2) {{ numEl.style.color = '#10B981'; msgEl.textContent = '✅ ≤ 2 g: Permitido SEM aprovação do operador.'; }}
      else if (gramas <= 8) {{ numEl.style.color = '#F59E0B'; msgEl.textContent = '⚠️ > 2 g até 8 g (POC/Médico): Requer APROVAÇÃO do operador (YES).'; }}
      else {{ numEl.style.color = '#EF4444'; msgEl.textContent = '⛔ > 8 g: PROIBIDO em bagagem de passageiro.'; }}
      return;
    }}

    const wh = (v * mah) / 1000;
    numEl.textContent = wh.toFixed(1) + ' Wh';

    if (tipo === 'wheelchair') {{
      if (wh <= 300) {{ numEl.style.color = '#10B981'; msgEl.textContent = '✅ ≤ 300 Wh: Aceite na SATA (sujeito a aprovação e proteção de terminais).'; }}
      else {{ numEl.style.color = '#EF4444'; msgEl.textContent = '⛔ > 300 Wh: PROIBIDO NA SATA (teto máximo de 300 Wh mesmo para baterias fixas).'; }}
    }} else {{
      if (wh <= 100) {{ numEl.style.color = '#10B981'; msgEl.textContent = '✅ ≤ 100 Wh: Permitido sem aprovação (Máx. 2 powerbanks na cabine junto ao passageiro).'; }}
      else if (wh <= 160) {{ numEl.style.color = '#F59E0B'; msgEl.textContent = '⚠️ 100–160 Wh: Requer APROVAÇÃO SATA (YES). Máx. 2 sobressalentes na cabine.'; }}
      else {{ numEl.style.color = '#EF4444'; msgEl.textContent = '⛔ > 160 Wh: PROIBIDO como powerbank / eletrónico portátil.'; }}
    }}
  }}
  calcularWh();
</script>
</body>
</html>
"""

components.html(html_efb, height=780, scrolling=True)
