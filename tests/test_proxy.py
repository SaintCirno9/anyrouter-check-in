from __future__ import annotations

from utils.proxy import get_playwright_proxy, get_proxy_server


def test_proxy_server_with_auth_url(monkeypatch):
	proxy_url = 'http://user123:pass456@proxy.example.com:8080'
	monkeypatch.setenv('CHECKIN_PROXY_URL', proxy_url)

	assert get_proxy_server(use_proxy=True) == proxy_url
	playwright_proxy = get_playwright_proxy(use_proxy=True)
	assert playwright_proxy == {
		'server': 'http://proxy.example.com:8080',
		'username': 'user123',
		'password': 'pass456',
	}


def test_proxy_server_with_colon_format(monkeypatch):
	# host:port:user:pass 格式
	raw_proxy = 'us2.cliproxy.io:3010:user123:pass456'
	monkeypatch.setenv('CHECKIN_PROXY_URL', raw_proxy)

	assert get_proxy_server(use_proxy=True) == 'http://user123:pass456@us2.cliproxy.io:3010'
	playwright_proxy = get_playwright_proxy(use_proxy=True)
	assert playwright_proxy == {
		'server': 'http://us2.cliproxy.io:3010',
		'username': 'user123',
		'password': 'pass456',
	}


def test_proxy_server_without_auth(monkeypatch):
	monkeypatch.setenv('CHECKIN_PROXY_URL', 'http://127.0.0.1:7890')

	assert get_proxy_server(use_proxy=True) == 'http://127.0.0.1:7890'
	assert get_playwright_proxy(use_proxy=True) == {'server': 'http://127.0.0.1:7890'}


def test_proxy_disabled(monkeypatch):
	monkeypatch.setenv('CHECKIN_PROXY_URL', 'http://127.0.0.1:7890')

	assert get_proxy_server(use_proxy=False) is None
	assert get_playwright_proxy(use_proxy=False) is None
