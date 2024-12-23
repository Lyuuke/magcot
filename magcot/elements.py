'''Here defines the base classes for GUI element description
# # #
hierarchy: Coord -> Marker -> Element
'''

from .contextmanager import *
from .providers import *
# # #
import json
from shutil import copytree



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
	_HTML_provider: Optional[HtmlProvider] = None
	# provides HTML elements

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

	def get_clip_direction(self) -> NoReturn:
		raise NotImplementedError("Only `ClippablePatchMarker` has this "
			"method, this ({}) does not.".format(self.__class__))

	def to_HTML(self, *args, **data) -> NoReturn:
		'''Write lines of HTML elements. Note that this usually requires
			external input data, such as colors, ordinals, etc.
		These data can be passed down level-by-level.
		Must be overridden by subclasses.
		# # #
		`return`: `str`
		'''
		raise NotImplementedError("This must be overridden.")


class PointMarker(Marker):
	'''Used to mark a point.
	# # #
	Defined field:
	`at`: the x-y coordinate of this point.
	'''

	__slots__ = ("at",)
	_HTML_provider = HtmlProvider("div", ["element", "point"],
		"logPointInfo(this)")

	def to_HTML(self, id_: str, color: str, symbol: str, z_index: Real,
		additional_classes: List[str], suffix: str) -> str:
		'''Needs external `id_`, `color`, and `symbol`.
		'''
		return self._HTML_provider(id_, symbol, additional_classes,
			z_index=z_index, suffix=suffix,
			color=color, x=self.at._0, y=self.at._1
		)


class OffsetMarker(Marker):
	'''Used to mark an offset relative to a given point of an area,
		usually to the upper left point.
	# # #
	Defined field:
	`at`: the Δx-Δy coordinate of this point.
	'''

	__slots__ = ("at",)
	_HTML_provider = HtmlProvider("div", ["element", "point"],
		"logOffsetInfo(this)")

	def to_HTML(self, id_: str, color: str, symbol: str, z_index: Real,
		ref: PointMarker, additional_classes: List[str], suffix: str) -> str:
		'''Needs external `id_`, `color`, and `symbol`, and an ADDITIONAL
			`ref` (a `PointMarker` object) as the local origin point.
		'''
		ex, wye = self.at + ref.at
		return self._HTML_provider(id_, symbol, additional_classes,
			z_index=z_index, suffix=suffix,
			color=color, x=ex, y=wye
		)


class GridMarker(Marker):
	'''Used to specify a grid, mostly used in creating `Atlas` instances.
	# # #
	`ul`: the x-y coordinate of the upper left point.
	`grid`: the number of grid intervals in horizontal and vertical
		directions.
	`clip`: the width and height of a single clip.
	'''

	__slots__ = ("ul", "grid", "clip")
	_HTML_provider = HtmlProvider("div", ["element", "area grid"],
		"logGridInfo(this)")

	def to_HTML(self, id_: str, color: str, symbol: str, z_index: Real,
		additional_classes: List[str], suffix: str) -> str:
		'''Needs external `id_`, `color`, and `symbol`.
		'''
		return self._HTML_provider(id_, symbol, additional_classes,
			z_index=z_index, suffix=suffix,
			color=color, x=self.ul._0, y=self.ul._1,
			clip_w=self.clip._0, clip_h=self.clip._1,
			grid_x=self.grid._0, grid_y=self.grid._1,
		)


class PatchMarker(Marker):
	'''Used to mark a patch (rectangular region).
	# # #
	Defined fields:
	`ul`: the x-y coordinate of the upper left point.
	`size`: width and height of this patch.
	'''

	__slots__ = ("ul", "size")
	_HTML_provider = HtmlProvider("div", ["element", "area patch"],
		"logPatchInfo(this)")

	def to_HTML(self, id_: str, color: str, symbol: str, z_index: Real,
		additional_classes: List[str], suffix: str) -> str:
		'''Needs external `id_`, `color`, and `symbol`.
		'''
		return self._HTML_provider(id_, symbol, additional_classes,
			z_index=z_index, suffix=suffix,
			color=color, x=self.ul._0, y=self.ul._1,
			w=self.size._0, h=self.size._1
		)


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
	_HTML_provider = HtmlProvider("div", ["element", "area cpatch"],
		"logClippablePatchInfo(this)")

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

	def to_HTML(self, id_: str, color: str, symbol: str, z_index: Real,
		additional_classes: List[str], suffix: str) -> str:
		'''Needs external `id_`, `color`, and `symbol`.
		'''
		DIRECTIONS = {"x": ("left", "right"), "y": ("bottom", "top")}
		axis, sign = self.get_clip_direction()
		return self._HTML_provider(id_, symbol, additional_classes,
			z_index=z_index, suffix=suffix,
			color=color, x=self.ul._0, y=self.ul._1,
			w=self.size._0, h=self.size._1,
			direction=DIRECTIONS[axis][sign]
		)



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
	ΔZ: int = 1
	# the z-index increment between two juxtaposed HTML elements.]

	def __init__(self, id_: str, context: Optional["GuiAnnotation"] = None,
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
		self.points: Dict[str, PointMarker] = {}
		self.patches: Dict[str,
			Union[PatchMarker, ClippablePatchMarker, GridMarker]] = {}
		self.offsets: Dict[str, OffsetMarker] = {}
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
		self.points[field_name] = marker
		self.__dict__[field_name] = marker

	@add_data.register
	def _(self, marker: PatchMarker, field_name: str) -> None:
		self.patches[field_name] = marker
		self.__dict__[field_name] = marker

	@add_data.register
	def _(self, marker: ClippablePatchMarker, field_name: str) -> None:
		self.patches[field_name] = marker
		self.__dict__[field_name] = marker

	@add_data.register
	def _(self, marker: GridMarker, field_name: str) -> None:
		self.patches[field_name] = marker
		self.__dict__[field_name] = marker

	@add_data.register
	def _(self, marker: OffsetMarker, field_name: str) -> None:
		self.offsets[field_name] = marker
		self.__dict__[field_name] = marker

	def to_object(self) -> NoReturn:
		'''Convert a instance to a JSON object (as Python dictionary) with
			essential information. Must be overridden by subclasses.
		`return`: `dict`
		'''
		raise NotImplementedError("This must be overridden.")

	def to_Java_like(self) -> NoReturn:
		'''Write lines of assignment statements that looks Java-ish.
		Must be overridden by subclasses.
		# # #
		`return`: (class_name, statement_line)
		'''
		raise NotImplementedError("This must be overridden.")

	def to_HTML(self, color: str, symbol: str, additional_classes: List[str],
		z_index: Real = 10) -> Tuple[str, ...]:
		'''Calls `Marker.to_HTML`.
		On this level, parameter `id_` is resolved, but `color`, `symbol`,
			and `z-index` still need to be provided externally.
		'''
		built: List[str] = []
		built.append(f"<!-- {self.__class__.__name__} `{self.id}` -->")
		# add a comment line
		el_count = -1 # element counter
		for pt_name, ptch in self.patches.items():
			el_count += 1
			built.append(ptch.to_HTML(f"{self.id}--{pt_name}", color, symbol,
				self.context.z_index_start["patch"] + z_index
				+ el_count * self.ΔZ, additional_classes, pt_name))
		for pn_name, pn in self.points.items():
			el_count += 1
			built.append(pn.to_HTML(f"{self.id}--{pn_name}", color, symbol,
				self.context.z_index_start["point"] + z_index
				+ el_count * self.ΔZ, additional_classes, pn_name))
		for ofs_name, ofs in self.offsets.items():
			# `OffsetMarker` must provide a reference point (the local
			# origin) to calculate the actual x-y coordinate
			# they are still points
			el_count += 1
			built.append(ofs.to_HTML(f"{self.id}--{ofs_name}", color, symbol,
				self.context.z_index_start["point"] + z_index
				+ el_count * self.ΔZ, ref=self.points["ul"],
				additional_classes=additional_classes, suffix=ofs_name))
		return tuple(built)


class Corner(Element):
	'''Single points.
	'''

	_user_fields = {"at": PointMarker}
	_object_provider = ObjectProvider("type", "name", "at", type="corner")
	_Java_like_provider = AssignmentStatementProvider("Point")

	@classmethod
	def of(cls, id_: str, at: Tuple[int, int],
		context: Optional["GuiAnnotation"] = None) -> Self:
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
		context: Optional["GuiAnnotation"] = None) -> Self:
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
		context: Optional["GuiAnnotation"] = None,
		**markers: Marker) -> None:
		super().__init__(id_, context, **markers)
		self.add_data(
			PatchMarker(ul=markers["ul"].at, size=(16, 16)),
			field_name="area"
		)

	@classmethod
	def of(cls, id_: str, ul: Tuple[int, int],
		context: Optional["GuiAnnotation"] = None) -> Self:
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
		context: Optional["GuiAnnotation"] = None) -> Self:
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
		context: Optional["GuiAnnotation"] = None,
		texture: Union[Texture, str, None] = None, **markers: Marker) -> None:
		super().__init__(id_, context, **markers)
		super(Element, self).__init__(texture)

	@classmethod
	def of(cls, id_: str, ul: Tuple[int, int], size: Tuple[int, int],
		texture: Union[Texture, str, None] = None,
		context: Optional["GuiAnnotation"] = None) -> Self:
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
		context: Optional["GuiAnnotation"] = None,
		texture: Union[Texture, str, None] = None, **markers: Marker) -> None:
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
		context: Optional["GuiAnnotation"] = None,
		texture: Union[Texture, str, None] = None, **markers: Marker) -> None:
		super().__init__(id_, context, **markers)
		super(Element, self).__init__(texture)

	@classmethod
	def of(cls, id_: str, ul: Tuple[int, int], grid: Tuple[int, int],
		clip: Tuple[int, int], texture: Union[Texture, str, None] = None,
		context: Optional["GuiAnnotation"] = None) -> Self:
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



class GuiAnnotation:
	'''The main class to operate GUI annotation workflows.
	# # #
	Must be instantialized with a mandatory texture path/object and optional
		`ordinal_style` and `color_series` to annotate a GUI.
	`color_series`: a list of color series names defined in
		`providers.color_series`.
	'''

	def __init__(self, main_texture: Union[Texture, str],
		z_index_start: Optional[Dict[str, Real]] = None,
		ordinal_style: str = "qianziwen",
		color_series: List[str] = ["red", "green", "blue", "yellow",
			"purple", "orange", "cyan", "crimson", "earthy",
			"indigo", "dim"]
	) -> None:
		self.textures: Dict[str, Texture] = {}
		self.groups: Dict[str, List[str]] = {}
		self._current_group: Optional[str] = None
		self.layouts: Dict[str, Layout] = {}
		self.elements: Dict[str, Element] = {}
		self.element_order: List[Tuple[Element, ...]] = []
		self.ungrouped_elements: Dict[str, Element] = {}
		self.add_texture(main_texture, "")
		# the key of main texture is an empty string
		self.z_index_start = {"point": 300, "patch": 100}
		self.ΔZ: Real = 10
		if isinstance(z_index_start, dict):
			self.z_index_start.update(z_index_start)
		# in this setting, when the number of patches is less than 200,
		# all the patches will be displayed below the points
		self.ordinals: Generator[str, None, None] = ordinals(ordinal_style)
		self.color_series = [str(cs) for cs in color_series]
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
		else:
			self.ungrouped_elements[el_id] = element
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
		file_path: Optional[str] = None) -> Dict[str, Union[Dumpable, dict]]:
		'''Convert GUI annotations to a JSON object (as Python dictionary)
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

	def to_Java_fragment(self, file_path: Optional[str] = None,
		order: Literal["class", "elementorder"] = "class") -> str:
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
		built.append("// This is a fragment. "
			"Paste this to where it should be.")
		built.append("HashMap<String, String> textures = "
			"new HashMap<String, String>();")
		for tn, tins in self.textures.items():
			# create texture mapping
			built.append("textures.put(\"{}\", \"{}\");".format(
				tn, tins.get_preferred_path()))
		built.append("")
		if order == "class":
			# arrange the elements by class
			statements_by_class: Dict[str, List[str]] = {
				"Point": [], "Rect": [], "UV": [], "TexturedUV": [],
				"AtlasUV": []
			} # temporary storage
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

	def to_HTML_fragment(self, file_path: Optional[str] = None,
		coloring: Literal["groupwise", "order"] = "groupwise",
		indent: int = 0) -> str:
		'''Convert GUI annotations to HTML elements.
		The information is nearly all preserved, but not guaranteed.
		# # #
		`coloring`: how the elements are colored.
			`groupwise`: elements within one group will be colored similarly.
			`order`: elements will be colored according to their order,
				regardless of groups.
		`indent`: the number of tabs preceding each line.
		# # #
		If an element belongs to `group_name`, then it will have the class
			"g--`group_name`".
		Texture named `tex_name` will have the class "tex--`tex_name`".
		'''
		built: Dict[str, List[str]] = {tn: [] for tn in self.textures}
		# every texture has a list
		texture_el_counts: Dict[str, int] = {}
		if coloring == "groupwise":
			el_i = -1
			csn = cycle(self.color_series)
			for gn, gels in self.groups.items():
				# grouped elements first
				group_color_series = color_series(next(csn))
				for el_name in gels:
					el = self.elements[el_name]
					if isinstance(el, Textured):
						etx = el.texture.bound_shortcut
					else:
						etx = ""
					if etx not in self.textures:
						# only consider elements with textures
						continue
					texture_el_counts[etx] = el_i = \
						texture_el_counts.get(etx, 0) + 1
					built[etx].append("\n".join(el.to_HTML(
						color=next(group_color_series),
						symbol=next(self.ordinals),
						z_index=self.ΔZ * el_i,
						additional_classes=["g--" + gn]
					)))
			group_color_series = color_series("dim")
			for el in self.ungrouped_elements.values():
				# then ungrouped ones
				if isinstance(el, Textured):
					etx = el.texture.bound_shortcut
				else:
					etx = ""
				if etx not in self.textures:
					# only consider elements with textures
					continue
				texture_el_counts[etx] = el_i = \
					texture_el_counts.get(etx, 0) + 1
				built[etx].append("\n".join(el.to_HTML(
					color=next(group_color_series),
					symbol=next(self.ordinals),
					z_index=self.ΔZ * el_i,
					additional_classes=[]
				)))
		elif coloring == "order":
			group_color_series = color_series("any")
			for eln, el in self.elements.items():
				groups_containing: List[str] = []
				for gn, gels in self.groups:
					# find all groups that contain this element
					if eln in gels:
						groups_containing.append("g--" + eln)
				if isinstance(el, Textured):
					etx = el.texture.bound_shortcut
				else:
					etx = ""
				if etx not in self.textures:
					# only consider elements with textures
					continue
				texture_el_counts[etx] = el_i = \
					texture_el_counts.get(etx, 0) + 1
				built[etx].append("\n".join(el.to_HTML(
					color=next(group_color_series),
					symbol=next(self.ordinals),
					z_index=self.ΔZ * el_i,
					additional_classes=groups_containing
				)))
		else:
			raise ValueError("Unsupported value for `coloring`.")
		# # #
		all_built_texts: List[str] = []
		all_built_texts.append(
			"<script>var allGroupData = {}</script>".format(repr(self.groups)
				.replace("(", "[").replace(")", "]").replace("'", '"'))
		) # add a group list
		for tn, segs in built.items():
			texture_built_text = ("<div class=\"tex--{} texwrap\" "
				"data='{{\"w\":{},\"h\":{},\"path\":\"{}\"}}'>\n").format(
					tn, *self.textures[tn].size,
					self.textures[tn].get_preferred_path())
			texture_built_text += "<img src=\"{}\">".format(
				to_data_URL(self.textures[tn].texture_path)
			)
			texture_built_text += "\n\n"
			texture_built_text += "\n\n".join(segs)
			texture_built_text += "\n</div>"
			all_built_texts.append("\n".join("\t" * indent + ln
				if ln.strip() else ln
				for ln in texture_built_text.splitlines())
			)
		# # #
		built_text = "\n\n".join(all_built_texts)
		if file_path:
			with open(recognize_resource_location(file_path,
				ext=".html"), "w") as file:
				file.write(built_text)
		# will return regardless of whether `file_path` is None
		return built_text

	def assemble_webpage(self, file_path: Optional[str] = None,
		embed: bool = True, lang: str = "zh_cn") -> None:
		'''Assemble a webpage that visualizes the annotation.
		# # #
		`embed`: whether style sheets and scripts are embedded into one
			HTML file.
		`lang`: language in the document.
		'''
		HERE = os.path.dirname(__file__)
		if not os.path.exists(lang_dir := HERE + f"/blocks/lang/{lang}.json"):
			# look for the language file
			raise ValueError(f"Language file `{lang}.json` does not exist.")
		with open(lang_dir, "r", encoding="utf-8") as lang_file:
			lang_dict = json.load(lang_file)
		with open(HERE + "/blocks/frame.html",
			"r", encoding="utf-8") as frame_file:
			frame = frame_file.read()
		# these slots should be defined in the HTML frame:
		# $stylesheet$, $langdict$, $scripts$, $iconsrc$, $elements$
		frame = frame.replace("$langdict$",
			'<script type="text/javascript">\n\t\t'
			'langEntries = {{\n\t\t\t'
			'{}\n\t\t'
			'}}\n\t</script>'.format(
				"\n\t\t\t".join(
					'"{}": "{}",'.format(k, v)
					for k, v in lang_dict.items()
				)
			)
		) # $langdict$ is filled by the same way regardless of `embed`
		if not embed:
			frame = frame.replace("$stylesheet$",
				'<link rel="stylesheet" type="text/css" '
				'href="./sources/magcotstyle.css">'
			)
			frame = frame.replace("$scripts$",
				'<script type="text/javascript" '
				'src="./sources/arrangement.js"></script>\n\t'
				'<script type="text/javascript" '
				'src="./sources/interaction.js"></script>'
			)
			frame = frame.replace("$iconsrc$", "./sources/icon.png")
			frame = frame.replace("$elements$",
				self.to_HTML_fragment(indent = 4))
			out_file_name = recognize_resource_location(file_path,
				ext=".html")
			destination = os.path.split(out_file_name)[0]
			# destination to copy the resource files
			copytree(HERE + "/blocks/sources", destination + "/sources",
				dirs_exist_ok=True)
			with open(out_file_name, "w", encoding="utf-8") as file:
				file.write(frame)
		else:
			# embed all the files
			SOURCE_BASE = HERE + "/blocks/sources/"
			with open(SOURCE_BASE + "magcotstyle.css", "r",
				encoding="utf-8") as file:
				read_text = file.read()
			frame = frame.replace("$stylesheet$",
				'<style type="text/css">\n'
				+ "\n".join(
					"\t\t" + ln for ln in read_text.splitlines()
				)
				+ '\n\t</style>'
			)
			JSs = ["arrangement", "interaction"]
			# JavaScript file names used
			JS_texts: List[str] = []
			for js in JSs:
				with open(SOURCE_BASE + js + ".js", "r",
				encoding="utf-8") as file:
					read_text = file.read()
					JS_texts.append('<script type="text/javascript">\n'
						+ "\n".join(
						"\t\t" + ln for ln in read_text.splitlines())
						+ '\n\t</script>'
					)
			frame = frame.replace("$scripts$", "\n\t".join(JS_texts))
			frame = frame.replace("$iconsrc$",
				to_data_URL(SOURCE_BASE + "icon.png"))
			frame = frame.replace("$elements$",
				self.to_HTML_fragment(indent = 4))
			with open(recognize_resource_location(file_path,
				ext=".html"), "w", encoding="utf-8") as file:
				file.write(frame)