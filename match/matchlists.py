import AAshe.utils.config
import AAshe.utils.request
import AAshe.utils.ratelimit
import AAshe.sqlite

import AAshe.match.match

import asyncio
import aiohttp
import sqlite3
import time
import json


class MatchReference(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"lane",  # type: str
		"gameId",  # type: int
		"champion",  # type: int
		"platformId",  # type: str
		"season",  # type: int
		"queue",  # type: int
		"role",  # type: str
		"timestamp"  # type: int
	)
	
	def __repr__(self):
		return "<{}:{}>".format(self.gameId, self.lane)


class MatchList(AAshe.sqlite.SQLite):
	"""Matchlist for summoner in League of Legends.

	Public Attributes:
	------------
	__table_name_: str
		SQLite table name used inside the cache.
	__request_cooldown__: int
		Time until a cache entry is deemed to be too old and require a refresh.
	__loudness__:str
		Prints various things of interest depending on current value.

	Attributes:
		matches: [MatchReference]
			List of matches.
		totalGames: int
			Total Games.
		startIndex: int
			Where it began counting the matches.
		endIndex: int
			Where it stopped counting the matches.

		accountId: int):
		matchId: int
			ID for the match.
		time: float
			The time this object was created
		region: str
			The region summoner plays on.

	"""

	__table_name__ = "aashe_history_match"
	__request_cooldown__ = 0
	__loudness__ = 4

	__slots__ = (
		"matches",  # type: [MatchReference]
		"totalGames",  # type: int
		"startIndex",  # type: int
		"endIndex",  # type: int
		
		"accountId",  # type: int
		"time",  # type: float
		"region"  # type: str
	)
	
	__null__ = []
	__null_key__ = []
	__integer__ = [
		"totalGames",
		"startIndex",
		"endIndex",
		"gameCreation"
	]
	__integer_key__ = ["accountId"]
	__real__ = ["time"]
	__real_key__ = []
	__text__ = [
		"matches"  # type: [MatchReference]
	]
	__text_key__ = ["region"]
	__blob__ = []
	__blob_key__ = []
	
	def __init__(self, **kwargs):
		for k in self.__class__.__slots__:
			setattr(self, k, kwargs.get(k, None))
	
	def __repr__(self):
		return "<{}:{}:{}>".format(self.region, self.accountId, self.startIndex)
	
	@classmethod
	async def get_matchlist(
		cls,
		region,
		aiosession,
		account_id,
		begin_time: int = None,
		end_time: int=None,
		begin_index: int = None,
		end_index: int = None,
		champion: [int]=None,
		queue: [int]=None,
		season: [int]=None,
		recent=False)->'MatchList':
		"""
			Gets a match by it's id.

			Args:
				region: str):
					Region related to the call.
				aiosession: aiohttp.ClientSession
					The aiosession which will be used to make the request.
				account_id: int
					The account involved.
				begin_time: int
					The starting point for the counting. If < 3 Years
				end_time: int
					Counter to starting point. Still if < 3 Years
				begin_index: int
					Iterate all the things!
				end_index: in
					Maybe not all the things?E
				champion: [int]
					Filter for champion
				queue: [int]
					Filter for queue
				season: [int]
					Filter for season.
				recent: bool
					Gets the most recent games.

			Returns
			--------
			Matchlist or None
				It returns the match if it exists, otherwise it return None.

			Raises
			------
			BadRequest
				The request cannot be fulfilled due to bad syntax.
			Unauthorized
				Error code response for missing or invalid API key.
			Forbidden
				The request was a legal request, but the server is
				refusing to respond to it. Unlike a 401 Unauthorized
				response, authenticating will make no difference.
			DataNotFound
				The requested resource could not be found but may
				be available again in the future. Subsequent requests
				by the client are permissible.
			MethodNotAllowed
				A request was made of a resource using a request
				method not supported by that resource.
			UnsupportedMediaType
				The request entity has a media type which the
				server does not support.
			RateLimitExceeded
				The user has sent too many requests in a given amount
				of time.
			InternalServerError
				The general catch-all error when the server-side
				throws an exception.
			BadGateway
				The server was acting as a gateway or proxy and
				received an invalid response from the upstream server.
			ServiceUnavailable
				The server is currently unavailable (because it is
				overloaded or down for maintenance).
			GatewayTimeout
				The server was acting as a gateway or proxy and did
				not receive a timely response from the upstream server.

			>>> AAshe.utils.ratelimit.RateLimit.__loudness__ = 0
			>>> MatchList.__loudness__ = 0

			>>> conn = sqlite3.connect("database.db")
			>>> AAshe.utils.config.Config.initiate(api_key="RGAPI-498880b9-d3e9-4f45-98e6-b5f66721e28b", conn=conn)
			>>> MatchList.init_database(c=conn.cursor(), conn=conn)

			>>> type(AAshe.utils.config.run_async(MatchList.get_matchlist, region="euw1", account_id=38334548, recent=True)) is MatchList
			True
			>>> AAshe.utils.config.run_async(MatchList.get_matchlist, region="euw1", account_id=38334548, recent=True)
			<euw1:38334548:0>
		"""

		game = None
		
		# Searches the database (Cache)
		data = cls.read_all_data(accountId=account_id, region=region, order_by=[cls.desc("time")])
		if data and \
			begin_time is None and \
			end_time is None and \
			begin_index is None and \
			end_index is None and \
			champion is None and \
			queue is None and \
			season is None:

			if time.time() - data[0].time < cls.__request_cooldown__:
				game = data[0]
				
				game.matches = [MatchReference(**kw) for kw in json.loads(game.matches)]

				cls.safe_print(
					"Found accountId {} in database".format(account_id),
					title=cls.__name__,
					subtitle=None,
					colour=AAshe.sqlite.BColors.OKGREEN,
					level=3)
			else:
				for d in data:
					d.del_data(commit=False)
				cls.commit()
		
		if game:
			return game
		
		# Makes a web request
		url = "https://{}.api.riotgames.com" + "/lol/match/v3/matchlists/by-account/{}".format(account_id)
		
		if recent:
			url += "/recent"
		
		contents = ["api_key={}".format(AAshe.utils.config.Config.get_api_key())]
		
		if not recent:
			if end_time is not None:
				contents.append("endTime={}".format(end_time))
			
			if begin_time is not None:
				contents.append("beginTime={}".format(begin_time))
			
			if begin_index is not None:
				contents.append("beginIndex={}".format(begin_index))
	
			if end_index is not None:
				contents.append("endIndex={}".format(end_index))
	
			if champion is not None:
				for c in champion:
					contents.append("champion={}".format(c))
			
			if queue is not None:
				for q in queue:
					contents.append("queue={}".format(q))
	
			if season is not None:
				for s in season:
					contents.append("season={}".format(s))
		
		url += "?" + "&".join(contents)

		cls.safe_print(
			"Making a webrequest with accountId {}".format(account_id),
			title=cls.__name__,
			subtitle=None,
			colour=AAshe.sqlite.BColors.OKGREEN,
			level=3)

		resp_data = await AAshe.match.match.MatchEndpoint.request_matchlists(
			aiosession=aiosession,
			url=url,
			region=region,
			headers={},
			_cls=cls)

		kwargs = json.loads(resp_data.decode())
		kwargs["accountId"] = account_id
		kwargs["region"] = region
		kwargs["time"] = time.time()
		kwargs["matches"] = [MatchReference(**kw) for kw in kwargs["matches"]]
		
		game = cls(**kwargs)
		game.write_data()
		
		return game


if __name__ == "__main__":
	import doctest
	doctest.testmod()

