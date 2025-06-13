# -*- coding: utf-8 -*-
import pandas as pd
import streamlit as st
import json
import os
from datetime import datetime

from database import get_connection
from utils.filtros import filtro_data, filtro_categorias, aplicar_filtros
from utils.formatacao import formatar_valor_monetario
from utils.ofx_reader import OFXReader
from utils.exception_handler import ExceptionHandler

# Configurações da página
st.set_page_config(
    page_title="Gerenciar Transações - Richness",
    page_icon="🏷️",
    layout="wide"
)

# Verificar autenticação
def verificar_autenticacao():
    if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
        st.error("🔐 Acesso negado. Faça login primeiro.")
        st.stop()

verificar_autenticacao()

# Constantes
CATEGORIAS_DISPONIVEIS = [
    "Alimentação",
    "Transporte", 
    "Saúde",
    "Educação",
    "Lazer",
    "Casa e Utilidades",
    "Vestuário",
    "Investimentos",
    "Transferências",
    "Salário",
    "Freelance",
    "Compras Online",
    "Combustível",
    "Farmácia",
    "Supermercado",
    "Restaurante",
    "Academia",
    "Streaming",
    "Telefone",
    "Internet",
    "Banco/Taxas",
    "Outros"
]

CACHE_CATEGORIAS_FILE = "cache_categorias_usuario.json"
CATEGORIAS_PERSONALIZADAS_FILE = "categorias_personalizadas.json"

def carregar_cache_categorias():
    """Carrega o cache de categorizações personalizadas do usuário"""
    if os.path.exists(CACHE_CATEGORIAS_FILE):
        try:
            with open(CACHE_CATEGORIAS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_cache_categorias(cache):
    """Salva o cache de categorizações personalizadas"""
    try:
        with open(CACHE_CATEGORIAS_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar categorizações: {e}")
        return False

def carregar_categorias_personalizadas():
    """Carrega as categorias personalizadas criadas pelo usuário"""
    if os.path.exists(CATEGORIAS_PERSONALIZADAS_FILE):
        try:
            with open(CATEGORIAS_PERSONALIZADAS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def salvar_categorias_personalizadas(categorias):
    """Salva as categorias personalizadas"""
    try:
        with open(CATEGORIAS_PERSONALIZADAS_FILE, 'w', encoding='utf-8') as f:
            json.dump(categorias, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar categorias personalizadas: {e}")
        return False

def get_todas_categorias():
    """Retorna todas as categorias disponíveis (padrão + personalizadas)"""
    categorias_personalizadas = carregar_categorias_personalizadas()
    todas_categorias = CATEGORIAS_DISPONIVEIS + categorias_personalizadas
    return sorted(list(set(todas_categorias)))

@st.cache_data(ttl=300)
def carregar_transacoes():
    """Carrega todas as transações disponíveis"""
    def _load_data():
        ofx_reader = OFXReader()
        
        # Carregar dados dos arquivos OFX
        df_extratos = ofx_reader.buscar_extratos()
        df_cartoes = ofx_reader.buscar_cartoes()
        
        # Combinar extratos e cartões
        df = pd.concat([df_extratos, df_cartoes], ignore_index=True) if not df_extratos.empty or not df_cartoes.empty else pd.DataFrame()
        
        if not df.empty:
            df["Data"] = pd.to_datetime(df["Data"])
            df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
            
            # Aplicar categorizações personalizadas do usuário
            cache = carregar_cache_categorias()
            
            def aplicar_categoria_personalizada(row):
                descricao_normalizada = row["Descrição"].lower().strip()
                if descricao_normalizada in cache:
                    return cache[descricao_normalizada]
                return row.get("Categoria", "Outros")
            
            df["Categoria"] = df.apply(aplicar_categoria_personalizada, axis=1)
        
        return df
    
    return ExceptionHandler.safe_execute(
        func=_load_data,
        error_handler=ExceptionHandler.handle_generic_error,
        default_return=pd.DataFrame()
    )

# Interface principal
st.title("🏷️ Gerenciar Transações")
st.markdown("**Corrija e personalize a categorização das suas transações**")

# Carregar dados
df = carregar_transacoes()

if df.empty:
    st.warning("📭 Nenhuma transação encontrada!")
    st.info("💡 Verifique se há arquivos OFX nas pastas `extratos/` e `faturas/`")
    st.stop()

# Métricas de resumo
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📊 Total de Transações", len(df))

with col2:
    cache = carregar_cache_categorias()
    st.metric("🏷️ Categorizações Personalizadas", len(cache))

with col3:
    receitas = len(df[df["Valor"] > 0])
    st.metric("📈 Receitas", receitas)

with col4:
    despesas = len(df[df["Valor"] < 0])
    st.metric("📉 Despesas", despesas)

# Seção de gerenciamento de categorias
st.subheader("🎨 Gerenciar Categorias")
with st.expander("➕ Criar Nova Categoria"):
    col1, col2 = st.columns([3, 1])
    
    with col1:
        nova_categoria = st.text_input(
            "Nome da nova categoria",
            placeholder="Ex: Pets, Doações, Hobby, etc.",
            help="Digite o nome da categoria que deseja criar"
        )
    
    with col2:
        st.write("")  # Espaçamento
        criar_categoria = st.button("✨ Criar", type="primary")
    
    if criar_categoria and nova_categoria:
        nova_categoria = nova_categoria.strip()
        
        # Validações
        if len(nova_categoria) < 2:
            st.error("❌ A categoria deve ter pelo menos 2 caracteres.")
        elif len(nova_categoria) > 30:
            st.error("❌ A categoria deve ter no máximo 30 caracteres.")
        elif nova_categoria in get_todas_categorias():
            st.warning("⚠️ Esta categoria já existe.")
        else:
            # Criar nova categoria
            categorias_personalizadas = carregar_categorias_personalizadas()
            categorias_personalizadas.append(nova_categoria)
            
            if salvar_categorias_personalizadas(categorias_personalizadas):
                st.success(f"✅ Categoria '{nova_categoria}' criada com sucesso!")
                st.rerun()
    
    # Mostrar categorias personalizadas existentes
    categorias_personalizadas = carregar_categorias_personalizadas()
    if categorias_personalizadas:
        st.markdown("**📋 Suas categorias personalizadas:**")
        
        for i, categoria in enumerate(categorias_personalizadas):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.text(f"• {categoria}")
            
            with col2:
                if st.button("🗑️", key=f"del_cat_{i}", help=f"Remover '{categoria}'"):
                    # Confirmar remoção
                    if st.button(f"⚠️ Confirmar remoção de '{categoria}'", key=f"confirm_del_{i}", type="secondary"):
                        categorias_personalizadas.remove(categoria)
                        salvar_categorias_personalizadas(categorias_personalizadas)
                        
                        # Também remover do cache de categorizações se existir
                        cache = carregar_cache_categorias()
                        cache_atualizado = {k: v for k, v in cache.items() if v != categoria}
                        if len(cache_atualizado) != len(cache):
                            salvar_cache_categorias(cache_atualizado)
                        
                        st.success(f"✅ Categoria '{categoria}' removida!")
                        st.rerun()

# Seção de filtros
st.subheader("🔍 Filtros")
col1, col2, col3 = st.columns(3)

with col1:
    data_inicio, data_fim = filtro_data(df)

with col2:
    # Atualizar o DataFrame com todas as categorias antes de aplicar o filtro
    df_com_todas_categorias = df.copy()
    categorias_selecionadas = st.multiselect(
        "Categorias",
        options=sorted(df_com_todas_categorias["Categoria"].unique()),
        default=None,
        help="Selecione uma ou mais categorias para filtrar"
    )

with col3:
    tipo_transacao = st.selectbox(
        "Tipo de Transação",
        options=["Todas", "Receitas", "Despesas"],
        help="Filtrar por tipo de transação"
    )

# Aplicar filtros
df_filtrado = aplicar_filtros(df, data_inicio, data_fim, categorias_selecionadas)

# Filtro adicional por tipo
if tipo_transacao == "Receitas":
    df_filtrado = df_filtrado[df_filtrado["Valor"] > 0]
elif tipo_transacao == "Despesas":
    df_filtrado = df_filtrado[df_filtrado["Valor"] < 0]

if df_filtrado.empty:
    st.warning("🔍 Nenhuma transação encontrada com os filtros aplicados.")
    st.stop()

# Seção de edição em lote
st.subheader("⚡ Edição em Lote")
with st.expander("📝 Alterar categoria de múltiplas transações"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_descricao = st.text_input(
            "Filtrar por descrição",
            placeholder="Ex: PIX, MERCADO, POSTO",
            help="Digite parte da descrição para filtrar transações similares"
        )
    
    with col2:
        categoria_lote = st.selectbox(
            "Nova categoria",
            options=get_todas_categorias(),
            key="categoria_lote"
        )
    
    with col3:
        st.write("")  # Espaçamento
        aplicar_lote = st.button("🔄 Aplicar em Lote", type="primary")
    
    if filtro_descricao:
        transacoes_similares = df_filtrado[
            df_filtrado["Descrição"].str.contains(filtro_descricao, case=False, na=False)
        ]
        
        if not transacoes_similares.empty:
            st.info(f"📊 {len(transacoes_similares)} transações encontradas com '{filtro_descricao}'")
            
            # Preview das transações que serão alteradas
            preview_df = transacoes_similares[["Data", "Descrição", "Categoria", "Valor"]].head(5)
            st.dataframe(preview_df, use_container_width=True)
            
            if len(transacoes_similares) > 5:
                st.caption(f"... e mais {len(transacoes_similares) - 5} transações")
            
            if aplicar_lote:
                cache = carregar_cache_categorias()
                alteracoes = 0
                
                for _, row in transacoes_similares.iterrows():
                    descricao_normalizada = row["Descrição"].lower().strip()
                    cache[descricao_normalizada] = categoria_lote
                    alteracoes += 1
                
                if salvar_cache_categorias(cache):
                    st.success(f"✅ {alteracoes} transações categorizadas como '{categoria_lote}'!")
                    st.cache_data.clear()  # Limpar cache para recarregar dados
                    st.rerun()
        else:
            st.warning("❌ Nenhuma transação encontrada com essa descrição.")

# Seção de edição individual
st.subheader("📋 Transações")

# Inicializar estado de sessão para mudanças pendentes
if 'mudancas_pendentes' not in st.session_state:
    st.session_state.mudancas_pendentes = {}

# Preparar dados para exibição
df_display = df_filtrado.copy()
df_display = df_display.sort_values("Data", ascending=False)

# Paginação
itens_por_pagina = 20
total_paginas = len(df_display) // itens_por_pagina + (1 if len(df_display) % itens_por_pagina > 0 else 0)

if total_paginas > 1:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pagina_atual = st.selectbox(
            "Página",
            options=list(range(1, total_paginas + 1)),
            format_func=lambda x: f"Página {x} de {total_paginas}"
        )
else:
    pagina_atual = 1

# Controles de edição em lote
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    mudancas_count = len(st.session_state.mudancas_pendentes)
    st.metric("📝 Mudanças Pendentes", mudancas_count)

with col2:
    if mudancas_count > 0:
        if st.button("💾 Salvar Todas", type="primary", help=f"Salvar {mudancas_count} alterações"):
            cache = carregar_cache_categorias()
            
            # Aplicar todas as mudanças pendentes
            for descricao_norm, nova_categoria in st.session_state.mudancas_pendentes.items():
                cache[descricao_norm] = nova_categoria
            
            if salvar_cache_categorias(cache):
                st.success(f"✅ {mudancas_count} alterações salvas com sucesso!")
                st.session_state.mudancas_pendentes = {}  # Limpar mudanças pendentes
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("❌ Erro ao salvar alterações")

with col3:
    if mudancas_count > 0:
        if st.button("🗑️ Descartar Todas", help="Descartar todas as mudanças pendentes"):
            st.session_state.mudancas_pendentes = {}
            st.rerun()

with col4:
    modo_edicao = st.toggle("⚡ Modo Edição em Lote", help="Ativar para fazer múltiplas edições antes de salvar")

# Informação adicional sobre o modo de edição ativo
if modo_edicao:
    st.info("🔄 **Modo Edição em Lote ativado**: As alterações serão acumuladas e podem ser salvas todas de uma vez.")
else:
    st.info("💾 **Modo Individual ativado**: Cada alteração será salva imediatamente ao clicar no botão de salvar.")

st.markdown("---")

# Calcular índices da página
inicio = (pagina_atual - 1) * itens_por_pagina
fim = inicio + itens_por_pagina
df_pagina = df_display.iloc[inicio:fim]

# Exibir transações com opção de edição
for idx, row in df_pagina.iterrows():
    with st.container():
        col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 1])
        
        with col1:
            st.text(row["Data"].strftime("%d/%m/%Y"))
        
        with col2:
            st.text(row["Descrição"][:50] + ("..." if len(row["Descrição"]) > 50 else ""))
        
        with col3:
            valor_formatado = formatar_valor_monetario(row["Valor"])
            cor = "🟢" if row["Valor"] > 0 else "🔴"
            st.text(f"{cor} {valor_formatado}")
        
        with col4:
            categoria_atual = row["Categoria"]
            todas_categorias = get_todas_categorias()
            descricao_normalizada = row["Descrição"].lower().strip()
            
            # Verificar se há mudança pendente para esta transação
            categoria_exibida = categoria_atual
            if descricao_normalizada in st.session_state.mudancas_pendentes:
                categoria_exibida = st.session_state.mudancas_pendentes[descricao_normalizada]
            
            nova_categoria = st.selectbox(
                "Categoria",
                options=todas_categorias,
                index=todas_categorias.index(categoria_exibida) if categoria_exibida in todas_categorias else 0,
                key=f"cat_{idx}",
                label_visibility="collapsed"
            )
            
            # Detectar mudanças
            if nova_categoria != categoria_atual:
                if modo_edicao:
                    # Modo lote: adicionar à lista de mudanças pendentes
                    st.session_state.mudancas_pendentes[descricao_normalizada] = nova_categoria
                    st.caption("� Mudança pendente")
                else:
                    # Modo individual: manter comportamento original
                    st.session_state.mudancas_pendentes.pop(descricao_normalizada, None)  # Remove das pendentes se existir
            else:
                # Se voltou à categoria original, remover das pendentes
                st.session_state.mudancas_pendentes.pop(descricao_normalizada, None)
        
        with col5:
            if not modo_edicao and nova_categoria != categoria_atual:
                # Modo individual: salvar imediatamente
                if st.button("💾", key=f"save_{idx}", help="Salvar alteração"):
                    cache = carregar_cache_categorias()
                    cache[descricao_normalizada] = nova_categoria
                    
                    if salvar_cache_categorias(cache):
                        st.success("✅ Salvo!")
                        st.cache_data.clear()
                        st.rerun()
            elif modo_edicao and descricao_normalizada in st.session_state.mudancas_pendentes:
                # Modo lote: mostrar indicador de mudança pendente
                st.markdown("🔄")
        
        st.divider()

# Estatísticas da página
if total_paginas > 1:
    st.caption(f"Exibindo {len(df_pagina)} de {len(df_display)} transações (Página {pagina_atual} de {total_paginas})")

# Mostrar detalhes das mudanças pendentes
if st.session_state.mudancas_pendentes:
    with st.expander(f"📋 Detalhes das Mudanças Pendentes ({len(st.session_state.mudancas_pendentes)})"):
        st.markdown("**Transações que serão alteradas:**")
        
        for i, (descricao_norm, nova_categoria) in enumerate(st.session_state.mudancas_pendentes.items(), 1):
            # Encontrar a transação original para mostrar mais detalhes
            transacao_original = df_filtrado[df_filtrado["Descrição"].str.lower().str.strip() == descricao_norm]
            
            if not transacao_original.empty:
                row_original = transacao_original.iloc[0]
                col1, col2, col3 = st.columns([3, 2, 2])
                
                with col1:
                    st.text(f"{i}. {row_original['Descrição'][:40]}...")
                
                with col2:
                    st.text(f"{row_original['Categoria']} → {nova_categoria}")
                
                with col3:
                    if st.button("❌", key=f"remove_pending_{i}", help="Remover desta mudança"):
                        st.session_state.mudancas_pendentes.pop(descricao_norm)
                        st.rerun()
        
        # Botões de ação na seção de detalhes
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Salvar Todas as Mudanças", type="primary", key="save_all_details"):
                cache = carregar_cache_categorias()
                mudancas_count = len(st.session_state.mudancas_pendentes)
                
                for descricao_norm, nova_categoria in st.session_state.mudancas_pendentes.items():
                    cache[descricao_norm] = nova_categoria
                
                if salvar_cache_categorias(cache):
                    st.success(f"✅ {mudancas_count} alterações salvas com sucesso!")
                    st.session_state.mudancas_pendentes = {}
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar alterações")
        
        with col2:
            if st.button("🗑️ Descartar Todas", key="discard_all_details"):
                st.session_state.mudancas_pendentes = {}
                st.rerun()

# Seção de gerenciamento do cache
st.subheader("🔧 Gerenciamento")
with st.expander("⚙️ Opções Avançadas"):
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Limpar Todas as Categorizações", type="secondary"):
            if st.button("⚠️ Confirmar Limpeza", type="secondary"):
                if os.path.exists(CACHE_CATEGORIAS_FILE):
                    os.remove(CACHE_CATEGORIAS_FILE)
                    st.success("✅ Todas as categorizações personalizadas foram removidas!")
                    st.cache_data.clear()
                    st.rerun()
    
    with col2:
        cache = carregar_cache_categorias()
        if cache:
            # Exportar categorizações
            cache_json = json.dumps(cache, indent=2, ensure_ascii=False)
            st.download_button(
                "📥 Exportar Categorizações",
                data=cache_json,
                file_name=f"categorizacoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

# Informações de ajuda
with st.expander("ℹ️ Como usar esta página"):
    st.markdown("""
    ### 🎯 Objetivo
    Esta página permite corrigir e personalizar a categorização automática das suas transações.
    
    ### 🔧 Funcionalidades
    
    **🎨 Criar Categorias Personalizadas:**
    - Crie suas próprias categorias (Ex: Pets, Doações, Hobby)
    - Gerencie e remova categorias criadas
    - Use em qualquer transação após criadas
    
    **⚡ Edição em Lote (NOVO):**
    - Ative o "Modo Edição em Lote" para fazer múltiplas alterações
    - Faça quantas mudanças quiser sem salvar imediatamente
    - Visualize todas as mudanças pendentes antes de confirmar
    - Salve todas de uma vez ou descarte se não estiver satisfeito
    
    **📝 Edição Individual:**
    - Altere a categoria de cada transação usando o menu suspenso
    - No modo individual, mudanças são salvas imediatamente
    - Clique no botão 💾 para confirmar cada alteração
    
    **🔍 Edição por Descrição Similar:**
    - Digite parte da descrição para encontrar transações similares
    - Aplique uma nova categoria a todas elas de uma vez
    - Use categorias padrão ou suas categorias personalizadas
    
    **🔍 Filtros:**
    - Use os filtros para encontrar transações específicas
    - Filtre por data, categoria ou tipo (receita/despesa)
    
    ### 💡 Dicas para Edição em Lote
    
    **⚡ Modo Edição em Lote (Recomendado):**
    1. Ative o toggle "Modo Edição em Lote"
    2. Navegue pelas páginas fazendo as alterações desejadas
    3. Acompanhe o contador de "Mudanças Pendentes"
    4. Revise os detalhes das mudanças na seção expandível
    5. Clique em "Salvar Todas" quando estiver satisfeito
    
    **📋 Modo Individual:**
    - Ideal para correções pontuais
    - Cada mudança é salva imediatamente
    - Não acumula mudanças pendentes
    
    ### 🏷️ Exemplos de Categorias Personalizadas
    - **Pets**: Ração, veterinário, petshop
    - **Doações**: Instituições de caridade, causas sociais
    - **Hobby**: Coleções, artesanato, instrumentos musicais
    - **Negócios**: Despesas de trabalho freelance
    - **Família**: Presentes, eventos familiares
    
    ### ⚠️ Importante
    - **Mudanças pendentes** são perdidas se você sair da página sem salvar
    - **Filtros aplicados** não afetam as mudanças pendentes de outras páginas
    - **Categorias personalizadas** são aplicadas em todo o sistema automaticamente
    """)
