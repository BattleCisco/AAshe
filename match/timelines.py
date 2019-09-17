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


class Frame(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"timestamp",  # type: int
		"participantFrames",  # type: {int, ParticipantFrame}
		"events",  # type: [Event]
	)
	
	def __repr__(self):
		return "<{}>".format(self.timestamp)
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		# self.participantFrames = []
		for k in list(kwargs["participantFrames"].keys()):
			self.participantFrames[k] = ParticipantFrame(**kwargs["participantFrames"][k])
		self.events = [Event(**kw) for kw in kwargs["events"]]


class ParticipantFrame(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"totalGold",  # type: int
		"teamScore",  # type: int
		"participantId",  # type: int
		"level",  # type: int
		"currentGold",  # type: int
		"minionsKilled",  # type: int
		"dominionScore",  # type: int
		"position",  # type: Position
		"xp",  # type: int
		"jungleMinionsKilled",  # type: int
		
		"region",
	)
	
	def __repr__(self):
		return "<{}:{}>".format(self.participantId, self.level)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		if "position" in kwargs and kwargs["position"]:
			self.position = Position(**kwargs["position"])
		else:
			self.position = None


class Position(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"y",  # type: int
		"x",  # type: int
	)
	
	def __repr__(self):
		return "<{}:{}>".format(self.x, self.y)


class Event(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"eventType",  # type: str
		"towerType",  # type: str
		"teamId",  # type: int
		"ascendedType",  # type: str
		"killerId",  # type: int
		"levelUpType",  # type: str
		"pointCaptured",  # type: str
		"assistingParticipantIds",  # type: [int]
		"wardType",  # type: str
		"monsterType",  # type: str
		"type",  # type: str
		# Legal values:
		# CHAMPION_KILL, WARD_PLACED, WARD_KILL, BUILDING_KILL, ELITE_MONSTER_KILL, ITEM_PURCHASED,
		# ITEM_SOLD, ITEM_DESTROYED, ITEM_UNDO, SKILL_LEVEL_UP, ASCENDED_EVENT, CAPTURE_POINT, PORO_KING_SUMMON
		
		"skillSlot",  # type: int
		"victimId",  # type: int
		"timestamp",  # type: int
		"afterId",  # type: int
		"monsterSubType",  # type: str
		"laneType",  # type: str
		"itemId",  # type: int
		"participantId",  # type: int
		"buildingType",  # type: str
		"creatorId",  # type: int
		"position",  # type: Position
		"beforeId",  # type: int
	)
	
	def __repr__(self):
		return "<{}:{}>".format(self.participantId, self.eventType)


class Timeline(AAshe.sqlite.SQLite):
	"""
	Timeline with frames of a played game.
	"""

	table_name = "aashe_timelines"
	request_cooldown__ = 0
	
	__slots__ = (
		"frames",  # type: [Frame]
		"frameInterval",  # type: int
		
		"matchId",  # type: int
		"time",  # type: float
		"region"  # type: str
	)
	
	variable_names = AAshe.sqlite.SQLiteVariableNames(
		integer=["frameInterval"],
		integer_key=["matchId"],
		real=["time"],
		text=["frames"],
		text_key=["region"])
	
	def __init__(self, **kwargs):
		for k in self.__class__.__slots__:
			setattr(self, k, kwargs.get(k, None))
	
	def __repr__(self):
		return "<{}:{}:{}>".format(self.region, self.matchId, self.frameInterval)
	
	@classmethod
	async def get_timeline(cls, region, aiosession, match_id: int or str):
		"""
		Gets a Timeline for a match using match ID from the Riot API.

		Args:
			region (str): The region searched on.
			aiosession (aiohttp.ClientSession): The aiosession used for the async search.
			match_id (int): Match ID to get Timeline for.

		Returns:
			LiveMatch: If found, it returns a type LiveMatch.
			None: Else if nothing is returned.

		Raises:
			BadRequest: The request cannot be fulfilled due to bad syntax.
			Unauthorized: Error code response for missing or invalid API key.
			Forbidden: The request was a legal request, but the server is
				refusing to respond to it. Unlike a 401 Unauthorized
				response, authenticating will make no difference.
			DataNotFound: The requested resource could not be found but may
				be available again in the future. Subsequent requests
				by the client are permissible.
			MethodNotAllowed: A request was made of a resource using a request
				method not supported by that resource.
			UnsupportedMediaType: The request entity has a media type which the
				server does not support.
			RateLimitExceeded: The user has sent too many requests in a given amount
				of time.
			InternalServerError: The general catch-all error when the server-side
				throws an exception.
			BadGateway: The server was acting as a gateway or proxy and
				received an invalid response from the upstream server.
			ServiceUnavailable: The server is currently unavailable (because it is
				overloaded or down for maintenance).
			GatewayTimeout: The server was acting as a gateway or proxy and did
				not receive a timely response from the upstream server.

			>>> AAshe.utils.ratelimit.RateLimit.__loudness__ = 0
			>>> summoners.Summoner.__loudness__ = 0
			>>> LiveMatch.__loudness__ = 0

			>>> conn = sqlite3.connect("database.db")
			>>> AAshe.utils.config.Config.initiate(api_key="RGAPI-498880b9-d3e9-4f45-98e6-b5f66721e28b", conn=conn)
			>>> summoners.Summoner.init_database(c=conn.cursor(), conn=conn)
			>>> LiveMatch.init_database(c=conn.cursor(), conn=conn)
			>>> _summoner = AAshe.utils.config.run_async(summoners.Summoner.get_summoner, region="euw1", summonerName="godbro sama loyal")
			>>> g = AAshe.utils.config.run_async(LiveMatch.get_game, region="euw1", summonerId=_summoner.summonerId)
			>>> isinstance(g, LiveMatch)
			True
		
			Gets a time-line by using the ID for the match.

			Parameters
			-----------
			region : str
				Region related to the call.
			aiosession : aiohttp.ClientSession
				The aiosession which will be used to make the request.
			match_id : int
				The ID for the match which timeline should be retrieved.

			Returns
			--------
			Timeline or None
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
		
		data = cls.read_all_data(matchId=int(match_id), region=region, order_by=[cls.desc("time")])
		if data:
			if time.time() - data[0].time < cls.__request_cooldown__:
				game = data[0]

				game.frames = [Frame(**kw) for kw in json.loads(game.frames)]

				cls.safe_print(
					"Found matchId {} in database".format(match_id),
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
		url = "https://{}.api.riotgames.com" + "/lol/match/v3/timelines/by-match/{}?api_key={}".format(
			match_id,
			AAshe.utils.config.Config.get_api_key())
		
		if url:
			cls.safe_print(
				"Making a webrequest with matchId {}".format(match_id),
				title=cls.__name__,
				subtitle=None,
				colour=AAshe.sqlite.BColors.OKGREEN,
				level=3)

			resp_data = await AAshe.match.match.MatchEndpoint.request_timeline(
				aiosession=aiosession,
				url=url,
				region=region,
				headers={})
			
			kwargs = json.loads(resp_data.decode())
			kwargs["matchId"] = int(match_id)
			kwargs["region"] = region
			kwargs["time"] = time.time()
			kwargs["frames"] = [Frame(**kw) for kw in kwargs["frames"]]
			
			game = cls(**kwargs)
			game.write_data()
		
		return game


async def async_main(aiosession: aiohttp.ClientSession):
	game = await Timeline.get_timeline(region="euw1", aiosession=aiosession, match_id=3482810381)
	print(game)
	pass


def main():
	loop = asyncio.get_event_loop()
	aiosession = aiohttp.ClientSession(loop=loop)
	
	conn = sqlite3.connect("database.db")
	AAshe.utils.config.Config.initiate(api_key="RGAPI-498880b9-d3e9-4f45-98e6-b5f66721e28b", conn=conn)
	Timeline.init_database(c=conn.cursor(), conn=conn)

	loop.run_until_complete(async_main(aiosession=aiosession))  # suebegedei
	loop.run_forever()


if __name__ == "__main__":
	import doctest
	doctest.testmod()