'''Here defines the context manager, used to manage what GUI is currently
	being annotated.
'''

import os


class CurrentContext:
	'''Store the context (only possible to be a `GuiAnnotation` instance
		so far) currently used, and manage namespaces.
	This class is intended to be manipulated by programs, not by users,
		thus can be unsafe if the instance be manually modified.
	# # #
	Singleton class.
	'''

	__instance: "Optional[Self]" = None
	__slots__ = ("_context", "_namespaces")

	def __new__(cls):
		'''To make this singleton.
		'''
		if cls.__instance is None:
			hold = super().__new__(cls)
			hold._context: "List[GuiAnnotation]" = []
			hold._namespaces: "Dict[str, str]" = {}
			cls.__instance = hold
		return cls.__instance

	def get(self) -> "Optional[GuiAnnotation]":
		if len(self._context) > 0:
			return self._context[-1]
		return None

	def focus_on(self, new_context: "GuiAnnotation") -> None:
		'''Focus on a new context. Previous ones are remembered.
		'''
		self._context.append(new_context)

	def recall(self) -> None:
		'''Turn to the second-to-last context. The current context will be
			forgotten.
		'''
		if len(self._context) > 0:
			self._context.pop()

	def define_namespace(self, ns: str, path: str) -> None:
		'''Define a namespace. `path` must be a path pointing to a folder
			named "assets".
		'''
		if os.path.basename(path) != "assets":
			raise ValueError("`path` must be an 'assets' folder.")
		if not os.path.isdir(path):
			raise FileNotFoundError(f"'{path}' does not exist.")
		if set(ns) - set("1234567890" "abcdefghijklmnopqrstuvwxyz" "-_."):
			raise ValueError("Bad namespace name.")
		self._namespaces[ns] = path.replace("\\", "/")



def define_namespace(ns: str, path: str) -> None:
	'''Wrapper of `CurrentContext.define_namespace`, can be used externally.
	'''
	CurrentContext().define_namespace(ns, path)