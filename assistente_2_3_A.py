import os
import glob
import pdfplumber
import streamlit as st
from openai import OpenAI

# --- CONFIGURAÇÃO DA PÁGINA (MOBILE + DESKTOP) ---
st.set_page_config(
    page_title="DGR SATA - Secção 2 & 2.3.A",
    page_icon="✈️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- PROTEÇÃO POR PASSWORD ---
def verificar_acesso():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.title("✈️ Consultor DGR SATA")
        st.caption("Secção 2 IATA DGR (67ª Edição) + Variações Operacionais SATA")
        senha = st.text_input("Código de acesso:", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            senha_correta = str(st.secrets.get("APP_PASSWORD", "")).strip()
            if senha.strip() == senha_correta and senha_correta != "":
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Código incorreto. Verifica maiúsculas/minúsculas e espaços.")
        st.stop()

verificar_acesso()

OPENAI_API_KEY = str(st.secrets["OPENAI_API_KEY"]).strip()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CARREGAMENTO AUTOMÁTICO DE TODOS OS PDFs DA SECÇÃO 2 ---
@st.cache_data
def carregar_todos_pdfs(diretorio):
    """Lê todos os PDFs na pasta raiz e na subpasta 'manuais/' mantendo o layout."""
    padroes = [
        os.path.join(diretorio, "*.pdf"),
        os.path.join(diretorio, "manuais", "*.pdf")
    ]
    ficheiros = []
    for p in padroes:
        ficheiros.extend(glob.glob(p))
    ficheiros = sorted(list(set(ficheiros)))

    blocos_texto = []
    nomes_carregados = []

    for caminho in ficheiros:
        nome_ficheiro = os.path.basename(caminho)
        nomes_carregados.append(nome_ficheiro)
        paginas_doc = [f"=== DOCUMENTO: {nome_ficheiro} ==="]
        with pdfplumber.open(caminho) as pdf:
            for num_pag, page in enumerate(pdf.pages, start=1):
                texto_alinhado = page.extract_text(layout=True)
                if texto_alinhado:
                    paginas_doc.append(f"--- {nome_ficheiro} | PÁGINA {num_pag} ---\n{texto_alinhado}")
        blocos_texto.append("\n\n".join(paginas_doc))

    return "\n\n========================================\n\n".join(blocos_texto), nomes_carregados

# --- CARREGAMENTO DAS REGRAS ESPECÍFICAS DA SATA ---
REGRAS_SATA_PADRAO = """1. VEÍCULOS E EQUIPAMENTOS ELÉTRICOS DE MOBILIDADE PESSOAL:
   - PROIBIDO o transporte (porão e mão) de equipamentos elétricos de mobilidade pessoal: trotinetes elétricas, hoverboards, monociclos elétricos (solowheels), segways, bicicletas elétricas e similares.
   - EXCEÇÃO ÚNICA: Cadeiras de rodas elétricas e auxiliares de mobilidade médica (Mobility Aids) para passageiros com mobilidade reduzida, sujeitos às regras aplicáveis (2.3.2.2 / 2.3.2.3 / 2.3.2.4).

2. DESUMIDIFICADORES:
   - PROIBIDO o transporte em bagagem de porão e bagagem de mão.

3. TINTEIROS E TONERS (Impressoras / Fotocopiadoras):
   - PROIBIDO o transporte em bagagem de porão e bagagem de mão.

4. LATAS DE TINTA E SPRAYS / AEROSSÓIS TÉCNICOS:
   - PROIBIDO o transporte de latas de tinta e sprays (tintas em spray, sprays técnicos/inflamáveis/domésticos) em bagagem de porão e bagagem de mão. (Artigos de higiene/medicinais não inflamáveis/não tóxicos seguem a 2.3.5.1).

5. CAMPING GAS, GASES INFLAMÁVEIS (DIV. 2.1) E RECIPIENTES DE COMBUSTÍVEL LÍQUIDO (CLASSE 3):
   - PROIBIDO o transporte (porão e mão) de camping gas, botijas/cartuchos de gás inflamável (Div. 2.1, ex: butano, propano) e fogões ou recipientes que contenham ou tenham contido combustível líquido inflamável, estejam CHEIOS ou VAZIOS.
   - EXCEÇÃO IMPORTANTE: Gases NÃO INFLAMÁVEIS e NÃO TÓXICOS (Divisão 2.2), como cartuchos/botijas de CO2 (dióxido de carbono), cilindros para membros mecânicos ou oxigénio gasoso medicinal, NÃO são proibidos por esta regra e seguem os limites da Tabela 2.3.A e Subsecção 2.3.

6. MUNIÇÕES (Div. 1.4S, UN 0012 / UN 0014):
   - Permitidas apenas em bagagem de porão dentro dos limites regulamentares (máx. 5 kg peso bruto por pessoa, aprovação do operador obrigatória).
   - REGRA ESPECÍFICA SATA: O Comandante (Pilot-in-Command) DEVE SER SEMPRE INFORMADO (YES) da localização das munições a bordo (NOTOC).
"""

def carregar_regras_sata():
    caminho_txt = os.path.join(BASE_DIR, "regras_sata.txt")
    if os.path.exists(caminho_txt):
        with open(caminho_txt, "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
            if conteudo:
                return conteudo
    return REGRAS_SATA_PADRAO

texto_referencia, lista_pdfs = carregar_todos_pdfs(BASE_DIR)
regras_sata_base = carregar_regras_sata()

st.title("✈️ Consultor DGR: Secção 2 + SATA")
st.caption("IATA DGR 67ª Edição (1 Jan 2026) | Variações Operacionais SATA")

with st.expander(f"📚 Documentos carregados ({len(lista_pdfs)} PDFs) & Regras SATA"):
    if lista_pdfs:
        for pdf_nome in lista_pdfs:
            st.markdown(f"- `{pdf_nome}`")
    else:
        st.warning("Nenhum PDF encontrado na pasta.")
    
    st.divider()
    aplicar_regras_sata = st.toggle("Aplicar Restrições Específicas SATA", value=True)
    regras_sata_ativas = st.text_area(
        "Regras SATA ativas (podes editar aqui para testar ou atualizar no ficheiro regras_sata.txt):",
        value=regras_sata_base,
        height=240
    )

# --- ATALHOS RÁPIDOS ---
st.markdown("**Consultas rápidas:**")
col_a, col_b = st.columns(2)
if "pergunta_texto" not in st.session_state:
    st.session_state["pergunta_texto"] = ""

with col_a:
    if st.button("🔋 Powerbanks / Baterias", use_container_width=True):
        st.session_state["pergunta_texto"] = "Quais os limites e regras para baterias de lítio sobressalentes / powerbanks?"
    if st.button("🔫 Munições (1.4S)", use_container_width=True):
        st.session_state["pergunta_texto"] = "Quais as regras e limites para transporte de munições na SATA?"

with col_b:
    if st.button("🧯 Botijas CO2 vs Camping Gas", use_container_width=True):
        st.session_state["pergunta_texto"] = "Qual a diferença de regras e limites entre cartuchos de CO2 e camping gas?"
    if st.button("🛴 Trotinete / Cadeira Rodas", use_container_width=True):
        st.session_state["pergunta_texto"] = "Passageiro quer transportar trotinete elétrica ou cadeira de rodas elétrica. O que se aplica?"

pergunta = st.text_area(
    "Descreve o artigo, subsecção ou cenário do passageiro:",
    value=st.session_state["pergunta_texto"],
    placeholder="Ex: Quais as regras da subsecção 2.3.4.2 para cartuchos de CO2? / Passageiro com marisco...",
    height=105
)

if st.button("🔍 Verificar Regra", type="primary", use_container_width=True):
    if not texto_referencia.strip():
        st.error("Erro: Nenhum PDF da Secção 2 foi encontrado no repositório.")
    elif not pergunta.strip():
        st.warning("Escreve uma pergunta primeiro.")
    else:
        client = OpenAI(api_key=OPENAI_API_KEY)

        bloco_sata = f"""
        HIERARQUIA REGULAMENTAR OBRIGATÓRIA:
        1º Lugar (MÁXIMA PRIORIDADE): REGRAS E RESTRIÇÕES ESPECÍFICAS DA SATA (Operador).
        2º Lugar: MANUAL IATA DGR SECÇÃO 2 (67ª Edição) fornecido abaixo.

        ATENÇÃO À DISTINÇÃO ENTRE GASES:
        - A proibição da SATA aplica-se APENAS a gases inflamáveis (Div. 2.1, como camping gas/butano/propano) e recipientes de combustível líquido inflamável (cheios ou vazios).
        - Gases NÃO INFLAMÁVEIS e NÃO TÓXICOS (Divisão 2.2), como cartuchos/botijas de CO2, NÃO são proibidos pela SATA: devem ser avaliados pelas entradas correspondentes da Tabela 2.3.A e Subsecção 2.3 da IATA.

        REGRAS ESPECÍFICAS DA SATA:
        {regras_sata_ativas}
        """ if aplicar_regras_sata else "Aplica apenas a regra geral do Manual IATA DGR Secção 2."

        system_prompt = f"""
        És um Instrutor Certificado de IATA Dangerous Goods Regulations (DGR - 67ª Edição) a operar na SATA.
        Analisa a pergunta cruzando TODOS os capítulos/documentos da Secção 2 da IATA DGR e as Regras Específicas da SATA fornecidos abaixo.

        REGRA OBRIGATÓRIA DE DETALHE NUMÉRICO E SUBSECÇÕES:
        - Cita sempre o número exato da subsecção aplicável (ex.: 2.3.2.5, 2.3.4.2, 2.3.5.8, 2.8, etc.) e o nome do documento onde encontraste a informação.
        - NUNCA omitas valores numéricos, capacidades, pesos ou quantidades máximas (volumes em mL/L, pesos em g/kg, energia em Wh, número máximo de unidades por pessoa ou dispositivo).
        - Transcreve TODOS os cenários previstos dentro da entrada aplicável.

        ESTRUTURA DAS COLUNAS DA TABELA 2.3.A IATA (quando aplicável, da esquerda para a direita):
        1. Artigo / Descrição e limitações
        2. The approval of the operator is required (Aprovação do Operador) -> YES / NO
        3. Permitted in or as checked baggage (Bagagem de Porão) -> YES / NO
        4. Permitted in or as carry-on baggage (Bagagem de Mão) -> YES / NO / ON ONE'S PERSON
        5. The pilot-in-command must be informed of the location (NOTOC) -> YES / NO

        Responde em Português de Portugal, com terminologia aeronáutica rigorosa, usando exatamente este formato:

        ### 📋 Veredicto Final (Operação SATA)
        *(Indica claramente se é PROIBIDO na SATA, PERMITIDO ou PERMITIDO COM CONDIÇÕES)*

        ### 📊 Enquadramento Regulamentar (IATA vs. SATA)
        * **Subsecção / Entrada aplicável:** [Ex.: Tabela 2.3.A / Subsecção 2.3.4.2]
        * **Aprovação do Operador:** [YES / NO / N/A]
        * **Bagagem de Porão (Checked):** [YES / NO / N/A — indicando se há restrição SATA]
        * **Bagagem de Mão (Carry-on):** [YES / NO / N/A — indicando se há restrição SATA]
        * **Informar o Comandante (NOTOC):** [YES / NO / N/A — destacando exigências SATA]

        ### 📏 Limites Quantitativos e Capacidades Exatas
        *(Lista obrigatória de TODOS os valores numéricos: volumes em mL/L, pesos em g/kg, Wh, número máximo de unidades).*

        ### 📝 Condições Operacionais e Notas Técnicas
        *(Explica todas as condições de acondicionamento, proteção e detalhes extraídos dos capítulos da Secção 2 e das regras da SATA).*

        ---
        {bloco_sata}

        ---
        DOCUMENTAÇÃO REGULAMENTAR CARREGADA (SECÇÃO 2 IATA DGR - 67ª EDIÇÃO):
        {texto_referencia}
        """

        with st.spinner("A consultar Secção 2 IATA + Regras SATA..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    temperature=0.0,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": pergunta}
                    ]
                )
                st.markdown("---")
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Erro na API: {e}")
