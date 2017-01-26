from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtQuick import QQuickView

from entity import *
from render_engine import SceneRenderer
from game_engine import GameEngine


class View(QQuickView):
	colorChanged = pyqtSignal(float, float, float)
	positionChanged = pyqtSignal(float, float, float)
	rotationChanged = pyqtSignal(float, float, float)
	scaleChanged = pyqtSignal(float, float, float)

	def __init__ (self, parent = None):
		super(View, self).__init__(parent)
		self._renderer = None
		self._camera = Camera()
		self._renderer = SceneRenderer(self, self._camera)
		self._game = GameEngine(self, self._camera)

		self.sceneGraphInitialized.connect(self.initialize_scene, type = Qt.DirectConnection)
		self.beforeSynchronizing.connect(self.synchronize_scene, type = Qt.DirectConnection)
		self.beforeRendering.connect(self.render_scene, type = Qt.DirectConnection)
		self.sceneGraphInvalidated.connect(self.invalidate_scene, type = Qt.DirectConnection)

		self.rootContext().setContextProperty("_camera", self._camera)
		self.rootContext().setContextProperty("_window", self)
		# self.rootContext().setContextProperty("_checker_board_entities", self._renderer._title_entities)

		self.setClearBeforeRendering(False)  # otherwise quick would clear everything we render

		self._game.delete_entity.connect(self._renderer.on_delete_entity)

	def initialize_scene (self):
		self._renderer.initialize()
		self.resetOpenGLState()

	def render_scene (self):
		self._renderer.prepare_titles(self._game.hover_table())
		self._renderer.prepare_pieces(self._game.board_table())
		self._renderer.render()
		self.resetOpenGLState()

	def invalidate_scene (self):
		self._renderer.invalidate()
		self.resetOpenGLState()

	def synchronize_scene (self):
		self._renderer.sync()
		self.resetOpenGLState()

	@pyqtSlot(int, int, int)
	def add_piece (self, kind, row, col):
		pass

	@pyqtSlot(int)
	def delete_piece (self, index):
		pass

	@pyqtSlot(int)
	def select_piece (self, index):
		pass

	@pyqtSlot(int)
	def move_camera (self, key):
		self._renderer.move_camera(key)

	@pyqtSlot(int, int)
	def rotate_camera (self, dx, dy):
		self._renderer.rotate_camera(dx, dy)

	@pyqtSlot(int, int)
	def set_mouse_position (self, x, y):
		self._renderer.update_mouse_position(x, y)

	@pyqtSlot(int, int)
	def on_hover (self, x, y):
		self._game.on_mouse_move(x, y)

	@pyqtSlot(int, int, int)
	def on_clicked (self, button, x, y):
		self._game.on_clicked(button, x, y)

	@pyqtSlot()
	def reset_board (self):
		self._renderer.reset_board()
		self._game.reset_board()

	# SLots for signals from QML
	@pyqtSlot(float, float, float)
	def onScaleChanged (self, x, y, z):
		self._renderer.on_scale_changed(x, y, z)

	@pyqtSlot(float, float, float)
	def onPositionChanged (self, x, y, z):
		self._renderer.on_position_changed(x, y, z)

	@pyqtSlot(float, float, float)
	def onColorChanged (self, r, g, b):
		self._renderer.on_color_changed(r, g, b)

	@pyqtSlot(float, float, float)
	def onRotationChanged (self, rx, ry, rz):
		self._renderer.on_rotation_changed(rx, ry, rz)

	# Send signals to QML
	@pyqtSlot(float, float, float)
	def on_selection_color_changed (self, r, g, b):
		self.colorChanged.emit(r, g, b)

	@pyqtSlot(float, float, float)
	def on_selection_position_changed (self, x, y, z):
		self.positionChanged.emit(x, y, z)

	@pyqtSlot(float, float, float)
	def on_selection_rotation_changed (self, rx, ry, rz):
		self.rotationChanged.emit(rx, ry, rz)

	@pyqtSlot(float, float, float)
	def on_selection_scale_changed (self, x, y, z):
		self.scaleChanged.emit(x, y, z)

	@pyqtSlot()
	def on_delete_current_selection (self):
		self._game.delete_current_selection()
