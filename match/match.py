#!/usr/bin/python

import AAshe.utils.request
import AAshe.utils.ratelimit
import AAshe.sqlite

import aiohttp

# This file is just to keep the methods counting on the same endpoint.


class MatchEndpoint(AAshe.sqlite.MessagePrint):
	__loudness__ = 4
	__method_limit__ = None

	@classmethod
	@AAshe.utils.ratelimit.method_limited(refresh_cooldown=3600, name="Match-V3", use_lock=True)
	async def request_match(
			cls,
			region: str,
			aiosession: aiohttp.ClientSession,
			url: str,
			headers: dict,
			timeout: int = 10,
			count=True,
			_cls=None)->bytes:
		return await AAshe.utils.request.make_riot_request(
			cls=_cls or cls,
			aiosession=aiosession,
			url=url,
			region=region,
			headers=headers,
			timeout=timeout,
			count=count)