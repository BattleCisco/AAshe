import traceback
import sqlite3
import json
import sys
import typing
import logging


class SQLiteSubClass:
	"""
	The class is used to assist with having more enhancing
	the object orientation on the SQLite objects.
	"""
	__slots__ = []
	
	def __init__(self, **kwargs):
		for k in self.__class__.__slots__:
			try:
				getattr(self, k)
			except AttributeError:
				setattr(self, k, kwargs.get(k, None))
	
	def before_dumping(self)->dict:
		"""This function should return the properly formatted string ready for injection into the SQLite database."""
		d = {}
		for k in self.__class__.__slots__:
			d[k.replace("_", "", 1)] = self.prepare_value(getattr(self, k))
		return d
	
	def prepare_value(self, v):
		"""Prepares a value to be injected into the sqlite database."""
		if isinstance(v, SQLiteSubClass):
			return v.before_dumping()
		elif isinstance(v, list):
			li = list()
			for e in v:
				li.append(self.prepare_value(e))
			return li
		elif type(v) is dict:
			d = {}
			for k in list(v.keys()):
				d[k] = self.prepare_value(v[k])
			return d
		return v


class SQLiteVariableNames:
	"""Represents the values variables used to write to a database."""
	
	__slots__ = [
		"_null",	"_null_key",
		"_integer", "_integer_key",
		"_real", "_real_key",
		"_text", "_text_key",
		"_blob", "_blob_key"
	]
	
	@property
	def null(self):
		return self.null
	
	@property
	def null_key(self):
		return self.null_key
	
	@property
	def integer(self):
		return self.null
	
	@property
	def integer_key(self):
		return self.null_key
	
	@property
	def real(self):
		return self._real
	
	@property
	def real_key(self):
		return self._real_key
	
	@property
	def text(self):
		return self._text
	
	@property
	def text_key(self):
		return self._text_key
	
	@property
	def blob(self):
		return self.blob
	
	@property
	def blob_key(self):
		return self._blob_key
	
	def __init__(
			self,
			null: list=None, null_key: list=None,
			integer: list=None, integer_key: list=None,
			real: list=None, real_key: list=None,
			text: list=None, text_key: list=None,
			blob: list=None, blob_key: list=None):
		
		self._null = null if null else []
		self._null_key = null_key if null_key else []
		self._integer = integer if integer else []
		self._integer_key = integer_key if integer_key else []
		self._real = real if real else []
		self._real_key = real_key if real_key else []
		self._text = text if text else []
		self._text_key = text_key if text_key else []
		self._blob = blob if blob else []
		self._blob_key = blob_key if blob_key else []
	
	def non_keys(self):
		names = list()
		names.extend(self.null)
		names.extend(self.integer)
		names.extend(self.real)
		names.extend(self.text)
		names.extend(self.blob)
		return names
		
	def keys(self):
		names = list()
		names.extend(self.null_key)
		names.extend(self.integer_key)
		names.extend(self.real_key)
		names.extend(self.text_key)
		names.extend(self.blob_key)
		return names


class SQLite:
	"""
	Represents a SQLite writable object.
	"""
	
	class Order:
		__slots__ = ("query",)
		
		def __init__(self, query):
			self.query = query
	
	class Ascending(Order):
		"""Internally used class, please don't create object of this."""
	
	class Descending(Order):
		"""Internally used class, please don't create object of this."""
	
	logger = logging.getLogger(__name__)
	table_name = None
	conn = None  # type: sqlite3.Connection
	variable_names = None  # type: SQLiteVariableNames
	
	@classmethod
	def set_logger_level(cls, level: int):
		return cls.logger.setLevel(level)
	
	@classmethod
	def debug(cls, msg: str, *args, **kwargs):
		cls.logger.debug(msg=msg, *args, **kwargs)
	
	@classmethod
	def info(cls, msg: str, *args, **kwargs):
		cls.logger.info(msg=msg, *args, **kwargs)
	
	@classmethod
	def warning(cls, msg: str, *args, **kwargs):
		cls.logger.warning(msg=msg, *args, **kwargs)
	
	@classmethod
	def critical(cls, msg: str, *args, **kwargs):
		cls.logger.critical(msg=msg, *args, **kwargs)
	
	@staticmethod
	def print_exc():
		traceback.print_exc()
	
	@classmethod
	def ascending(cls, name)->Ascending:
		"""
		This is for people who prefer to write the full word instead of just `asc`
		"""
		return cls.asc(name=name)
		
	@classmethod
	def asc(cls, name)->Ascending:
		"""
		Returns the part of the query used to sort by ascending order.
		
		Args:
			name (str): Variable name which should be sort ascending

		Returns:
			Ascending
			
		Raises:
			ValueError: If the name is not recognized.

		"""
		args_names, keys_names = cls.get_names()
		args_names = [arg.lower for arg in args_names]
		keys_names = [key.lower for key in keys_names]
		if name.lower() in args_names or name.lower() in keys_names:
			return cls.Ascending(query="{} ASC".format(name))
		raise ValueError("Name not recognized.")
	
	@classmethod
	def descending(cls, name)->Descending:
		"""
		This is for people who prefer to write the full word instead of just `desc`
		"""
		return cls.desc(name=name)
	
	@classmethod
	def desc(cls, name)->Descending:
		"""
		Returns the part of the query used to sort by descending order.

		Args:
			name (str): Variable name which should be sort descending

		Returns:
			Descending

		Raises:
			ValueError: If the name is not recognized.

		"""
		args_names, keys_names = cls.get_names()
		args_names = [arg.lower for arg in args_names]
		keys_names = [key.lower for key in keys_names]
		if name.lower() in args_names or name.lower() in keys_names:
			return cls.Descending(query="{} DESC".format(name))
		raise ValueError("Name not recognized.")
	
	@classmethod
	def commit(cls):
		"""Commits the recent journal to the database."""
		cls.conn.commit()

	@classmethod
	def get_names(cls)->typing.Tuple[typing.List[str], typing.List[str]]:
		"""Returns two lists with the argument and key arguments names."""
		args_names = cls.variable_names.non_keys()
		keys_names = cls.variable_names.keys()

		return args_names, keys_names
	
	def prepare_value(self, value: typing.Union[list, dict, object])->typing.Union[list, dict, object]:
		"""Prepares a value for writing.
		
		To make the writing process go smoothly, this is used to
		recursively store all values and sub-values into states that can be written.
		
		Args:
			value(list, dict, object):

		Returns:
			list: If a list was provided.
			dict: If a dictionary was provided.
			object: If an object was provided.

		"""
		if isinstance(value, SQLiteSubClass):
			return value.before_dumping()
		elif type(value) is list:
			li = []
			for o in value:
				li.append(self.prepare_value(o))
			return li
		elif type(value) is dict:
			d = {}
			for k in list(value.keys()):
				d[k] = self.prepare_value(value[k])
			return d
		else:
			return value
			
	def get_values(self)->(typing.List[str], typing.List[object], typing.List[str], typing.List[object]):
		"""Returns the values and names of the variables.
		
		Returns:
			tuple(list, list, list, list)

		"""
		args_names, keys_names = self.__class__.get_names()
		
		args = list()
		for arg in args_names:
			value = self.prepare_value(value=getattr(self, arg, None))
			if isinstance(getattr(self, arg, None), list) or \
				isinstance(getattr(self, arg, None), dict) or \
				isinstance(getattr(self, arg, None), SQLiteSubClass):
				value = json.dumps(value)
			args.append(value)

		keys = list()
		for key in keys_names:
			value = self.prepare_value(value=getattr(self, key, None))
			if isinstance(getattr(self, key, None), list) or \
				isinstance(getattr(self, key, None), dict) or \
				isinstance(getattr(self, key, None), SQLiteSubClass):
				value = json.dumps(value)
			keys.append(value)

		return args_names, args, keys_names, keys

	def read_data(self, **kwargs):
		"""Reads data from the database assuming keys are set if they are in use.
		
		Args:
			**kwargs(dict): This can be used to read more specifically.

		Returns:
			bool: If the read was successful or not.
		"""
		args_names, args, keys_names, keys = self.get_values()
		if args:
			args_names.extend(keys_names)
			args.extend(keys)

			for key in list(kwargs.keys()):
				i = args_names.index(key)
				args_names.pop(i)
				args.pop(i)

				keys_names.append(key)
				keys.append(kwargs.get(key))

		query = "SELECT {} FROM {}".format(", ".join(args_names), self.table_name or self.__class__.__name__)

		if keys_names:

			query += " WHERE {}".format(" AND ".join([key_name + "=(?)" for key_name in keys_names]))
		
		self.logger.debug(msg="-> QUERY : {} , {}".format(query, keys))
		self.conn.cursor().execute(query, keys)

		data = self.conn.cursor().fetchone()

		if data:
			self.logger.debug(msg="-> DATA {}".format(data))
			for i, name in enumerate(args_names):
				setattr(self, name, data[i])

			return True

		else:
			for name in args_names:
				setattr(self, name, None)

			return False

	@classmethod
	def read_all_data(
			cls,
			order_by: typing.List['SQLite.Order']=None,
			limit: int=None, **kwargs)->['SQLite']:
		"""Reads and returns a list following the rules specified.
		
		Args:
			order_by(list): Specifies how the results should be ordered.
			limit(int): Limit how many entries should be returned.
			**kwargs: Specifies certain values the result must have.
		"""
		
		args_names, keys_names = cls.get_names()
		args_names.extend(keys_names)

		query = "SELECT {} FROM {}".format(", ".join(args_names), cls.table_name or cls.__name__)
		
		args = None
		
		if kwargs:

			query += " WHERE {}".format(" AND ".join([key_name + "=(?)" for key_name in list(kwargs.keys())]))
			args = list(kwargs.values())
		
		if order_by:
			
			if not isinstance(order_by, list):
				raise ValueError("order_by type must be list.")
			
			for order in order_by:
				if not isinstance(order, cls.Order):
					raise ValueError(f"Incorrect value was passed to into order_by. ({order_by})")
			
			query += " ORDER BY {}".format(", ".join([order.query for order in order_by]))
		
		if limit:
			query += " LIMIT {}".format(limit)

		if kwargs:
			cls.logger.debug(msg="-> QUERY : {} , {}".format(query, args))
			cls.conn.cursor().execute(query, args)

		else:
			cls.logger.debug(msg="-> QUERY : {}".format(query))
			cls.conn.cursor().execute(query)

		data = cls.conn.cursor().fetchall()
		
		if data:
			entries = list()

			for entry in data:
				_object = cls()
				for i, arg in enumerate(args_names):
					setattr(_object, arg, entry[i])
				entries.append(_object)
			return entries
		return []

	def write_data(self, commit: bool=True)->bool:
		"""Writes to the database, or updates the entry with the the same keys.
		
		Args:
			commit(bool): If it should commit the journal to the database when finished.

		Returns:
			bool: If it managed to write it.
		"""
		args_names, args, keys_names, keys = self.get_values()

		query = "SELECT * FROM {}".format(self.table_name or self.__class__.__name__)

		if keys_names:
			query += " WHERE {}".format(" AND ".join([key_name + "=(?)" for key_name in keys_names]))
		
		self.logger.debug(msg="-> QUERY : {} , {}".format(query, keys))
		self.conn.cursor().execute(query, keys)

		if self.conn.cursor().fetchone():

			query = "UPDATE {} SET {}".format(
				self.table_name or self.__class__.__name__,
				", ".join([args_name + "=(?)" for args_name in args_names]))

			if keys_names:
				query += " WHERE {}".format(" AND ".join([key_name + "=(?)" for key_name in keys_names]))

			args.extend(keys)

			self.logger.debug(msg=f"-> QUERY : {query} , {args}")
			self.conn.cursor().execute(query, args)

		else:

			args_names.extend(keys_names)
			args.extend(keys)

			query = "INSERT INTO {}({}) VALUES ({})".format(
				self.table_name or self.__class__.__name__, ", ".join(args_names),
				", ".join(["?" for _ in args_names]))

			self.logger.debug(msg=f"-> QUERY : {query} , {args}")
			self.conn.cursor().execute(query, args)

		if commit:
			self.commit()

		return True

	def insert_data(self, commit=True, abort_if_key_are_none=False)->bool:
		"""Inserts
		
		Args:
			commit(bool): Commit the journal to the database when finished.
			abort_if_key_are_none(bool): If true this will abort the writing
				if a attribute is found to be None

		Returns:

		"""
		args_names, args, keys_names, keys = self.get_values()

		if abort_if_key_are_none:
			for i, key in enumerate(keys):
				if key is None:
					self.logger.warning(msg=f"Aborted insertion due to {keys_names[i]} being None.")
					return False

		args_names.extend(keys_names)
		args.extend(keys)

		query = "INSERT INTO {}({}) VALUES ({})".format(
			self.table_name or self.__class__.__name__,
			", ".join(args_names),  ", ".join(["?" for _ in args_names]))

		self.logger.debug(msg=f"-> QUERY : {query} , {args}")
		self.conn.cursor().execute(query, args)

		if commit:
			self.commit()

		return True

	def del_data(self, commit=True)->None:
		"""Deletes the entries that matches ALL attributes of the current instance.
		
		Args:
			commit(bool): Commit the journal to the database when finished.

		Returns:
			None
			
		"""
		args_names, args, keys_names, keys = self.get_values()

		args_names.extend(keys_names)
		args.extend(keys)

		query = "DELETE FROM {} WHERE {}".format(
			self.table_name or self.__class__.__name__,
			" AND ".join([arg_name + "=(?)" for arg_name in args_names]))

		self.logger.debug(msg=f"-> QUERY : {query}, {args}")
		self.conn.cursor().execute(query, args)

		if commit:
			self.commit()

	def print_data(self)->None:
		"""Prints all the data from the instance.
		
		Returns:
			None

		"""
		
		args_names, args, keys_names, keys = self.get_values()
		print("#" * 40)
		print("Information for {}".format(self.table_name or self.__class__.__name__))
		print("#" * 40)
		for i, arg in enumerate(args_names):
			print("[SQL]: Args - [{}] - [{}] - [{}]".format(arg, args[i], type(args[i])))
		print("#" * 40)
		for i, key in enumerate(keys_names):
			print("[SQL]: Args - [{}] - [{}] - [{}]".format(key, keys[i], type(args[i])))
		print("#" * 40)

	@classmethod
	def create_table(cls)->str:
		"""Returns the query for creating the table required by the class."""
		create_names = []
		
		create_names.extend([f"{entry} NULL" for entry in cls.variable_names.null])
		create_names.extend([f"{entry} INTEGER" for entry in cls.variable_names.integer])
		create_names.extend([f"{entry} REAL" for entry in cls.variable_names.real])
		create_names.extend([f"{entry} TEXT" for entry in cls.variable_names.text])
		create_names.extend([f"{entry} BLOB" for entry in cls.variable_names.blob])
		
		create_names.extend([f"{entry} NULL" for entry in cls.variable_names.null_key])
		create_names.extend([f"{entry} INTEGER" for entry in cls.variable_names.integer_key])
		create_names.extend([f"{entry} REAL" for entry in cls.variable_names.real_key])
		create_names.extend([f"{entry} TEXT" for entry in cls.variable_names.text_key])
		create_names.extend([f"{entry} BLOB" for entry in cls.variable_names.blob_key])
	
		query = "CREATE TABLE IF NOT EXISTS {}({})".format(cls.table_name or cls.__name__, ", ".join(create_names))

		return query

	@classmethod
	def init_database(cls, conn: sqlite3.Connection, commit:bool =True)->None:
		"""Writes the needed templates to the database, also saves the database connection for further usage.
		
		Args:
			conn(sqlite3.Connection): Connection to the sqlite3 database used
			commit(bool):

		Returns:
			None

		"""
		cls.conn = conn
		
		query = cls.create_table()
		cls.logger.debug(msg=f"-> QUERY : {query}")
		cls.conn.cursor().execute(query)

		if commit:
			cls.commit()

	
def init_table(c: sqlite3.Cursor, conn: sqlite3.Connection, new_table, commit=True):
	c.execute(new_table.create_table)
	
	if commit:
		conn.commit()

