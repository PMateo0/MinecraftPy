from settings import *
from numba import njit, uint8
import numpy as np

@njit
def get_ao(local_pos, world_pos, world_voxels, plane):
    x, y, z = local_pos
    wx, wy, wz = world_pos

    if plane == 'Y':
        a = is_void((x    , y, z - 1), (wx    , wy, wz - 1), world_voxels)
        b = is_void((x - 1, y, z - 1), (wx - 1, wy, wz - 1), world_voxels)
        c = is_void((x - 1, y, z    ), (wx - 1, wy, wz    ), world_voxels)
        d = is_void((x - 1, y, z + 1), (wx - 1, wy, wz + 1), world_voxels)
        e = is_void((x    , y, z + 1), (wx    , wy, wz + 1), world_voxels)
        f = is_void((x + 1, y, z + 1), (wx + 1, wy, wz + 1), world_voxels)
        g = is_void((x + 1, y, z    ), (wx + 1, wy, wz    ), world_voxels)
        h = is_void((x + 1, y, z - 1), (wx + 1, wy, wz - 1), world_voxels)
    elif plane == 'X':
        a = is_void((x, y    , z - 1), (wx, wy    , wz - 1), world_voxels)
        b = is_void((x, y - 1, z - 1), (wx, wy - 1, wz - 1), world_voxels)
        c = is_void((x, y - 1, z    ), (wx, wy - 1, wz    ), world_voxels)
        d = is_void((x, y - 1, z + 1), (wx, wy - 1, wz + 1), world_voxels)
        e = is_void((x, y    , z + 1), (wx, wy    , wz + 1), world_voxels)
        f = is_void((x, y + 1, z + 1), (wx, wy + 1, wz + 1), world_voxels)
        g = is_void((x, y + 1, z    ), (wx, wy + 1, wz    ), world_voxels)
        h = is_void((x, y + 1, z - 1), (wx, wy + 1, wz - 1), world_voxels)
    else:  # Z plane
        a = is_void((x - 1, y    , z), (wx - 1, wy    , wz), world_voxels)
        b = is_void((x - 1, y - 1, z), (wx - 1, wy - 1, wz), world_voxels)
        c = is_void((x    , y - 1, z), (wx    , wy - 1, wz), world_voxels)
        d = is_void((x + 1, y - 1, z), (wx + 1, wy - 1, wz), world_voxels)
        e = is_void((x + 1, y    , z), (wx + 1, wy    , wz), world_voxels)
        f = is_void((x + 1, y + 1, z), (wx + 1, wy + 1, wz), world_voxels)
        g = is_void((x    , y + 1, z), (wx    , wy + 1, wz), world_voxels)
        h = is_void((x - 1, y + 1, z), (wx - 1, wy + 1, wz), world_voxels)
    ao = (a + b + c, g + h + a, e + f + g, c + d + e)
    return ao

@njit
def pack_data(x, y, z, voxel_id, face_id, ao_id, flip_id):
    # x: 6bit, y: 6bit, z: 6bit, voxel_id: 8bit, face_id: 3bit, ao_id: 2bit, flip_id: 1bit
    a, b, c, d, e, f, g = x, y, z, voxel_id, face_id, ao_id, flip_id
    b_bit, c_bit, d_bit, e_bit, f_bit, g_bit = 6, 6, 8, 3, 2, 1
    fg_bit = f_bit + g_bit
    efg_bit = e_bit + fg_bit
    defg_bit = d_bit + efg_bit
    cdefg_bit = c_bit + defg_bit
    bcdefg_bit = b_bit + cdefg_bit
    packed = (a << bcdefg_bit) | (b << cdefg_bit) | (c << defg_bit) | (d << efg_bit) | (e << fg_bit) | (f << g_bit) | g
    return packed

@njit
def get_chunk_index(world_voxel_pos):
    wx, wy, wz = world_voxel_pos
    cx = wx // CHUNK_SIZE
    cy = wy // CHUNK_SIZE
    cz = wz // CHUNK_SIZE
    if not (0 <= cx < WORLD_W and 0 <= cy < WORLD_H and 0 <= cz < WORLD_D):
        return -1
    return cx + WORLD_W * cz + WORLD_AREA * cy

@njit
def is_void(local_voxel_pos, world_voxel_pos, world_voxels):
    chunk_index = get_chunk_index(world_voxel_pos)
    if chunk_index == -1:
        return False
    chunk_voxels = world_voxels[chunk_index]
    x, y, z = local_voxel_pos
    voxel_index = x % CHUNK_SIZE + (z % CHUNK_SIZE) * CHUNK_SIZE + (y % CHUNK_SIZE) * CHUNK_AREA
    if chunk_voxels[voxel_index]:
        return False
    return True

@njit
def add_data(vertex_data, index, *vertices):
    for v in vertices:
        vertex_data[index] = v
        index += 1
    return index

def build_chunk_mesh(chunk_voxels, format_size, chunk_pos, world_voxels):
    """
    Genera la malla del chunk. Por cada vértice se crea una tupla: (packed_data, (u, v)).
    Se devuelve un array estructurado con dtype [('packed_data', uint32), ('in_uv', float32, (2,))]
    """
    vertices = []
    # UV locales estándar para un cuadrado
    uv0 = (0.0, 0.0)
    uv1 = (1.0, 0.0)
    uv2 = (1.0, 1.0)
    uv3 = (0.0, 1.0)
    
    for x in range(CHUNK_SIZE):
        for y in range(CHUNK_SIZE):
            for z in range(CHUNK_SIZE):
                voxel_index = x + CHUNK_SIZE * z + CHUNK_AREA * y
                voxel_id = chunk_voxels[voxel_index]
                if voxel_id == 0:
                    continue
                cx, cy, cz = chunk_pos
                wx = x + cx * CHUNK_SIZE
                wy = y + cy * CHUNK_SIZE
                wz = z + cz * CHUNK_SIZE
                
                # Top face (face_id = 0)
                if is_void((x, y+1, z), (wx, wy+1, wz), world_voxels):
                    ao = get_ao((x, y+1, z), (wx, wy+1, wz), world_voxels, 'Y')
                    flip_id = (ao[1] + ao[3]) > (ao[0] + ao[2])
                    v0 = pack_data(x, y+1, z, voxel_id, 0, ao[0], flip_id)
                    v1 = pack_data(x+1, y+1, z, voxel_id, 0, ao[1], flip_id)
                    v2 = pack_data(x+1, y+1, z+1, voxel_id, 0, ao[2], flip_id)
                    v3 = pack_data(x, y+1, z+1, voxel_id, 0, ao[3], flip_id)
                    if flip_id:
                        vertices.append((v1, uv1))
                        vertices.append((v0, uv0))
                        vertices.append((v3, uv3))
                        vertices.append((v1, uv1))
                        vertices.append((v3, uv3))
                        vertices.append((v2, uv2))
                    else:
                        vertices.append((v0, uv0))
                        vertices.append((v3, uv3))
                        vertices.append((v2, uv2))
                        vertices.append((v0, uv0))
                        vertices.append((v2, uv2))
                        vertices.append((v1, uv1))
                
                # Bottom face (face_id = 1)
                if is_void((x, y-1, z), (wx, wy-1, wz), world_voxels):
                    ao = get_ao((x, y-1, z), (wx, wy-1, wz), world_voxels, 'Y')
                    flip_id = (ao[1] + ao[3]) > (ao[0] + ao[2])
                    v0 = pack_data(x, y, z, voxel_id, 1, ao[0], flip_id)
                    v1 = pack_data(x+1, y, z, voxel_id, 1, ao[1], flip_id)
                    v2 = pack_data(x+1, y, z+1, voxel_id, 1, ao[2], flip_id)
                    v3 = pack_data(x, y, z+1, voxel_id, 1, ao[3], flip_id)
                    if flip_id:
                        vertices.append((v1, uv1))
                        vertices.append((v3, uv3))
                        vertices.append((v0, uv0))
                        vertices.append((v1, uv1))
                        vertices.append((v2, uv2))
                        vertices.append((v3, uv3))
                    else:
                        vertices.append((v0, uv0))
                        vertices.append((v2, uv2))
                        vertices.append((v3, uv3))
                        vertices.append((v0, uv0))
                        vertices.append((v1, uv1))
                        vertices.append((v2, uv2))
                
                # Right face (face_id = 2)
                if is_void((x+1, y, z), (wx+1, wy, wz), world_voxels):
                    ao = get_ao((x+1, y, z), (wx+1, wy, wz), world_voxels, 'X')
                    flip_id = (ao[1] + ao[3]) > (ao[0] + ao[2])
                    v0 = pack_data(x+1, y, z, voxel_id, 2, ao[0], flip_id)
                    v1 = pack_data(x+1, y+1, z, voxel_id, 2, ao[1], flip_id)
                    v2 = pack_data(x+1, y+1, z+1, voxel_id, 2, ao[2], flip_id)
                    v3 = pack_data(x+1, y, z+1, voxel_id, 2, ao[3], flip_id)
                    if flip_id:
                        vertices.append((v3, uv3))
                        vertices.append((v0, uv0))
                        vertices.append((v1, uv1))
                        vertices.append((v3, uv3))
                        vertices.append((v1, uv1))
                        vertices.append((v2, uv2))
                    else:
                        vertices.append((v0, uv0))
                        vertices.append((v1, uv1))
                        vertices.append((v2, uv2))
                        vertices.append((v0, uv0))
                        vertices.append((v2, uv2))
                        vertices.append((v3, uv3))
                
                # Left face (face_id = 3)
                if is_void((x-1, y, z), (wx-1, wy, wz), world_voxels):
                    ao = get_ao((x-1, y, z), (wx-1, wy, wz), world_voxels, 'X')
                    flip_id = (ao[1] + ao[3]) > (ao[0] + ao[2])
                    v0 = pack_data(x, y, z, voxel_id, 3, ao[0], flip_id)
                    v1 = pack_data(x, y+1, z, voxel_id, 3, ao[1], flip_id)
                    v2 = pack_data(x, y+1, z+1, voxel_id, 3, ao[2], flip_id)
                    v3 = pack_data(x, y, z+1, voxel_id, 3, ao[3], flip_id)
                    if flip_id:
                        vertices.append((v3, uv3))
                        vertices.append((v1, uv1))
                        vertices.append((v0, uv0))
                        vertices.append((v3, uv3))
                        vertices.append((v2, uv2))
                        vertices.append((v1, uv1))
                    else:
                        vertices.append((v0, uv0))
                        vertices.append((v2, uv2))
                        vertices.append((v1, uv1))
                        vertices.append((v0, uv0))
                        vertices.append((v3, uv3))
                        vertices.append((v2, uv2))
                
                # Back face (face_id = 4)
                if is_void((x, y, z-1), (wx, wy, wz-1), world_voxels):
                    ao = get_ao((x, y, z-1), (wx, wy, wz-1), world_voxels, 'Z')
                    flip_id = (ao[1] + ao[3]) > (ao[0] + ao[2])
                    v0 = pack_data(x, y, z, voxel_id, 4, ao[0], flip_id)
                    v1 = pack_data(x, y+1, z, voxel_id, 4, ao[1], flip_id)
                    v2 = pack_data(x+1, y+1, z, voxel_id, 4, ao[2], flip_id)
                    v3 = pack_data(x+1, y, z, voxel_id, 4, ao[3], flip_id)
                    if flip_id:
                        vertices.append((v3, uv3))
                        vertices.append((v0, uv0))
                        vertices.append((v1, uv1))
                        vertices.append((v3, uv3))
                        vertices.append((v1, uv1))
                        vertices.append((v2, uv2))
                    else:
                        vertices.append((v0, uv0))
                        vertices.append((v1, uv1))
                        vertices.append((v2, uv2))
                        vertices.append((v0, uv0))
                        vertices.append((v2, uv2))
                        vertices.append((v3, uv3))
                
                # Front face (face_id = 5)
                if is_void((x, y, z+1), (wx, wy, wz+1), world_voxels):
                    ao = get_ao((x, y, z+1), (wx, wy, wz+1), world_voxels, 'Z')
                    flip_id = (ao[1] + ao[3]) > (ao[0] + ao[2])
                    v0 = pack_data(x, y, z+1, voxel_id, 5, ao[0], flip_id)
                    v1 = pack_data(x, y+1, z+1, voxel_id, 5, ao[1], flip_id)
                    v2 = pack_data(x+1, y+1, z+1, voxel_id, 5, ao[2], flip_id)
                    v3 = pack_data(x+1, y, z+1, voxel_id, 5, ao[3], flip_id)
                    if flip_id:
                        vertices.append((v3, uv3))
                        vertices.append((v1, uv1))
                        vertices.append((v0, uv0))
                        vertices.append((v3, uv3))
                        vertices.append((v2, uv2))
                        vertices.append((v1, uv1))
                    else:
                        vertices.append((v0, uv0))
                        vertices.append((v2, uv2))
                        vertices.append((v1, uv1))
                        vertices.append((v0, uv0))
                        vertices.append((v3, uv3))
                        vertices.append((v2, uv2))
                        
    dtype = np.dtype([('packed_data', np.uint32), ('in_uv', np.float32, (2,))])
    vertex_array = np.array(vertices, dtype=dtype)
    return vertex_array
