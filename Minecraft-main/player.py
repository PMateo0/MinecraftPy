import pygame as pg
from camera import Camera
from settings import *
import glm
import math

class Player(Camera):
    def __init__(self, app, position=PLAYER_POS, yaw=-90, pitch=0):
        self.app = app
        try:
            pg.mouse.set_relative(True)
        except AttributeError:
            print("Warning: pg.mouse.set_relative no está disponible. Usando pg.event.set_grab(True) en su lugar.")
            pg.event.set_grab(True)
        super().__init__(position, yaw, pitch)
        # Tamaño del jugador para las colisiones
        self.player_height = 1.8  # Altura del jugador en bloques
        self.player_width = 0.6   # Ancho del jugador en bloques

    def check_collision(self, new_pos):
        # Obtener las coordenadas de los bloques que rodean al jugador
        x, y, z = new_pos.x, new_pos.y, new_pos.z
        voxel_handler = self.app.scene.world.voxel_handler

        # Verificar colisiones en puntos clave del jugador
        check_points = [
            glm.vec3(x - self.player_width/2, y, z - self.player_width/2),  # Esquina inferior izquierda
            glm.vec3(x + self.player_width/2, y, z - self.player_width/2),  # Esquina inferior derecha
            glm.vec3(x - self.player_width/2, y, z + self.player_width/2),  # Esquina superior izquierda
            glm.vec3(x + self.player_width/2, y, z + self.player_width/2),  # Esquina superior derecha
            glm.vec3(x, y + self.player_height, z)                          # Punto superior central
        ]

        for point in check_points:
            # Convertir las coordenadas a índices enteros
            check_x = math.floor(point.x)
            check_y = math.floor(point.y)
            check_z = math.floor(point.z)
            check_pos = glm.ivec3(check_x, check_y, check_z)
            voxel_id, _, _, _ = voxel_handler.get_voxel_id(check_pos)
            # Permitir el movimiento si el voxel es aire (0) o agua (2)
            if voxel_id not in [0, 2]:
                return False
        return True

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
        # Aplicar sensibilidad para la rotación
        self.rotate_yaw(delta_x=mouse_dx * MOUSE_SENSITIVITY)
        self.rotate_pitch(delta_y=mouse_dy * MOUSE_SENSITIVITY)

    def keyboard_control(self):
        key_state = pg.key.get_pressed()
        vel = PLAYER_SPEED * self.app.delta_time

        # Duplicar la velocidad si se presiona shift
        if key_state[pg.K_LSHIFT] or key_state[pg.K_RSHIFT]:
            vel *= 2.0

        # Crear una copia de la posición actual
        new_pos = glm.vec3(self.position)

        # Movimiento horizontal
        if key_state[pg.K_w]:
            new_pos += self.forward * vel
        if key_state[pg.K_s]:
            new_pos -= self.forward * vel
        if key_state[pg.K_d]:
            new_pos += self.right * vel
        if key_state[pg.K_a]:
            new_pos -= self.right * vel

        # Movimiento vertical con space y control
        if key_state[pg.K_SPACE]:
            new_pos += self.up * vel
        if key_state[pg.K_LCTRL] or key_state[pg.K_RCTRL]:
            new_pos -= self.up * vel

        # Movimiento adicional con Q y E (alternativo para subir y bajar)
        if key_state[pg.K_q]:
            new_pos += self.up * vel
        if key_state[pg.K_e]:
            new_pos -= self.up * vel

        # Actualizar la posición si no hay colisión
        if self.check_collision(new_pos):
            self.position = new_pos
