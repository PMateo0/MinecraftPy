#version 330 core

layout (location = 0) in uint packed_data;
layout (location = 1) in vec2 in_uv;

uniform mat4 m_proj;
uniform mat4 m_view;
uniform mat4 m_model;

flat out int voxel_id;
flat out int face_id;
flat out int ao_id;
flat out int flip_id;

out vec2 uv;
out float shading;
out vec3 frag_world_pos;

const float ao_values[4] = float[4](0.1, 0.25, 0.5, 1.0);
const float face_shading[6] = float[6](
    1.0, 0.5,  // top, bottom
    0.5, 0.8,  // right, left
    0.5, 0.8   // front, back
);

void unpack(uint packed_data, out int _x, out int _y, out int _z, out int _voxel_id, out int _face_id, out int _ao_id, out int _flip_id) {
    // Definición de bits y máscaras (según pack_data)
    uint b_bit = 6u, c_bit = 6u, d_bit = 8u, e_bit = 3u, f_bit = 2u, g_bit = 1u;
    uint b_mask = 63u, c_mask = 63u, d_mask = 255u, e_mask = 7u, f_mask = 3u, g_mask = 1u;
    uint fg_bit = f_bit + g_bit;
    uint efg_bit = e_bit + fg_bit;
    uint defg_bit = d_bit + efg_bit;
    uint cdefg_bit = c_bit + defg_bit;
    uint bcdefg_bit = b_bit + cdefg_bit;
    
    _x = int(packed_data >> bcdefg_bit);
    _y = int((packed_data >> cdefg_bit) & b_mask);
    _z = int((packed_data >> defg_bit) & c_mask);
    _voxel_id = int((packed_data >> efg_bit) & d_mask);
    _face_id  = int((packed_data >> fg_bit) & e_mask);
    _ao_id    = int((packed_data >> g_bit) & f_mask);
    _flip_id  = int(packed_data & g_mask);
}

void main() {
    int _x, _y, _z, _voxel_id, _face_id, _ao_id, _flip_id;
    unpack(packed_data, _x, _y, _z, _voxel_id, _face_id, _ao_id, _flip_id);
    
    voxel_id = _voxel_id;
    face_id = _face_id;
    ao_id = _ao_id;
    flip_id = _flip_id;
    
    // Se utiliza la UV tal como se generó en el mesh
    uv = in_uv;
    shading = face_shading[face_id] * ao_values[ao_id];
    
    vec4 world_pos = m_model * vec4(float(_x), float(_y), float(_z), 1.0);
    frag_world_pos = world_pos.xyz;
    
    gl_Position = m_proj * m_view * world_pos;
}
