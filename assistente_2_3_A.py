import os
import pdfplumber
import streamlit as st
from openai import OpenAI

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="DGR SATA 2.3.A",
    page_icon="✈️",
    layout="centered"
)

# --- PROTEÇÃO POR PASSWORD (PARA PROTEGER A TUA API KEY) ---
def verificar_acesso():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.title("✈️ Consultor DGR - Acesso Restrito")
        senha = st.text_input("Introduz o código de acesso:", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            if senha == st.secrets["APP_PASSWORD"]:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Código incorreto.")
        st.stop()

verificar_acesso()

# --- LEITURA SEGURA DA CHAVE API ---
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
FICHEIRO_TABELA = "Tabela 2.3.A - 67th Edição - 1 Janeiro 2026.pdf"

# --- RESTRIÇÕES ESPECÍFICAS DA SATA (PREVALECEM SOBRE A IATA) ---
REGRAS_ESPECIFICAS_SATA = """
1. VEÍCULOS E EQUIPAMENTOS ELÉTRICOS DE MOBILIDADE PESSOAL:
   - PROIBIDO o transporte (tanto em bagagem de porão como de mão) de equipamentos elétricos de mobilidade pessoal, tais como trotinetes elétricas, hoverboards, monociclos elétricos (solowheels), segways, bicicletas elétricas e similares.
   - EXCEÇÃO ÚNICA: Cadeiras de rodas elétricas e auxiliares de mobilidade médica (Mobility Aids) para passageiros com mobilidade reduzida, sujeitos às regras aplicáveis.

2. DESUMIDIFICADORES:
   - PROIBIDO o transporte em bagagem de porão e bagagem de mão.

3. TINTEIROS E TONERS (Impressoras / Fotocopiadoras):
   - PROIBIDO o transporte em bagagem de porão e bagagem de mão.

4. LATAS DE TINTA E SPRAYS / AEROSSÓIS TÉCNICOS:
   - PROIBIDO o transporte de latas de tinta e sprays (tintas em spray, sprays técnicos/inflamáveis/domésticos) em bagagem de porão e bagagem de mão. (Nota: artigos de higiene/medicinais não inflamáveis/não tóxicos são permitidos dentro dos limites da 2.3.5.1).

5. CAMPING GAS, GASES INFLAMÁVEIS (DIV. 2.1) E RECIPIENTES DE COMBUSTÍVEL LÍQUIDO (CLASSE 3):
   - PROIBIDO o transporte (em bagagem de porão e de mão) de camping gas, botijas/cartuchos de gás inflamável (Div. 2.1, ex: butano, propano) e fogões ou recipientes que contenham ou tenham contido combustível líquido inflamável, estejam CHEIOS ou VAZIOS.
   - EXCEÇÃO IMPORTANTE (NÃO PROIBIDO): Esta proibição NÃO se aplica a gases não inflamáveis e não tóxicos (Divisão 2.2), tais como cartuchos/botijas de CO2 (dióxido de carbono), cilindros para membros mecânicos ou oxigénio gasoso medicinal, os quais SÃO PERMITIDOS de acordo com as condições e limites da Tabela 2.3.A da IATA (e respetivas subsecções, como a 2.3.4.2).

6. MUNIÇÕES (Div. 1.4S, UN 0012 / UN 0014):
   - Permitidas apenas em bagagem de porão dentro dos limites regulamentares (máx. 5 kg peso bruto por pessoa, aprovação do operador obrigatória).
   - REGRA ESPECÍFICA SATA: Ao contrário da regra geral da Tabela 2.3.A da IATA (que indica NO para NOTOC), na SATA o Comandante (Pilot-in-Command) DEVE SER SEMPRE INFORMADO (YES) da localização das munições a bordo (NOTOC).
"""

st.title("✈️ Consultor DGR: IATA 2.3.A + SATA")
st.caption("67ª Edição (1 Jan 2026) | Variações Operacionais SATA")

@st.cache_data
def carregar_tabela_automatica(caminho_pdf):
    paginas = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for num_pag, page in enumerate(pdf.pages, start=1):
            texto_alinhado = page.extract_text(layout=True)
            if texto_alinhado:
                paginas.append(f"=== PÁGINA {num_pag} ===\n{texto_alinhado}")
    return "\n\n".join(paginas)

caminho_completo = os.path.join(os.path.dirname(os.path.abspath(__file__)), FICHEIRO_TABELA)
texto_referencia = carregar_tabela_automatica(caminho_completo) if os.path.exists(caminho_completo) else ""

with st.sidebar:
    st.header("⚙️ Opções")
    aplicar_regras_sata = st.checkbox("Aplicar Restrições Específicas SATA", value=True)
    with st.expander("📋 Ver / Editar Regras SATA"):
        regras_sata_ativas = st.text_area(
            "Regras ativas:",
            value=REGRAS_ESPECIFICAS_SATA,
            height=250
        )

pergunta = st.text_area(
    "Escreve a questão ou cenário:",
    placeholder="Ex: Passageiro com 2 cartuchos de CO2 de 28g para colete salva-vidas...",
    height=100
)

if st.button("🔍 Verificar Regra", type="primary", use_container_width=True):
    if not texto_referencia.strip():
        st.error("Erro: PDF da Tabela 2.3.A não encontrado no servidor.")
    elif not pergunta.strip():
        st.warning("Escreve uma pergunta primeiro.")
    else:
        client = OpenAI(api_key=OPENAI_API_KEY)

        bloco_sata = f"""
        HIERARQUIA REGULAMENTAR OBRIGATÓRIA:
        1º Lugar (MÁXIMA PRIORIDADE): REGRAS E RESTRIÇÕES ESPECÍFICAS DA SATA (Operador).
        2º Lugar: TABELA 2.3.A DA IATA DGR (67ª Edição).

        ATENÇÃO À DISTINÇÃO ENTRE GASES:
        - A proibição da SATA aplica-se APENAS a gases inflamáveis (Div. 2.1, como camping gas/butano/propano) e recipientes de combustível líquido inflamável (cheios ou vazios).
        - Gases NÃO INFLAMÁVEIS e NÃO TÓXICOS (Divisão 2.2), como cartuchos/botijas de CO2, NÃO são proibidos pela SATA: devem ser avaliados pelas entradas correspondentes da Tabela 2.3.A da IATA.

        REGRAS ESPECÍFICAS DA SATA:
        {regras_sata_ativas}
        """ if aplicar_regras_sata else "Aplica apenas a regra geral da Tabela 2.3.A da IATA DGR."

        system_prompt = f"""
        És um Instrutor Certificado de IATA Dangerous Goods Regulations (DGR - 67ª Edição) a operar na SATA.
        Analisa a pergunta com base na Tabela 2.3.A da IATA e nas Regras Específicas da SATA fornecidas abaixo.

        REGRA OBRIGATÓRIA DE DETALHE NUMÉRICO:
        - NUNCA omitas valores numéricos, capacidades, pesos ou quantidades máximas que constem na Tabela 2.3.A (ex.: volumes em mL ou L, pesos em g ou kg, energia em Wh, número máximo de unidades por pessoa ou por dispositivo, e remissões para subsecções como 2.3.4.2, 2.3.5.1, 2.3.5.8, etc.).
        - Transcreve TODOS os cenários previstos dentro da entrada aplicável.

        ESTRUTURA DAS COLUNAS DA TABELA 2.3.A IATA (da esquerda para a direita):
        1. Artigo / Descrição e limitações
        2. The approval of the operator is required (Aprovação do Operador) -> YES / NO
        3. Permitted in or as checked baggage (Bagagem de Porão) -> YES / NO
        4. Permitted in or as carry-on baggage (Bagagem de Mão) -> YES / NO / ON ONE'S PERSON
        5. The pilot-in-command must be informed of the location (NOTOC) -> YES / NO

        Responde em Português de Portugal, com terminologia aeronáutica rigorosa, usando exatamente este formato:

        ### 📋 Veredicto Final (Operação SATA)
        *(Indica claramente se é PROIBIDO na SATA, PERMITIDO ou PERMITIDO COM CONDIÇÕES)*

        ### 📊 Comparação: Regra Geral IATA vs. Regra SATA
        * **Entrada na Tabela 2.3.A (IATA):** [Nome exato da entrada]
        * **Aprovação do Operador:** [YES / NO]
        * **Bagagem de Porão (Checked):** [YES / NO — indicando se há restrição SATA]
        * **Bagagem de Mão (Carry-on):** [YES / NO — indicando se há restrição SATA]
        * **Informar o Comandante (NOTOC):** [YES / NO — destacando "YES (Exigência SATA)" no caso de munições]

        ### 📏 Limites Quantitativos e Capacidades Exatas
        *(Lista obrigatória de TODOS os valores numéricos da tabela: volumes em mL/L, pesos em g/kg, Wh, número máximo de cartuchos/baterias/artigos por pessoa ou dispositivo).*

        ### 📝 Condições Operacionais e Referências
        *(Explica todas as condições de acondicionamento, proteção e referências regulamentares como 2.3.4.2, 2.3.2.5, etc., bem como qualquer regra específica da SATA).*

        ---
        {bloco_sata}

        ---
        TEXTO DA TABELA 2.3.A IATA (67ª EDIÇÃO):
        {texto_referencia}
        """

        with st.spinner("A consultar Tabela 2.3.A + SATA..."):
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