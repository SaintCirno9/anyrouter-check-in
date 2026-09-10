"""代理配置：读取环境变量并供浏览器 / HTTP 客户端使用。"""

from __future__ import annotations

import os
from urllib.parse import urlparse


def _normalize_proxy_url(server: str) -> str:
	"""规范化代理 URL，支持 host:port、host:port:user:pass、http://user:pass@host:port 等格式。"""
	s = server.strip()
	if not s:
		return ''
	if '://' in s:
		scheme, rest = s.split('://', 1)
	else:
		scheme, rest = 'http', s
	parts = rest.split(':')
	if len(parts) == 4 and '@' not in rest:
		host, port, user, pwd = parts
		return f'{scheme}://{user}:{pwd}@{host}:{port}'
	elif len(parts) == 2 and '@' not in rest:
		return f'{scheme}://{rest}'
	elif '@' in rest:
		return f'{scheme}://{rest}'
	elif '://' not in s:
		return f'{scheme}://{s}'
	return s


def get_proxy_server(*, use_proxy: bool = True) -> str | None:
	"""按平台配置读取 CHECKIN_PROXY_URL；use_proxy=False 时不返回代理地址。"""
	if not use_proxy:
		return None
	server = os.getenv('CHECKIN_PROXY_URL', '').strip()
	if not server:
		return None
	return _normalize_proxy_url(server) or None


def get_playwright_proxy(*, use_proxy: bool = True) -> dict[str, str] | None:
	"""提取 Playwright 所需代理配置字典，自动拆分认证用户名与密码。"""
	server = get_proxy_server(use_proxy=use_proxy)
	if not server:
		return None
	u = urlparse(server)
	if u.username or u.password:
		host_port = f'{u.hostname}:{u.port}' if u.port else f'{u.hostname}'
		proxy_dict: dict[str, str] = {
			'server': f'{u.scheme}://{host_port}',
		}
		if u.username:
			proxy_dict['username'] = u.username
		if u.password:
			proxy_dict['password'] = u.password
		return proxy_dict
	return {'server': server}

