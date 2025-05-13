import streamlit as st
import pandas as pd
import bcrypt
import base64
from sqlalchemy import create_engine, text
from docx import Document
import time

# ─── NOVO IMPORT PARA OPÇÃO 2 ───────────────────────────────────────────────
import importlib.util
import os





# ————————————————————————————— Page config & CSS —————————————————————————————
st.set_page_config(page_title="Portal Yugen", layout="wide")
st.markdown("""
<style>
  div[data-testid="stSidebar"] > div:first-child { width: 300px; }
  div[data-testid="stSidebar"] .sidebar-content {
    display: flex; flex-direction: column; align-items: center;
  }
  div[data-testid="stSidebar"] h3,
  div[data-testid="stSidebar"] label,
  div[data-testid="stSidebar"] button {
    font-size: 1.1rem; color: #333333;
  }
  .instr-box {
    background-color: #f0f2f6 !important;
    color: #333333 !important;
    border-radius: 0.5rem !important;
    padding: 1rem !important;
    margin-bottom: 0.5rem !important;
  }
</style>
""", unsafe_allow_html=True)

# ————————————————————————————— Helpers —————————————————————————————
def get_engine():
    db = st.secrets["postgres"]
    url = (
        f"postgresql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/{db['dbname']}"
    )
    return create_engine(url)

def logout_and_notify():
    st.session_state.clear()
    st.success("Sessão encerrada!")
    time.sleep(2)
    st.session_state.page = "Login"
    st.rerun()


# ─── FUNÇÃO QUE CARREGA E EXECUTA O DASH EXTERNO ────────────────────────────
def load_and_run_dre(engine, uid, page="Dashboard Geral"):
    dre_path = r"C:\Users\sergi\Desktop\Yugen-projetos\dre\dash_dre_v2.py"
    spec = importlib.util.spec_from_file_location("dash_dre_v2", dre_path)
    module = importlib.util.module_from_spec(spec)

    # Monkey-patch para evitar erro de set_page_config duplicado
    original_set = st.set_page_config
    st.set_page_config = lambda *args, **kwargs: None
    try:
        spec.loader.exec_module(module)
    finally:
        st.set_page_config = original_set  # restaura

    # Agora chama o main do dash externo com 3 argumentos
    module.main(engine, uid, page)

# ————————————————————————————— Signup —————————————————————————————
def show_signup(engine):
    st.header("📋 Cadastro de Novo Usuário")
    with st.form("signup_form", clear_on_submit=True):
        email    = st.text_input("E-mail")
        name     = st.text_input("Nome completo")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Registrar")
    if submitted:
        with engine.begin() as conn:
            if conn.execute(text("SELECT 1 FROM users WHERE email=:e"), {"e": email}).fetchone():
                st.error("E-mail já cadastrado.")
                return
            pwd_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                text("INSERT INTO users (email,name,password_hash,role,is_active) VALUES (:e,:n,:ph,'client',FALSE)"),
                {"e": email, "n": name, "ph": pwd_hash}
            )
        st.success("Cadastro enviado! Aguardando aprovação.")
        st.session_state.page = "Login"



# ————————————————————————————— Login —————————————————————————————
def show_login(engine):
    st.header("🔑 Login")

    # inicializa variáveis de sessão
    if "login_email" not in st.session_state:
        st.session_state.login_email = ""
    if "login_pwd" not in st.session_state:
        st.session_state.login_pwd = ""
    if "login_submit" not in st.session_state:
        st.session_state.login_submit = False

    # callback que dispara ao apertar Enter no campo de senha
    def _on_enter():
        st.session_state.login_submit = True

    # campos de input
    st.text_input("E-mail", key="login_email")
    st.text_input(
        "Senha",
        type="password",
        key="login_pwd",
        on_change=_on_enter
    )

    # botão de Entrar
    clicked = st.button("Entrar")

    # se apertou Enter no campo ou clicou no botão
    if clicked or st.session_state.login_submit:
        # reseta a flag
        #st.session_state.login_submit = False

        email = st.session_state.login_email
        pwd   = st.session_state.login_pwd

        # executa a verificação no banco
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT id, name, password_hash "
                     "FROM users "
                     "WHERE email=:e AND is_active=TRUE"),
                {"e": email}
            ).mappings().fetchone()

        if row and bcrypt.checkpw(pwd.encode(), row["password_hash"].encode()):
            st.session_state.user_id   = row["id"]
            st.session_state.user_name = row["name"]
            st.success(f"Bem-vindo, {row['name']}!")
            st.session_state.page = "Dashboard"
            st.rerun()
        else:
            st.error("E-mail ou senha incorretos.")


# ————————————————————————————— Dashboards & Reports —————————————————————————————
def show_dashboard_financeiro(engine, uid):
    if st.session_state.get("user_id"):
        cols = st.columns([9, 1])
        if cols[1].button("🚪 Logout"):
            logout_and_notify()

        # Renderiza as páginas do dash financeiro conforme a escolha
        subpage = st.radio(
            "Navegar entre as páginas:",
            ["Dashboard Geral", "Análise de Faturamento", "DRE Trimestral", "DRE Completo", "Relatório Executivo"]
        )

        # Chama o dash externo com a subpágina
        load_and_run_dre(engine, uid, page=subpage)

        if st.button("← Voltar"):
            st.session_state.page = "Dashboard"
            del st.session_state.dashboard_choice
            st.stop()


def show_dashboard_comercial(engine, uid):
    if st.session_state.get("user_id"):
        cols = st.columns([9,1])
        if cols[1].button("🚪 Logout"):
            logout_and_notify()
    st.title("📈 Dashboard Comercial")
    st.write("…gráficos comerciais aqui…")
    if st.button("← Voltar"):
        st.session_state.page = "Dashboard"
        del st.session_state.dashboard_choice
        st.stop()

def show_report_vendas(engine, uid):
    if st.session_state.get("user_id"):
        cols = st.columns([9,1])
        if cols[1].button("🚪 Logout"):
            logout_and_notify()
    st.title("📑 Relatório de Vendas")
    st.write("…relatório de vendas…")
    if st.button("← Voltar"):
        st.session_state.page = "Dashboard"
        del st.session_state.report_choice
        st.stop()

def show_report_fluxo(engine, uid):
    if st.session_state.get("user_id"):
        cols = st.columns([9,1])
        if cols[1].button("🚪 Logout"):
            logout_and_notify()
    st.title("📑 Relatório de Fluxo de Caixa")
    st.write("…relatório de fluxo de caixa…")
    if st.button("← Voltar"):
        st.session_state.page = "Dashboard"
        del st.session_state.report_choice
        st.stop()

def show_report_diagnostico(engine, uid):
    if st.session_state.get("user_id"):
        cols = st.columns([9,1])
        if cols[1].button("🚪 Logout"):
            logout_and_notify()
    st.title("📑 Diagnóstico Trimestral TeutoMaq")
    doc = Document("Diagnostico_Trimestral_TeutoMaq.docx")
    for p in doc.paragraphs:
        if p.text.strip(): st.write(p.text)
    if st.button("← Voltar"):
        st.session_state.page = "Dashboard"
        del st.session_state.report_choice
        st.stop()

# ————————————————————————————— Main —————————————————————————————
def main():
    engine = get_engine()
    sidebar = st.sidebar

    # logo
    logo = base64.b64encode(open("logo_yugen.png","rb").read()).decode()
    sidebar.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{logo}" width="150"></div>', unsafe_allow_html=True)
    sidebar.markdown("---")

    # contato (Login/Register)
    if st.session_state.get("page") in (None,"Login","Registrar"):
        sidebar.markdown(
            "**Yugen Soluções Corporativas**  \n"
            "CNPJ 47.843.475/0001-03  \n"
            "Campo Mourão - PR  \n\n"
            "[✉️ E-mail](mailto:sergiohono@gmail.com)  \n"
            "[💬 WhatsApp](https://wa.me/5544999627532)"
        )
        sidebar.markdown("---")

    # Bem-vindo
    user = st.session_state.get("user_name")
    sidebar.markdown(
        f"<div style='text-align:center;font-size:1.2rem;'><strong>Bem-vindo, {user or 'visitante'}!</strong></div>",
        unsafe_allow_html=True
    )
    sidebar.markdown("---")
    # instrução inicial
    if st.session_state.get("user_id") and "dashboard_choice" not in st.session_state:
        st.markdown('<div class="instr-box"><strong>Selecione um Dashboard no menu lateral</strong></div>', unsafe_allow_html=True)


# ——————————————————————— Sidebar ———————————————————————
    user_id = st.session_state.get("user_id")
    page = st.session_state.get("page", "Login")
    
    if not user_id:
        # Antes do login: mostrar botões de login/registro
        c1, c2 = sidebar.columns(2)
        if c1.button("🔑 Login"):     st.session_state.page = "Login"; st.stop()
        if c2.button("📝 Registrar"): st.session_state.page = "Registrar"; st.stop()
    else:
        # Após login: mostrar empresa, dashboards e logout
        sidebar.markdown("<strong>Selecione a Empresa</strong>", unsafe_allow_html=True)
        empresa = sidebar.selectbox("", ["– selecione –", "TeutoMaq"], key="company_choice")

        if empresa != "– selecione –":
            sidebar.markdown("<strong style='margin-top:0.5rem;'>Dashboards e Análises</strong>", unsafe_allow_html=True)
            sidebar.selectbox(
                "", 
                ["– selecione –", "Dashboard Geral", "Análise de Faturamento", "DRE Trimestral", "DRE Completo"], 
                key="dashboard_choice"
            )


        sidebar.markdown("---")
        if sidebar.button("🚪 Logout"):
            logout_and_notify()
            
        # render
    
    if page == "Registrar":
        show_signup(engine)
    elif page == "Login":
        show_login(engine)
    else:
        uid = st.session_state.user_id
        dash = st.session_state.get("dashboard_choice", "– selecione –")
        rpt  = st.session_state.get("report_choice", "– selecione –")

        if dash == "Dashboard Geral":
            load_and_run_dre(engine, uid, page="Dashboard Geral")
        elif dash == "Análise de Faturamento":
            load_and_run_dre(engine, uid, page="Análise de Faturamento")
        elif dash == "DRE Trimestral":
            load_and_run_dre(engine, uid, page="DRE Trimestral")
        elif dash == "DRE Completo":
            load_and_run_dre(engine, uid, page="DRE Completo")
        elif dash == "Relatório Executivo":
            load_and_run_dre(engine, uid, page="Relatório Executivo")

        elif dash == "Comercial":
            show_dashboard_comercial(engine, uid)
        elif rpt == "Vendas":
            show_report_vendas(engine, uid)
        elif rpt == "Fluxo de Caixa":
            show_report_fluxo(engine, uid)
        elif rpt == "Diagnóstico Trimestral":
            show_report_diagnostico(engine, uid)

if __name__=="__main__":
    main()
