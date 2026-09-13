import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from checkin import (
	is_session_expired,
	get_user_info,
	check_in_account_with_retry,
)
from utils.config import AccountConfig, AppConfig


def test_is_session_expired_status_code_401():
	assert is_session_expired(401, text='{"message":"unauthorized"}') is True
	assert is_session_expired(401, text='') is True


def test_is_session_expired_ignores_waf_html():
	# WAF 返回的 HTML 挑战页即使包含 401/403 也不应误判为 Session 过期
	html = '<html><head><title>Aliyun WAF</title></head><body>Captcha</body></html>'
	assert is_session_expired(401, text=html) is False
	assert is_session_expired(403, text=html) is False


def test_is_session_expired_keywords_in_data():
	assert is_session_expired(200, data={'success': False, 'message': '用户未登录'}) is True
	assert is_session_expired(200, data={'success': False, 'message': '登录已过期，请重新登录'}) is True
	assert is_session_expired(200, data={'success': False, 'message': 'New-Api-User 与登录用户不匹配'}) is True
	assert is_session_expired(200, data={'success': True, 'data': {}}) is False


def test_get_user_info_handles_session_expired():
	mock_client = MagicMock()
	mock_response = MagicMock()
	mock_response.status_code = 401
	mock_response.text = '{"message": "未登录或登录已过期", "success": false}'
	mock_response.json.return_value = {'message': '未登录或登录已过期', 'success': False}
	mock_client.get.return_value = mock_response

	result = get_user_info(mock_client, {}, 'https://example.com/api/user/self')
	assert result['success'] is False
	assert result.get('session_expired') is True
	assert 'Session 已过期或失效' in result['error']


def test_get_user_info_handles_waf_html_challenge():
	mock_client = MagicMock()
	mock_response = MagicMock()
	mock_response.status_code = 200
	mock_response.text = '<html><script src="waf.js"></script></html>'
	mock_response.json.side_effect = ValueError('Expecting value: line 1 column 1')
	mock_client.get.return_value = mock_response

	result = get_user_info(mock_client, {}, 'https://example.com/api/user/self')
	assert result['success'] is False
	assert result.get('session_expired') is not True
	assert 'WAF challenge' in result['error'] or 'Expecting value' in result['error']


@pytest.mark.asyncio
async def test_check_in_account_with_retry_succeeds_first_attempt():
	account = AccountConfig(name='TestUser', cookies={'session': 'dummy'})
	app_config = AppConfig(providers={})

	with patch('checkin.check_in_account', new_callable=AsyncMock) as mock_checkin:
		mock_checkin.return_value = (True, {'success': True, 'quota': 10, 'used_quota': 0}, {'success': True, 'quota': 10, 'used_quota': 0})
		
		success, before, after = await check_in_account_with_retry(account, 0, app_config, max_retries=2, retry_delay=0)
		assert success is True
		assert mock_checkin.call_count == 1


@pytest.mark.asyncio
async def test_check_in_account_with_retry_retries_transient_failure():
	account = AccountConfig(name='TestUser', cookies={'session': 'dummy'})
	app_config = AppConfig(providers={})

	with patch('checkin.check_in_account', new_callable=AsyncMock) as mock_checkin:
		# 第一次失败（WAF 错误），第二次成功
		mock_checkin.side_effect = [
			(False, None, {'success': False, 'error': 'WAF challenge'}),
			(True, {'success': True, 'quota': 10, 'used_quota': 0}, {'success': True, 'quota': 10, 'used_quota': 0}),
		]
		
		success, before, after = await check_in_account_with_retry(account, 0, app_config, max_retries=2, retry_delay=0)
		assert success is True
		assert mock_checkin.call_count == 2


@pytest.mark.asyncio
async def test_check_in_account_with_retry_bails_out_on_session_expired():
	account = AccountConfig(name='TestUser', cookies={'session': 'dummy'})
	app_config = AppConfig(providers={})

	with patch('checkin.check_in_account', new_callable=AsyncMock) as mock_checkin:
		# 第一次即报告 session_expired，不应继续进行第二次重试
		mock_checkin.return_value = (False, None, {'success': False, 'error': 'Session 已过期', 'session_expired': True})
		
		success, before, after = await check_in_account_with_retry(account, 0, app_config, max_retries=2, retry_delay=0)
		assert success is False
		assert mock_checkin.call_count == 1
