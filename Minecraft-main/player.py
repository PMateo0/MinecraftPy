import pygame as pg
from camera import Camera
from settings import *

class Player(Camera):
    def __init__(self, app, position=PLAYER_POS, yaw=-90, pitch=0):
        self.app = app
        # Intenta activar el modo relativo para el ratón; si falla, se informa y se utiliza el grab de eventos
        try:
            pg.mouse.set_relative(True)
        except AttributeError:
            print("Warning: pg.mouse.set_relative no está disponible. Usando pg.event.set_grab(True) en su lugar.")
            pg.event.set_grab(True)
        super().__init__(position, yaw, pitch)

    def update(self):
        self.keyboard_control()
        self.mouse_control()
        super().update()

    def handle_event(self, event):
        # Agregar o eliminar voxeles según se hagan clics del ratón
        if event.type == pg.MOUSEBUTTONDOWN:
            voxel_handler = self.app.scene.world.voxel_handler
            if event.button == 1:
                voxel_handler.set_voxel()
            if event.button == 3:
                voxel_handler.switch_mode()

    def mouse_control(self):
        mouse_dx, mouse_dy = pg.mouse.get_rel()
        # Se aplican los desplazamientos multiplicados por la sensibilidad
        self.rotate_yaw(delta_x=mouse_dx * MOUSE_SENSITIVITY)
        self.rotate_pitch(delta_y=mouse_dy * MOUSE_SENSITIVITY)

    def keyboard_control(self):
        key_state = pg.key.get_pressed()
        vel = PLAYER_SPEED * self.app.delta_time
        if key_state[pg.K_w]:
            self.move_forward(vel)
        if key_state[pg.K_s]:
            self.move_back(vel)
        if key_state[pg.K_d]:
            self.move_right(vel)
        if key_state[pg.K_a]:
            self.move_left(vel)
        if key_state[pg.K_q]:
            self.move_up(vel)
        if key_state[pg.K_e]:
            self.move_down(vel)
