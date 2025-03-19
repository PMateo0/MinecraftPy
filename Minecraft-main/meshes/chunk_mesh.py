from meshes.base_mesh import BaseMesh
from meshes.chunk_mesh_builder import build_chunk_mesh

class ChunkMesh(BaseMesh):
    def __init__(self, chunk):
        super().__init__()
        self.app = chunk.app
        self.chunk = chunk
        self.ctx = self.app.ctx
        self.program = self.app.shader_program.chunk

        # Formato: 1 unsigned int (4 bytes) + 2 floats (8 bytes) = 12 bytes por vértice
        self.vbo_format = '1u4 2f'
        self.format_size = 12  # 12 bytes por vértice
        self.attrs = ('packed_data', 'in_uv')
        self.vao = self.get_vao()

    def rebuild(self):
        self.vao = self.get_vao()

    def get_vertex_data(self):
        mesh = build_chunk_mesh(
            chunk_voxels=self.chunk.voxels,
            format_size=self.format_size,
            chunk_pos=self.chunk.position,
            world_voxels=self.chunk.world.voxels
        )
        return mesh.tobytes()
