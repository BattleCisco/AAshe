from AAshe.utils.config import *
from AAshe.utils.request import *
from AAshe.utils.ratelimit import *
from AAshe.sqlite import *

import asyncio
import aiohttp
import sqlite3
import time
import json
import copy
import AAshe.summoner


class Service(SQLiteSubClass):
	__slots__ = (
		"status",  # type: str
		"incidents",  # type: [Incident]
		"name",  # type: str
		"slug"  # type: str
	)
	
	def __repr__(self):
		return "<{}:{}>".format(self.name, self.status)
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		
		self.incidents = [Incident(**kw) for kw in kwargs["incidents"]]


class Incident(SQLiteSubClass):
	__slots__ = (
		"active",  # type: bool
		"created_at",  # type: str
		"id",  # type: int
		"updates"  # type: [Message]
	)
	
	def __repr__(self):
		return "<{}:{}>".format(self.id, self.created_at)
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		
		self.updates = [Message(**kw) for kw in kwargs["updates"]]


class Message(SQLiteSubClass):
	__slots__ = (
		"severity",  # type: str
		"author",  # type: str
		"created_at",  # type: str
		"translations",  # type: [Translation]
		"updated_at",  # type: str
		"content",  # type: str
		"id"  # type: str
	)
	
	def __repr__(self):
		return "<{}:{}>".format(self.id, self.created_at)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		
		self.translations = [Translation(**kw) for kw in kwargs["translations"]]


class Translation(SQLiteSubClass):
	__slots__ = (
		"locale",  # type: str
		"content",  # type: str
		"updated_at"  # type: str
	)
	
	def __repr__(self):
		return "<{}:{}>".format(self.locale, self.locale)


class Status(SQLite):
	__slots__ = (
		"name",  # type: str
		"region_tag",  # type: str
		"hostname",  # type: str
		"services",  # type: [Service]
		"slug",  # type: str
		"locales",  # type: [str]
		
		"region",
		"time"
	)
	
	__silent__ = False
	__request_cooldown__ = 0
	__method_limit__ = None
	
	__table_name__ = "aashe_lol_status"
	
	__null__ = []
	__null_key__ = []
	__integer__ = []
	__integer_key__ = []
	__real__ = ["time"]
	__real_key__ = []
	__text__ = [
		"name",  # type: str
		"hostname",  # type: str
		"region_tag",  # type: str
		"locales",  # type: [str]
		"slug",  # type: str
		
		"services",  # type: [Service]
	]
	__text_key__ = ["region"]
	__blob__ = []
	__blob_key__ = []
	
	def __init__(self, **kwargs):
		for k in self.__class__.__slots__:
			setattr(self, k, kwargs.get(k, None))
	
	def __repr__(self):
		return "<{}:{}:{}>".format(self.region_tag, self.name, self.slug)
	
	@classmethod
	async def get_status(cls, region, aiosession):
		game = None
		
		# Searches the database (Cache)
		data = cls.read_all_data(region=region.lower(), order_by=[cls.desc("time")])
		print(data)
		if data:
			if time.time() - data[0].time < cls.__request_cooldown__:
				game = data[0]
				
				game.services = [Service(**kw) for kw in json.loads(game.services)]
				
				print("Found from database!")
			else:
				print("Entry in database outdated, updating.")
				for d in data:
					d.del_data(commit=False)
				cls.commit()
		
		if game:
			return game
		
		# Makes a web request
		url = "https://{}.api.riotgames.com" + "/lol/status/v3/shard-data?api_key={}".format(Config.get_api_key())
		
		print("Making web request!")
		resp_data = await cls.request_status(aiosession=aiosession, url=url, region=region, headers={})
		
		kwargs = json.loads(resp_data.decode())
		kwargs["region"] = region
		kwargs["time"] = time.time()
		kwargs["services"] = [Service(**kw) for kw in kwargs["services"]]
		
		status = cls(**kwargs)
		status.write_data()
		
		return status

	@classmethod
	@method_limited(refresh_cooldown=3600, name="Summoner", use_lock=True)
	async def request_status(cls, region: str, aiosession: aiohttp.ClientSession, url: str, headers: dict,
	                           timeout: int=10, count=False):
		return await make_riot_request(
			aiosession=aiosession,
			url=url,
			region=region,
			headers=headers,
			timeout=timeout,
			count=count)


async def async_main(aiosession: aiohttp.ClientSession):
	#status = await Status.get_status(region="euw1", aiosession=aiosession)
	#print(game.matches[0])
	#print_object(status)
	#print(status)
	s = await Status.get_status(region="euw1", aiosession=aiosession)
	print(s)
	s = await Status.get_status(region="euw1", aiosession=aiosession)
	print(s)
	print("Done")


def main():
	loop = asyncio.get_event_loop()
	aiosession = aiohttp.ClientSession(loop=loop)
	
	conn = sqlite3.connect("database.db")
	Config.initiate(api_key="RGAPI-498880b9-d3e9-4f45-98e6-b5f66721e28b", conn=conn)
	Status.init_database(c=conn.cursor(), conn=conn)
	AAshe.summoner.Summoner.init_database(c=conn.cursor(), conn=conn)
	
	loop.run_until_complete(async_main(aiosession=aiosession))  # suebegedei
	loop.run_forever()


if __name__ == "__main__":
	main()
