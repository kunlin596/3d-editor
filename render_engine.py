import OpenGL.GL as GL
from PyQt5.QtCore import (QPropertyAnimation,
                          QParallelAnimationGroup)
from PyQt5.QtGui import (QMatrix4x4,
                         QOpenGLShader,
                         QOpenGLShaderProgram)
import cProfile

from entity import *
from model import *
from utils import *


class SceneRenderer(QObject):
	def __init__ (self, window = None, camera = None, parent = None):
		super(SceneRenderer, self).__init__(parent)
		self._window = window
		self._camera = camera
		self._shader = None
		self._entity_creator = None

		self._camera.update_projection_matrix(640.0, 480.0)

		self._model_matrix = np.identity(4)

		self._cpu_manager = GpuManager()  # load data onto gpu
		self._mesh_data = dict()  # store all the raw mesh data
		self._models = dict()  # for model-entity look up
		self._light_sources = []  # lighting

		self._title_entities = ModelEntityList()
		self._piece_entities = [[None for i in range(8)] for j in range(8)]

		self._light_sources.append(Light('sun1',
		                                 np.array([1000.0, 2000.0, 3000.0]),
		                                 np.array([0.7, 0.7, 0.7])))
		self._light_sources.append(Light('sun2',
		                                 np.array([-1000.0, 2000.0, -3000.0]),
		                                 np.array([0.6, 0.6, 0.6])))

		self._mouse_position = np.array([0.0, 0.0])

		# animation for tile
		self._tile_hover_animation_group = QParallelAnimationGroup()
		self._tile_hover_1 = QPropertyAnimation()
		self._tile_hover_2 = QPropertyAnimation()

		self._piece_select_animation_group = QParallelAnimationGroup()
		self._piece_select_animation = []

		self._piece_selected_1 = QPropertyAnimation()
		self._piece_selected_2 = QPropertyAnimation()

		self._tile_move_1 = QPropertyAnimation()
		self._tile_move_2 = QPropertyAnimation()

		self._piece_move_animation_group = QParallelAnimationGroup()
		self._piece_move_animation = []

		self._piece_reset_animation_group = QParallelAnimationGroup()
		self._piece_reset_animation = []

		self._move_animation_finished = True
		self._reset_animation_finished = True

		self._custom_color_ptr = np.zeros((3,))
		self._custom_position_ptr = np.zeros((3,))
		self._custom_rotation_ptr = np.zeros((3,))
		self._custom_scale_ptr = np.zeros((3,))

		self._selected = [-1, -1]

	@pyqtSlot()
	def move_animation_finished (self):
		self._move_animation_finished = True

	@pyqtSlot()
	def reset_animation_finished (self):
		self._reset_animation_finished = True

	def initialize (self):

		self.set_viewport_size(self._window.size() * self._window.devicePixelRatio())
		self._mesh_data[CUBE_MODEL_INDEX] = MeshData.ReadFromFile('mesh/cube_tile.obj', 'cube', offset = 0.5)
		if RENDER_CUBE_AS_PIECE:
			self._mesh_data[CHESS_KING_MODEL_INDEX] = MeshData.ReadFromFile('mesh/ico_sphere.obj', 'king')
			self._mesh_data[CHESS_QUEEN_MODEL_INDEX] = MeshData.ReadFromFile('mesh/cube.obj', 'queen')
			self._mesh_data[CHESS_BISHOP_MODEL_INDEX] = MeshData.ReadFromFile('mesh/cone.obj', 'bishop')
			self._mesh_data[CHESS_KNIGHT_MODEL_INDEX] = MeshData.ReadFromFile('mesh/torus.obj', 'knight')
			self._mesh_data[CHESS_TOWER_MODEL_INDEX] = MeshData.ReadFromFile('mesh/cylinder.obj', 'tower')
			self._mesh_data[CHESS_PAWN_MODEL_INDEX] = MeshData.ReadFromFile('mesh/sphere.obj', 'pawn')
		else:
			self._mesh_data[CHESS_KING_MODEL_INDEX] = MeshData.ReadFromFile('mesh/king.obj', 'king')
			self._mesh_data[CHESS_QUEEN_MODEL_INDEX] = MeshData.ReadFromFile('mesh/queen.obj', 'queen')
			self._mesh_data[CHESS_BISHOP_MODEL_INDEX] = MeshData.ReadFromFile('mesh/bishop.obj', 'bishop')
			self._mesh_data[CHESS_KNIGHT_MODEL_INDEX] = MeshData.ReadFromFile('mesh/knight.obj', 'knight')
			self._mesh_data[CHESS_TOWER_MODEL_INDEX] = MeshData.ReadFromFile('mesh/tower.obj', 'tower')
			self._mesh_data[CHESS_PAWN_MODEL_INDEX] = MeshData.ReadFromFile('mesh/pawn.obj', 'pawn')

			# MeshData.CheckData(self._mesh_data[CUBE_MODEL_INDEX])
			# MeshData.CheckData(self._mesh_data[CHESS_KING_MODEL_INDEX])
			# MeshData.CheckData(self._mesh_data[CHESS_QUEEN_MODEL_INDEX])
			# MeshData.CheckData(self._mesh_data[CHESS_BISHOP_MODEL_INDEX])
			# MeshData.CheckData(self._mesh_data[CHESS_KNIGHT_MODEL_INDEX])
			# MeshData.CheckData(self._mesh_data[CHESS_TOWER_MODEL_INDEX])
			# MeshData.CheckData(self._mesh_data[CHESS_PAWN_MODEL_INDEX])
			pass

		self._create_shader()

		# Setup mesh data
		self._shader.bind()
		for k, v in self._mesh_data.items():
			self._models[k] = self._cpu_manager.load_to_vao(v)

		# Setup diffuse lighting
		for i in range(len(self._light_sources)):
			self._shader.setUniformValue('light_position[{}]'.format(i), QVector3D(self._light_sources[i].position[0],
			                                                                       self._light_sources[i].position[1],
			                                                                       self._light_sources[i].position[2]))
			self._shader.setUniformValue('light_color[{}]'.format(i), QVector3D(self._light_sources[i].color[0],
			                                                                    self._light_sources[i].color[1],
			                                                                    self._light_sources[i].color[2]))

		self._shader.setUniformValue('shine_damper', 20.0)
		self._shader.setUniformValue('reflectivity', 1.0)
		self._shader.setUniformValue('projection_matrix',
		                             QMatrix4x4(self._camera.get_projection_matrix().flatten().tolist()))
		self._shader.release()

		self._entity_creator = EntityCreator(self._models)
		self._entity_creator.create_checker_board(self._title_entities)
		self._entity_creator.create_chess_pieces(self._piece_entities, self._title_entities)

	def sync (self):
		self._camera.update_projection_matrix(self._window.width(), self._window.height())
		self._shader.bind()
		self._shader.setUniformValue('projection_matrix',
		                             QMatrix4x4(self._camera.get_projection_matrix().flatten().tolist()))
		self._shader.release()

	def invalidate (self):
		# TODO
		pass

	def prepare_titles (self, hover_table):
		for row in range(8):
			for col in range(8):
				e = self._title_entities[col + 8 * row]
				if hover_table[row][col] > 0.0:
					if e.position[1] < 0.0:
						self.animate_hover_tile(e)
				else:
					e.color = e.original_color.copy()
					e.position[1] = -0.25

	def prepare_pieces (self, board_table):
		# Change the current entities table in the renderer using the board_table
		for row in range(8):
			for col in range(8):
				if board_table[row][col].status == TILE_EMPTY:
					continue
				elif board_table[row][col].status == TILE_OCCUPIED and self._move_animation_finished:
					self.reset_piece(self._piece_entities[row][col], row, col)
				elif board_table[row][col].status == TILE_SELECTED:
					e = self._piece_entities[row][col]
					if e is not None:
						if self._selected != board_table.selected:
							self.change_current_selection(e)
						else:
							SceneRenderer._ChangeCustomAttribPtr(e.custom_color, self._custom_color_ptr,
							                                     self._window.on_selection_color_changed)
							SceneRenderer._ChangeCustomAttribPtr(e.custom_postion, self._custom_position_ptr,
							                                     self._window.on_selection_position_changed)
							SceneRenderer._ChangeCustomAttribPtr(e.custom_rotation, self._custom_rotation_ptr,
							                                     self._window.on_selection_rotation_changed)
							SceneRenderer._ChangeCustomAttribPtr(e.custom_scale, self._custom_scale_ptr,
							                                     self._window.on_selection_scale_changed)

						self.animate_select_piece(e)
						self._title_entities[col + 8 * row].color = TILE_SELECTED_COLOR.copy()

				elif board_table[row][col].status == TILE_DESTINATION:
					start_r, start_c = board_table.selected
					board_table[start_r][start_c].status = TILE_EMPTY
					board_table[row][col].status = TILE_OCCUPIED
					if start_r is None or start_r is None:
						continue

					e = self._piece_entities[start_r][start_c]
					self._piece_entities[start_r][start_c] = None
					self._piece_entities[row][col] = e
					e.color = e.original_color

					# after the animation the position will be changed
					self.animate_piece_move(e,
					                        self._title_entities[start_c + 8 * start_r].position,
					                        self._title_entities[col + 8 * row].position)
					self._move_animation_finished = False

	def reset_piece (self, e, row, col):
		# self.animate_reset_piece(e, row, col)
		e.position = self._title_entities[col + 8 * row].position.copy()
		e.position[1] += self._title_entities[col + 8 * row].position[1] + PIECE_STATIC_Y_OFFSET
		e.scale = PIECE_STATIC_SCALE.copy()
		e.color = e.original_color.copy()
		e.rotation = np.zeros((3,))

	def animate_hover_tile (self, e):
		self._tile_hover_animation_group = QParallelAnimationGroup()
		self._tile_hover_1 = QPropertyAnimation(e, str.encode('_color'))
		self._tile_hover_1.setDuration(100)
		self._tile_hover_1.setStartValue(QVector3D(e.color[0], e.color[1], e.color[2]))
		self._tile_hover_1.setEndValue(QVector3D(TILE_HOVER_COLOR[0], TILE_HOVER_COLOR[1], TILE_HOVER_COLOR[2]))

		self._tile_hover_2 = QPropertyAnimation(e, str.encode('_position'))
		self._tile_hover_2.setDuration(100)
		self._tile_hover_2.setStartValue(QVector3D(e.position[0], e.position[1], e.position[2]))
		self._tile_hover_2.setEndValue(QVector3D(e.position[0], TILE_HOVER_Y_POSITION, e.position[2]))

		self._tile_hover_animation_group.addAnimation(self._tile_hover_1)
		self._tile_hover_animation_group.addAnimation(self._tile_hover_2)

		self._tile_hover_animation_group.start(policy = QParallelAnimationGroup.DeleteWhenStopped)

	def animate_select_piece (self, e):
		self._piece_select_animation_group = QParallelAnimationGroup()

		a1 = QPropertyAnimation(e, str.encode('_position'))
		a1.setDuration(50)
		a1.setStartValue(QVector3D(e.position[0], e.position[1], e.position[2]))

		a1.setEndValue(
			QVector3D(e.custom_position[0] + e.original_position[0],
			          e.custom_position[1] + e.original_position[1],
			          e.custom_position[2] + e.original_position[2]))

		a2 = QPropertyAnimation(e, str.encode('_scale'))
		a2.setDuration(50)
		a2.setStartValue(QVector3D(e.scale[0], e.scale[1], e.scale[2]))
		a2.setEndValue(
			QVector3D(e.custom_scale[0], e.custom_scale[1], e.custom_scale[2]))

		a3 = QPropertyAnimation(e, str.encode('_rotation'))
		a3.setDuration(100)
		a3.setStartValue(QVector3D(e.rotation[0], e.rotation[1], e.rotation[2]))
		a3.setEndValue(QVector3D(e.custom_rotation[0], e.custom_rotation[1], e.custom_rotation[2]))

		a4 = QPropertyAnimation(e, str.encode('_color'))
		a4.setDuration(100)
		a4.setStartValue(QVector3D(e.color[0], e.color[1], e.color[2]))
		a4.setEndValue(
			QVector3D(e.custom_color[0], e.custom_color[1], e.custom_color[2]))

		self._piece_select_animation.append(a1)
		self._piece_select_animation.append(a2)
		self._piece_select_animation.append(a3)
		self._piece_select_animation.append(a4)

		self._piece_select_animation_group.addAnimation(a1)
		self._piece_select_animation_group.addAnimation(a2)
		self._piece_select_animation_group.addAnimation(a3)
		self._piece_select_animation_group.addAnimation(a4)

		self._piece_select_animation_group.start(policy = QParallelAnimationGroup.DeleteWhenStopped)

	def animate_selected_piece (self, e):
		self._piece_selected_1 = QPropertyAnimation(e, str.encode('_rotation'))
		self._piece_selected_1.setDuration(200)
		self._piece_selected_1.setStartValue(QVector3D(e.rotation[0], 0.0, e.rotation[2]))
		self._piece_selected_1.setEndValue(QVector3D(e.rotation[0], 360.0, e.rotation[2]))
		self._piece_selected_1.start()

	def animate_piece_move (self, e, start, end):
		self._move_animation_finished = False
		self._piece_move_animation_group = QParallelAnimationGroup()
		self._piece_move_animation_group.finished.connect(self.move_animation_finished)

		a1 = QPropertyAnimation(e, str.encode('_position'))
		a1.setDuration(100)
		a1.setStartValue(QVector3D(start[0], PIECE_SELECTION_Y_VALUE, start[2]))
		a1.setEndValue(QVector3D(end[0], end[1] + PIECE_STATIC_Y_OFFSET, end[2]))

		a2 = QPropertyAnimation(e, str.encode('_color'))
		a2.setDuration(100)
		a2.setStartValue(QVector3D(e.color[0], e.color[1], e.color[2]))
		a2.setEndValue(QVector3D(e.original_color[0], e.original_color[1], e.original_color[2]))

		a3 = QPropertyAnimation(e, str.encode('_scale'))
		a3.setDuration(100)
		a3.setStartValue(QVector3D(e.scale[0], e.scale[1], e.scale[2]))
		a3.setEndValue(QVector3D(PIECE_STATIC_SCALE[0], PIECE_STATIC_SCALE[1], PIECE_STATIC_SCALE[2]))

		a4 = QPropertyAnimation(e, str.encode('_rotation'))
		a4.setDuration(100)
		a4.setStartValue(QVector3D(e.rotation[0], e.rotation[1], e.rotation[2]))
		a4.setEndValue(QVector3D(0.0, 0.0, 0.0))

		self._piece_move_animation.append(a1)
		self._piece_move_animation.append(a2)
		self._piece_move_animation.append(a3)
		self._piece_move_animation.append(a4)
		self._piece_move_animation_group.addAnimation(a1)
		self._piece_move_animation_group.addAnimation(a2)
		self._piece_move_animation_group.addAnimation(a3)
		self._piece_move_animation_group.addAnimation(a4)

		self._piece_move_animation_group.start(policy = QParallelAnimationGroup.DeleteWhenStopped)

	def animate_reset_piece (self, e, row, col):
		self._reset_animation_finished = False
		self._piece_reset_animation_group = QParallelAnimationGroup()

		a1 = QPropertyAnimation(e, str.encode('_rotation'))
		a1.setDuration(300)
		a1.setStartValue(QVector3D(e.rotation[0], e.rotation[1], e.rotation[2]))
		a1.setEndValue(QVector3D(34.0, 0.0, 0.0))
		self._piece_reset_animation.append(a1)

		new_pos = self._title_entities[col + 8 * row].position.copy()
		new_pos[1] = self._title_entities[col + 8 * row].position[1] + PIECE_STATIC_Y_OFFSET

		a2 = QPropertyAnimation(e, str.encode('_position'))
		a2.setDuration(3000)
		a2.setStartValue(QVector3D(e.position[0], e.position[1], e.position[2]))
		a2.setEndValue(QVector3D(new_pos[0], new_pos[1], new_pos[2]))
		self._piece_reset_animation.append(a2)

		a3 = QPropertyAnimation(e, str.encode('_scale'))
		a3.setDuration(300)
		a3.setStartValue(QVector3D(e.scale[0], e.scale[1], e.scale[2]))
		a3.setEndValue(QVector3D(PIECE_STATIC_SCALE[0], PIECE_STATIC_SCALE[1], PIECE_STATIC_SCALE[2]))
		self._piece_reset_animation.append(a3)

		a4 = QPropertyAnimation(e, str.encode('_color'))
		a4.setDuration(300)
		a4.setStartValue(QVector3D(e.color[0], e.color[1], e.color[2]))
		a4.setEndValue(QVector3D(e.original_color[0], e.original_color[1], e.original_color[2]))
		self._piece_reset_animation.append(a4)

		self._piece_reset_animation_group.addAnimation(a1)
		self._piece_reset_animation_group.addAnimation(a2)
		self._piece_reset_animation_group.addAnimation(a3)
		self._piece_reset_animation_group.addAnimation(a4)

		self._piece_reset_animation_group.start(policy = QParallelAnimationGroup.DeleteWhenStopped)

	def render (self):
		w = self._window.width()
		h = self._window.height()
		GL.glViewport(0, 0, w * 2, h * 2)
		GL.glClearColor(CLEAR_COLOR[0], CLEAR_COLOR[1], CLEAR_COLOR[2], 1)
		GL.glEnable(GL.GL_DEPTH_TEST)
		GL.glEnable(GL.GL_CULL_FACE)
		GL.glCullFace(GL.GL_BACK)
		GL.glEnable(GL.GL_LINE_SMOOTH)

		GL.glClear(GL.GL_COLOR_BUFFER_BIT)
		GL.glClear(GL.GL_DEPTH_BUFFER_BIT)

		view_matrix = self._camera.get_view_matrix()

		self._shader.bind()
		self._shader.setUniformValue('view_matrix', QMatrix4x4(view_matrix.flatten().tolist()))

		self._render_tiles()
		# cProfile.runctx('self.render_pieces()', globals(), locals())
		self._render_pieces()

		self._shader.release()
		self._window.update()

	def _render_tiles (self):
		self._setup_model(self._models[CUBE_MODEL_INDEX])

		# [1] intel driver doesn't include this, must bind manually
		GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER,
		                self._models[CUBE_MODEL_INDEX].indices_vbo)

		for row in range(8):
			for col in range(8):
				e = self._title_entities[col + 8 * row]
				self._setup_entity(e)
				GL.glDrawElements(GL.GL_TRIANGLES,
				                  self._models[CUBE_MODEL_INDEX].num_indices,
				                  GL.GL_UNSIGNED_INT,
				                  None)  # [1]
		GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)  # [1]
		self._release_model()

	def _render_pieces (self):
		for row in range(8):
			for col in range(8):
				e = self._piece_entities[row][col]
				if e is None:
					continue
				self._setup_model(e.model)
				GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, e.model.indices_vbo)
				self._setup_entity(e)
				GL.glDrawElements(GL.GL_TRIANGLES,
				                  e.model.num_indices,
				                  GL.GL_UNSIGNED_INT,
				                  None)  # [1]
				GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)  # [1]
				self._release_model()

	def set_viewport_size (self, size):
		self._viewport_size = size

	def _setup_model (self, model):
		GL.glBindVertexArray(model.vao)
		GL.glEnableVertexAttribArray(0)
		GL.glEnableVertexAttribArray(1)
		GL.glEnableVertexAttribArray(2)

	def _release_model (self):
		GL.glDisableVertexAttribArray(0)
		GL.glDisableVertexAttribArray(1)
		GL.glDisableVertexAttribArray(2)
		GL.glBindVertexArray(0)

	def _setup_entity (self, entity):
		m = create_transformation_matrix(entity.position,
		                                 entity.rotation,
		                                 entity.scale)

		self._shader.setUniformValue('uniform_color', QVector3D(entity.color[0], entity.color[1], entity.color[2]))
		self._shader.setUniformValue('model_matrix', QMatrix4x4(m.flatten().tolist()))

	def _create_shader (self):
		self._shader = QOpenGLShaderProgram()
		self._shader.addShaderFromSourceFile(QOpenGLShader.Vertex, 'shaders/OpenGL_4_1/vertex.glsl')
		self._shader.addShaderFromSourceFile(QOpenGLShader.Fragment, 'shaders/OpenGL_4_1/fragment.glsl')
		self._shader.link()

	def update_mouse_position (self, x, y):
		self._mouse_position[0] = x
		self._mouse_position[1] = y

	def move_camera (self, key):

		vertical_direction = normalize_vector(np.cross(self._camera.up, self._camera.target))
		head_direction = normalize_vector(np.cross(self._camera.target, vertical_direction))

		if key == Camera.Translation.FORWARD:
			self._camera.eye += normalize_vector(self._camera.target)
		elif key == Camera.Translation.BACKWARD:
			self._camera.eye -= normalize_vector(self._camera.target)
		elif key == Camera.Translation.LEFT:
			self._camera.eye += vertical_direction
		elif key == Camera.Translation.RIGHT:
			self._camera.eye -= vertical_direction
		elif key == Camera.Translation.UP:
			self._camera.eye += head_direction
		elif key == Camera.Translation.DOWN:
			self._camera.eye -= head_direction
		self._camera.update_view_matrix()

	def rotate_camera (self, dx, dy):
		rate = 0.001
		self._camera.target = rotate(-dx * rate, self._camera.up) @ self._camera.target
		self._camera.target = rotate(dy * rate, np.cross(self._camera.up, self._camera.target)) @ self._camera.target
		self._camera.update_view_matrix()

	def checker_board_entities (self):
		return self._title_entities

	def reset_board (self):
		self._entity_creator = EntityCreator(self._models)
		self._entity_creator.create_checker_board(self._title_entities)
		self._piece_entities = [[None for i in range(8)] for j in range(8)]
		self._entity_creator.create_chess_pieces(self._piece_entities, self._title_entities)

	def on_color_changed (self, r, g, b):
		SceneRenderer._AssignCustomAttribBuffer(self._custom_color_ptr, [r, g, b])

	def on_position_changed (self, x, y, z):
		SceneRenderer._AssignCustomAttribBuffer(self._custom_position_ptr, [x, y, z])

	def on_rotation_changed (self, rx, ry, rz):
		SceneRenderer._AssignCustomAttribBuffer(self._custom_rotation_ptr, [rx, ry, rz])

	def on_scale_changed (self, x, y, z):
		SceneRenderer._AssignCustomAttribBuffer(self._custom_scale_ptr, [x, y, z])

	def on_added (self):
		pass

	@staticmethod
	def _AssignCustomAttribBuffer (buf, vals):
		buf[0] = vals[0] if buf[0] != vals[0] else buf[0]
		buf[1] = vals[1] if buf[1] != vals[1] else buf[1]
		buf[2] = vals[2] if buf[2] != vals[2] else buf[2]

	@staticmethod
	def _ChangeCustomAttribPtr (attrib, buf, change_func):
		"""
		Compare the current attrib and the buf, if they are not the same, the change_func will be called
		:param attrib:
		:param buf:
		:param change_func:
		:return:
		"""
		if (attrib != buf).any():
			attrib = buf.copy()
			change_func(attrib[0],
			            attrib[1],
			            attrib[2])

	def change_current_selection (self, e):
		self._custom_color_ptr = e.custom_color
		self._custom_position_ptr = e.custom_position
		self._custom_rotation_ptr = e.custom_rotation
		self._custom_scale_ptr = e.custom_scale
		self._window.on_selection_color_changed(e.custom_color[0],
		                                        e.custom_color[1],
		                                        e.custom_color[2])
		self._window.on_selection_position_changed(e.custom_position[0],
		                                           e.custom_position[1],
		                                           e.custom_position[2])
		self._window.on_selection_rotation_changed(e.custom_rotation[0],
		                                           e.custom_rotation[1],
		                                           e.custom_rotation[2])
		self._window.on_selection_scale_changed(e.custom_scale[0],
		                                        e.custom_scale[1],
		                                        e.custom_scale[2])

	@pyqtSlot(int, int)
	def on_delete_entity (self, row, col):
		e = self._piece_entities[row][col]
		self._piece_entities[row][col] = None
		del e


class GpuManager(object):
	POSITION_LOCATION = 0
	COLOR_LOCATION = 1
	NORMAL_LOCATION = 2

	def __init__ (self):
		self.vaos = []
		self.vbos = []
		self.textures = []

	def __del__ (self):
		# self.release_all()
		pass

	def load_to_vao (self, mesh_data):
		"""
		Upload data to GPU
		:return: RawModel
		"""
		vao = self.create_and_bind_vao()
		self.set_vertex_attribute_data(GpuManager.POSITION_LOCATION, 3, mesh_data.vertices)
		self.set_vertex_attribute_data(GpuManager.COLOR_LOCATION, 3, mesh_data.colors)
		self.set_vertex_attribute_data(GpuManager.NORMAL_LOCATION, 3, mesh_data.normals)

		indices_vbo = self.create_indices_buffer(mesh_data.indices)
		self.unbind_vao()

		return RawModel(vao, indices_vbo, len(mesh_data.indices))

	def set_vertex_attribute_data (self, attrib_id, component_size, data):
		data = data.astype(np.float32)  # data is of float64 by default
		vbo = GL.glGenBuffers(1)
		GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
		GL.glBufferData(GL.GL_ARRAY_BUFFER, len(data) * FLOAT_SIZE * component_size, data, GL.GL_STATIC_DRAW)
		GL.glEnableVertexAttribArray(attrib_id)
		GL.glVertexAttribPointer(attrib_id, component_size, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
		GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
		self.vbos.append(vbo)

	# def load_texture ( self ):
	# 	texture = Texture.CreateFromFile('')
	# 	GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
	# 	GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_LINEAR)
	# 	GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_LOD_BIAS, -0.4)

	def create_and_bind_vao (self):
		vao = GL.glGenVertexArrays(1)
		self.vaos.append(vao)
		GL.glBindVertexArray(vao)
		return vao

	def unbind_vao (self):
		GL.glBindVertexArray(0)

	def create_indices_buffer (self, indices):
		vbo = GL.glGenBuffers(1)
		GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, vbo)
		GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER,
		                len(indices) * UNSIGNED_INT_SIZE,
		                indices,
		                GL.GL_STATIC_DRAW)
		GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
		self.vbos.append(vbo)
		return vbo

	def release_all (self):
		for b in self.vaos:
			GL.glDeleteVertexArrays(b)
		for b in self.vbos:
			GL.glDeleteBuffers(b)
