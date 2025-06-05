import time
import threading
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self):
        self.MAX_LOGIN_ATTEMPTS = 5
        self.LOGIN_WINDOW_MINUTES = 15
        self.BLOCK_DURATION_MINUTES = 30
        
        self._attempts_by_ip = defaultdict(deque)
        self._attempts_by_user = defaultdict(deque)
        self._blocked_ips = {}
        self._blocked_users = {}
        self._lock = threading.Lock()
    
    def check_rate_limit(self, ip_address, username=None):
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - (self.LOGIN_WINDOW_MINUTES * 60)
            
            while self._attempts_by_ip[ip_address] and self._attempts_by_ip[ip_address][0] < cutoff_time:
                self._attempts_by_ip[ip_address].popleft()
            
            if len(self._attempts_by_ip[ip_address]) >= self.MAX_LOGIN_ATTEMPTS:
                return False
            
            if username:
                while self._attempts_by_user[username] and self._attempts_by_user[username][0] < cutoff_time:
                    self._attempts_by_user[username].popleft()
                
                if len(self._attempts_by_user[username]) >= self.MAX_LOGIN_ATTEMPTS:
                    return False
            
            return True
    
    def record_attempt(self, ip_address, username=None, success=False):
        with self._lock:
            current_time = time.time()
            
            if not success:
                self._attempts_by_ip[ip_address].append(current_time)
                if username:
                    self._attempts_by_user[username].append(current_time)
            else:
                if ip_address in self._attempts_by_ip:
                    self._attempts_by_ip[ip_address].clear()
                if username and username in self._attempts_by_user:
                    self._attempts_by_user[username].clear()
    
    def is_blocked(self, ip_address, username=None):
        return not self.check_rate_limit(ip_address, username), ""
    
    def is_allowed(self, ip_address, username=None):
        """Check if a request is allowed from this IP/user"""
        return self.check_rate_limit(ip_address, username)
    
    def get_remaining_attempts(self, ip_address, username=None):
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - (self.LOGIN_WINDOW_MINUTES * 60)
            
            while self._attempts_by_ip[ip_address] and self._attempts_by_ip[ip_address][0] < cutoff_time:
                self._attempts_by_ip[ip_address].popleft()
            
            ip_attempts = len(self._attempts_by_ip[ip_address])
            remaining_ip = max(0, self.MAX_LOGIN_ATTEMPTS - ip_attempts)
            
            if username:
                while self._attempts_by_user[username] and self._attempts_by_user[username][0] < cutoff_time:
                    self._attempts_by_user[username].popleft()
                
                user_attempts = len(self._attempts_by_user[username])
                remaining_user = max(0, self.MAX_LOGIN_ATTEMPTS - user_attempts)
                return min(remaining_ip, remaining_user)
            
            return remaining_ip


_rate_limiter_instance = None


def get_rate_limiter():
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = RateLimiter()
    return _rate_limiter_instance
