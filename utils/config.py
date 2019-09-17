import traceback
import aiohttp
import sqlite3
import asyncio

regions = [
	"BR1",
	"EUN1",
	"EUW1",
	"JP1",
	"KR",
	"LA1",
	"LA2",
	"NA1",
	"OC1",
	"TR1",
	"RU",
	"PBE1"]


class Config:
	api_key = None
	calls = 0
	
	sql_cache = True
	conn = None
	
	def __init__(self):
		pass
	
	@classmethod
	def get_api_key(cls):
		return cls.api_key
	
	# Why this?
	# One unified place to have the request method and rate limit, in case its found in local db
			
	@classmethod
	def initiate(cls, api_key, conn: sqlite3.Connection=None):
		cls.__API_KEY__ = api_key
		if conn:
			cls.__sql_cache__ = True
			cls.__conn__ = conn
			cls.__c__ = conn.cursor()


def run_async(func: asyncio.coroutine, **kwargs)->object:
	"""Allows testing within the docstrings"""
	loop = asyncio.get_event_loop()
	aiosession = aiohttp.ClientSession(loop=loop)

	try:
		kwargs["aiosession"] = aiosession
		m = loop.run_until_complete(func(**kwargs))
		# loop.run_forever()

	except:
		traceback.print_exc()
		m = None

	aiosession.close()

	return m
