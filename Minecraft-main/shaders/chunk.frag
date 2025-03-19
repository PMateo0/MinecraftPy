#version 330 core

layout (location = 0) out vec4 fragColor;

const vec3 gamma = vec3(2.2);
const vec3 inv_gamma = 1.0 / gamma;

uniform sampler2DArray u_texture_array_0;
uniform vec3 bg_color;
uniform float water_line;

in vec2 uv;
in float shading;
in vec3 frag_world_pos;

flat in int face_id;
flat in int voxel_id;

void main() {
    // Usamos las UV recibidas directamente sin transformaciones adicionales.
    vec2 final_uv = uv;
    
    // Ajustamos el índice: suponemos que los IDs están definidos de 1 a 7,
    // de modo que restamos 1 para obtener un índice 0-indexado.
    vec3 tex_col = texture(u_texture_array_0, vec3(final_uv, float(voxel_id - 1))).rgb;
    tex_col = pow(tex_col, gamma);
    tex_col *= shading;
    
    // Efecto bajo el nivel de agua.
    if (frag_world_pos.y < water_line)
        tex_col *= vec3(0.0, 0.3, 1.0);
    
    // Efecto de niebla.
    float fog_dist = gl_FragCoord.z / gl_FragCoord.w;
    tex_col = mix(tex_col, bg_color, (1.0 - exp2(-0.00001 * fog_dist * fog_dist)));
    
    tex_col = pow(tex_col, inv_gamma);
    fragColor = vec4(tex_col, 1.0);
}
