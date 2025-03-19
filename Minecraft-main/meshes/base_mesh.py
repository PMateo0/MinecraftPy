import numpy as np

class BaseMesh:
    def __init__(self):
        # OpenGL context
        self.ctx = None
        # shader program
        self.program = None
        # vertex buffer data type format: e.g., "3f 3f" o "1u4 2f"
        self.vbo_format = None
        # attribute names according to the format: ("in_position", "in_color") o similar
        self.attrs: tuple[str, ...] = None
        # vertex array object
        self.vao = None

    def get_vertex_data(self) -> np.array:
        """
        Método abstracto que debe devolver los datos del vértice, ya sea como un array de NumPy o como bytes.
        """
        raise NotImplementedError

    def get_vao(self):
        vertex_data = self.get_vertex_data()
        # Si se devuelve un objeto tipo bytes:
        if isinstance(vertex_data, (bytes, bytearray)):
            if len(vertex_data) == 0:
                # Se asume un tamaño de vértice por defecto (por ejemplo, 12 bytes)
                dummy = b'\x00' * 12
                vertex_data = dummy
        else:
            # Si se devuelve un array de NumPy
            if vertex_data.size == 0:
                vertex_data = np.zeros(1, dtype=vertex_data.dtype)
            # Convertir a bytes, en caso de que no lo esté
            vertex_data = vertex_data.tobytes()
        vbo = self.ctx.buffer(vertex_data)
        vao = self.ctx.vertex_array(
            self.program, [(vbo, self.vbo_format, *self.attrs)], skip_errors=True
        )
        return vao

    def render(self):
        self.vao.render()
