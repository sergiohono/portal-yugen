import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import os

def format_currency(value):
    return f"R$ {value:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

def main(engine=None, uid=None, page=None):
    if engine is None and uid is None:
        st.set_page_config(page_title='Portal DRE TeutoMaq', layout='wide')
        # Se rodando standalone (fora do portal), mostra opções na sidebar
        page = st.sidebar.selectbox("Selecione a Página", [
            "Dashboard Geral",
            "Análise de Faturamento",
            "DRE Trimestral",
            "DRE Completo",
            "Relatório Executivo"
        ])
    elif page is None:
        # Se chamado pelo app.py e não especificaram página, assume default
        page = "Dashboard Geral"

    # Escolhe qual página renderizar
    if page == "Dashboard Geral":
        dashboard_geral()
    elif page == "Análise de Faturamento":
        faturamento_page()
    elif page == "DRE Trimestral":
        base_path = os.path.join(os.path.dirname(__file__), 'data')
        path_apagar = f'{base_path}/contasapagar2024.xlsx'
        path_areceber = f'{base_path}/contasareceber2024.xlsx'
        path_classif = f'{base_path}/Classificacao_Custos_Variavel_x_Fixo.xlsx'

        xls_ap = pd.ExcelFile(path_apagar)
        cpa_raw = pd.concat([xls_ap.parse(sheet) for sheet in ['teutocar', 'teutomaq']], ignore_index=True)
        cpa_raw['DataPagamento'] = pd.to_datetime(cpa_raw['Pagto'], dayfirst=True, errors='coerce')

        classif_df = pd.read_excel(path_classif, sheet_name=0)
        map_df = pd.read_excel(path_classif, sheet_name=1)
        cpa_raw['CategoriaLimpa'] = cpa_raw['Categoria'].astype(str).str.replace(r'^\d+\s*', '', regex=True)
        cpa = cpa_raw.merge(map_df.rename(columns={'contasantigas': 'CategoriaLimpa'}), on='CategoriaLimpa', how='left')
        cpa['ContaPadrao'] = cpa['contasnovas'].combine_first(cpa['CategoriaLimpa'])
        cpa = cpa.merge(classif_df.rename(columns={'Conta': 'ContaPadrao'}), on='ContaPadrao', how='left')

        xls_cr = pd.ExcelFile(path_areceber)
        cre = pd.concat([xls_cr.parse(sheet) for sheet in ['teutocar', 'teutomaq']], ignore_index=True)
        cre['DataPagamento'] = pd.to_datetime(cre['Pagto.'], dayfirst=True, errors='coerce')

        analise_gastos_page(cpa, cre)
    elif page == "DRE Completo":
        dre_completo_page()
    elif page == "Relatório Executivo":
        relatorio_executivo_page()



def dashboard_geral():
    st.markdown("<h2 style='font-size:28px;'>Dashboard Geral</h2>", unsafe_allow_html=True)
    base_path = os.path.join(os.path.dirname(__file__), 'data')
    path_apagar = f'{base_path}/contasapagar2024.xlsx'
    path_areceber = f'{base_path}/contasareceber2024.xlsx'
    path_classif = f'{base_path}/Classificacao_Custos_Variavel_x_Fixo.xlsx'

    meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    col_titulo, col_filtro = st.columns([3, 1])
    with col_filtro:
        mes_sel = st.selectbox("Selecione o Mês:", ["Anual"] + meses, index=0)

    xls_ap = pd.ExcelFile(path_apagar)
    cpa_raw = pd.concat([xls_ap.parse(sheet) for sheet in ['teutocar', 'teutomaq']], ignore_index=True)
    cpa_raw['DataPagamento'] = pd.to_datetime(cpa_raw['Pagto'], dayfirst=True, errors='coerce')

    classif_df = pd.read_excel(path_classif, sheet_name=0)
    map_df = pd.read_excel(path_classif, sheet_name=1)
    cpa_raw['CategoriaLimpa'] = cpa_raw['Categoria'].astype(str).str.replace(r'^\d+\s*', '', regex=True)
    cpa = cpa_raw.merge(map_df.rename(columns={'contasantigas': 'CategoriaLimpa'}), on='CategoriaLimpa', how='left')
    cpa['ContaPadrao'] = cpa['contasnovas'].combine_first(cpa['CategoriaLimpa'])
    cpa = cpa.merge(classif_df.rename(columns={'Conta': 'ContaPadrao'}), on='ContaPadrao', how='left')

    if mes_sel != "Anual":
        cpa_filtered = cpa[cpa['DataPagamento'].dt.month == meses.index(mes_sel) + 1]
    else:
        cpa_filtered = cpa

    xls_cr = pd.ExcelFile(path_areceber)
    cre = pd.concat([xls_cr.parse(sheet) for sheet in ['teutocar', 'teutomaq']], ignore_index=True)
    cre['DataPagamento'] = pd.to_datetime(cre['Pagto.'], dayfirst=True, errors='coerce')

    if mes_sel != "Anual":
        cre_filtered = cre[cre['DataPagamento'].dt.month == meses.index(mes_sel) + 1]
    else:
        cre_filtered = cre

    # Receita Total (apenas valores positivos)
    receitas_total = cre_filtered[cre_filtered['Valor'] > 0]['Valor'].sum()

    # Deduções: negativos + positivos classificados como desconto/devolução
    deducoes_neg = abs(cre_filtered[(cre_filtered['Valor'] < 0) &
                                    (cre_filtered['Categoria'].str.contains('desconto|devolução', case=False, na=False))]['Valor'].sum())

    deducoes_pos = cre_filtered[(cre_filtered['Valor'] > 0) &
                                (cre_filtered['Categoria'].str.contains('desconto|devolução', case=False, na=False))]['Valor'].sum()

    deducoes = deducoes_neg + deducoes_pos

    # Receita Líquida
    receita_liquida = receitas_total - deducoes

    # Excluir transferências
    cpa_no_transf = cpa_filtered[~cpa_filtered['ContaPadrao'].str.contains('transferência entre contas', case=False, na=False)]

    # Folha
    folha_total = cpa_no_transf[cpa_no_transf['Grupo'].str.lower() == 'despesas com folha']['Valor'].sum()
    folha_var = folha_total * 0.6
    folha_fix = folha_total * 0.4

    # Despesas variáveis (sem impostos e financeiras)
    cpa_desp_var = cpa_no_transf[
        (cpa_no_transf['Classificação'].str.lower() == 'variável') &
        (~cpa_no_transf['Grupo'].str.lower().isin(['imposto', 'despesas financeiras']))
    ]
    desp_var = cpa_desp_var['Valor'].sum() + folha_var

    # Impostos
    impostos = cpa_no_transf[cpa_no_transf['Grupo'].str.lower() == 'imposto']['Valor'].sum()
    simples_nacional = cpa_no_transf[cpa_no_transf['ContaPadrao'].str.lower().str.contains('simples nacional', na=False)]['Valor'].sum()
    total_impostos = impostos + simples_nacional

    # Lucro Bruto já deduzindo impostos antes
    lucro_bruto = receita_liquida - desp_var - total_impostos

    # Despesas fixas (sem impostos e financeiras)
    cpa_desp_fix = cpa_no_transf[
        (cpa_no_transf['Classificação'].str.lower() == 'fixo') &
        (~cpa_no_transf['Grupo'].str.lower().isin(['imposto', 'despesas financeiras']))
    ]
    desp_fix = cpa_desp_fix['Valor'].sum() + folha_fix

    # Despesas financeiras
    despesas_financeiras = cpa_no_transf[cpa_no_transf['Grupo'].str.lower() == 'despesas financeiras']['Valor'].sum()

    # EBITDA e Lucro Líquido
    ebitda = lucro_bruto - desp_fix
    gasto_total = desp_var + desp_fix + despesas_financeiras + total_impostos
    lucro_liquido = receita_liquida - gasto_total

    # Margem de Contribuição corrigida (sobre receita líquida)
    margem_contribuicao_perc = ((lucro_bruto / receita_liquida) * 100) if receita_liquida else 0
    ponto_equilibrio = desp_fix / (margem_contribuicao_perc / 100) if margem_contribuicao_perc else 0


    st.markdown("---")
    # KPIs
    st.markdown("### Indicadores Chave")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Receitas Total", format_currency(receitas_total))
    col2.metric("Despesas Totais", format_currency(gasto_total))
    col3.metric("Margem de Contribuição", f"{margem_contribuicao_perc:.2f}%")
    col4.metric("Lucro Líquido", format_currency(lucro_liquido))

    st.markdown("---")

    col_peq1, col_peq2, _, _ = st.columns(4)
    col_peq1.metric("Ponto de Equilíbrio", format_currency(ponto_equilibrio))
    col_peq2.metric("Receita - PE", f"{(receitas_total - ponto_equilibrio):,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
    # Linha estética após Indicadores Chave
    st.markdown("---")

    # Gráfico anual
    st.markdown("### Evolução Mensal de Receita e Lucro Líquido (Anual)")

    lucro_liquido_mensal = []
    receita_liquida_mensal = []

    for i, mes in enumerate(meses, start=1):
        cre_mes = cre[cre['DataPagamento'].dt.month == i]
        cpa_mes = cpa[cpa['DataPagamento'].dt.month == i]

        receita_total = cre_mes[cre_mes['Valor'] > 0]['Valor'].sum()
        deducoes_neg = abs(cre_mes[(cre_mes['Valor'] < 0) & cre_mes['Categoria'].str.contains('desconto|devolução', case=False, na=False)]['Valor'].sum())
        deducoes_pos = cre_mes[(cre_mes['Valor'] > 0) & cre_mes['Categoria'].str.contains('desconto|devolução', case=False, na=False)]['Valor'].sum()
        deducoes = deducoes_neg + deducoes_pos
        receita_liquida = receita_total - deducoes
        receita_liquida_mensal.append(receita_liquida)

        folha = cpa_mes[cpa_mes['Grupo'].str.lower() == 'despesas com folha']['Valor'].sum()
        folha_var = folha * 0.6
        folha_fix = folha * 0.4

        cpa_var = cpa_mes[(cpa_mes['Classificação'].str.lower() == 'variável') & (~cpa_mes['Grupo'].str.lower().isin(['imposto', 'despesas financeiras']))]
        cpa_fix = cpa_mes[(cpa_mes['Classificação'].str.lower() == 'fixo') & (~cpa_mes['Grupo'].str.lower().isin(['imposto', 'despesas financeiras']))]

        desp_var = cpa_var['Valor'].sum() + folha_var
        desp_fix = cpa_fix['Valor'].sum() + folha_fix

        despesas_financeiras = cpa_mes[cpa_mes['Grupo'].str.lower() == 'despesas financeiras']['Valor'].sum()
        impostos = cpa_mes[cpa_mes['Grupo'].str.lower() == 'imposto']['Valor'].sum()
        simples_nacional = cpa_mes[cpa_mes['ContaPadrao'].str.lower().str.contains('simples nacional', na=False)]['Valor'].sum()
        total_impostos = impostos + simples_nacional

        lucro_liquido = receita_liquida - (desp_var + desp_fix + despesas_financeiras + total_impostos)
        lucro_liquido_mensal.append(lucro_liquido)

    from datetime import datetime
    mes_atual_index = datetime.today().month - 1  # 0-based

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=meses,
        y=receita_liquida_mensal,
        mode='lines+markers+text',
        name='Receita Líquida',
        line=dict(color='blue'),
        text=[f"R$ {v:,.0f}".replace(",", "v").replace(".", ",").replace("v", ".") for v in receita_liquida_mensal],
        textposition="top center"
    ))
    fig.add_trace(go.Scatter(
        x=meses,
        y=lucro_liquido_mensal,
        mode='lines+markers+text',
        name='Lucro Líquido',
        line=dict(color='green'),
        marker=dict(color=['green' if val >= 0 else 'red' for val in lucro_liquido_mensal]),
        text=[f"R$ {v:,.0f}".replace(",", "v").replace(".", ",").replace("v", ".") for v in lucro_liquido_mensal],
        textposition="bottom center"
    ))
    fig.add_vrect(
        x0=meses[mes_atual_index], x1=meses[mes_atual_index],
        line_width=0, fillcolor="gray", opacity=0.2,
        annotation_text="Mês Atual", annotation_position="top left"
    )
    fig.update_layout(
        template='plotly_dark',
        height=420,
        title='Evolução Mensal de Receita Líquida e Lucro Líquido (Anual)',
        xaxis_title="Mês",
        yaxis_title="Valor (R$)"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Linha estética após gráfico
    st.markdown("---")

    # Tabela: Top 5 Centros de Custos com Maiores Gastos
    st.markdown("### Top 5 Centros de Custos com Maiores Gastos")

    top5_centros = (
        cpa_filtered.groupby("Setor Cons.")["Valor"]
        .sum()
        .nlargest(5)
        .reset_index()
        .rename(columns={"Setor Cons.": "Centro de Custo", "Valor": "Valor (R$)"})
    )

    top5_centros.index = top5_centros.index + 1  # índice começa em 1
    top5_centros["Valor (R$)"] = top5_centros["Valor (R$)"].apply(format_currency)

    st.dataframe(top5_centros.style.set_properties(**{
        'text-align': 'left'
    }), use_container_width=True, hide_index=False)


def faturamento_page():
    st.markdown("<h2 style='font-size:28px;'>Análise de Faturamento</h2>", unsafe_allow_html=True)
    base_path = os.path.join(os.path.dirname(__file__), 'data')
    path_faturamento = f'{base_path}/faturamento2024.xlsx'
    meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho',
             'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    col_titulo, col_filtro = st.columns([3, 1])
    with col_filtro:
        mes_sel = st.selectbox("Selecione o Mês:", ["Anual"] + meses, index=0)

    xls_fat = pd.ExcelFile(path_faturamento)
    fat = pd.concat([xls_fat.parse(sheet) for sheet in xls_fat.sheet_names], ignore_index=True)
    fat.columns = [str(c).strip() for c in fat.columns]

    if mes_sel == "Anual":
        fat_mes = fat.copy()
        fat_mes['TotalCliente'] = fat[meses].sum(axis=1)
    else:
        fat_mes = fat[fat[mes_sel] > 0].copy()
        fat_mes['TotalCliente'] = fat_mes[mes_sel]

    faturamento_total = fat_mes['TotalCliente'].sum()
    num_vendas = fat_mes.shape[0]
    num_clientes = fat_mes['Cliente'].nunique()
    ticket_medio_venda = faturamento_total / num_vendas if num_vendas else 0
    ticket_medio_cliente = faturamento_total / num_clientes if num_clientes else 0

    melhor_vendedor = fat_mes.groupby('Vendedor')['TotalCliente'].sum().idxmax()
    melhor_vendedor_valor = fat_mes.groupby('Vendedor')['TotalCliente'].sum().max()
    melhor_cliente = fat_mes.groupby('Cliente')['TotalCliente'].sum().idxmax()
    melhor_cliente_valor = fat_mes.groupby('Cliente')['TotalCliente'].sum().max()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Faturamento Total", format_currency(faturamento_total))
    col2.metric("Nº de Vendas", num_vendas)
    col3.metric("Ticket Médio/Venda", format_currency(ticket_medio_venda))
    col4.metric("Ticket Médio/Cliente", format_currency(ticket_medio_cliente))

    col1, col2 = st.columns(2)
    col1.metric("Melhor Vendedor", melhor_vendedor, format_currency(melhor_vendedor_valor))
    col2.metric("Melhor Cliente", melhor_cliente, format_currency(melhor_cliente_valor))

    # Gráficos de barras para Top 5 Vendedores e Clientes
    col_vend, col_cli = st.columns([1, 1])
    with col_vend:
        st.markdown("### Top 5 Vendedores")
        top5_vendedores = fat_mes.groupby('Vendedor')['TotalCliente'].sum().nlargest(5)
        fig_vend = go.Figure(go.Bar(x=top5_vendedores.values, y=top5_vendedores.index,
                                    orientation='h', marker_color='purple'))
        fig_vend.update_layout(template='plotly_dark', height=300, title="Top 5 Vendedores")
        st.plotly_chart(fig_vend, use_container_width=True)

    with col_cli:
        st.markdown("### Top 5 Clientes")
        top5_clientes = fat_mes.groupby('Cliente')['TotalCliente'].sum().nlargest(5)
        fig_cli = go.Figure(go.Bar(x=top5_clientes.values, y=top5_clientes.index,
                                   orientation='h', marker_color='orange'))
        fig_cli.update_layout(template='plotly_dark', height=300, title="Top 5 Clientes")
        st.plotly_chart(fig_cli, use_container_width=True)

    st.markdown("### Evolução Mensal do Faturamento")
    evolucao_mensal = fat[meses].sum()
    fig = go.Figure(go.Scatter(x=meses, y=evolucao_mensal, mode='lines+markers', line_color='blue'))
    fig.update_layout(template='plotly_dark', height=400)
    st.plotly_chart(fig, use_container_width=True)


def analise_gastos_page(df_cpa, df_cre):
    st.markdown("<h2 style='font-size:28px;'>DRE Trimestral 2024</h2>", unsafe_allow_html=True)

    meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    col_filtro, _ = st.columns([1, 3])
    mes_nome = col_filtro.selectbox("Selecione o Mês:", meses[1:11], index=0)  # fevereiro a novembro
    mes_index = meses.index(mes_nome) + 1
    mes_ant = ((mes_index - 2) % 12) + 1
    mes_pos = (mes_index % 12) + 1

    simbolos = ["+", "-", "=", "-", "-", "=", "-", "=", "-", "="]
    itens = [
        "Receita Total", "Deduções", "Receita Líquida",
        "Impostos", "Custos Variáveis", "Lucro Bruto",
        "Custos Fixos", "EBITDA",
        "Despesas Financeiras", "Lucro Líquido"
    ]

    def calcular_kpis(mes=None):
        if mes:
            cpa = df_cpa[df_cpa['DataPagamento'].dt.month == mes]
            cre = df_cre[df_cre['DataPagamento'].dt.month == mes]
        else:
            cpa = df_cpa.copy()
            cre = df_cre.copy()

        receitas_total = cre[cre['Valor'] > 0]['Valor'].sum()
        deducoes = cre[cre['Categoria'].str.contains('desconto|devolução', case=False, na=False)]['Valor'].abs().sum()
        receita_liquida = receitas_total - deducoes

        folha = cpa[cpa['Grupo'].str.lower() == 'despesas com folha']['Valor'].sum()
        folha_var = folha * 0.6
        folha_fix = folha * 0.4

        cpa_var = cpa[(cpa['Classificação'].str.lower() == 'variável') &
                      (~cpa['Grupo'].str.lower().isin(['imposto', 'despesas financeiras']))]
        cpa_fix = cpa[(cpa['Classificação'].str.lower() == 'fixo') &
                      (~cpa['Grupo'].str.lower().isin(['imposto', 'despesas financeiras']))]

        desp_var = cpa_var['Valor'].sum() + folha_var
        desp_fix = cpa_fix['Valor'].sum() + folha_fix
        impostos = cpa[cpa['Grupo'].str.lower() == 'imposto']['Valor'].sum() + \
                   cpa[cpa['ContaPadrao'].str.lower().str.contains('simples nacional', na=False)]['Valor'].sum()
        despesas_financeiras = cpa[cpa['Grupo'].str.lower() == 'despesas financeiras']['Valor'].sum()

        lucro_bruto = receita_liquida - impostos - desp_var
        ebitda = lucro_bruto - desp_fix
        lucro_liquido = receita_liquida - (impostos + desp_var + desp_fix + despesas_financeiras)

        return {
            "Receita Total": receitas_total,
            "Deduções": deducoes,
            "Receita Líquida": receita_liquida,
            "Impostos": impostos,
            "Custos Variáveis": desp_var,
            "Lucro Bruto": lucro_bruto,
            "Custos Fixos": desp_fix,
            "EBITDA": ebitda,
            "Despesas Financeiras": despesas_financeiras,
            "Lucro Líquido": lucro_liquido
        }

    def montar_df(kpis):
        valores = [
            kpis["Receita Total"],
            kpis["Deduções"],
            kpis["Receita Líquida"],
            kpis["Impostos"],
            kpis["Custos Variáveis"],
            kpis["Lucro Bruto"],
            kpis["Custos Fixos"],
            kpis["EBITDA"],
            kpis["Despesas Financeiras"],
            kpis["Lucro Líquido"]
        ]

        df = pd.DataFrame({
            " ": simbolos,
            "Indicador": itens,
            "Valor": [format_currency(v) for v in valores]
        })
        return df

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.2])
    with col1:
        st.markdown(f"**DRE ({meses[mes_ant - 1]})**")
        st.dataframe(montar_df(calcular_kpis(mes_ant)), height=410, use_container_width=True, hide_index=True)

    with col2:
        st.markdown(f"**DRE ({meses[mes_index - 1]})**")
        st.dataframe(montar_df(calcular_kpis(mes_index)), height=410, use_container_width=True, hide_index=True)

    with col3:
        st.markdown(f"**DRE ({meses[mes_pos - 1]})**")
        st.dataframe(montar_df(calcular_kpis(mes_pos)), height=410, use_container_width=True, hide_index=True)

    with col4:
        st.markdown("**DRE (Anual)**")
        st.dataframe(montar_df(calcular_kpis(None)), height=410, use_container_width=True, hide_index=True)


def dre_completo_page():
    st.markdown("<h2 style='font-size:28px;'>DRE Completo</h2>", unsafe_allow_html=True)
    base_path = os.path.join(os.path.dirname(__file__), 'data')
    path_apagar = f'{base_path}/contasapagar2024.xlsx'
    path_areceber = f'{base_path}/contasareceber2024.xlsx'
    path_classif = f'{base_path}/Classificacao_Custos_Variavel_x_Fixo.xlsx'

    meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    # === Leitura e preparação dos dados ===
    xls_ap = pd.ExcelFile(path_apagar)
    cpa_raw = pd.concat([xls_ap.parse(sheet) for sheet in ['teutocar', 'teutomaq']], ignore_index=True)
    cpa_raw['DataPagamento'] = pd.to_datetime(cpa_raw['Pagto'], dayfirst=True, errors='coerce')

    classif_df = pd.read_excel(path_classif, sheet_name=0)
    map_df = pd.read_excel(path_classif, sheet_name=1)
    cpa_raw['CategoriaLimpa'] = cpa_raw['Categoria'].astype(str).str.replace(r'^\d+\s*', '', regex=True)
    cpa = cpa_raw.merge(map_df.rename(columns={'contasantigas': 'CategoriaLimpa'}), on='CategoriaLimpa', how='left')
    cpa['ContaPadrao'] = cpa['contasnovas'].combine_first(cpa['CategoriaLimpa'])
    cpa = cpa.merge(classif_df.rename(columns={'Conta': 'ContaPadrao'}), on='ContaPadrao', how='left')

    xls_cr = pd.ExcelFile(path_areceber)
    cre = pd.concat([xls_cr.parse(sheet) for sheet in ['teutocar', 'teutomaq']], ignore_index=True)
    cre['DataPagamento'] = pd.to_datetime(cre['Pagto.'], dayfirst=True, errors='coerce')

    dre_data = []

    for i, mes in enumerate(meses, start=1):
        receita_total = cre[(cre['DataPagamento'].dt.month == i) & (cre['Valor'] > 0)]['Valor'].sum()

        deducoes_neg = abs(cre[(cre['DataPagamento'].dt.month == i) &
                               (cre['Valor'] < 0) &
                               (cre['Categoria'].str.contains('desconto|devolução', case=False, na=False))]['Valor'].sum())

        deducoes_pos = cre[(cre['DataPagamento'].dt.month == i) &
                           (cre['Valor'] > 0) &
                           (cre['Categoria'].str.contains('desconto|devolução', case=False, na=False))]['Valor'].sum()

        deducoes = deducoes_neg + deducoes_pos
        receita_liquida = receita_total - deducoes

        cpa_mes = cpa[cpa['DataPagamento'].dt.month == i]
        folha_mes = cpa_mes[cpa_mes['Grupo'].str.lower() == 'despesas com folha']['Valor'].sum()
        folha_var_mes = folha_mes * 0.6
        folha_fix_mes = folha_mes * 0.4

        cpa_desp_var_mes = cpa_mes[(cpa_mes['Classificação'].str.lower() == 'variável') &
                                   (~cpa_mes['Grupo'].str.lower().isin(['imposto', 'despesas financeiras']))]['Valor'].sum()
        desp_var_mes = cpa_desp_var_mes + folha_var_mes

        cpa_desp_fix_mes = cpa_mes[(cpa_mes['Classificação'].str.lower() == 'fixo') &
                                   (~cpa_mes['Grupo'].str.lower().isin(['imposto', 'despesas financeiras']))]['Valor'].sum()
        desp_fix_mes = cpa_desp_fix_mes + folha_fix_mes

        despesas_financeiras_mes = cpa_mes[cpa_mes['Grupo'].str.lower() == 'despesas financeiras']['Valor'].sum()
        impostos_mes = cpa_mes[cpa_mes['Grupo'].str.lower() == 'imposto']['Valor'].sum()
        simples_nacional_mes = cpa_mes[cpa_mes['ContaPadrao'].str.lower().str.contains('simples nacional', na=False)]['Valor'].sum()
        total_impostos_mes = impostos_mes + simples_nacional_mes

        # ⚠️ Lucro Bruto agora deduz impostos ANTES
        lucro_bruto = receita_liquida - total_impostos_mes - desp_var_mes
        ebitda = lucro_bruto - desp_fix_mes
        lucro_liquido = receita_liquida - (desp_var_mes + desp_fix_mes + despesas_financeiras_mes + total_impostos_mes)

        dre_data.append({
            'Mês': mes,
            'Receita Total': receita_total,
            'Deduções': deducoes,
            'Receita Líquida': receita_liquida,
            'Impostos': total_impostos_mes,
            'Custos Variáveis': desp_var_mes,
            'Lucro Bruto': lucro_bruto,
            'Custos Fixos': desp_fix_mes,
            'EBITDA': ebitda,
            'Despesas Financeiras': despesas_financeiras_mes,
            'Lucro Líquido': lucro_liquido
        })

    df_dre = pd.DataFrame(dre_data)

    # Adiciona linhas extras
    empty_row = {col: '' for col in df_dre.columns}
    total_row = {col: df_dre[col].sum() if col != 'Mês' else 'Total' for col in df_dre.columns}
    df_dre = pd.concat([df_dre, pd.DataFrame([empty_row]), pd.DataFrame([total_row])], ignore_index=True)

    # Formata para exibição
    df_dre_display = df_dre.copy()
    df_dre_display.index = [str(i + 1) if i < len(df_dre) - 2 else '' for i in range(len(df_dre))]

    cols_moeda = df_dre.columns.drop(['Mês'])
    for col in cols_moeda:
        df_dre_display[col] = df_dre_display[col].apply(lambda x: format_currency(x) if isinstance(x, (int, float)) else x)

    st.markdown("### Demonstrativo de Resultados (DRE) Mensal com Total")
    st.dataframe(df_dre_display, use_container_width=True, height=525)

    # Gráfico
    st.markdown("### Composição Visual do DRE (por Mês)")
    fig = go.Figure()
    for nome, cor in [
        ('Receita Total', 'blue'),
        ('Custos Variáveis', 'orange'),
        ('Custos Fixos', 'purple'),
        ('Despesas Financeiras', 'red'),
        ('Impostos', 'brown'),
        ('Lucro Líquido', 'green')
    ]:
        fig.add_trace(go.Bar(x=df_dre['Mês'][:-2], y=df_dre[nome][:-2], name=nome, marker_color=cor))
    fig.update_layout(barmode='group', template='plotly_dark', height=500)
    st.plotly_chart(fig, use_container_width=True)

def relatorio_executivo_page():
    st.markdown("<h2 style='font-size:28px;'>Relatório Executivo: Lucro Líquido Negativo</h2>", unsafe_allow_html=True)

    # Recalcular variáveis reais (mesma lógica do dashboard)
    base_path = os.path.join(os.path.dirname(__file__), 'data')
    path_apagar = f'{base_path}/contasapagar2024.xlsx'
    path_areceber = f'{base_path}/contasareceber2024.xlsx'
    path_classif = f'{base_path}/Classificacao_Custos_Variavel_x_Fixo.xlsx'

    xls_ap = pd.ExcelFile(path_apagar)
    cpa_raw = pd.concat([xls_ap.parse(sheet) for sheet in ['teutocar', 'teutomaq']], ignore_index=True)
    cpa_raw['DataPagamento'] = pd.to_datetime(cpa_raw['Pagto'], dayfirst=True, errors='coerce')

    classif_df = pd.read_excel(path_classif, sheet_name=0)
    map_df = pd.read_excel(path_classif, sheet_name=1)
    cpa_raw['CategoriaLimpa'] = cpa_raw['Categoria'].astype(str).str.replace(r'^\d+\s*', '', regex=True)
    cpa = cpa_raw.merge(map_df.rename(columns={'contasantigas': 'CategoriaLimpa'}), on='CategoriaLimpa', how='left')
    cpa['ContaPadrao'] = cpa['contasnovas'].combine_first(cpa['CategoriaLimpa'])
    cpa = cpa.merge(classif_df.rename(columns={'Conta': 'ContaPadrao'}), on='ContaPadrao', how='left')

    xls_cr = pd.ExcelFile(path_areceber)
    cre = pd.concat([xls_cr.parse(sheet) for sheet in ['teutocar', 'teutomaq']], ignore_index=True)
    cre['DataPagamento'] = pd.to_datetime(cre['Pagto.'], dayfirst=True, errors='coerce')

    cre_filtered = cre
    cpa_filtered = cpa

    receitas_total = cre_filtered[cre_filtered['Valor'] > 0]['Valor'].sum()
    deducoes_neg = abs(cre_filtered[(cre_filtered['Valor'] < 0) &
                                    (cre_filtered['Categoria'].str.contains('desconto|devolução', case=False, na=False))]['Valor'].sum())
    deducoes_pos = cre_filtered[(cre_filtered['Valor'] > 0) &
                                (cre_filtered['Categoria'].str.contains('desconto|devolução', case=False, na=False))]['Valor'].sum()
    deducoes = deducoes_neg + deducoes_pos

    receita_liquida = receitas_total - deducoes

    cpa_no_transf = cpa_filtered[~cpa_filtered['ContaPadrao'].str.contains('transferência entre contas', case=False, na=False)]
    folha_total = cpa_no_transf[cpa_no_transf['Grupo'].str.lower() == 'despesas com folha']['Valor'].sum()
    folha_var = folha_total * 0.6
    folha_fix = folha_total * 0.4

    cpa_desp_var = cpa_no_transf[(cpa_no_transf['Classificação'].str.lower() == 'variável') &
                                 (~cpa_no_transf['Grupo'].str.lower().isin(['imposto', 'despesas financeiras']))]
    desp_var = cpa_desp_var['Valor'].sum() + folha_var

    cpa_desp_fix = cpa_no_transf[(cpa_no_transf['Classificação'].str.lower() == 'fixo') &
                                 (~cpa_no_transf['Grupo'].str.lower().isin(['imposto', 'despesas financeiras']))]
    desp_fix = cpa_desp_fix['Valor'].sum() + folha_fix

    despesas_financeiras = cpa_no_transf[cpa_no_transf['Grupo'].str.lower() == 'despesas financeiras']['Valor'].sum()
    impostos = cpa_no_transf[cpa_no_transf['Grupo'].str.lower() == 'imposto']['Valor'].sum()
    simples_nacional = cpa_no_transf[cpa_no_transf['ContaPadrao'].str.lower().str.contains('simples nacional', na=False)]['Valor'].sum()
    total_impostos = impostos + simples_nacional

    margem_contribuicao = ((receita_liquida - desp_var) / receita_liquida * 100) if receita_liquida else 0
    ponto_equilibrio = desp_fix / (margem_contribuicao / 100) if margem_contribuicao else 0
    lucro_liquido = receita_liquida - (desp_fix + desp_var + despesas_financeiras + total_impostos)

    faturamento_operacional = receita_liquida + deducoes
    margem_contribuicao_total = receita_liquida - desp_var
    margem_liquida = (lucro_liquido / receita_liquida) * 100 if receita_liquida else 0

    st.write("📋 **Relatório Especial: 5 Fatores que Explicam o Lucro Líquido Negativo — Alan Weiss Style**")
    st.write(f"1️⃣ **Faturamento abaixo das Receitas Contábeis**")
    st.write(f"As Receitas Totais em 2024 somam {format_currency(receitas_total)}, enquanto o Faturamento Operacional efetivo foi {format_currency(faturamento_operacional)}, mostrando que parte da receita veio de fontes não recorrentes.")

    st.write(f"2️⃣ **Despesas Financeiras Altas pela Falta de Capital de Giro**")
    st.write(f"As despesas financeiras somaram {format_currency(despesas_financeiras)}, representando aproximadamente {(despesas_financeiras / receitas_total) * 100:.2f}% das Receitas Totais.")

    st.write(f"3️⃣ **Ponto de Equilíbrio Não Atingido**")
    st.write(f"O ponto de equilíbrio foi calculado em {format_currency(ponto_equilibrio)}, mas o faturamento real alcançou apenas {format_currency(faturamento_operacional)}.")

    st.write(f"4️⃣ **Crescimento Desalinhado entre Custos Variáveis e Receita**")
    st.write(f"Enquanto a Receita cresceu {(faturamento_operacional / receitas_total) * 100:.2f}% no ano, os Custos Variáveis atingiram {format_currency(desp_var)}, absorvendo boa parte da margem bruta.")
    st.write(f"Índice Margem de Contribuição: aproximadamente {(margem_contribuicao_total / receita_liquida) * 100:.2f}%")

    st.write(f"5️⃣ **Margem Líquida Negativa Reflete Problemas Estratégicos**")
    st.write(f"O Lucro Líquido representa {margem_liquida:.2f}% das Receitas Líquidas.")

if __name__ == '__main__':
    main()
