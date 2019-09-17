from typing import Union

import AAshe.errors as errors
import AAshe.utils.ratelimit as ratelimit
import AAshe.sqlite

import aiohttp
import time
import json


async def make_riot_request(
	cls: AAshe.sqlite.SQLite, aiosession: aiohttp.ClientSession, region: str, url: str, headers: dict, timeout: int=10, count=True) \
		->(bytes, dict):
	"""
	Makes a web request with an aiosession and returns the data.

	Args:
		cls: AAshe.sqlite.MessagePrint
			Used to broadcast status messages.
		aiosession:
			aiosession used to make the request.
		region:
			Region used in the request.
		url:
			URL to call.
		headers:
			Headers used for the call, usually empty.
		timeout:
			Timeout timer.
		count:
			If it should count on the rate limit.

	Returns:
		(bytes, dict)
			Contains the raw data, and the return headers.
	"""
	# Insures there is a Rate Limit object
	if ratelimit.RateLimit.key_limit is None:
		ratelimit.RateLimit.key_limit = ratelimit.RateLimit(name="Api Key Limit")
	
	# Checks the rate limits
	await ratelimit.RateLimit.key_limit.check_cooldown(region=region, count=count)
	
	resp_data = None
	resp_headers = None
	# Makes actual request
	with aiohttp.Timeout(timeout):
		async with aiosession.get(url=url.format(region.lower()), headers=headers) as resp:
			resp_data = await resp.read()
			resp_headers = resp.headers
	
	if region.lower() not in ratelimit.RateLimit.key_limit.region_limits:
		cls.info(msg="Region was not within dictionary, adding.")
		ratelimit.RateLimit.key_limit.region_limits[region.lower()] = ratelimit.RateLimit.Region(
			region=region,
			lock=True)
	
	region_limit = ratelimit.RateLimit.key_limit.region_limits[region.lower()]
	
	if resp_headers:
		if "X-App-Rate-Limit" in resp_headers and "X-App-Rate-Limit-Count" in resp_headers:
			if time.time() - region_limit.time > ratelimit.RateLimit.key_refresh_cooldown:
				if ratelimit.RateLimit.key_refresh_cooldown != 0 or not region_limit.limits:
					# Cleanup old
					if isinstance(region_limit.limits, list):
						for i, limit in enumerate(region_limit.limits):
							del region_limit.limits[i]
					region_limit.limits = []
					
					# Prepare new
					rate_limits = {}
					for str_limit in resp_headers["X-App-Rate-Limit"].strip().split(","):
						period, every = str_limit.split(":", 1)
						
						rate_limits[int(every)] = int(period)
					
					rate_limit_count = {}
					for str_limit in resp_headers["X-App-Rate-Limit-Count"].strip().split(","):
						count, every = str_limit.split(":", 1)
						
						rate_limit_count[int(every)] = int(count)
					
					# Adds them
					for every in list(rate_limits.keys()):
						if ratelimit.RateLimit.key_limit.add_limit(
								period=rate_limits[every],
								every=float(every),
								region=region,
								count=rate_limit_count[every]):
							
							cls.debug(msg=f"Added limit <{rate_limits[every]}/{every}s> with count {rate_limit_count[every]}.")

	if "status" in json.loads(resp_data.decode()):
		exceptions = \
			{
				# You fucked up
				400: errors.BadRequest,
				401: errors.Unauthorized,
				403: errors.Forbidden,
				404: errors.DataNotFound,
				405: errors.MethodNotAllowed,
				415: errors.UnsupportedMediaType,
				429: errors.RateLimitExceeded,

				# Server fucked up
				500: errors.InternalServerError,
				502: errors.BadGateway,
				503: errors.ServiceUnavailable,
				504: errors.GatewayTimeout
			}
		
		exception = exceptions[json.loads(resp_data.decode())["status"]["status_code"]]
		exception.server_message = json.loads(resp_data.decode())["status"]["message"]
		raise exception
	
	return resp_data, resp_headers


a