#!/usr/bin/python

import AAshe.utils.request
import AAshe.utils.ratelimit
import AAshe.sqlite

import aiohttp

# This file is just to keep the methods counting on the same endpoint.


class LolStatusEndpoint(AAshe.sqlite.MessagePrint):
	__method_limit__ = None

	@classmethod
	@AAshe.utils.ratelimit.method_limited(refresh_cooldown=3600, name="Summoner-V3", use_lock=True)
	async def request_lolstatus(
			cls,
			region: str,
			aiosession: aiohttp.ClientSession,
			url: str,
			headers: dict,
			timeout: int=10,
			count: bool=True,
			_cls=None):

		return await AAshe.utils.request.make_riot_request(
			aiosession=aiosession,
			url=url,
			region=region,
			headers=headers,
			timeout=timeout,
			count=count,
			cls=_cls or cls)
