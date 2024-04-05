'''Here defines classes used to provide code strings in other programming
	or mark-up languages, but only very simple ones.
'''

import base64
from collections.abc import Iterable as iterable
# collections.abc.Iterable can be used in type check, unlike typing.Iterable
# they are both used_
from functools import cached_property, singledispatchmethod
from itertools import cycle
from numbers import Real
import os
import struct
from typing import *



Dumpable = Union[int, float, bool, list, None]
# types that can be dumped into JSON
Self = TypeVar("Self")
# not needed since Python 3.11, but I'm using 3.8
hook_ = {"namespaces": {}}



def is_resource_location_like(path: str) -> bool:
	'''Determine whether a path is a resource location or not.
	# # #
	The criterion is rough: if a ":" is present in `path`, but is not
		followed by a slash nor a backlash, then `path` is considered
		a resource location.
	The path will be further checked in `__init__`.
	'''
	if path.count(":") == 1:
		return False if ":/" in path or ":\\" in path else True
	return False



def recognize_resource_location(path: str, ext: str,
	infix: Optional[str]=None) -> str:
	'''Check whether `path` is a resource location. If yes, expand it to
		full path; otherwise return itself unaltered.
	# # #
	`ext`: the extension that the path is expected to have, will be
		appended if there is none.
	`infix`: intermediate levels between `assets` folder and `path`.
		e.g. "textures/items"
		if None, treated as no intermediate levels.
	'''
	if not is_resource_location_like(path):
		return path
	ns, rest_path = path.split(":")
	if not os.path.splitext(rest_path)[-1]:
		rest_path += ext
	ns_dir = hook_["namespaces"][ns]
	if infix is not None:
		full_path = "/".join((
			ns_dir, ns, infix, rest_path)).replace("\\", "/")
	else:
		full_path = "/".join((ns_dir, ns, rest_path)).replace("\\", "/")
	return full_path




class Texture:

	def __init__(self, texture_path: str) -> None:
		if is_resource_location_like(texture_path):
			self.texture_path: Optional[str] = None
			self.resource_location: Optional[Tuple[str, str]] = \
				tuple(texture_path.split(":"))
			# (namespace: str, location: str)
			# LAZY, the existence of the namespace and the full path will
			# not be evaluated until used
		else:
			self.texture_path: Optional[str] = os.path.abspath(texture_path)
			# store as absolute path
			# LAZY, not evaluating whether the file exists until used
			self.resource_location: Optional[Tuple[str, str]] = None
		self.bound_shortcut: Optional[str] = None
		# if this texture is bound to a certain `GuiAnnotation` instance,
		# this will be the texture name in that context
		self._validated = False
		# whether the path has been validated
		# turns True only if `validate_path` is run without an error

	def __repr__(self) -> str:
		return f"Texture(\"{self.texture_path}\")"

	@cached_property
	def size(self) -> Tuple[int, int]:
		'''Read the size of the texture file. PNG-only.
		'''
		with open(self.texture_path, "rb") as file:
			file.read(16)
			# skip 16 bytes at the file head:
			# 8-byte signature + 4-byte chunk length
			# + 4-byte chunk type (header chunk here)
			width, = struct.unpack(">I", file.read(4))
			height, = struct.unpack(">I", file.read(4))
		return width, height

	def bind_shortcut(self, name: str) -> Self:
		self.bound_shortcut = str(name)
		return self

	def validate_path(self) -> Self:
		if self._validated:
			# has already been validated
			return self
		if self.texture_path is not None:
			# instance created with non-resource location path
			if not os.path.isfile(self.texture_path):
				raise FileNotFoundError("Bad texture path: '{}'".format(
					self.texture_path))
			self.texture_path = self.texture_path.replace("\\", "/")
			self._validated = True
			return self
		# instance created with a resource location-like path goes this far
		ns, path = self.resource_location
		if not os.path.splitext(path)[-1]:
			# no extension, suppose PNG
			path += ".png"
		full_path = (hook_["namespaces"][ns] + f"/{ns}/textures/"
			+ path.replace("\\", "/"))
		if os.path.isfile(full_path):
			self.texture_path = full_path
			self._validated = True
			return self
		raise FileNotFoundError(f"Bad resource location: '{ns}:{path}'")

	def get_preferred_path(self) -> str:
		'''Return resource locations if defined; otherwise full paths.
			Only return non-empty strings if validated.
		'''
		if not self._validated:
			return ""
		else:
			if self.resource_location is not None:
				return ":".join(self.resource_location)
			else:
				return self.texture_path



def to_data_URL(path: str, mime: str="image/png") -> str:
	'''Read and convert a file into base64 data URL (a.k.a. data URI).
	# # #
	`path`: the path string of the file.
	`mime`: the MIME type of the file, by default "img/png".
	'''
	with open(path, "rb") as file:
		data = file.read()
	return (f"data:{mime};base64,"
		+ base64.b64encode(data).decode("ASCII"))



def handle_direction_string(
	dirstr: Literal["+x", "-x", "+y", "-y"]) -> Tuple[int, int]:
	'''Turn a direction string (any of "+"|"-" "x"|"y") into a pair of
		integers. Should be further converted into a `Coord` instance
		to indicate the clipping direction of a UI element. 
	'''
	return {
		"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)
	}[dirstr]



def validated_id(id_: str) -> str:
	'''To check whether an ID is valid (matches [0-9a-zA-Z_] only).
		If not, error is raised.
	'''
	if not isinstance(id_, str):
		raise ValueError(f"ID must be a string, not {id_.__class__}")
	legal_chars = ("0123456789" "abcdefghijklmnopqrstuvwxyz"
		"ABCDEFGHIJKLMNOPQRSTUVWXYZ" "_")
	# not using RE
	if bool(set(id_) - set(legal_chars)):
		raise ValueError(f"'{id_}' is not a valid ID.")
	return id_



def camel_case(id_: str) -> str:
	'''Convert snake case string to camel case.
	'''
	segments = id_.split("_")
	return segments[0].lower() + "".join(seg.title() for seg in segments[1:])



def ordinals(ord_name: str) -> Generator[str, None, None]:
	'''Get cyclic ordinal characters (e.g. a, b, c; 甲, 乙, 丙; ...)
		of series `ord_name`. It is recommended that a series contains
		at least 40 characters, for a typical GUI might require so
		many ones to annotate.
	The series are specified in the path "./ordinaldata/*.txt".
	'''
	def _() -> Generator[str, None, None]:
		with open(f"./ordinaldata/{ord_name}.txt", "r",
			encoding="utf-8") as dfile:
			ord_nums = dfile.read().strip()
		yield from ord_nums
	return cycle(_())



class ObjectProvider:
	'''A class used to provide JSON objects (as Python dictionaries).
	# # #
	field names must be specified when creating instances. Once set, the
		fields are not recommended to be altered, i.e. one instance is
		supposed only to build objects (dictionaries) with the same set
		of keys.
	'''

	def __init__(self, *fields: str, **defaults: Any):
		self.fields = tuple(validated_id(fn) for fn in fields)
		self.defaults = {fn: self.to_dumpable(fdef) \
			for fn, fdef in defaults.items() if fn in self.fields}

	def __call__(self, **args):
		built: Dict[str, Dumpable] = {}
		for fn in self.fields:
			if fn in args:
				built[fn] = self.to_dumpable(args[fn])
			else:
				built[fn] = self.defaults[fn]
			# if a defined field name is neither found in `args` nor in
			# `self.defaults`, an error is caused.
		return built

	@singledispatchmethod
	@classmethod
	def to_dumpable(cls, value: Any) -> Dumpable:
		'''Try to convert `value` to objects supported by JSON.
		'''
		raise ValueError("This is not dumpable.")

	@to_dumpable.register(Real)
	@classmethod
	def _(cls, value: Real) -> Dumpable:
		'''`int`, `float`, `bool` will go here.
		'''
		return value

	@to_dumpable.register(str)
	@classmethod
	def _(cls, value: str) -> Dumpable:
		return value

	@to_dumpable.register(iterable)
	@classmethod
	def _(cls, value: iterable) -> Dumpable:
		'''Convert iterables to lists of dumpables by recursion.
		'''
		return [cls.to_dumpable(i) for i in value]



class RawExp:
	'''Signify an expression in the goal language, rather than a string.
		Used in `AssignmentStatementProvider`.
	'''

	def __init__(self, name: str) -> None:
		self._ = str(name)

	def __str__(self) -> str:
		return self._



class AssignmentStatementProvider:
	'''A class used to provide assignment statements according to given
		styles. The default style is Java-like.
	# # #
	`prefixes` comes first. If None, none will be added.
	`type_signature` examples:
		"before":	Point p
		"after":	p: Point
		"::after":	p::Point
	`sign`: which symbol (or sequence of symbols) is/are used to link
		left-hand-side and right-hand-side.
	`new`: whether a "new" is needed to create a new instance.
	`semicolon`: whether a trailing semicolon at the end of the
		statement is needed.
	`type_literal_map` defines what to do with Python stringified objects
		to convert them into literals in the goal language. Each value is
		a 2-tuple, whence #0 is a string formatter, and #1 is a `Callable`
		that is called before the strings are formatted.
	'''

	def __init__(self, class_name: str,
		prefixes: Optional[Iterable[str]]=("private", "static", "final"),
		type_signature: Union[Literal["before", "after", "::after"],
			None]="before",
		sign: str="=",
		new: bool=True,
		semicolon: bool=True,
		type_literal_map: Mapping[type, Tuple[str,
			Optional[Callable[[str], str]]]]={
				str: ('"{}"', None), bool: ("{}", str.lower),
				type(None): ("null", None)
			}
	) -> None:
		if type_signature == "before":
			lhs = class_name + " {}"
		elif type_signature == "after":
			lhs = "{}: " + class_name
		elif type_signature == "::after":
			lhs = "{}::" + class_name
		else:
			raise ValueError("Unsupported type signature type.")
		if prefixes is not None:
			lhs = " ".join(prefixes) + " " + lhs
		rhs = class_name + "({})"
		if new:
			rhs = "new " + rhs
		if semicolon:
			rhs += ";"
		self.template = " ".join((lhs, sign, rhs))
		self.type_literal_map = type_literal_map.copy()
		# this should be type-checked in the future

	def __call__(self, var_name: str, *parameters: Any) -> str:
		par_strings = []
		for par in parameters:
			ptype, pstr = type(par), str(par)
			if ptype in self.type_literal_map:
				formatter, postprocessor = self.type_literal_map[ptype]
				if postprocessor is None:
					pstr = formatter.format(pstr)
				else:
					pstr = formatter.format(postprocessor(pstr))
			par_strings.append(pstr)
		return self.template.format(var_name, ", ".join(par_strings))



class XmlProvider:

	pass