# src/utils/vpn.py
"""
Утилита для проверки VPN соединения
"""
import json
import subprocess
from pathlib import Path
import requests
from typing import Dict, Optional, Tuple
from loguru import logger

from config.settings import (
    USE_VPN,
    VPN_CONFIG_PATH,
    VPN_PROTOCOL,
    XRAY_CONFIG_PATH,
)


class VPNChecker:
    """Проверка VPN соединения"""

    @staticmethod
    def _run_command(command: list[str], timeout: int = 5) -> subprocess.CompletedProcess:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    
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
            result = VPNChecker._run_command(['wg', 'show'])
            return result.returncode == 0 and len(result.stdout) > 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def _load_xray_config() -> Optional[Dict]:
        """Загрузить Xray config.json"""
        config_path = Path(XRAY_CONFIG_PATH).expanduser()
        if not config_path.exists():
            logger.warning(f"Xray config не найден: {config_path}")
            return None

        try:
            with config_path.open('r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Не удалось прочитать Xray config {config_path}: {e}")
            return None

    @staticmethod
    def _extract_xray_proxy(config: Dict) -> Optional[Dict[str, str]]:
        """Извлечь локальный proxy endpoint из Xray-конфига"""
        inbounds = config.get('inbounds') or []
        preferred_protocols = ('socks', 'http')

        for protocol in preferred_protocols:
            for inbound in inbounds:
                if inbound.get('protocol') != protocol:
                    continue

                listen = inbound.get('listen') or '127.0.0.1'
                if listen == '0.0.0.0':
                    listen = '127.0.0.1'

                port = inbound.get('port')
                if not port:
                    continue

                if protocol == 'socks':
                    proxy_scheme = 'socks5'
                elif protocol == 'http':
                    proxy_scheme = 'http'
                else:
                    proxy_scheme = protocol

                return {
                    'scheme': proxy_scheme,
                    'host': listen,
                    'port': str(port),
                    'url': f"{proxy_scheme}://{listen}:{port}",
                    'tag': inbound.get('tag', protocol),
                    'protocol': protocol,
                }

        return None

    @staticmethod
    def _extract_vless_endpoint(config: Dict) -> Optional[Dict[str, str]]:
        """Извлечь информацию об outbound VLESS"""
        outbounds = config.get('outbounds') or []

        for outbound in outbounds:
            if outbound.get('protocol') != 'vless':
                continue

            vnext = ((outbound.get('settings') or {}).get('vnext') or [])
            if not vnext:
                continue

            endpoint = vnext[0]
            users = endpoint.get('users') or [{}]
            user = users[0] if users else {}

            return {
                'address': str(endpoint.get('address', '')),
                'port': str(endpoint.get('port', '')),
                'id': str(user.get('id', '')),
                'flow': str(user.get('flow', '')),
                'security': str(((outbound.get('streamSettings') or {}).get('security')) or ''),
                'network': str(((outbound.get('streamSettings') or {}).get('network')) or ''),
                'tag': str(outbound.get('tag', 'vless')),
            }

        return None

    @staticmethod
    def get_xray_proxy_settings() -> Optional[Dict[str, str]]:
        """Получить локальный proxy endpoint из Xray"""
        config = VPNChecker._load_xray_config()
        if not config:
            return None

        proxy = VPNChecker._extract_xray_proxy(config)
        if not proxy:
            logger.warning("В Xray config не найден локальный socks/http inbound")
            return None

        return proxy

    @staticmethod
    def get_xray_proxy_url() -> Optional[str]:
        """Получить proxy URL для клиента Instagram"""
        proxy = VPNChecker.get_xray_proxy_settings()
        return proxy['url'] if proxy else None

    @staticmethod
    def is_xray_active() -> bool:
        """Проверить активность Xray"""
        commands = (
            ['systemctl', 'is-active', 'xray'],
            ['systemctl', 'is-active', 'xray.service'],
            ['pgrep', '-f', 'xray'],
        )

        for command in commands:
            try:
                result = VPNChecker._run_command(command)
                if result.returncode == 0:
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return False

    @staticmethod
    def detect_vpn_backend() -> str:
        """Определить backend VPN/proxy"""
        if VPN_PROTOCOL != 'auto':
            return VPN_PROTOCOL

        if Path(XRAY_CONFIG_PATH).expanduser().exists():
            return 'xray_vless'
        return 'wireguard'
    
    @staticmethod
    def check_vpn_status() -> dict:
        """Полная проверка VPN статуса"""
        if not USE_VPN:
            return {
                'enabled': False,
                'active': False,
                'backend': None,
                'message': 'VPN отключен в настройках'
            }

        backend = VPNChecker.detect_vpn_backend()
        ip, country = VPNChecker.get_ip_info()

        if backend == 'xray_vless':
            proxy = VPNChecker.get_xray_proxy_settings()
            vless_endpoint = VPNChecker._extract_vless_endpoint(VPNChecker._load_xray_config() or {})
            xray_active = VPNChecker.is_xray_active()
            message = 'Xray/VLESS активен' if xray_active else 'Xray/VLESS не активен'
            if proxy:
                message += f" через {proxy['url']}"

            return {
                'enabled': True,
                'active': xray_active,
                'backend': backend,
                'ip': ip,
                'country': country,
                'proxy_url': proxy['url'] if proxy else None,
                'proxy_tag': proxy['tag'] if proxy else None,
                'vless_endpoint': vless_endpoint,
                'message': message,
            }

        wireguard_active = VPNChecker.is_wireguard_active()
        return {
            'enabled': True,
            'active': wireguard_active,
            'backend': backend,
            'ip': ip,
            'country': country,
            'message': f'WireGuard {"активен" if wireguard_active else "не активен"}'
        }
    
    @staticmethod
    def ensure_vpn_connected() -> bool:
        """Убедиться что VPN подключен"""
        if not USE_VPN:
            return True  # Если VPN не требуется, считаем что все ок

        status = VPNChecker.check_vpn_status()

        if not status['active']:
            logger.warning(
                f"{status.get('backend') or 'VPN'} не активен! "
                f"IP: {status.get('ip')}, Страна: {status.get('country')}"
            )
            return False

        logger.info(
            f"{status.get('backend') or 'VPN'} активен. "
            f"IP: {status.get('ip')}, Страна: {status.get('country')}"
        )
        return True
    
    @staticmethod
    def connect_vpn() -> bool:
        """Попытаться подключить VPN"""
        backend = VPNChecker.detect_vpn_backend()
        if backend == 'xray_vless':
            logger.error(
                "Автозапуск Xray/VLESS не реализован в приложении. "
                "Запустите сервис xray отдельно."
            )
            return False

        try:
            logger.info(f"Подключаем VPN через {VPN_CONFIG_PATH}")
            result = VPNChecker._run_command(
                ['wg-quick', 'up', VPN_CONFIG_PATH],
                timeout=10,
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
        backend = VPNChecker.detect_vpn_backend()
        if backend == 'xray_vless':
            logger.error(
                "Остановка Xray/VLESS из приложения не поддерживается. "
                "Остановите сервис xray отдельно."
            )
            return False

        try:
            result = VPNChecker._run_command(
                ['wg-quick', 'down', VPN_CONFIG_PATH],
                timeout=10,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Ошибка отключения VPN: {e}")
            return False
