import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from lxml import etree
import os

# --- 1. CONFIGURAÇÃO E MAPEAMENTOS (Zona Global) ---
st.set_page_config(page_title="Arquivo Eurico: Carta 67", layout="wide", page_icon="✉️")

# ADICIONADO: Estilo visual personalizado
st.markdown("""
    <style>
    .main { background-color: #fdfaf5; } /* Fundo creme tipo papel antigo */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; 
        white-space: pre-wrap; 
        background-color: #f0ede9; 
        border-radius: 5px 5px 0 0; 
        gap: 1px; padding-top: 10px; padding-bottom: 10px; 
    }
    .stTabs [aria-selected="true"] { background-color: #e2dfda; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ADICIONADO: Mapeamento de Cores para o Grafo
cores_map = {
    "compositor": "#FFD700",    # Dourado
    "navio": "#1E90FF",         # Azul Marinho
    "gravadora": "#BA55D3",     # Orquídea
    "escola": "#32CD32",        # Verde Lima
    "cidade": "#FF4500",        # Laranja avermelhado
    "pais": "#20B2AA",          # Verde Marinho
    "cantora": "#FF69B4",       # Rosa Choque
    "destinatario": "#FF4B4B",  # Vermelho Bosch
    "default": "#999999"        # Cinza
}

img_map = {
    "Envelope_Frente": "C067.1.envelope.jpg",
    "Envelope_Verso": "C067.1v.envelope.jpg",
    "2": "C067.2.jpg",
    "2v": "C067.2v.branco_e_3 (1).jpg",
    "3": "C067.4 (1).jpg", 
    "4": "C067.4v.branco_e_5 (1).jpg",
    "Partitura_Capa": "C067.6.partitura_Choro_em_Oitavas.Arnaldo_Rebello_1956.jpg",
    "Partitura_Pag1": "C067.6v.jpg",
    "Partitura_Pag2": "C067.7.jpg",
    "Partitura_Verso": "C067.7v.manuscrita_Arnaldo_Rebello.jpg"
}

# --- 2. FUNÇÕES AUXILIARES (Zona de Lógica) ---

# ADICIONADO: Função de Highlighting para a Transcrição
def destacar_entidades(texto):
    """Substitui termos chave por versões coloridas em HTML."""
    substituicoes = {
        "Eurico": cores_map["destinatario"],
        "Rio de Janeiro": cores_map["cidade"],
        "Brasil": cores_map["pais"],
        "Marialma": cores_map["cantora"],
        "Odeon": cores_map["gravadora"]
    }
    for termo, cor in substituicoes.items():
        html_span = f'<span style="background-color: {cor}44; border-bottom: 2px solid {cor}; padding: 0 2px;">{termo}</span>'
        texto = texto.replace(termo, html_span)
    return texto

def processar_tei_xml(xml_path):
    if not os.path.exists(xml_path): return None, None, None
    try:
        tree = etree.parse(xml_path)
        root = tree.getroot()

        meta = {
            "autor": root.xpath("//letHeading/author/text()")[0],
            "dest": root.xpath("//letHeading/addressee/text()")[0],
            "data": root.xpath("//letHeading/dateLet/text()")[0],
            "local": root.xpath("//letHeading/placeLet/text()")[0]
        }

        # ADICIONADO: Extração de Entidades COM TIPO para cores no grafo
        entidades_com_tipo = []
        for el in root.xpath("//nome | //cantora | //lugar | //titulo"):
            nome_texto = "".join(el.xpath(".//text()")).strip()
            tipo = el.get("tipo") if el.get("tipo") else el.tag
            if nome_texto and nome_texto not in [meta['autor'], "Eurico", "Thomi", "Tomí"]:
                entidades_com_tipo.append((nome_texto, tipo))

        folios = []
        sections = root.xpath("//text/carta/*")
        current_folio, current_text = "1", ""
        for element in sections:
            if element.tag == 'folio':
                if current_text: folios.append({"n": current_folio, "texto": current_text})
                current_folio = element.get("n")
                current_text = ""
            elif element.tag == 'p':
                current_text += "".join(element.xpath(".//text()")).replace("\n", " ") + "\n\n"
        folios.append({"n": current_folio, "texto": current_text})

        return meta, entidades_com_tipo, folios
    except Exception as e:
        st.error(f"Erro: {e}")
        return None, None, None

# --- 3. INTERFACE PRINCIPAL ---

st.title("🎼 Correspondência Eurico Tomaz Lima")
xml_path = "dados/correspondencia.xml"
meta, rede_nomes, folios = processar_tei_xml(xml_path)

# ADICIONADO: Filtros e Legenda na Sidebar
if meta:
    st.sidebar.header("🔍 Exploração de Dados")
    
    # 1. Filtro de Categorias
    todos_tipos = sorted(list(set([t for n, t in rede_nomes])))
    tipos_selecionados = st.sidebar.multiselect(
        "Filtrar por Categoria", 
        options=todos_tipos, 
        default=todos_tipos
    )
    
    # 2. Legenda de Cores
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎨 Legenda da Rede")
    for tipo in todos_tipos:
        cor = cores_map.get(tipo, cores_map["default"])
        st.sidebar.markdown(f'<span style="color:{cor}">●</span> {tipo.capitalize()}', unsafe_allow_html=True)
    
    # Filtrar a lista de nomes baseada na seleção
    rede_nomes_filtrada = [item for item in rede_nomes if item[1] in tipos_selecionados]

if meta:
    # MÉTRICAS
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Remetente", meta['autor'])
    c2.metric("Destinatário", meta['dest'])
    c3.metric("Data", meta['data'])
    c4.metric("Local", meta['local'])

    # ADICIONADO: Separador para o Código-Fonte XML (Sugestão 4)
    tab1, tab2, tab3 = st.tabs(["📊 Rede e Mapa", "📖 Manuscritos", "📄 Fonte XML"])

    with tab1:
        col_grafo, col_mapa = st.columns([2, 1])
        
        with col_grafo:
            st.subheader("Rede de Influência")
            G = nx.Graph()
            G.add_node(meta['autor'], color=cores_map["destinatario"], size=25)
            # ADICIONADO: Aplicação de cores dinâmicas nos nós (Sugestão 1)
            for nome, tipo in set(rede_nomes_filtrada):
                cor_no = cores_map.get(tipo, cores_map["default"])
                G.add_node(nome, color=cor_no, title=f"Categoria: {tipo}")
                G.add_edge(meta['autor'], nome)

            net = Network(height="400px", width="100%", bgcolor="#ffffff")
            net.from_nx(G)
            net.save_graph("temp.html")
            components.html(open("temp.html", 'r').read(), height=450)

        with col_mapa:
            # ADICIONADO: Mapa de Rota Rio-Porto (Sugestão 3)
            st.subheader("📍 Rota Postal")
            df_mapa = pd.DataFrame({
                'lat': [-22.9068, 41.1579],
                'lon': [-43.1729, -8.6291]
            })
            st.map(df_mapa)
            st.caption("Conexão Transatlântica: Rio de Janeiro ✈️ Porto")

    with tab2:
        # SECÇÃO ENVELOPE
        with st.expander("📬 Ver Envelope (Frente e Verso)"):
            ce1, ce2 = st.columns(2)
            ce1.image(f"imagens/{img_map['Envelope_Frente']}", caption="Frente")
            ce2.image(f"imagens/{img_map['Envelope_Verso']}", caption="Verso")

        # CONTEÚDO DA CARTA COM HIGHLIGHTING
        st.markdown("---")
        for f in folios:
            with st.expander(f"Folio {f['n']}", expanded=(f['n']=="2")):
                col_txt, col_img = st.columns(2)
                with col_txt:
                    # ADICIONADO: Texto com realce visual (Sugestão 2)
                    st.markdown(destacar_entidades(f['texto']), unsafe_allow_html=True)
                with col_img:
                    img_f = img_map.get(f['n'])
                    if img_f and os.path.exists(f"imagens/{img_f}"):
                        st.image(f"imagens/{img_f}")

        # SECÇÃO PARTITURA
        st.markdown("---")
        st.subheader("🎼 Material Musical")
        with st.expander("Ver Partitura: Chôro em Oitavas"):
            st.image("imagens/C067.6v_e_7.Partitura_completa_1955.jpg", use_container_width=True)

    with tab3:
        # ADICIONADO: Visualizador do código TEI (Sugestão 4)
        st.subheader("Arquivo Semântico (TEI-XML)")
        with open(xml_path, "r", encoding="utf-8") as f_xml:
            st.code(f_xml.read(), language="xml")
            
        # ADICIONADO: Botão de Download
    st.markdown("---")
    with open(xml_path, "rb") as file:
        st.download_button(
            label="💾 Descarregar Ficheiro TEI-XML",
            data=file,
            file_name="correspondencia_eurico_67.xml",
            mime="application/xml",
            help="Clique para baixar o arquivo original codificado em TEI."
        )

st.sidebar.caption("Curadoria Digital | Projeto Eurico Thomaz Lima")