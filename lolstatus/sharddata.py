import AAshe.utils.config
import AAshe.utils.request
import AAshe.utils.ratelimit
import AAshe.sqlite

import AAshe.lolstatus.lolstatus

import asyncio
import aiohttp
import sqlite3
import time
import json
import copy

import typing


class Translation(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"locale",  # type: str
		"content",  # type: str
		"updated_at"  # type: str
	)

	def __repr__(self):
		return f"<{self.locale}:{self.updated_at}>"


class Message(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"severity",  # type: str
		"author",  # type: str
		"created_at",  # type: str
		"translations",  # type: typing.Union[Translation]
		"updated_at",  # type: str
		"content",  # type: str
		"id"  # type: str
	)

	def __repr__(self):
		return f"<{self.id}:{self.updated_at}>"


class Incident(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"active",  # type:	bool
		"created_at",  # type:	str
		"id",  # type: int
		"updates",  # type:	typing.Union[Message]
	)

	def __repr__(self):
		return f"<{self.id}:{self.active}>"


class Service(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"status",  # type: str
		"incidents",  # type: typing.Union[Incident]
		"name",  # type: str
		"slug",  # type: str
	)

	def __repr__(self):
		return f"<{self.name}:{self.slug}>"


class ShardStatus(AAshe.sqlite.SQLite):
	"""
	Represent a Shard retrieved from the Riot API.
	"""

	__table_name__ = "aashe_shard"
	__request_cooldown__ = 0
	__loudness__ = 4

	__slots__ = (
		"name",  # type: str
		"region_tag",  # type: str
		"hostname",  # type: str
		"services",  # type: typing.List[Service]
		"slug",  # type: str
		"locales",  # type: typing.List[str]
		"region",

		"time",  # type: float
	)
	
	__null__ = []
	__null_key__ = []
	__integer__ = []
	__integer_key__ = []
	__real__ = ["time"]
	__real_key__ = []
	__text__ = [
		"name",
		"region_tag",
		"hostname",
		"slug",
		
		"services",
		"locales"
	]
	__text_key__ = [
		"region"
	]
	__blob__ = []
	__blob_key__ = []

	def __init__(self, **kwargs):
		for k in self.__class__.__slots__:
			setattr(self, k, kwargs.get(k, None))

	def __repr__(self):
		return f"<{self.region}:{self.region_tag}:{self.hostname}>"

	@classmethod
	async def get_shardstatus(
			cls,
			region: str,
			aiosession: aiohttp.ClientSession) -> typing.Union['ShardStatus', None]:
		"""
			Gets a match by it's id.

			Args:
				region: str
					The region searched on.
				aiosession: :class: `aiohttp.ClientSession`
					The aiosession used for the async search.

			Returns:
				ShardStatus:
					If found, it returns a type Match.
				None:
					Else if nothing is returned.

			Raises:
				BadRequest:
					The request cannot be fulfilled due to bad syntax.
				Unauthorized:
					Error code response for missing or invalid API key.
				Forbidden:
					The request was a legal request, but the server is
					refusing to respond to it. Unlike a 401 Unauthorized
					response, authenticating will make no difference.
				DataNotFound:
					The requested resource could not be found but may
					be available again in the future. Subsequent requests
					by the client are permissible.
				MethodNotAllowed:
					A request was made of a resource using a request
					method not supported by that resource.
				UnsupportedMediaType:
					The request entity has a media type which the
					server does not support.
				RateLimitExceeded:
					The user has sent too many requests in a given amount
					of time.
				InternalServerError:
					The general catch-all error when the server-side
					throws an exception.
				BadGateway:
					The server was acting as a gateway or proxy and
					received an invalid response from the upstream server.
				ServiceUnavailable:
					The server is currently unavailable (because it is
					overloaded or down for maintenance).
				GatewayTimeout:
					The server was acting as a gateway or proxy and did
					not receive a timely response from the upstream server.


			>>> AAshe.utils.ratelimit.RateLimit.__loudness__ = 0
			>>> ShardStatus.__loudness__ = 0
			>>> conn = sqlite3.connect("database.db")
			>>> ShardStatus.init_database(c=conn.cursor(), conn=conn)
			>>> AAshe.utils.config.Config.initiate(api_key="RGAPI-498880b9-d3e9-4f45-98e6-b5f66721e28b", conn=conn)

			>>> AAshe.utils.config.run_async(ShardStatus.get_shardstatus, region="euw1")
			<euw1:eu:prod.euw1.lol.riotgames.com>
		"""
		shard = None
		data = cls.read_all_data(region_tag=region, order_by=[cls.desc("time")])

		if data:
			if time.time() - data[0].time < cls.__request_cooldown__:
				shard = data[0]
				shard.services = [Service(**kwargs) for kwargs in json.loads(shard.services)]

				cls.safe_print(
					"Found shard still active in cache.",
					title=cls.__name__,
					colour=AAshe.sqlite.BColors.OKGREEN,
					level=4)
			else:
				for d in data:
					d.del_data(commit=False)
				cls.commit()

		if shard:
			return shard

		url = "https://{}.api.riotgames.com" + \
			f"/lol/status/v3/shard-data?api_key={AAshe.utils.config.Config.get_api_key()}"

		if url:
			cls.safe_print(
				f"Making a webrequest({url}) to shard-data",
				title=cls.__name__,
				colour=AAshe.sqlite.BColors.OKGREEN,
				level=4)

			resp_data = await AAshe.lolstatus.lolstatus.LolStatusEndpoint.request_lolstatus(
				aiosession=aiosession,
				url=url,
				region=region,
				headers={},
				_cls=cls)

			kwargs = json.loads(resp_data.decode())
			kwargs["region"] = region
			kwargs["time"] = time.time()
			kwargs["services"] = [Service(**kwargs) for kwargs in kwargs["services"]]

			shard = cls(**kwargs)
			shard.write_data()

		return shard


if __name__ == "__main__":
	#import doctest

	#doctest.testmod()
	AAshe.utils.ratelimit.RateLimit.__loudness__ = 4
	ShardStatus.__loudness__ = 4

	conn = sqlite3.connect("database.db")
	ShardStatus.init_database(c=conn.cursor(), conn=conn)
	AAshe.utils.config.Config.initiate(api_key="RGAPI-498880b9-d3e9-4f45-98e6-b5f66721e28b", conn=conn)

	print(AAshe.utils.config.run_async(ShardStatus.get_shardstatus, region="euw1"))
