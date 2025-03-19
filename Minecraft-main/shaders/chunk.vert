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

void unpack(uint packed_data) {
    // Se asume el siguiente orden: x (6 bits), y (6 bits), z (6 bits),
    // voxel_id (8 bits), face_id (3 bits), ao_id (2 bits), flip_id (1 bit)
    uint b_bit = 6u, c_bit = 6u, d_bit = 8u, e_bit = 3u, f_bit = 2u, g_bit = 1u;
    uint fg_bit = f_bit + g_bit;
    uint efg_bit = e_bit + fg_bit;
    uint defg_bit = d_bit + efg_bit;
    uint cdefg_bit = c_bit + defg_bit;
    uint bcdefg_bit = b_bit + cdefg_bit;

    // Desempaquetado
    int _x = int(packed_data >> bcdefg_bit);
    int _y = int((packed_data >> cdefg_bit) & 63u);
    int _z = int((packed_data >> defg_bit) & 63u);
    voxel_id = int((packed_data >> efg_bit) & 255u);
    face_id  = int((packed_data >> fg_bit) & 7u);
    ao_id    = int((packed_data >> g_bit) & 3u);
    flip_id  = int(packed_data & 1u);

    // Asignar posición
    // (Aquí se asume que la posición se codifica con precisión entera; de ser necesario, se puede convertir a float)
    // Se almacenan en variables globales x, y, z (implícitas)
    // Para efectos del shader, usaremos estos valores en la reconstrucción de la posición.
    // En este ejemplo, usaremos _x, _y, _z directamente.
    // (Podrías optar por pasarlos a float en este punto.)
}

void main() {
    unpack(packed_data);

    // Usamos la UV pasada en el atributo
    uv = in_uv;

    shading = face_shading[face_id] * ao_values[ao_id];

    // Reconstruir la posición del vértice a partir de los valores desempaquetados
    vec4 world_pos = m_model * vec4(float(_x), float(_y), float(_z), 1.0);
    frag_world_pos = world_pos.xyz;

    gl_Position = m_proj * m_view * world_pos;
}
