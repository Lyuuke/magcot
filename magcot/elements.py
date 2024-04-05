'''Here defines the base classes for GUI element description
# # #
hierarchy: Coord -> Marker -> Element -> ElementMapping -> Layout
'''

from .contextmanager import *
from .providers import *
# # #
import json



hook_["namespaces"] = CurrentContext()._namespaces



class Coord:
	'''Coordinate class.
	# # #
	A coordinate is a pair of integers, used to describe a point,
		a width-by-height area, or x-y offset.
	'''

	__slots__ = ("_0", "_1")

	@singledispatchmethod
	def __init__(self, *args) -> NoReturn:
		raise TypeError(f"Cannot convert {args[0].__class__} and such "
			"into `Coord`.")

	@__init__.register
	def _(self, first: int, last: int) -> None:
		'''Initialize with two integers.
		'''
		self._0, self._1 = first, last

	@__init__.register
	def _(self, pair: iterable) -> None:
		'''Initialize with a pair of integers in an iterable.
		# # #
		`pair`: theoretically an iterable with two integer elements,
				but who knows?
		'''
		pair = map(int, pair)
		self._0, self._1, *_ = pair

	@property
	def pair(self) -> Tuple[int, int]:
		return (self._0, self._1)

	@classmethod
	def assure(cls, obj: Any) -> Self:
		'''Try to return a `Coord` instance if possible.
		'''
		if isinstance(obj, cls):
			return obj
		else:
			# here be dragons
			return cls(obj)

	def __repr__(self) -> str:
		return "@" + self.pair.__repr__()

	def __add__(self, other: Self) -> Self:
		return Coord(self._0 + other._0, self._1 + other._1)

	def __sub__(self, other: Self) -> Self:
		return Coord(self._0 - other._0, self._1 - other._1)

	def __iter__(self) -> Generator[int, None, None]:
		yield from self.pair



class Marker:
	'''Marker base class, use to store positions and sizes of UI elements.
	'''
	
	__slots__ = ()
	# here defines all the data fields
	# all fields (e.g. point x-y, size w-h, clip direction) are stored
	# with `Coord` instances
	HTML_provider: Optional[XmlProvider] = None

	def __init__(self, **data: Union[Coord, iterable]) -> None:
		if (missing := set(self.__slots__) - set(data)):
			# `data` does not cover all the fields
			raise ValueError("All fields should be provided, "
				"but {} are missing.".format(missing.__repr__()))
		for field in self.__slots__:
			setattr(self, field, Coord.assure(data[field]))

	def __repr__(self) -> str:
		return "{}({})".format(
			self.__class__.__name__,
			"; ".join(("{} {}".format(fn, getattr(self, fn).__repr__())
				for fn in self.__slots__))
		)

	def get_clip_direction(self) -> Tuple[bool, bool]:
		raise NotImplementedError("Only `ClippablePatchMarker` has this "
			"method, this ({}) does not.".format(self.__class__))


class PointMarker(Marker):
	'''Used to mark a point.
	# # #
	Defined field:
	`at`: the x-y coordinate of this point.
	'''

	__slots__ = ("at",)


class OffsetMarker(Marker):
	'''Used to mark an offset relative to a given point of an area,
		usually to the upper left point.
	# # #
	Defined field:
	`at`: the Δx-Δy coordinate of this point.
	'''

	__slots__ = ("at",)


class GridMarker(Marker):
	'''Used to specify a grid, mostly used in creating `Atlas` instances.
	# # #
	`ul`: the x-y coordinate of the upper left point.
	`grid`: the number of grid intervals in horizontal and vertical
		directions.
	`clip`: the width and height of a single clip.
	'''

	__slots__ = ("ul", "grid", "clip")


class PatchMarker(Marker):
	'''Used to mark a patch (rectangular region).
	# # #
	Defined fields:
	`ul`: the x-y coordinate of the upper left point.
	`size`: width and height of this patch.
	'''

	__slots__ = ("ul", "size")


class ClippablePatchMarker(Marker):
	'''Used to mark a clippable patch (rectangular region that are usually
		clipped according to certain values, such as progress bars).
	# # #
	Defined fields:
	`ul`: the x-y coordinate of the upper left point.
	`size`: width and height of this patch.
	`direction`: how to clip this patch - only the signs of this pair of
		integers are considered. The first integer 
	'''
	__slots__ = ("ul", "size", "direction")

	def get_clip_direction(self) -> Optional[Tuple[str, bool]]:
		'''Get the actual clip direction specified by `self.direction`.
		# # #
		`return`: a string, denoting the axis of clipping; and an boolean,
			denoting whether clipping from the right (True) or the left
			(False).
		'''
		sign: Callable[[int], Optional[bool]] = \
			lambda x: (x > 0) if x != 0 else None
		x_dir = sign(self.direction._0)
		if x_dir is not None:
			return ("x", x_dir)
		y_dir = sign(self.direction._1)
		if y_dir is not None:
			return ("y", y_dir)
		return None



class Textured:
	'''Data class used to provide textured elements with texture-related
		functions.
	# # #
	This MUST BE INHERITED TOGETHER WITH (and AFTER) `Element` if needed.
	'''

	@singledispatchmethod
	def __init__(self, texture: Any) -> NoReturn:
		'''Initialize.
		# # #
		`texture`: used directly if this be a `Texture` instance. Otherwise,
			try to use `texture` as a key to loop up in the texture
			list of `context` if `texture` is a string, or use the main
			texture of `context` if `texture` is None.
		'''
		raise TypeError("`texture` must be a `Texture` instance, "
			"a string (as the key to look up context textures), "
			"or None (the main context texture).")

	@__init__.register
	def _(self, texture: Texture) -> None:
		self.texture = texture

	@__init__.register
	def _(self, texture: str) -> None:
		if self.context is not None:
			self.texture = self.context.textures.get(texture, None)
		else:
			self.texture = None

	@__init__.register
	def _(self, texture: None) -> None:
		if self.context is not None:
			self.texture = self.context.textures.get("", None)
		else:
			self.texture = None
	


class Element:
	'''UI element definition base class, having the function to provide
		simple foreign codes.
	# # #
	A UI element is typically made up of points (defined by `PointMarker`
		instances) and patches (`(Clippable)PatchMarker` instances).
	Using `of` to initialize is more convenient, refraining from dealing
		with lower-level objects.
	Attribute `context` specifies a `GuiAnnotation` instance, to provide
		other information about the GUI being annotated, including texture
		files used, visual styles that the elements sould be shown on the
		web page, etc.
	'''

	_user_fields: Dict[str, type] = {}
	# the data fields that require user input
	# there may be additional auto-generated fields
	# all the keys will become attributes
	_object_provider: Optional[ObjectProvider] = None
	# provides JSON objects
	_Java_like_provider: Optional[AssignmentStatementProvider] = None
	# provides Java-like assignment statements

	def __init__(self, id_: str, context: Optional["GuiAnnotation"]=None,
		**markers: Marker) -> None:
		'''Initialize.
		# # #
		`context`: current (annotation) context. Will try to get current
			context if this parameter is None. `self.context` can still
			be None finally, if no `GuiAnnotation` instance be created.
		'''
		self.id = validated_id(id_)
		if context is None:
			self.context = CurrentContext().get()
		else:
			self.context = context
		self.points: List[PointMarker] = []
		self.patches: List[Union[PatchMarker, ClippablePatchMarker]] = []
		self.grids: List[GridMarker] = []
		self.offsets: List[OffsetMarker] = []
		for fn, field_type in self._user_fields.items():
			intended_field_data = markers[fn]
			if not isinstance(intended_field_data, field_type):
				raise TypeError("The class of given `{}` does not match "
					"definition (expected {}, got {}).".format(
						fn, field_type, intended_field_data.__class__
				))
			self.add_data(markers[fn], fn)

	@classmethod
	def of(cls, id_: str, *args: Any,
		context: Optional["GuiAnnotation"]) -> NoReturn:
		'''Initialize with simpler data (tuples, etc.) instead of explicit
			`Marker` instances. Must be overridden by subclasses.
		'''
		raise NotImplementedError("This must be overridden.")

	def __repr__(self) -> str:
		return "{}(\n\t{}\n)".format(
			self.__class__.__name__,
			";\n\t".join(("{} -> {}".format(fn, mk.__repr__())
				for fn, mk in self.__dict__.items()
				if isinstance(mk, (Marker, Texture, str))))
		)

	@singledispatchmethod
	def add_data(self, marker: Marker, field_name: str) -> NoReturn:
		raise TypeError(f"Unsupported data class {marker.__class__}.")

	@add_data.register
	def _(self, marker: PointMarker, field_name: str) -> None:
		self.points.append(marker)
		self.__dict__[field_name] = marker

	@add_data.register
	def _(self, marker: PatchMarker, field_name: str) -> None:
		self.patches.append(marker)
		self.__dict__[field_name] = marker

	@add_data.register
	def _(self, marker: ClippablePatchMarker, field_name: str) -> None:
		self.patches.append(marker)
		self.__dict__[field_name] = marker

	@add_data.register
	def _(self, marker: GridMarker, field_name: str) -> None:
		self.grids.append(marker)
		self.__dict__[field_name] = marker

	@add_data.register
	def _(self, marker: OffsetMarker, field_name: str) -> None:
		self.offsets.append(marker)
		self.__dict__[field_name] = marker

	def to_object(self) -> NoReturn:
		'''Convert a instance to a JSON object (as Python dictionary) with
			essential information. Must be overridden by subclasses.
		'''
		raise NotImplementedError("This must be overridden.")

	def to_Java_like(self) -> NoReturn:
		'''Write lines of assignment statements that looks Java-ish.
		Must be overridden by subclasses.
		# # #
		`return`: (class_name, statement_line)
		'''
		raise NotImplementedError("This must be overridden.")


class Corner(Element):
	'''Single points.
	'''

	_user_fields = {"at": PointMarker}
	_object_provider = ObjectProvider("type", "name", "at", type="corner")
	_Java_like_provider = AssignmentStatementProvider("Point")

	@classmethod
	def of(cls, id_: str, at: Tuple[int, int],
		context: Optional["GuiAnnotation"]=None) -> Self:
		if context is None:
			context = CurrentContext().get()
		return cls(id_, context, at=PointMarker(at=at))

	def to_object(self) -> Dict[str, Dumpable]:
		return self._object_provider(
			name=self.id, at=self.at.at
		)

	def to_Java_like(self) -> Tuple[str, str]:
		return "Point", self._Java_like_provider(
			camel_case(self.id), *self.at.at
		)



class Rectangle(Element):
	'''Single patch.
	'''

	_user_fields = {"area": PatchMarker}
	_object_provider = ObjectProvider("type", "name", "ul", "size",
		type="rectangle")
	_Java_like_provider = AssignmentStatementProvider("Rect")

	@classmethod
	def of(cls, id_: str, ul: Tuple[int, int], size: Tuple[int, int],
		context: Optional["GuiAnnotation"]=None) -> Self:
		if context is None:
			context = CurrentContext().get()
		return cls(id_, context, area=PatchMarker(ul=ul, size=size))

	def to_object(self) -> Dict[str, Dumpable]:
		return self._object_provider(
			name=self.id, ul=self.area.ul, size=self.area.size
		)

	def to_Java_like(self) -> Tuple[str, str]:
		return "Rect", self._Java_like_provider(
			camel_case(self.id), *self.area.ul, *self.area.size
		)


class ItemSlot(Element):
	'''Common item slots. This class marks the ACTUAL (16 * 16) item slots
		regions to render item stacks on, where any decorative margins
		are excluded.
	'''

	_user_fields = {"ul": PointMarker}
	_object_provider = ObjectProvider("type", "name", "ul", type="itemslot")
	_Java_like_provider = AssignmentStatementProvider("Rect")

	def __init__(self, id_: str,
		context: Optional["GuiAnnotation"]=None,
		**markers: Marker) -> None:
		super().__init__(id_, context, **markers)
		self.add_data(
			PatchMarker(ul=markers["ul"].at, size=(16, 16)),
			field_name="area"
		)

	@classmethod
	def of(cls, id_: str, ul: Tuple[int, int],
		context: Optional["GuiAnnotation"]=None) -> Self:
		if context is None:
			context = CurrentContext().get()
		return cls(id_, context, ul=PointMarker(at=ul))

	def to_object(self) -> Dict[str, Dumpable]:
		return self._object_provider(
			name=self.id, ul=self.ul.at
		)

	def to_Java_like(self) -> Tuple[str, str]:
		return "Rect", self._Java_like_provider(
			camel_case(self.id), *self.ul.at, 16, 16
		)


class FluidTank(Element):
	'''Fluid tanks. This class marks the ACTUAL regions to render fluid
		textures on, where any decorative margins are excluded.
	'''

	_user_fields = {"ul": PointMarker, "area": ClippablePatchMarker}
	_object_provider = ObjectProvider("type", "name", "ul", "size", "axis",
		"sign", type="fluidtank")
	_Java_like_provider = AssignmentStatementProvider("Rect")

	@classmethod
	def of(cls, id_: str, ul: Tuple[int, int], size: Tuple[int, int],
		direction: Literal["+x", "-x", "+y", "-y"],
		context: Optional["GuiAnnotation"]=None) -> Self:
		if context is None:
			context = CurrentContext().get()
		return cls(
			id_, context, ul=PointMarker(at=ul),
			area=ClippablePatchMarker(
				ul=ul, size=size,
				direction=handle_direction_string(direction),
			)
		)

	def to_object(self) -> Dict[str, Dumpable]:
		_axis, _sign = self.area.get_clip_direction()
		return self._object_provider(
			name=self.id, ul=self.area.ul, size=self.area.size,
			axis=_axis, sign=_sign
		)

	def to_Java_like(self) -> Tuple[str, str]:
		return "Rect", self._Java_like_provider(
			camel_case(self.id), *self.area.ul, *self.area.size
		)


class Crop(Element, Textured):
	'''Image crops to paste around. This may include most decorative
		UI elements. Textured.
	'''

	_user_fields = {"ul": PointMarker, "area": PatchMarker}
	_object_provider = ObjectProvider("type", "name", "ul", "size", "texture",
		type="crop")
	_Java_like_provider = AssignmentStatementProvider("TexturedUV")

	def __init__(self, id_: str,
		context: Optional["GuiAnnotation"]=None,
		texture: Union[Texture, str, None]=None, **markers: Marker) -> None:
		super().__init__(id_, context, **markers)
		super(Element, self).__init__(texture)

	@classmethod
	def of(cls, id_: str, ul: Tuple[int, int], size: Tuple[int, int],
		texture: Union[Texture, str, None]=None,
		context: Optional["GuiAnnotation"]=None) -> Self:
		if context is None:
			context = CurrentContext().get()
		return cls(
			id_, context, texture,
			ul=PointMarker(at=ul),
			area=PatchMarker(ul=ul, size=size)
		)

	def to_object(self) -> Dict[str, Dumpable]:
		return self._object_provider(
			name=self.id, ul=self.ul.at, size=self.area.size,
			texture=(self.texture.bound_shortcut
				if self.texture is not None else None)
		)

	def to_Java_like(self) -> Tuple[str, str]:
		return "TexturedUV", self._Java_like_provider(
			camel_case(self.id),
			RawExp("textures.get(\"{}\")".format(
				self.texture.bound_shortcut)),
			*self.area.ul, *self.area.size,
			*self.texture.size
		)


class ProgressBar(Element, Textured):
	'''Progress bars. Textured.
	# # #
	Generally, a progress bar refer to any texture clip that grows towards
		one specific direction according to a scalar value, thus the clip
		must be clippable, and the direction is specified as a parameter
		when creating `area` (a `ClippablePatchMarker` instance).
	'''

	_user_fields = {"ul": PointMarker, "area": ClippablePatchMarker}
	_object_provider = ObjectProvider("type", "name", "ul", "size", "axis",
		"sign", "texture", type="progressbar")
	_Java_like_provider = AssignmentStatementProvider("TexturedUV")

	def __init__(self, id_: str,
		context: Optional["GuiAnnotation"]=None,
		texture: Union[Texture, str, None]=None, **markers: Marker) -> None:
		super().__init__(id_, context, **markers)
		super(Element, self).__init__(texture)

	@classmethod
	def of(cls, id_: str, ul: Tuple[int, int], size: Tuple[int, int],
		direction: Literal["+x", "-x", "+y", "-y"],
		texture: Union[Texture, str, None]=None,
		context: Optional["GuiAnnotation"]=None) -> Self:
		return cls(
			id_, context, texture,
			ul=PointMarker(at=ul),
			area=ClippablePatchMarker(
				ul=ul, size=size,
				direction=handle_direction_string(direction),
			)
		)

	def to_object(self) -> Dict[str, Dumpable]:
		_axis, _sign = self.area.get_clip_direction()
		return self._object_provider(
			name=self.id, ul=self.ul.at, size=self.area.size, axis=_axis,
			sign=_sign, texture=(self.texture.bound_shortcut
				if self.texture is not None else None)
		)

	def to_Java_like(self) -> Tuple[str, str]:
		return "TexturedUV", self._Java_like_provider(
			camel_case(self.id),
			RawExp("textures.get(\"{}\")".format(
				self.texture.bound_shortcut)),
			*self.area.ul, *self.area.size,
			*self.texture.size
		)


class Atlas(Element, Textured):
	'''Atlantes consisting of crops of textures arranged in a regular grid.
	'''

	_user_fields = {"ul": PointMarker, "grid": GridMarker}
	_object_provider = ObjectProvider("type", "name", "ul", "grid", "clip",
		"texture", type="atlas")
	_Java_like_provider = AssignmentStatementProvider("AtlasUV")

	def __init__(self, id_: str,
		context: Optional["GuiAnnotation"]=None,
		texture: Union[Texture, str, None]=None, **markers: Marker) -> None:
		super().__init__(id_, context, **markers)
		super(Element, self).__init__(texture)

	@classmethod
	def of(cls, id_: str, ul: Tuple[int, int], grid: Tuple[int, int],
		clip: Tuple[int, int], texture: Union[Texture, str, None]=None,
		context: Optional["GuiAnnotation"]=None) -> Self:
		return cls(
			id_, context, texture,
			ul=PointMarker(at=ul),
			grid=GridMarker(ul=ul, grid=grid, clip=clip)
		)

	def to_object(self) -> Dict[str, Dumpable]:
		return self._object_provider(
			name=self.id, ul=self.ul.at, grid=self.grid.grid,
			clip=self.grid.clip, texture=(self.texture.bound_shortcut
				if self.texture is not None else None)
		)

	def to_Java_like(self) -> Tuple[str, str]:
		return "AtlasUV", self._Java_like_provider(
			camel_case(self.id),
			RawExp("textures.get(\"{}\")".format(
				self.texture.bound_shortcut)),
			*self.grid.ul,
			self.grid.grid._0 * self.grid.clip._0, # total width
			self.grid.grid._1 * self.grid.grid._1, # total height
			self.grid.grid._0,
			self.grid.grid._0 * self.grid.grid._1, # total clip number
			*self.texture.size
		)



class ElementMapping:
	pass



class Layout:
	pass



class GuiAnnotation:
	'''WIP
	'''

	def __init__(self, main_texture: Union[Texture, str]):
		self.textures: Dict[str, Texture] = {}
		self.groups: Dict[str, List[str]] = {}
		self._current_group: Optional[str] = None
		self.layouts: Dict[str, Layout] = {}
		self.elements: Dict[str, Element] = {}
		self.element_order: List[Tuple[Element, ...]] = []
		self.add_texture(main_texture, "")
		# the key of main texture is an empty string
		CurrentContext().focus_on(self)

	def __getitem__(self, key: str) -> Union[Element, List[Element]]:
		'''Get an element or a group of elements with element ID or
			group ID (starting with "#").
		'''
		if key.startswith("#"):
			return [self.elements[ii] for ii in self.groups[key[1:]]]
		return self.elements[key]

	@singledispatchmethod
	def add_texture(self, texture: Any, name: str) -> NoReturn:
		'''Add a texture into this workflow.
		'''
		raise TypeError("Only `Texture` and `str` instances are accepted.")

	@add_texture.register
	def _(self, texture: str, name: str) -> Self:
		if (name := str(name)) in self.textures:
			raise ValueError(f"There is already a textured named {name}.")
		self.textures[str(name)] = (Texture(texture).bind_shortcut(name)
			.validate_path())
		return self

	@add_texture.register
	def _(self, texture: Texture, name: str) -> Self:
		if (name := str(name)) in self.textures:
			raise ValueError(f"There is already a textured named {name}.")
		self.textures[str(name)] = (texture.bind_shortcut(name)
			.validate_path())
		return self

	@singledispatchmethod
	def annotate(self, element: Any) -> NoReturn:
		raise TypeError("Unsupported element class {}".format(
			element.__class__))

	@annotate.register
	def _(self, element: Element) -> Self:
		el_id = element.id
		if el_id in self.elements:
			raise ValueError(f"There is already an element with id {el_id}.")
		self.elements[el_id] = element
		self.element_order.append((el_id,))
		if self._current_group is not None:
			self.groups[self._current_group].append(el_id)
		return self

	def switch_group(self, group_id: Optional[str]) -> Self:
		'''Switch the current group to `group_id`. If `group_id` is None,
			then clear the current group.
		'''
		if group_id is None:
			self._current_group = None
		else:
			group_id = validated_id(group_id)
			if group_id not in self.groups:
				self.groups[group_id] = []
			self._current_group = group_id
		return self

	def __matmul__(self, rhs) -> Self:
		'''(@) A shorthand of `add_texture`.
		'''
		return self.add_texture(*rhs)

	def __add__(self, rhs) -> Self:
		'''(+) A shorthand of `switch_group`.
		'''
		return self.switch_group(rhs)

	def __sub__(self, rhs) -> Self:
		'''(-) A shorthand of `annotate`.
		'''
		return self.annotate(rhs)

	def serialize(self,
		file_path: Optional[str]=None) -> Dict[str, Union[Dumpable, dict]]:
		'''Convert GUI annotation to a JSON object (as Python dictionary)
			with essential information. This does not use `ObjectProvider`
			as the homonymous method of `Element`.
		'''
		built: [str, Union[Dumpable, dict]] = {}
		built["textures"] = {tn: tins.get_preferred_path()
			for tn, tins in self.textures.items()}
		built["groups"] = {gn: list(gels) for gn, gels in self.groups.items()}
		built["elements"] = [el.to_object() for el in self.elements.values()]
		if file_path:
			with open(recognize_resource_location(file_path,
				ext=".json"), "w") as file:
				json.dump(built, file, ensure_ascii=False, indent="\t")
		# will return regardless of whether `file_path` is None
		return built

	def to_Java_fragment(self, file_path: Optional[str]=None,
		order: Literal["class", "elementorder"]="class") -> str:
		'''Record essential information of annotations as Java code lines.
			Note that this method does not produce runnable Java code,
			the lines should be pasted manually to where they should be.
		Not all the information will be recorded - some will be lost, such
			as the grouping and clipping directions of clippable elements.
		# # #
		`order`: in what order should the statements be arranged.
			"class": statements of the same class are put together.
			"elementorder": by the order that elements are annotated.
		'''
		built: List[str] = []
		built.append("// This is a fragment. Paste this to where it should be.")
		built.append("HashMap<String, String> textures = "
			"new HashMap<String, String>();")
		for tn, tins in self.textures.items():
			built.append("textures.put(\"{}\", \"{}\");".format(
				tn, tins.get_preferred_path()))
		built.append("")
		if order == "class":
			# arrange the elements by class
			statements_by_class: Dict[str, List[str]] = {
				"Point": [], "Rect": [], "UV": [], "TexturedUV": [],
				"AtlasUV": []
			}
			for el in self.elements.values():
				cls_name, stat = el.to_Java_like()
				if len(stat) > 79:
					break_p = stat.find("(") + 1
					if break_p > 1:
						stat = stat[:break_p] + "\n\t" + stat[break_p:]
				if cls_name in statements_by_class:
					statements_by_class[cls_name].append(stat)
				else:
					statements_by_class[cls_name] = [stat]
			for cls_name, lines in statements_by_class.items():
				if lines:
					# add a comment line to mark the class name
					built.append(f"// {cls_name}")
				built += lines
		elif order == "elementorder":
			# arrange the elements by the order that they were annotated
			for el in self.elements.values():
				cls_name, stat = el.to_Java_like()
				if len(stat) > 79:
					break_p = stat.find("(") + 1
					if break_p > 1:
						stat = stat[:break_p] + "\n\t" + stat[break_p:]
				built.append(stat)
		built_text = "\n".join(built)
		if file_path:
			with open(recognize_resource_location(file_path,
				ext=".java"), "w") as file:
				file.write(built_text)
		# will return regardless of whether `file_path` is None
		return built_text