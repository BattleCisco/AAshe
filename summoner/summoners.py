import typing
import aiohttp
import sqlite3
import time
import json

import AAshe.utils.config as config
import AAshe.utils.request
import AAshe.utils.ratelimit
import AAshe.sqlite
import AAshe.summoner.summoner


class Summoner(AAshe.sqlite.SQLite):
	"""
	Representation of a summoner(Player) in League of Legends.
	
	Attributes:
		profileIconId (int): ID of the summoner icon associated with the summoner.
		name (str): Summoner name.
		summonerLevel (int): Summoner level associated with the summoner.
		revisionDate (str): Date summoner was last modified specified as
			epoch milliseconds. The following events will update this timestamp:
			profile icon change, playing the tutorial or advanced tutorial,
			finishing a game, summoner name change.
		id (int): ID of the summoner icon associated with the summoner.
		accountId (int): Account ID.
		time (float): UNIX time when the entry was retrieved from the API.
		region (str): Which regional endpoint this Summoner is playing on.
	"""
	
	table_name = "AAshe_summoner"
	request_cooldown = 0
	variable_names = AAshe.sqlite.SQLiteVariableNames(
		integer=["profileIconId", "summonerLevel", "revisionDate", "accountId"],
		integer_key=["id"],
		real=["time"],
		text=["name"],
		text_key=["region"])
	
	__slots__ = (
		"profileIconId",  # type: int
		"name",  # type: str
		"summonerLevel",  # type: int
		"revisionDate",  # type: str
		"id",  # type: int
		"accountId",  # type: int
		"time",  # type: float
		"region",  # type: str
	)
	
	@property
	def summonerId(self)->int:
		"""ID and SummonerID is both used, to clear the confusion, summonerID returns ID."""
		return self.id
	
	@summonerId.setter
	def summonerId(self, value: int):
		"""Sets the ID."""
		setattr(self, "id", value)  # Identical to self.id = value
	
	def __init__(self, **kwargs):
		for k in self.__class__.__slots__:
			setattr(self, k, kwargs.get(k, None))
	
	def __repr__(self):
		return f"<{self.id}:{self.name}:{self.accountId}>"
	
	@classmethod
	async def get_summoner(
			cls,
			region: str,
			aiosession: aiohttp.ClientSession,
			*,
			summoner_name: str=None,
			summoner_id: int=None,
			account_id: int=None)->typing.Union['Summoner', None]:
		"""
		Gets a summoner from the League by Summoner ID, Account ID or Name.
		If more than one of these is filled, the priority is
		summoner_id > account_id > summoner_name

		Args:
			region (str): The region searched on.
			aiosession (aiohttp.ClientSession): The aiosession used for the async search.
			summoner_name (str): If this is not None, it will search by name.
			summoner_id (int): If this is not None, it will search by summoner ID.
			account_id (int): If this is not None, it will search by account ID.

		Returns:
			Summoner:
				If found, it returns a type summoner.
			None:
				Else, nothing is returned.
		
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

			>>> conn = sqlite3.connect("database.db")
			>>> AAshe.utils.config.Config.initiate(api_key="RGAPI-498880b9-d3e9-4f45-98e6-b5f66721e28b", conn=conn)
			>>> Summoner.init_database(c=conn.cursor(), conn=conn)

			>>> type(AAshe.utils.config.run_async(Summoner.get_summoner, region="euw1", summoner_name="Adde r2")) is Summoner
			True
			>>> AAshe.utils.config.run_async(Summoner.get_summoner, region="euw1", summoner_name="Adde r2")
			<euw1:adde r2:41>
		"""

		if not(summoner_name or summoner_id or account_id):
			cls.critical(msg="Incorrect parameters passed, return none.")
		
		data = None
		summoner = None
		
		if summoner_id is not None:
			data = cls.read_all_data(id=summoner_id, region=region.lower(), order_by=[cls.desc("time")])

		elif account_id is not None:
			data = cls.read_all_data(account_id=account_id, region=region.lower(), order_by=[cls.desc("time")])

		elif summoner_name is not None:
			data = cls.read_all_data(name=summoner_name.lower(), region=region.lower(), order_by=[cls.desc("time")])

		if data:
			if time.time() - data[0].time < cls.request_cooldown:
				summoner = data[0]
				
				cls.debug(msg=f"Found Summoner({summoner.id}) in cache.")
			else:
				for d in data:
					d.del_data(commit=False)
				cls.commit()
		
		if summoner:
			return summoner
		
		if summoner_id is not None:
			url = "https://{}.api.riotgames.com" + "/lol/summoner/v3/summoners/{}?api_key={}".format(
				summoner_id, config.Config.get_api_key())
			cls.debug(msg=f"Making a webrequest with Summoner ID {summoner_id}")

		elif account_id is not None:
			url = "https://{}.api.riotgames.com" + "/lol/summoner/v3/summoners/by-account/{}?api_key={}".format(
				account_id, config.Config.get_api_key())
			cls.debug(msg=f"Making a webrequest with Account ID {account_id}")

		elif summoner_name is not None:
			url = "https://{}.api.riotgames.com" + "/lol/summoner/v3/summoners/by-name/{}?api_key={}".format(
				summoner_name, config.Config.get_api_key())
			cls.debug(msg=f"Making a webrequest with Summoner Name {summoner_name}")
		
		else:
			return None
			
		if url:
			resp_data = await AAshe.summoner.summoner.SummonerEndpoint.\
				request_summoner(aiosession=aiosession, url=url, region=region, headers={}, _cls=cls)  # type: bytes
			
			kwargs = json.loads(resp_data.decode())
			kwargs["region"] = region.lower()
			kwargs["time"] = time.time()
			kwargs["name"] = kwargs["name"].lower()
			
			summoner = cls(**kwargs)
			summoner.write_data()
		
		return summoner  # type: typing.Union[Summoner, None]


if __name__ == "__main__":
	import doctest
	doctest.testmod()
