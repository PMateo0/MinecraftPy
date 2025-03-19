import pygame as pg
import moderngl as mgl
from settings import ATLAS_TILE_SIZE, ATLAS_COLS, ATLAS_ROWS

class Textures:
    def __init__(self, app):
        self.app = app
        self.ctx = app.ctx

        # Cargar texturas individuales
        self.texture_0 = self.load('frame.png')
        self.texture_1 = self.load('water.png')
        # Cargar el texture array usando el atlas
        self.texture_array_0 = self.load('tex_array_0.png', is_tex_array=True)

        # Asignar unidades de textura
        self.texture_0.use(location=0)
        self.texture_array_0.use(location=1)
        self.texture_1.use(location=2)

    def load(self, file_name, is_tex_array=False):
        # Cargar la imagen sin voltear (prueba primero sin flip)
        image = pg.image.load(f'assets/{file_name}').convert_alpha()
        # Si tu asset ya tiene la orientación correcta, no se voltea.
        # Si en cambio la imagen se ve invertida, prueba descomentando la siguiente línea:
        # image = pg.transform.flip(image, False, True)

        if is_tex_array:
            width, height = image.get_size()
            cols = width // ATLAS_TILE_SIZE
            rows = height // ATLAS_TILE_SIZE
            num_layers = cols * rows

            # Extraer cada tile: iteramos las filas en orden inverso para asignar la capa 0 a la fila inferior.
            data = bytearray()
            for row in range(rows - 1, -1, -1):
                for col in range(cols):
                    rect = (col * ATLAS_TILE_SIZE, row * ATLAS_TILE_SIZE, ATLAS_TILE_SIZE, ATLAS_TILE_SIZE)
                    sub_image = image.subsurface(rect).copy()  # copy() para asegurar una imagen independiente
                    data.extend(pg.image.tostring(sub_image, 'RGBA'))
                    
            texture = self.app.ctx.texture_array(
                size=(ATLAS_TILE_SIZE, ATLAS_TILE_SIZE, num_layers),
                components=4,
                data=bytes(data)
            )
        else:
            texture = self.ctx.texture(
                size=image.get_size(),
                components=4,
                data=pg.image.tostring(image, 'RGBA', False)
            )
        texture.anisotropy = 32.0
        texture.build_mipmaps()
        texture.filter = (mgl.NEAREST, mgl.NEAREST)
        return texture
