import numpy as np
import pyassimp as ai
from PyQt5.Qt import QQmlListProperty
from PyQt5.QtCore import pyqtProperty, pyqtSignal, QObject
from PyQt5.QtGui import QVector3D
from PyQt5.QtQml import QQmlListProperty
from common import *


class MeshData(object):
	"""
	Data structure for the mesh data
	"""

	def __init__ (self,
	              name = 'None',
	              vertices = None,
	              colors = None,
	              normals = None,
	              indices = None,
	              texturecoords = None):
		self.name = name
		self.vertices = vertices
		self.colors = colors
		self.normals = normals
		self.indices = indices
		self.texturecoords = texturecoords

	@classmethod
	def CheckData (cls, mesh):
		print(mesh.name + ':')
		if len(mesh.vertices) == 0:
			print(' vertices is empty')
		if len(mesh.colors) == 0:
			print(' colors is empty')
		if len(mesh.normals) == 0:
			print(' normals is empty')
		if len(mesh.indices) == 0:
			print(' indices is empty')
		if len(mesh.texturecoords) == 0:
			print(' texturecoords is empty')

	@classmethod
	def ReadFromFile (cls, file_name, name = 'None', offset = 0.0):
		scene = ai.load(file_name)
		mesh = scene.meshes[0]
		vertices = mesh.vertices - offset
		indices = mesh.faces.flatten()  # make 1d for passing
		colors = mesh.colors
		normals = mesh.normals
		texturecoords = mesh.texturecoords
		return MeshData(name, vertices, colors, normals, indices, texturecoords)


class RawModel(object):
	def __init__ (self, vao, indices_vbo, num_indices):
		self.vao = vao
		self.indices_vbo = indices_vbo
		self.num_indices = num_indices  # For glDrawElements()


class ModelEntity(QObject):
	name_changed = pyqtSignal()

	def __init__ (self, parent = None):
		super(ModelEntity, self).__init__(parent)
		self._name = 'ModelEntity'
		self.model = None
		self.position = None
		self.rotation = None
		self.scale = None
		self.color = None
		self.original_color = None
		self.select_color = None
		self.alpha = None

	@pyqtProperty('QString', notify = name_changed)
	def name (self):
		return '{0}'.format(self._name, self._name)

	@name.setter
	def name (self, name):
		self._name = name

	@pyqtProperty('QVector3D')
	def _position (self):
		return QVector3D(self.position[0], self.position[1], self.position[2])

	@_position.setter
	def _position (self, vec):
		self.position[0] = vec[0]
		self.position[1] = vec[1]
		self.position[2] = vec[2]

	@pyqtProperty('QVector3D')
	def _rotation (self):
		return QVector3D(self.rotation[0], self.rotation[1], self.rotation[2])

	@_rotation.setter
	def _rotation (self, vec):
		self.rotation[0] = vec[0]
		self.rotation[1] = vec[1]
		self.rotation[2] = vec[2]

	@pyqtProperty('QVector3D')
	def _scale (self):
		return QVector3D(self.scale[0], self.scale[1], self.scale[2])

	@_scale.setter
	def _scale (self, vec):
		self.scale[0] = vec[0]
		self.scale[1] = vec[1]
		self.scale[2] = vec[2]

	@pyqtProperty('QVector3D')
	def _color (self):
		return QVector3D(self.color[0], self.color[1], self.color[2])

	@_color.setter
	def _color (self, vec):
		self.color[0] = vec[0]
		self.color[1] = vec[1]
		self.color[2] = vec[2]

	@pyqtProperty('float')
	def _alpha (self):
		return self.alpha

	@_alpha.setter
	def _alpha (self, alpha):
		self.alpha = alpha


class ModelEntityList(QObject):
	def __init__ (self, parent = None):
		super(ModelEntityList, self).__init__(parent)
		self._entities = []

	@pyqtProperty(QQmlListProperty)
	def entities (self):
		"""
		This method is for Qml to access the list
		:return:
		"""
		return QQmlListProperty(ModelEntity, self, self._entities)

	@pyqtProperty(int)
	def length (self):
		return len(self._entities)

	def get_entities (self):
		"""
		This method is for Python to access the list
		:return:
		"""
		return self._entities

	def __getitem__ (self, key):
		if key >= len(self._entities):
			raise IndexError()
		return self._entities[key]

	def __setitem__ (self, key, value):
		self._entities[key] = value

	def __len__ (self):
		return len(self._entities)

	def append (self, item):
		self._entities.append(item)

	def extend (self, lst):
		self._entities.extend(lst)


class TexturedModel(object):
	def __init__ (self, raw_model = None, texture = None):
		self.raw_model = raw_model
		self.texture = texture


class Texture(object):
	def __init__ (self, data = None, width = None, height = None):
		self.data = data
		self.width = width
		self.height = height
		self.reflectivity = 0.0
		self.shine_damper = 1.0
		self.has_transparency = False

	@classmethod
	def CreateFromFile (cls, file_name):
		return Texture()


class PieceModelEntity(ModelEntity):
	def __init__ (self):
		super(PieceModelEntity, self).__init__()
		self.row = None
		self.col = None
		self.custom_color = None
		self.custom_position = None
		self.custom_rotation = None
		self.custom_scale = None


class EntityCreator(object):
	def __init__ (self, models):
		self._models = models

	def create_cube (self, position, rotation, scale, color):
		e = ModelEntity()
		e.model = self._models['cube']
		e.position = position
		e.rotation = rotation
		e.scale = scale
		e.color = color
		return e

	def create_bunny (self, position, rotation, scale, color):
		e = ModelEntity()
		e.model = self._models['bunny']
		e.position = position
		e.rotation = rotation
		e.scale = scale
		e.color = color
		return e

	def create_checker_board (self, title_entities, length = 10.0, rows = 8, cols = 8):
		y = -0.25
		color_black = np.array([0.0, 0.0, 0.0])
		color_white = np.array([1.0, 1.0, 1.0])

		for row in range(rows):
			for col in range(cols):
				position = np.array([col * length - cols * length / 2.0 + length / 2.0,
				                     y,
				                     row * length - rows * length / 2.0 + length / 2.0])
				rotation = np.array([0.0, 0.0, 0.0])
				scale = TILE_STATIC_SCALE
				if (col + row) % 2 == 0:
					color = color_black.copy()
				else:
					color = color_white.copy()

				e = ModelEntity()
				e.model = self._models[CUBE_MODEL_INDEX]
				e.position = position
				e.rotation = rotation
				e.scale = scale
				e.color = color
				e.original_color = color.copy()
				title_entities.append(e)

	def create_chess_pieces (self, piece_entities, tile_entities):
		"""

		:param piece_entities: in charge of all the entities
		:param tile_entities: for position reference
		:return:
		"""

		color_black = PIECE_COLOR_PLAYER_BLACK
		color_white = PIECE_COLOR_PLAYER_WHITE
		select_color1 = PIECE_SELECTION_COLOR_PLAYER_BLACK
		select_color2 = PIECE_SELECTION_COLOR_PLAYER_WHITE

		# black and white pawns
		for i in range(8):
			piece_entities[1][i] = self.create_piece(1, i, CHESS_PAWN_MODEL_INDEX, color_black, tile_entities,
			                                         select_color1, PLAYER_BLACK)
			piece_entities[6][i] = self.create_piece(6, i, CHESS_PAWN_MODEL_INDEX, color_white, tile_entities,
			                                         select_color2, PLAYER_WHITE)

		piece_entities[0][0] = self.create_piece(0, 0, CHESS_TOWER_MODEL_INDEX, color_black, tile_entities,
		                                         select_color1, PLAYER_BLACK)
		piece_entities[0][1] = self.create_piece(0, 1, CHESS_KNIGHT_MODEL_INDEX, color_black, tile_entities,
		                                         select_color1, PLAYER_BLACK)
		piece_entities[0][2] = self.create_piece(0, 2, CHESS_BISHOP_MODEL_INDEX, color_black, tile_entities,
		                                         select_color1, PLAYER_BLACK)
		piece_entities[0][3] = self.create_piece(0, 3, CHESS_KING_MODEL_INDEX, color_black, tile_entities,
		                                         select_color1, PLAYER_BLACK)
		piece_entities[0][4] = self.create_piece(0, 4, CHESS_QUEEN_MODEL_INDEX, color_black, tile_entities,
		                                         select_color1, PLAYER_BLACK)
		piece_entities[0][5] = self.create_piece(0, 5, CHESS_BISHOP_MODEL_INDEX, color_black, tile_entities,
		                                         select_color1, PLAYER_BLACK)
		piece_entities[0][6] = self.create_piece(0, 6, CHESS_KNIGHT_MODEL_INDEX, color_black, tile_entities,
		                                         select_color1, PLAYER_BLACK)
		piece_entities[0][7] = self.create_piece(0, 7, CHESS_TOWER_MODEL_INDEX, color_black, tile_entities,
		                                         select_color1, PLAYER_BLACK)

		piece_entities[7][0] = self.create_piece(7, 0, CHESS_TOWER_MODEL_INDEX, color_white, tile_entities,
		                                         select_color2, PLAYER_WHITE)
		piece_entities[7][1] = self.create_piece(7, 1, CHESS_KNIGHT_MODEL_INDEX, color_white, tile_entities,
		                                         select_color2, PLAYER_WHITE)
		piece_entities[7][2] = self.create_piece(7, 2, CHESS_BISHOP_MODEL_INDEX, color_white, tile_entities,
		                                         select_color2, PLAYER_WHITE)
		piece_entities[7][3] = self.create_piece(7, 3, CHESS_KING_MODEL_INDEX, color_white, tile_entities,
		                                         select_color2, PLAYER_WHITE)
		piece_entities[7][4] = self.create_piece(7, 4, CHESS_QUEEN_MODEL_INDEX, color_white, tile_entities,
		                                         select_color2, PLAYER_WHITE)
		piece_entities[7][5] = self.create_piece(7, 5, CHESS_BISHOP_MODEL_INDEX, color_white, tile_entities,
		                                         select_color2, PLAYER_WHITE)
		piece_entities[7][6] = self.create_piece(7, 6, CHESS_KNIGHT_MODEL_INDEX, color_white, tile_entities,
		                                         select_color2, PLAYER_WHITE)
		piece_entities[7][7] = self.create_piece(7, 7, CHESS_TOWER_MODEL_INDEX, color_white, tile_entities,
		                                         select_color2, PLAYER_WHITE)

	def create_piece (self, row, col, role, color, tile_entities, select_color, player):
		e = PieceModelEntity()
		e.model = self._models[role]

		e.color = color.copy()
		e.position = tile_entities[col + row * 8].position.copy()
		e.position[1] += PIECE_STATIC_Y_OFFSET
		e.rotation = np.zeros(shape = (3,))
		e.scale = PIECE_STATIC_SCALE.copy()

		e.select_color = select_color.copy()

		# dynamically assigned fields
		e.original_color = e.color.copy()
		e.original_position = e.position.copy()
		e.original_rotation = e.rotation.copy()
		e.original_scale = e.scale.copy()

		e.player = player  # dynamically assign this model to one player

		e.custom_color = e.select_color.copy()
		e.custom_position = np.zeros((3,))
		e.custom_position[1] = PIECE_SELECTION_Y_VALUE
		e.custom_rotation = e.rotation.copy()
		if e.player == PLAYER_BLACK:
			angle = 45.0
		elif e.player == PLAYER_WHITE:
			angle = -45.0

		e.custom_rotation[0] = angle
		e.custom_scale = PIECE_SELECTION_SCALE.copy()
		return e
