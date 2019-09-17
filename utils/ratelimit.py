import AAshe.utils.config as config
import AAshe.sqlite
import time
import asyncio
import logging


class RateLimit:
	
	logger = logging.getLogger(__name__)
	key_limit = None  # type: RateLimit
	margin_of_error = 0.0
	# The amount of seconds added to wait time.
	
	key_refresh_cooldown = 0
	# The time until the rate limits are refreshed from the headers.
	# 0 = Disabled (It will retrieve it once but not again)
	
	class Region:
		
		__quiet__ = False
		
		class Limit:
			
			__quiet__ = False
			
			__slots__ = (
				"period",  # type: int
				"every",  # type: float
				
				"first_call",  # type: float
				"calls",  # type: int
			)
			
			def __init__(self, period, every):
				self.period = period
				self.every = every
				
				self.first_call = 0.0
				self.calls = 0
			
			def __repr__(self):
				return "<{}/{}s:count-{}, {}>".format(self.period, self.every, self.calls, self.calls == self.period)
		
		__slots__ = (
			"region",  # type: str
			"limits",  # type: ['Limit']
			
			"time",  # type: float
			
			"lock"  # type: asyncio.Lock
		)
		
		def __init__(self, region: str, lock: bool):
			self.region = region
			self.limits = list()
			
			self.time = 0
			
			if lock:
				self.lock = asyncio.Lock()
			else:
				self.lock = None
		
		def __repr__(self):
			return "<{0.region}:{0.period}:{0.every}>".format(self)
		
		def add_limit(self, limit: Limit):
			self.limits.append(limit)
	
	__slots__ = (
		"name",  # type: str
		"time",  # type: float
		"use_lock",  # type: bool
		"region_limits"  # type: dict
	)
	
	def __init__(self, name: str, use_lock=True):
		self.name = name
		self.use_lock = use_lock
		self.time = time.time()
		self.region_limits = {}
	
	def set_calls(self, region: str, period: int, calls: int):
		if region.lower() not in self.region_limits:
			self.logger.info(msg="Region was not within dictionary, adding.")
		
		region_limit = self.region_limits[region.lower()]
		
		for limit in region_limit.limits:
			if limit.period == period and region_limit.region == region.lower():
				limit.calls = calls
	
	def add_limit(self, period, every, region, count=0):
		if region.lower() not in self.region_limits:
			self.region_limits[region.lower()] = self.__class__.Region(region=region, lock=self.use_lock)
			self.logger.info(msg="Region was not within dictionary, adding.")
		
		region_limit = self.region_limits[region.lower()]
		
		for limit in region_limit.limits:
			if limit.period == period and limit.every == every and region_limit.region == region.lower():
				self.logger.warning(msg="Unable to add limit due to existing one")
				return False
		
		region_limit.add_limit(RateLimit.Region.Limit(period=period, every=every))
		return True
	
	async def check_cooldown(self, region: str, count: bool= True) -> None or int:
		"""Checks the limits and how many requests are made."""
		# Checks if more time than `every` has passed.
		if region.lower() not in self.region_limits:
			self.logger.info(msg="Region was not within dictionary, adding.")
			self.region_limits[region.lower()] = self.__class__.Region(region=region, lock=self.use_lock)
			return True
		
		region_limit = self.region_limits[region.lower()]
		
		# You might ask why the fuck I did this.
		# The same limit class is used for method limits and api key limits.
		# And I dont want to lock down an entire region because of it.
		# Though this does create a potential hazard if you use more than one asyncio Loop.
		if self.use_lock:
			with await region_limit.lock:
				return await self.process_cooldown(region_limit=region_limit, count=count)
		return await self.process_cooldown(region_limit=region_limit, count=count)
	
	async def process_cooldown(self, region_limit: Region, count: bool):
		limit_reset = []
		time_to_sleep = 0
		for limit in region_limit.limits:
			t = self.process_limit(limit=limit, limit_reset=limit_reset, count=count)
			
			if t > time_to_sleep:
				time_to_sleep = t
		
		if time_to_sleep > 0:
			self.logger.critical(msg=f"LIMIT: waiting for cooldown. {time_to_sleep + self.margin_of_error}s")
			await asyncio.sleep(time_to_sleep + self.margin_of_error)
		
		if limit_reset:
			for limit in limit_reset:
				limit.first_call = time.time()
		
		del limit_reset
	
	@staticmethod
	def process_limit(limit: Region.Limit, limit_reset: list, count: bool) -> int:
		time_to_sleep = 0
		
		# In case time window has expired, and its starting again.
		# - Adds the limit to note the time when it fires a request.
		if time.time() - limit.first_call > limit.every:
			limit_reset.append(limit)
			limit.calls = 0
		
		# # A calculation so it waits the exact amount until it goes off cooldown. (Only keeps the highest wait time)
		# - Also adds the limit to note when it start counting again.
		elif limit.calls >= limit.period:
			if limit.every - (time.time() - limit.first_call) > time_to_sleep:
				time_to_sleep = limit.every - (time.time() - limit.first_call)
				limit_reset.append(limit)
			limit.calls = 0
		
		if count:
			limit.calls += 1
		
		return time_to_sleep
	
	def __repr__(self):
		return "<{}>".format(self.name)


def method_limited(refresh_cooldown=3600, name=None, use_lock=True):
	"""
	Prevent a method from being called
	if it was previously called before
	a time widows has elapsed.

	:param int refresh_cooldown: Amount of time before it refreshes.
	:param str name: Name of the limiter.
	:param bool count: If it should count on the api key. (Not all endpoints count on it)
	:param bool use_lock: If to use the asyncio locks to lock down regions.
	:return: Decorated function that will forward method invocations if the time window has elapsed.
	"""
	
	def decorator(func: asyncio.coroutine):
		"""
		Extend the behaviour of the following
		function, forwarding method invocations
		if the time window hes elapsed.

		:param function func: Function to decorate
		"""

		# To get around issues with function local scope
		# and reassigning variables, we wrap the time
		# within a list.
		async def wrapper(cls: AAshe.sqlite.SQLite, region: str, *args, **kwargs):
			"""Decorator wrapper function"""
			
			# Insures there is a Rate Limit object
			if cls.method_limit is None:
				cls.method_limit = RateLimit(name=name or func.__name__)

			# Checks the rate limits
			await cls.method_limit.check_cooldown(region=region)

			response = await func(*args, cls=cls, region=region, **kwargs)  # type: (bytes, dict,)

			if not response:
				RateLimit.logger.warning(msg="[Method]Failure: Empty reponse from {}".format(func.__name__))
				return None

			resp_data, resp_headers = response

			# Insures region is within the dictionary.
			if region.lower() not in cls.method_limit.region_limits:
				cls.info("[Error]: Region was not within dictionary, adding.")
				cls.method_limit.region_limits[region.lower()] = RateLimit.Region(
					region=region,
					lock=use_lock)
			
			region_limit = cls.method_limit.region_limits[region.lower()]  # type: RateLimit.Region

			if "X-Method-Rate-Limit" in resp_headers and "X-Method-Rate-Limit-Count" in resp_headers:
				if time.time() - region_limit.time > refresh_cooldown:
					if refresh_cooldown != 0 or not region_limit.limits:
						# Cleanup old
						if isinstance(region_limit.limits, list):
							for i, limit in enumerate(region_limit.limits):
								del region_limit.limits[i]
						region_limit.limits = []

						# Prepare new
						rate_limits = {}
						for str_limit in resp_headers["X-Method-Rate-Limit"].strip().split(","):
							period, every = str_limit.split(":", 1)
							rate_limits[int(every)] = int(period)

						rate_limit_count = {}
						for str_limit in resp_headers["X-Method-Rate-Limit-Count"].strip().split(","):
							rate_count, every = str_limit.split(":", 1)
							rate_limit_count[int(every)] = int(rate_count)

						# Adds them
						for every in list(rate_limits.keys()):
							if cls.method_limit.add_limit(
									period=rate_limits[every],
									every=float(every),
									region=region,
									count=rate_limit_count[every]):
								cls.info(
									msg=f"[Method] LIMIT: added limit <{rate_limits[every]}/{every}s> with count {rate_limit_count[every]}.")

				region_limit.time = time.time()
			
			return resp_data
		
		return wrapper
	
	return decorator


async def async_main():
	limit = RateLimit(name="LimitTest")
	limit.add_limit(period=3, every=10, region="euw1")
	limit.add_limit(period=1, every=2, region="euw1")
	
	for i in range(100):
		print("### Number {} ###".format(i + 1))
		await limit.check_cooldown(region="euw1")
		print(limit.region_limits["euw1"].limits)
		print("Makes a request")
		print("################")


def main():
	loop = asyncio.get_event_loop()
	loop.run_until_complete(async_main())
	loop.run_forever()


if __name__ == "__main__":
	main()