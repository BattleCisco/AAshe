import AAshe.utils.config
import AAshe.utils.request
import AAshe.utils.ratelimit
import AAshe.sqlite

import AAshe.summoner.summoners as summoners
import AAshe.spectator.spectator as spectator

import typing
import asyncio
import aiohttp
import sqlite3
import time
import json
import copy


class BannedChampion(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"pickTurn",  # type: int
		"championId",  # type: int
		"teamId"  # type: int
	)
	
	def __repr__(self):
		return "<{}:{}>".format(self.championId, self.teamId)


class Perks(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"perkStyle",  # type: int
		"perkIds",  # type: int
		"perkSubStyle"  # type: int
	)
	
	def __repr__(self):
		return "<{}:{}:{}>".format(self.perkIds, self.perkIds, self.perkSubStyle)


class GameParticipant(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"profileIconId",  # type: int
		"championId",  # type: int
		"summonerName",  # type: str
		"bot",  # type: bool
		"spell2Id",  # type: int
		"teamId",  # type: int
		"spell1Id",  # type: int
		"summonerId",  # type: int
		
		"gameCustomizationObjects",  # type: [GameCustomizationObject]
		"perks",  # type: Perks
		
		"region"  # type: str
	)
	
	def __repr__(self):
		return "<{}:{}:{}>".format(self.summonerId, self.summonerName, self.championId)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		
		self.perks = Perks(**kwargs["perks"])
		self.gameCustomizationObjects = [GameCustomizationObject(**kw) for kw in kwargs["gameCustomizationObjects"]]


class GameCustomizationObject(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"category",  # type: str
		"content"  # type: str
	)
	
	def __repr__(self):
		return "<{}>".format(self.content)


class Observer(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"encryptionKey",  # type: str
	)

	def __repr__(self):
		return "<{}>".format(self.encryptionKey)


class LiveMatch(AAshe.sqlite.SQLite):
	"""
	Represents an ongoing League of Legends match.
	
	Attributes:
		gameId (int): The ID of the game
		gameStartTime (int): The game start time represented in epoch milliseconds
		platformId (str): The ID of the platform on which the game is being played
		gameMode (str): The game mode
		mapId (int): The ID of the map
		gameType (str): The game type
		bannedChampions (typing.List[BannedChampion]): Banned champion information
		observers (Observer): The observer information
		participants (typing.List[CurrentGameParticipant]): The participant information
		gameLength (int): The amount of time in seconds that has passed since the game started
		gameQueueConfigId (int): The queue type (queue types are documented on the Game Constants page)
	"""

	table_name = "aashe_live_match"
	request_cooldown = 0
	variable_names = AAshe.sqlite.SQLiteVariableNames(
		integer=["gameStartTime", "mapId", "gameLength", "gameQueueConfigId", "summonerId"],
		integer_key=["gameId"],
		real=["time"],
		text=[
			"region", "platformId", "gameMode", "gameType",
			"bannedChampions", "observers", "participants"],
		text_key=["region"])

	__slots__ = (
		"gameId",  # type: int
		"gameStartTime",  # type: int
		"platformId",  # type: str
		"gameMode",  # type: str
		"mapId",  # type: int
		"gameType",  # type: str
		"gameLength",  # type: int
		"gameQueueConfigId",  # type: int
		
		"participants",  # type: [GameParticipant]
		"bannedChampions",  # type: [BannedChampion]
		"observers",  # type: Observer
		
		"summonerId",  # type: int
		"time",  # type: float
		"region"  # type: str
	)
	
	def __init__(self, **kwargs):
		for k in self.__class__.__slots__:
			setattr(self, k, kwargs.get(k, None))
		
	def __repr__(self):
		return "<{}:{}:{}>".format(self.region, self.gameId, self.gameMode)
	
	@classmethod
	async def get_game(
			cls,
			region: str,
			aiosession: aiohttp.ClientSession,
			summoner_id: int)->typing.Union['LiveMatch', None]:
		"""
		Retrieves the data about an ongoing game of league from the Riot API.

		Args:
			region (str): The region searched on.
			aiosession (aiohttp.ClientSession): The aiosession used for the async search.
			summoner_id (int): summoner ID to spectate.

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
		"""
		game = None
		
		data = cls.read_all_data(summonerId=summoner_id, order_by=[cls.desc("time")])
		if data:
			if time.time() - data[0].time < cls.request_cooldown:
				game = data[0]
				game.bannedChampions = [BannedChampion(**kw) for kw in json.loads(game.bannedChampions)]
				game_participants = copy.copy(json.loads(game.participants))
				game.participants = list()
				for kw in game_participants:
					kw["region"] = region
					game.participants.append(GameParticipant(**kw))
				game.observers = Observer(**json.loads(game.observers))
				
				cls.debug(msg="Found search in database")
			else:
				for d in data:
					d.del_data(commit=False)
				cls.commit()
		
		if game:
			return game
		
		url = "https://{}.api.riotgames.com" + "/lol/spectator/v3/active-games/by-summoner/{}?api_key={}".format(
			summoner_id, AAshe.utils.config.Config.get_api_key())
		
		if url:
			cls.debug(msg=f"Making a webrequest with summoner_id {summoner_id}")

			resp_data = await spectator.SpectatorEndpoint.request_spectator(
				aiosession=aiosession,
				url=url,
				region=region,
				headers={})  # type: bytes
			
			kwargs = json.loads(resp_data.decode())
			
			if "status" in kwargs:
				return None
			
			kwargs["summonerId"] = summoner_id
			kwargs["region"] = region
			kwargs["time"] = time.time()
			
			kwargs["bannedChampions"] = [BannedChampion(**kw) for kw in kwargs["bannedChampions"]]
			kwargs["observers"] = Observer(**kwargs["observers"])

			game_participants = copy.copy(kwargs["participants"])
			kwargs["participants"] = list()
			for kw in game_participants:
				kw["region"] = region
				kwargs["participants"].append(GameParticipant(**kw))
				
			game = cls(**kwargs)
			game.write_data()
		
		return game


if __name__ == "__main__":
	import doctest
	doctest.testmod()
