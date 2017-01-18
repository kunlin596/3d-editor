import OpenGL.GL as GL
from PyQt5.QtGui import QMatrix4x4, QOpenGLShader, QOpenGLShaderProgram

from entity import *
from model import *
from utils import *

FLOAT_SIZE = 4
DOUBLE_SIZE = 8
UNSIGNED_INT_SIZE = 4

CUBE_MODEL_INDEX = 0
BUNNY_INDEX = 1


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
		self._entities = dict()
		self._light_sources = []  # lighting

		self._board_entities = ModelEntityList()
		# self._piece_entities = ModelEntityList()
		self._piece_entities = dict()

		self._light_sources.append(Light('sun1',
		                                 np.array([1000.0, 2000.0, 3000.0]),
		                                 np.array([0.7, 0.7, 0.7])))
		self._light_sources.append(Light('sun2',
		                                 np.array([-1000.0, 2000.0, -3000.0]),
		                                 np.array([0.6, 0.6, 0.6])))

		self._mouse_position = np.array([0.0, 0.0])

	def initialize (self):

		self.set_viewport_size(self._window.size() * self._window.devicePixelRatio())
		self._mesh_data[CUBE_MODEL_INDEX] = MeshData.ReadFromFile('mesh/cube.obj', 'cube')
		self._mesh_data[BUNNY_INDEX] = MeshData.ReadFromFile('mesh/bunny.obj', 'bunny')

		MeshData.CheckData(self._mesh_data[CUBE_MODEL_INDEX])
		MeshData.CheckData(self._mesh_data[BUNNY_INDEX])

		self.create_shader()

		# Setup mesh data
		self._shader.bind()
		for k, v in self._mesh_data.items():
			self._models[k] = self._cpu_manager.load_to_vao(v)
			self._entities[k] = []

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
		self._entity_creator.create_checker_board(self._board_entities)

	def sync (self):
		self._camera.update_projection_matrix(self._window.width(), self._window.height())
		self._shader.bind()
		self._shader.setUniformValue('projection_matrix',
		                             QMatrix4x4(self._camera.get_projection_matrix().flatten().tolist()))
		self._shader.release()

	def invalidate (self):
		# TODO
		pass

	def prepare_board_table (self, board_table):
		for row in range(8):
			for col in range(8):
				e = self._board_entities[col + 8 * row]
				if board_table[row][col] > 0.0:
					e.color[0] = 0.3
					e.color[1] = 0.8
					e.color[2] = 0.2
				else:
					if (row + col) % 2 == 0:
						e.color[0] = 0.0
						e.color[1] = 0.0
						e.color[2] = 0.0
					else:
						e.color[0] = 1.0
						e.color[1] = 1.0
						e.color[2] = 1.0

	def prepare_piece_table (self, piece_table):
		for row in range(8):
			for col in range(8):
				if piece_table[row][col] > 0:
					position = self._board_entities[col + 8 * row].position.copy()
					position[1] = self._board_entities[col + 8 * row].position[1] + 6.0
					rotation = np.array([0.0, 0.0, 0.0])
					scale = np.array([9.0, 9.0, 9.0])

					e = ModelEntity()
					e.model = self._models[CUBE_INDEX]
					e.position = position
					e.rotation = rotation
					e.scale = scale
					e.color = np.array([0.2, 0.8, 0.6])
					self._piece_entities[(row, col)] = e
				else:
					if (row, col) in self._piece_entities.keys():
						self._piece_entities.pop((row, col))

	def render (self):

		# right on Ubuntu 16.04, must * 2 on mac
		w = self._window.width()
		h = self._window.height()

		GL.glViewport(0, 0, w * 2, h * 2)  #
		GL.glClearColor(0.5, 0.5, 0.5, 1)
		GL.glEnable(GL.GL_DEPTH_TEST)
		GL.glEnable(GL.GL_CULL_FACE)
		GL.glCullFace(GL.GL_BACK)
		GL.glClear(GL.GL_COLOR_BUFFER_BIT)
		GL.glClear(GL.GL_DEPTH_BUFFER_BIT)

		view_matrix = self._camera.get_view_matrix()

		self._shader.bind()
		self._shader.setUniformValue('view_matrix',
		                             QMatrix4x4(view_matrix.flatten().tolist()))

		self.setup_model(self._models[CUBE_MODEL_INDEX])
		GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER,
		                self._models[
			                CUBE_MODEL_INDEX].indices_vbo)  # [1] intel driver doesn't include this, must bind manually

		for row in range(8):
			for col in range(8):
				e = self._board_entities[col + 8 * row]
				self.setup_entity(e)
				GL.glDrawElements(GL.GL_TRIANGLES,
				                  self._models[CUBE_MODEL_INDEX].num_indices,
				                  GL.GL_UNSIGNED_INT,
				                  None)  # [1]

		for k, v in self._piece_entities.items():
			self.setup_entity(v)
			GL.glDrawElements(GL.GL_TRIANGLES,
			                  self._models[CUBE_MODEL_INDEX].num_indices,
			                  GL.GL_UNSIGNED_INT,
			                  None)  # [1]

		GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)  # [1]

		self.release_model()

		self._shader.release()

		# Restore the OpenGL state for QtQuick rendering
		self._window.update()

	def set_viewport_size (self, size):
		self._viewport_size = size

	def setup_model (self, model):
		raw_model = model
		GL.glBindVertexArray(raw_model.vao)
		GL.glEnableVertexAttribArray(0)
		GL.glEnableVertexAttribArray(1)
		GL.glEnableVertexAttribArray(2)

	def release_model (self):
		GL.glDisableVertexAttribArray(0)
		GL.glDisableVertexAttribArray(1)
		GL.glDisableVertexAttribArray(2)
		GL.glBindVertexArray(0)

	def setup_entity (self, entity):
		m = create_transformation_matrix(entity.position,
		                                 entity.rotation,
		                                 entity.scale)

		self._shader.setUniformValue('uniform_color', QVector3D(entity.color[0], entity.color[1], entity.color[2]))
		self._shader.setUniformValue('model_matrix', QMatrix4x4(m.flatten().tolist()))

	def create_shader (self):
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
		return self._board_entities


class GpuManager(object):
	POSITION_LOCATION = 0
	COLOR_LOCATION = 1
	NORMAL_LOCATION = 2

	def __init__ (self):
		self.vaos = []
		self.vbos = []
		self.textures = []

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
