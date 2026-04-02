import taichi as ti
import numpy as np

# 强制使用 GPU，会自动回退到可用后端
ti.init(arch=ti.gpu)

RES = 800
# 显存缓冲区
pixels = ti.Vector.field(3, dtype=ti.f32, shape=(RES, RES))
curve_points = ti.Vector.field(2, dtype=ti.f32, shape=1001)
gui_points = ti.Vector.field(2, dtype=ti.f32, shape=100)

control_points = []

def de_casteljau(points, t):
    curr = [np.array(p) for p in points]
    while len(curr) > 1:
        curr = [(1.0 - t) * curr[i] + t * curr[i+1] for i in range(len(curr) - 1)]
    return curr[0]

@ti.kernel
def render_kernel(n: ti.i32, anti_aliasing: ti.i32):
    # 背景微弱渐隐（留踪效果）或直接全清
    for i, j in pixels:
        pixels[i, j] *= 0.0 
    
    for k in range(n):
        p = curve_points[k] * float(RES)
        base_i, base_j = int(p.x), int(p.y)
        
        # 遍历邻域进行光栅化
        for i in range(base_i - 1, base_i + 2):
            for j in range(base_j - 1, base_j + 2):
                if 0 <= i < RES and 0 <= j < RES:
                    if anti_aliasing == 1:
                        # 选做：反走样逻辑 (高斯衰减)
                        dist = (ti.Vector([float(i) + 0.5, float(j) + 0.5]) - p).norm()
                        weight = ti.exp(-dist * dist * 3.0) 
                        pixels[i, j] += ti.Vector([0.0, weight, 0.0])
                    else:
                        if i == base_i and j == base_j:
                            pixels[i, j] = ti.Vector([0.0, 1.0, 0.0])

window = ti.ui.Window("Bezier Builder 2026", (RES, RES))
canvas = window.get_canvas()

while window.running:
    # 交互逻辑
    if window.get_event(ti.ui.PRESS):
        if window.event.key == ti.ui.LMB:
            if len(control_points) < 100:
                control_points.append(window.get_cursor_pos())
        elif window.event.key == 'c':
            control_points = []
            pixels.fill(0)

    # 绘制逻辑
    if len(control_points) >= 2:
        samples = [de_casteljau(control_points, t / 1000.0) for t in range(1001)]
        curve_points.from_numpy(np.array(samples, dtype=np.float32))
        render_kernel(1001, 1) # 1 为开启反走样

    # 更新控制点显示
    display_pts = np.full((100, 2), -10.0, dtype=np.float32)
    if control_points:
        display_pts[:len(control_points)] = control_points
    gui_points.from_numpy(display_pts)

    canvas.set_image(pixels)
    canvas.circles(gui_points, radius=0.008, color=(1.0, 0.0, 0.0))
    window.show()
