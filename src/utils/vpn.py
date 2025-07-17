# src/utils/vpn.py
"""
Утилита для проверки VPN соединения
"""
import subprocess
import requests
from typing import Optional, Tuple
from loguru import logger

from config.settings import USE_VPN, VPN_CONFIG_PATH


class VPNChecker:
    """Проверка VPN соединения"""
    
    @staticmethod
    def get_current_ip() -> Optional[str]:
        """Получить текущий IP адрес"""
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            if response.status_code == 200:
                return response.json().get('ip')
        except Exception as e:
            logger.error(f"Ошибка получения IP: {e}")
        return None
    
    @staticmethod
    def get_ip_info() -> Tuple[Optional[str], Optional[str]]:
        """Получить IP и страну"""
        try:
            response = requests.get('https://ipapi.co/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('ip'), data.get('country_name')
        except Exception as e:
            logger.error(f"Ошибка получения информации об IP: {e}")
        return None, None
    
    @staticmethod
    def is_wireguard_active() -> bool:
        """Проверить активен ли WireGuard"""
        try:
            # Проверяем статус WireGuard
            result = subprocess.run(
                ['wg', 'show'], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            return result.returncode == 0 and len(result.stdout) > 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @staticmethod
    def check_vpn_status() -> dict:
        """Полная проверка VPN статуса"""
        if not USE_VPN:
            return {
                'enabled': False,
                'active': False,
                'message': 'VPN отключен в настройках'
            }
        
        ip, country = VPNChecker.get_ip_info()
        wireguard_active = VPNChecker.is_wireguard_active()
        
        return {
            'enabled': True,
            'active': wireguard_active,
            'ip': ip,
            'country': country,
            'message': f'VPN {"активен" if wireguard_active else "не активен"}'
        }
    
    @staticmethod
    def ensure_vpn_connected() -> bool:
        """Убедиться что VPN подключен"""
        if not USE_VPN:
            return True  # Если VPN не требуется, считаем что все ок
        
        status = VPNChecker.check_vpn_status()
        
        if not status['active']:
            logger.warning(f"VPN не активен! IP: {status['ip']}, Страна: {status['country']}")
            
            # Можно попытаться подключить VPN автоматически
            # VPNChecker.connect_vpn()
            
            return False
        
        logger.info(f"VPN активен. IP: {status['ip']}, Страна: {status['country']}")
        return True
    
    @staticmethod
    def connect_vpn() -> bool:
        """Попытаться подключить VPN"""
        try:
            logger.info(f"Подключаем VPN через {VPN_CONFIG_PATH}")
            result = subprocess.run(
                ['wg-quick', 'up', VPN_CONFIG_PATH],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.success("VPN успешно подключен")
                return True
            else:
                logger.error(f"Ошибка подключения VPN: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Не удалось подключить VPN: {e}")
            return False
    
    @staticmethod
    def disconnect_vpn() -> bool:
        """Отключить VPN"""
        try:
            result = subprocess.run(
                ['wg-quick', 'down', VPN_CONFIG_PATH],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Ошибка отключения VPN: {e}")
            return False