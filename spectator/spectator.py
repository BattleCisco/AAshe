#!/usr/bin/python

import AAshe.utils.request
import AAshe.utils.ratelimit
import AAshe.sqlite

import aiohttp

# This file is just to keep the methods counting on the same endpoint.


class SpectatorEndpoint:
	__method_limit__ = None

	@classmethod
	@AAshe.utils.ratelimit.method_limited(refresh_cooldown=3600, name="Spectator-V3", use_lock=True)
	async def request_spectator(
			cls,
			region: str,
			aiosession: aiohttp.ClientSession,
			url: str,
			headers: dict,
			timeout: int=10,
			count: bool=True,
			_cls: AAshe.sqlite.SQLite=None)->bytes:
		"""To keep track of the calls being made.

		Args:
			region(str): Region targeted.
			aiosession(aiohttp.ClientSession):
			url(str): Region-less URL for the call
			headers(dict): Headers for the call, usually an empty dictionary.
			# Searches the database (Cache)
		timeout(int): Seconds until Timeout exception is raised.
			count(bool): If it should count on the limit.
			_cls(AAshe.sqlite.SQLite): Logger to use.

		Returns:
			bytes: Response from the call.
		"""

		return await AAshe.utils.request.make_riot_request(
			aiosession=aiosession,
			url=url,
			region=region,
			headers=headers,
			timeout=timeout,
			count=count,
			cls=_cls or cls)
