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
import copy
import AAshe.summoner.summoners


class Player(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"currentPlatformId",  # type: str
		"summonerName",  # type: str
		"matchHistoryUri",  # type: str
		"platformId",  # type: str
		"currentAccountId",  # type: int
		"profileIcon",  # type: int
		"summonerId",  # type: int
		"accountId",  # type: int
		
		"region"  # type: str
	)
	
	def __repr__(self):
		return f"<{self.region}:{self.summonerId}>"


class ParticipantIdentity(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"player",  # type: Player
		"participantId",  # type: int
		
		"region"  # type: str
	)
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		
		kwargs["region"] = self.region
		self.player = Player(**kwargs["player"])
	
	def __repr__(self):
		return f"<{self.participantId}:id>"


class TeamBan(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"pickTurn",  # type: int
		"championId"  # type: int
	)

	def __repr__(self):
		return "<{}:{}>".format(self.pickTurn, self.championId)


class TeamStats(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"firstDragon",  # type: bool
		"firstInhibitor",  # type: bool
		"baronKills",  # type: int
		"firstRiftHerald",  # type: bool
		"firstBaron",  # type: bool
		"riftHeraldKills",  # type: int
		"firstBlood",  # type: bool
		"teamId",  # type: int
		"firstTower",  # type: bool
		"vilemawKills",  # type: int
		"inhibitorKills",  # type: int
		"towerKills",  # type: int
		"dominionVictoryScore",  # type: int
		"win",  # type: str
		"dragonKills",  # type: int
		
		"bans"  # type: [TeamBan]
	)
	
	def __repr__(self):
		return "<{}:{}>".format(self.teamId, self.win)
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		
		self.bans = [TeamBan(**kw) for kw in kwargs["bans"]]


class ParticipantStats(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"physicalDamageDealt",  # type: int
		"neutralMinionsKilledTeamJungle",  # type: int
		"magicDamageDealt",  # type: int
		"totalPlayerScore",  # type: int
		"deaths",  # type: int
		"win",  # type: bool
		"neutralMinionsKilledEnemyJungle",  # type: int
		"altarsCaptured",  # type: int
		"largestCriticalStrike",  # type: int
		"totalDamageDealt",  # type: int
		"magicDamageDealtToChampions",  # type: int
		"visionWardsBoughtInGame",  # type: int
		"damageDealtToObjectives",  # type: int
		"largestKillingSpree",  # type: int
		"item1",  # type: int
		"quadraKills",  # type: int
		"teamObjective",  # type: int
		"totalTimeCrowdControlDealt",  # type: int
		"longestTimeSpentLiving",  # type: int
		"wardsKilled",  # type: int
		"firstTowerAssist",  # type: bool
		"firstTowerKill",  # type: bool
		"item2",  # type: int
		"item3",  # type: int
		"item0",  # type: int
		"firstBloodAssist",  # type: bool
		"visionScore",  # type: int
		"wardsPlaced",  # type: int
		"item4",  # type: int
		"item5",  # type: int
		"item6",  # type: int
		"turretKills",  # type: int
		"tripleKills",  # type: int
		"damageSelfMitigated",  # type: int
		"champLevel",  # type: int
		"nodeNeutralizeAssist",  # type: int
		"firstInhibitorKill",  # type: bool
		"goldEarned",  # type: int
		"magicalDamageTaken",  # type: int
		"kills",  # type: int
		"doubleKills",  # type: int
		"nodeCaptureAssist",  # type: int
		"trueDamageTaken",  # type: int
		"nodeNeutralize",  # type: int
		"firstInhibitorAssist",  # type: bool
		"assists",  # type: int
		"unrealKills",  # type: int
		"neutralMinionsKilled",  # type: int
		"objectivePlayerScore",  # type: int
		"combatPlayerScore",  # type: int
		"damageDealtToTurrets",  # type: int
		"altarsNeutralized",  # type: int
		"physicalDamageDealtToChampions",  # type: int
		"goldSpent",  # type: int
		"trueDamageDealt",  # type: int
		"trueDamageDealtToChampions",  # type: int
		"participantId",  # type: int
		"pentaKills",  # type: int
		"totalHeal",  # type: int
		"totalMinionsKilled",  # type: int
		"firstBloodKill",  # type: bool
		"nodeCapture",  # type: int
		"largestMultiKill",  # type: int
		"sightWardsBoughtInGame",  # type: int
		"totalDamageDealtToChampions",  # type: int
		"totalUnitsHealed",  # type: int
		"inhibitorKills",  # type: int
		"totalScoreRank",  # type: int
		"totalDamageTaken",  # type: int
		"killingSprees",  # type: int
		"timeCCingOthers",  # type: int
		"physicalDamageTaken"  # type: int
	)

	def __repr__(self):
		return "<{}:{}>".format(self.participantId, self.champLevel)


class ParticipantTimeline(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"lane",  # type: str
		"participantId",  # type: int
		"csDiffPerMinDeltas",  # type: {str: float}
		"goldPerMinDeltas",  # type:  {str: float}
		"xpDiffPerMinDeltas",  # type: {str: float}
		"creepsPerMinDeltas",  # type: {str: float}
		"xpPerMinDeltas",  # type: {str: float}
		"role",  # type: str
		"damageTakenDiffPerMinDeltas",  # type: {str: float}
		"damageTakenPerMinDeltas"  # type: {str: float}
	)

	def __repr__(self):
		return "<{}:{}>".format(self.participantId, self.lane)


# TODO: Replace with Runes Reforged.
class Rune(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"runeId",  # type: int
		"rank"  # type: int
	)

	def __repr__(self):
		return "<{}:{}>".format(self.runeId, self.rank)


class Mastery(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"masteryId",  # type: int
		"rank"  # type: int
	)

	def __repr__(self):
		return "<{}:{}>".format(self.masteryId, self.rank)


class Participant(AAshe.sqlite.SQLiteSubClass):
	__slots__ = (
		"participantId",  # type: int
		"teamId",  # type: int
		"spell2Id",  # type: int
		"highestAchievedSeasonTier",  # type: str
		"spell1Id",  # type: int
		"championId",  # type: int
		
		"stats",  # type: ParticipantStats
		"timeline",  # type: ParticipantTimeline
		
		# "runes",  # type: [Rune]
		# "masteries",  # type: [Mastery]
		# For the time being, these aren't operational
		
		"region"  # type: str
	)
	
	def __repr__(self):
		return "<{}:{}>".format(self.teamId, self.championId)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		
		self.stats = ParticipantStats(**kwargs["stats"])
		self.timeline = ParticipantTimeline(**kwargs["timeline"])
		# self.runes = [Rune(**kw) for kw in kwargs["runes"]]
		# self.masteries = [Mastery(**kw) for kw in kwargs["masteries"]]


class Match(AAshe.sqlite.SQLite):
	"""
	Represent an finished match retrieved from the Riot API.
	"""

	__table_name__ = "aashe_matches"
	__request_cooldown__ = 0
	__loudness__ = 4

	__slots__ = (
		"seasonId",  # type: int
		"queueId",  # type: int
		"gameId",  # type: int
		"gameVersion",  # type: str
		"platformId",  # type: str
		"gameMode",  # type: str
		"mapId",  # type: int
		"gameType",  # type: str
		"gameDuration",  # type: int
		"gameCreation",  # type: int
		
		"participantIdentities",  # type: [ParticipantIdentity]
		"participants",  # type: [Participant]
		"teams",  # type: [TeamStats]
		
		# "matchId",  # type: int
		"time",  # type: float
		"region"  # type: str
	)

	__null__ = []
	__null_key__ = []
	__integer__ = [
		"seasonId",
		"queueId",
		"mapId",
		"gameDuration",
		"gameCreation",
	]
	__integer_key__ = ["matchId"]
	__real__ = ["time"]
	__real_key__ = []
	__text__ = [
		"gameVersion",
		"gameMode",
		"gameType",
		"platformId",
		"region",
		
		"teams",  # type: [TeamStats]
		"participants",  # type: [Participant]
		"participantIdentities",  # type: [ParticipantIdentity]
	]
	__text_key__ = []
	__blob__ = []
	__blob_key__ = []

	@property
	def matchId(self) -> int:
		"""gameID and matchID is the same thing."""
		return self.gameId

	@matchId.setter
	def matchId(self, value: int):
		"""Sets the ID."""
		self.gameId = value

	def __init__(self, **kwargs):
		for k in self.__class__.__slots__:
			setattr(self, k, kwargs.get(k, None))
	
	def __repr__(self):
		return "<{}:{}:{}>".format(self.region, self.gameId, self.gameMode)
	
	@classmethod
	async def get_match(
			cls,
			region: str,
			aiosession: aiohttp.ClientSession,
			match_id: str or int)-> 'Match' or None:
		"""
			Gets a match by it's id.

			Args:
				region: str
					The region searched on.
				aiosession: :class: `aiohttp.ClientSession`
					The aiosession used for the async search.
				summonerId: str or int
					summoner ID to spectate.

			Returns:
				Match:
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
			>>> Match.__loudness__ = 0

			>>> conn = sqlite3.connect("database.db")
			>>> AAshe.utils.config.Config.initiate(api_key="RGAPI-498880b9-d3e9-4f45-98e6-b5f66721e28b", conn=conn)
			>>> Match.init_database(c=conn.cursor(), conn=conn)

			>>> type(AAshe.utils.config.run_async(Match.get_match, region="euw1", match_id=3482810381)) is Match
			True
			>>> AAshe.utils.config.run_async(Match.get_match, region="euw1", match_id=3482810381)
			<euw1:3482810381:CLASSIC>
		"""
		game = None
		data = cls.read_all_data(matchId=int(match_id), order_by=[cls.desc("time")])

		if data:
			if time.time() - data[0].time < cls.__request_cooldown__:
				game = data[0]
				
				game.teams = [TeamStats(**kw) for kw in json.loads(game.teams)]
				game.participants = [Participant(**kw) for kw in json.loads(game.participants)]
				game.participantIdentities = [ParticipantIdentity(**kw) for kw in json.loads(game.participantIdentities)]

				cls.safe_print(
					"Found matchId {} in database".format(match_id),
					title=cls.__name__,
					colour=AAshe.sqlite.BColors.OKGREEN,
					level=4)
			else:
				for d in data:
					d.del_data(commit=False)
				cls.commit()
		
		if game:
			return game
		
		# Makes a web request
		url = "https://{}.api.riotgames.com" + "/lol/match/v3/matches/{}?api_key={}".format(
			match_id, AAshe.utils.config.Config.get_api_key())
		
		if url:
			cls.safe_print(
				"Making a webrequest with matchId {}".format(match_id),
				title=cls.__name__,
				colour=AAshe.sqlite.BColors.OKGREEN,
				level=4)

			resp_data = await AAshe.match.match.MatchEndpoint.request_match(
				aiosession=aiosession,
				url=url,
				region=region,
				headers={},
				_cls=cls)
			
			kwargs = json.loads(resp_data.decode())
			kwargs["matchId"] = int(match_id)
			kwargs["region"] = region
			kwargs["time"] = time.time()
			kwargs["teams"] = [TeamStats(**kw) for kw in kwargs["teams"]]
			
			game_participants = copy.copy(kwargs["participants"])
			kwargs["participants"] = list()
			for kw in game_participants:
				kw["region"] = region
				kwargs["participants"].append(Participant(**kw))
			
			game_participant_identities = copy.copy(kwargs["participantIdentities"])
			kwargs["participantIdentities"] = list()
			for kw in game_participant_identities:
				kw["region"] = region
				kwargs["participantIdentities"].append(ParticipantIdentity(**kw))
			
			game = cls(**kwargs)
			game.write_data()
		
		return game


if __name__ == "__main__":
	import doctest
	doctest.testmod()
