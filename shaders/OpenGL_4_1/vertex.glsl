#version 410

layout (location = 0) in vec3 position;
layout (location = 1) in vec3 color;
layout (location = 2) in vec3 normal;

uniform mat4 model_matrix;
uniform mat4 view_matrix;
uniform mat4 projection_matrix;

uniform float uniform_color;

out vec3 pass_color;

void main () {
    mat4 m = projection_matrix * view_matrix * model_matrix;
    gl_Position = m * vec4(position, 1.0);
    pass_color = color;
//    pass_color = vec3(uniform_color, uniform_color, uniform_color);
}
