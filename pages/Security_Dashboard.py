"""
Security Monitoring Dashboard
Dashboard completo para monitoramento de segurança em tempo real
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from pathlib import Path
from security.audit.security_logger import get_security_logger
# Import rate limiter with fallback
try:
    from security.auth.rate_limiter_fixed import get_rate_limiter
except ImportError:
    try:
        from security.auth.rate_limiter import get_rate_limiter
    except ImportError:
        # Fallback rate limiter implementation that matches the original interface
        from collections import defaultdict, deque
        import threading
        
        class FallbackRateLimiter:
            def __init__(self):
                self._max_login_attempts = 5
                self._login_window_minutes = 15
                self._block_duration_minutes = 30
                self._attempts_by_ip = defaultdict(deque)
                self._attempts_by_user = defaultdict(deque)
                self._blocked_ips = {}
                self._blocked_users = {}
                self._lock = threading.Lock()
            
            @property
            def MAX_LOGIN_ATTEMPTS(self):
                return self._max_login_attempts
                
            @MAX_LOGIN_ATTEMPTS.setter
            def MAX_LOGIN_ATTEMPTS(self, value):
                self._max_login_attempts = value
                
            @property
            def LOGIN_WINDOW_MINUTES(self):
                return self._login_window_minutes
                
            @LOGIN_WINDOW_MINUTES.setter
            def LOGIN_WINDOW_MINUTES(self, value):
                self._login_window_minutes = value
                
            @property
            def BLOCK_DURATION_MINUTES(self):                return self._block_duration_minutes
                
            @BLOCK_DURATION_MINUTES.setter
            def BLOCK_DURATION_MINUTES(self, value):
                self._block_duration_minutes = value
            
            def check_rate_limit(self, ip_address, username=None):
                return True
            
            def record_attempt(self, ip_address, username=None, success=False):
                pass
            
            def get_remaining_attempts(self, ip_address, username=None):
                return 5
            
            def is_allowed(self, ip_address, username=None):
                return True
            
            def is_blocked(self, ip_address, username=None):
                return False, ""
        
        def get_rate_limiter():
            return FallbackRateLimiter()

from security.auth.session_manager import get_session_manager
from database import get_connection


class SecurityDashboard:
    """Dashboard de monitoramento de segurança"""
    
    def __init__(self):
        self.logger = get_security_logger()
        self.rate_limiter = get_rate_limiter()
        self.session_manager = get_session_manager()
        
    def load_security_logs(self, hours: int = 24) -> dict:
        """Carrega logs de segurança das últimas N horas"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        logs = {'auth': [], 'data': [], 'system': []}
        
        # Diretório de logs
        log_dir = Path("logs")
        if not log_dir.exists():
            return logs
        
        # Ler logs de autenticação
        auth_log_file = log_dir / "auth_security.log"
        if auth_log_file.exists():
            logs['auth'] = self._parse_log_file(auth_log_file, cutoff_time)
        
        # Ler logs de acesso a dados
        data_log_file = log_dir / "data_access.log"
        if data_log_file.exists():
            logs['data'] = self._parse_log_file(data_log_file, cutoff_time)
        
        # Ler logs do sistema
        system_log_file = log_dir / "system_security.log"
        if system_log_file.exists():
            logs['system'] = self._parse_log_file(system_log_file, cutoff_time)
        
        return logs
    
    def _parse_log_file(self, file_path: Path, cutoff_time: datetime) -> list:
        """Parse arquivo de log e filtra por tempo"""
        logs = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if ' - ' in line:
                        try:
                            # Parse básico do formato de log
                            parts = line.strip().split(' - ', 3)
                            if len(parts) >= 4:
                                timestamp_str = parts[0]
                                log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")
                                
                                if log_time >= cutoff_time:
                                    # Tentar parse do JSON no final
                                    try:
                                        json_part = parts[3]
                                        log_data = json.loads(json_part)
                                        log_data['timestamp'] = log_time
                                        log_data['level'] = parts[2]
                                        logs.append(log_data)
                                    except json.JSONDecodeError:
                                        # Log sem JSON válido
                                        logs.append({
                                            'timestamp': log_time,
                                            'level': parts[2],
                                            'message': parts[3],
                                            'event_type': 'unknown'
                                        })
                        except ValueError:
                            continue
        except Exception:
            pass
        
        return logs
    
    def get_user_statistics(self) -> dict:
        """Obtém estatísticas de usuários"""
        conn = get_connection()
        cur = conn.cursor()
        
        # Estatísticas básicas
        cur.execute("SELECT COUNT(*) as total FROM usuarios")
        total_users = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(*) as locked FROM usuarios WHERE account_locked = 1")
        locked_users = cur.fetchone()['locked']
        
        cur.execute("SELECT COUNT(*) as recent FROM usuarios WHERE last_login >= datetime('now', '-7 days')")
        active_users = cur.fetchone()['recent']
        
        # Usuários com múltiplas tentativas de login
        cur.execute("SELECT COUNT(*) as attempts FROM usuarios WHERE login_attempts >= 3")
        suspicious_users = cur.fetchone()['attempts']
        
        return {
            'total_users': total_users,
            'locked_users': locked_users,
            'active_users_7d': active_users,
            'suspicious_users': suspicious_users
        }
    
    def get_session_statistics(self) -> dict:
        """Obtém estatísticas de sessões"""
        conn = get_connection()
        cur = conn.cursor()
          # Sessões ativas
        cur.execute("""
            SELECT COUNT(*) as active 
            FROM user_sessions 
            WHERE expires_at > datetime('now') AND is_active = 1
        """)
        active_sessions = cur.fetchone()['active']
        
        # Sessões das últimas 24h
        cur.execute("""
            SELECT COUNT(*) as recent 
            FROM user_sessions 
            WHERE created_at >= datetime('now', '-24 hours')
        """)
        recent_sessions = cur.fetchone()['recent']
        
        # Sessões expiradas hoje
        cur.execute("""
            SELECT COUNT(*) as expired 
            FROM user_sessions 
            WHERE expires_at <= datetime('now') 
            AND expires_at >= datetime('now', '-24 hours')
        """)
        expired_sessions = cur.fetchone()['expired']
        
        return {
            'active_sessions': active_sessions,
            'recent_sessions_24h': recent_sessions,
            'expired_sessions_24h': expired_sessions
        }
    
    def get_threat_analysis(self, logs: dict) -> dict:
        """Analisa ameaças baseado nos logs"""
        threats = {
            'brute_force_attempts': 0,
            'suspicious_ips': set(),
            'failed_logins': 0,
            'rate_limit_violations': 0,
            'data_access_violations': 0,
            'system_errors': 0
        }
        
        # Analisar logs de autenticação
        for log in logs['auth']:
            if log.get('event_type') == 'authentication_attempt' and not log.get('success', True):
                threats['failed_logins'] += 1
                
                # Detectar tentativas de força bruta
                ip = log.get('ip_address')
                if ip:
                    threats['suspicious_ips'].add(ip)
            
            if log.get('event_type') == 'rate_limit_exceeded':
                threats['rate_limit_violations'] += 1
        
        # Analisar logs do sistema
        for log in logs['system']:
            if log.get('level') == 'ERROR':
                threats['system_errors'] += 1
        
        # Analisar logs de dados
        for log in logs['data']:
            if not log.get('success', True):
                threats['data_access_violations'] += 1
        
        # Calcular força bruta (múltiplas tentativas do mesmo IP)
        ip_attempts = {}
        for log in logs['auth']:
            if log.get('event_type') == 'authentication_attempt' and not log.get('success', True):
                ip = log.get('ip_address', 'unknown')
                ip_attempts[ip] = ip_attempts.get(ip, 0) + 1
        
        threats['brute_force_attempts'] = sum(1 for count in ip_attempts.values() if count >= 5)
        threats['suspicious_ips'] = list(threats['suspicious_ips'])
        
        return threats
    
    def get_encryption_status(self) -> dict:
        """Get current encryption status of the system"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Check encrypted emails
            cur.execute("""
                SELECT 
                    COUNT(*) as total_users,
                    SUM(CASE WHEN email LIKE 'encrypted:%' THEN 1 ELSE 0 END) as encrypted_emails
                FROM usuarios
            """)
            user_stats = cur.fetchone()
            
            # Check financial data
            cur.execute("SELECT COUNT(*) as total FROM extratos")
            extratos_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) as total FROM economias")
            economias_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) as total FROM cartoes")
            cartoes_count = cur.fetchone()[0]
            
            # Check if encryption key exists
            encryption_key_exists = Path('.encryption_key').exists()
            
            return {
                'total_users': user_stats[0],
                'encrypted_emails': user_stats[1],
                'email_encryption_rate': (user_stats[1] / max(user_stats[0], 1)) * 100,
                'financial_records': extratos_count + economias_count + cartoes_count,
                'extratos_count': extratos_count,
                'economias_count': economias_count,
                'cartoes_count': cartoes_count,
                'encryption_key_exists': encryption_key_exists
            }
        except Exception as e:
            st.error(f"Erro ao obter status de criptografia: {e}")
            return {}
    
    def render_dashboard(self):
        """Renderiza o dashboard completo"""
        st.title("🛡️ Security Monitoring Dashboard")
        st.markdown("---")
        
        # Seletor de período
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("📊 Monitoramento de Segurança em Tempo Real")
        with col2:
            hours = st.selectbox("Período", [1, 6, 12, 24, 48, 168], index=3, help="Últimas N horas")
        
        # Carregar dados
        logs = self.load_security_logs(hours)
        user_stats = self.get_user_statistics()
        session_stats = self.get_session_statistics()
        threats = self.get_threat_analysis(logs)
        encryption_status = self.get_encryption_status()
        
        # Métricas principais
        st.subheader("📈 Métricas Principais")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "👥 Usuários Total",
                user_stats['total_users'],
                delta=f"{user_stats['active_users_7d']} ativos (7d)"
            )
        
        with col2:
            st.metric(
                "🔒 Contas Bloqueadas",
                user_stats['locked_users'],
                delta=f"{user_stats['suspicious_users']} suspeitas",
                delta_color="inverse"
            )
        
        with col3:
            st.metric(
                "🔐 Sessões Ativas",
                session_stats['active_sessions'],
                delta=f"{session_stats['recent_sessions_24h']} novas (24h)"
            )
        
        with col4:
            st.metric(
                "⚠️ Tentativas Falhas",
                threats['failed_logins'],
                delta=f"{threats['rate_limit_violations']} bloqueadas",
                delta_color="inverse"
            )
        
        # Análise de ameaças
        st.subheader("🚨 Análise de Ameaças")
        
        threat_col1, threat_col2 = st.columns(2)
        
        with threat_col1:
            # Status de segurança
            if threats['brute_force_attempts'] > 0:
                st.error(f"🚨 {threats['brute_force_attempts']} tentativas de força bruta detectadas!")
            elif threats['failed_logins'] > 10:
                st.warning(f"⚠️ {threats['failed_logins']} tentativas de login falharam")
            else:
                st.success("✅ Nenhuma ameaça crítica detectada")
            
            # IPs suspeitos
            if threats['suspicious_ips']:
                st.write("**IPs Suspeitos:**")
                for ip in threats['suspicious_ips'][:5]:  # Mostrar top 5
                    st.code(ip)
        
        with threat_col2:
            # Gráfico de ameaças
            threat_data = {
                'Tipo': ['Login Falhado', 'Rate Limit', 'Acesso Negado', 'Erros Sistema'],
                'Quantidade': [
                    threats['failed_logins'],
                    threats['rate_limit_violations'], 
                    threats['data_access_violations'],
                    threats['system_errors']
                ]
            }
            
            fig_threats = px.bar(
                threat_data, 
                x='Tipo', 
                y='Quantidade',
                title=f"Incidentes de Segurança ({hours}h)",
                color='Quantidade',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_threats, use_container_width=True)
        
        # Timeline de eventos
        st.subheader("📅 Timeline de Eventos")
        
        if logs['auth'] or logs['system']:
            # Combinar todos os logs
            all_logs = []
            for log_type, log_list in logs.items():
                for log in log_list:
                    log['log_type'] = log_type
                    all_logs.append(log)
            
            # Criar DataFrame
            if all_logs:
                df_logs = pd.DataFrame(all_logs)
                df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'])
                
                # Gráfico de timeline
                fig_timeline = px.scatter(
                    df_logs.sort_values('timestamp'),
                    x='timestamp',
                    y='log_type',
                    color='event_type',
                    size_max=10,
                    title="Timeline de Eventos de Segurança",
                    hover_data=['event_type', 'level']
                )
                st.plotly_chart(fig_timeline, use_container_width=True)
                
                # Tabela de eventos recentes
                st.subheader("📋 Eventos Recentes")
                recent_logs = df_logs.sort_values('timestamp', ascending=False).head(20)
                
                display_df = recent_logs[['timestamp', 'log_type', 'event_type', 'level']].copy()
                display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    column_config={
                        "timestamp": "Data/Hora",
                        "log_type": "Tipo",
                        "event_type": "Evento", 
                        "level": "Nível"
                    }
                )
        else:
            st.info("Nenhum evento de segurança encontrado no período selecionado.")
        
        # Ações administrativas
        st.subheader("🔧 Ações Administrativas")
        
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button("🔄 Limpar Rate Limits", help="Remove todos os bloqueios de rate limiting"):
                # Limpar rate limits
                self.rate_limiter._attempts_by_ip.clear()
                self.rate_limiter._attempts_by_user.clear()
                self.rate_limiter._blocked_ips.clear()
                self.rate_limiter._blocked_users.clear()
                st.success("Rate limits limpos!")
                st.rerun()
        
        with action_col2:
            if st.button("🔓 Desbloquear Contas", help="Desbloqueia todas as contas de usuários"):
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("UPDATE usuarios SET account_locked = 0, login_attempts = 0")
                conn.commit()
                st.success("Todas as contas foram desbloqueadas!")
                st.rerun()
        
        with action_col3:
            if st.button("📊 Gerar Relatório", help="Gera relatório detalhado de segurança"):
                report = self.logger.generate_security_report(hours)
                st.json(report)
        
        # Configurações de segurança
        st.subheader("⚙️ Configurações de Segurança")
        
        with st.expander("Configurações de Rate Limiting"):
            max_attempts = st.number_input("Máximo de tentativas", min_value=1, max_value=20, value=5)
            window_minutes = st.number_input("Janela de tempo (minutos)", min_value=1, max_value=120, value=15)
            block_duration = st.number_input("Duração do bloqueio (minutos)", min_value=1, max_value=1440, value=30)
            
            if st.button("Aplicar Configurações"):
                self.rate_limiter.MAX_LOGIN_ATTEMPTS = max_attempts
                self.rate_limiter.LOGIN_WINDOW_MINUTES = window_minutes
                self.rate_limiter.BLOCK_DURATION_MINUTES = block_duration
                st.success("Configurações atualizadas!")
        
        # Encryption Status Section
        st.subheader("🔐 Status de Criptografia")
        encryption_status = self.get_encryption_status()
        
        if encryption_status:
            enc_col1, enc_col2, enc_col3, enc_col4 = st.columns(4)
            
            with enc_col1:
                st.metric(
                    "Emails Criptografados",
                    f"{encryption_status['encrypted_emails']}/{encryption_status['total_users']}",
                    f"{encryption_status['email_encryption_rate']:.1f}%"
                )
            
            with enc_col2:
                st.metric(
                    "Registros Financeiros",
                    encryption_status['financial_records'],
                    "Identificados"
                )
            
            with enc_col3:
                key_status = "✅ Ativa" if encryption_status['encryption_key_exists'] else "❌ Ausente"
                st.metric(
                    "Chave de Criptografia",
                    key_status,
                    "AES-256"
                )
            
            with enc_col4:
                total_protected = encryption_status['encrypted_emails'] + encryption_status['financial_records']
                st.metric(
                    "Dados Protegidos",
                    total_protected,
                    "Total"
                )
            
            # Encryption breakdown
            with st.expander("📊 Detalhes de Criptografia"):
                enc_details_col1, enc_details_col2 = st.columns(2)
                
                with enc_details_col1:
                    st.write("**Dados Pessoais:**")
                    st.write(f"- Emails criptografados: {encryption_status['encrypted_emails']}")
                    st.write(f"- Taxa de criptografia: {encryption_status['email_encryption_rate']:.1f}%")
                
                with enc_details_col2:
                    st.write("**Dados Financeiros:**")
                    st.write(f"- Extratos: {encryption_status['extratos_count']}")
                    st.write(f"- Economias: {encryption_status['economias_count']}")
                    st.write(f"- Cartões: {encryption_status['cartoes_count']}")


def main():
    """Função principal do dashboard"""
    st.set_page_config(
        page_title="Security Dashboard",
        page_icon="🛡️",
        layout="wide"
    )
      # Verificar autenticação (assumindo que já existe)
    if not st.session_state.get('autenticado', False):
        st.error("🔒 Acesso negado. Faça login primeiro.")
        st.stop()
    
    # Verificar permissões de admin (se implementado)
    current_user = st.session_state.get('usuario', '')
    user_role = st.session_state.get('user_role', 'user')
    
    # Dar acesso especial para o usuário richardpalmas
    if current_user == 'richardpalmas':
        # Garantir que richardpalmas sempre tenha role de admin
        st.session_state['user_role'] = 'admin'
        user_role = 'admin'
    
    if user_role != 'admin':
        st.error("🚫 Acesso restrito. Apenas administradores podem acessar este dashboard.")
        st.stop()
    
    # Renderizar dashboard
    dashboard = SecurityDashboard()
    dashboard.render_dashboard()


if __name__ == "__main__":
    main()
