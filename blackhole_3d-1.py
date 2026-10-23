"""
3D BLACK HOLE — animated OpenGL scene
-------------------------------------
Install dependencies in VS Code terminal:
    py -m pip install pygame PyOpenGL PyOpenGL_accelerate

Run:
    py blackhole_3d.py

Controls:
    Mouse drag = rotate camera
    Mouse wheel = zoom
    SPACE = pause/resume
    ESC = quit

This is a stylized real-time 3D visualization, not a scientific simulation.
"""

import math
import random
import sys

import pygame
from pygame.locals import (
    DOUBLEBUF,
    KEYDOWN,
    K_ESCAPE,
    K_SPACE,
    MOUSEBUTTONDOWN,
    MOUSEBUTTONUP,
    MOUSEMOTION,
    OPENGL,
    QUIT,
    RESIZABLE,
    VIDEORESIZE,
)
from OpenGL.GL import *
from OpenGL.GLU import *

WIDTH, HEIGHT = 1200, 800
BLACK = (0.0, 0.0, 0.0)

# Disk dimensions and visual density
INNER_RADIUS = 1.55
OUTER_RADIUS = 5.8
PARTICLE_COUNT = 9500
STAR_COUNT = 700

random.seed(22)
particles = []
for _ in range(PARTICLE_COUNT):
    # More material close to the inner disk, but leave a clear central hole.
    r = INNER_RADIUS + (random.random() ** 0.72) * (OUTER_RADIUS - INNER_RADIUS)
    angle = random.random() * math.tau
    particles.append({
        "r": r,
        "a": angle,
        "speed": (0.16 / (r ** 1.42)) * random.uniform(0.72, 1.32),
        "size": random.choices([1.0, 1.5, 2.0, 3.0], [48, 32, 16, 4])[0],
        "jitter": random.random() * math.tau,
        "tone": random.random(),
        "y": random.gauss(0.0, 0.045 + 0.018 * r),
    })

stars = []
for _ in range(STAR_COUNT):
    # Distant stars distributed around the camera's view.
    stars.append((random.uniform(-17, 17), random.uniform(-11, 11),
                  random.uniform(-10, -3), random.uniform(0.25, 0.9),
                  random.choice([1.0, 1.0, 1.5, 2.0])))

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def setup_lighting():
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glEnable(GL_POINT_SMOOTH)
    glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

def draw_stars(t):
    glDisable(GL_DEPTH_TEST)
    for size in (1.0, 1.5, 2.0):
        glPointSize(size)
        glBegin(GL_POINTS)
        for x, y, z, brightness, star_size in stars:
            if star_size != size:
                continue
            pulse = 0.72 + 0.28 * math.sin(t * 0.7 + x * 2.0 + y)
            glColor4f(0.62 * brightness, 0.72 * brightness,
                      1.0 * brightness, brightness * pulse)
            glVertex3f(x, y, z)
        glEnd()
    glEnable(GL_DEPTH_TEST)

def draw_disk(t):
    # Main particle disk, with a subtle vertical warp for a less flat, more 3D look.
    for size in (1.0, 1.5, 2.0, 3.0):
        glPointSize(size)
        glBegin(GL_POINTS)
        for p in particles:
            if p["size"] != size:
                continue
            r = p["r"]
            a = p["a"] + t * p["speed"]
            # Gentle rippling / warping
            y = p["y"] + 0.055 * math.sin(a * 2.0 + t * 0.75 + p["jitter"]) * (r / OUTER_RADIUS)
            x = r * math.cos(a)
            z = r * math.sin(a)

            # Hot inner ring, gold middle, cooler blue outer edge.
            heat = clamp((OUTER_RADIUS - r) / (OUTER_RADIUS - INNER_RADIUS))
            if p["tone"] < 0.13:
                cr, cg, cb = 0.26, 0.58, 1.0
            elif r < 2.2:
                cr, cg, cb = 1.0, 0.92, 0.70
            elif r < 3.35:
                cr, cg, cb = 1.0, 0.42 + 0.30 * heat, 0.10
            elif p["tone"] < 0.62:
                cr, cg, cb = 1.0, 0.63, 0.22
            else:
                cr, cg, cb = 0.34, 0.57, 1.0

            # Relativistic-looking bright arc: one side is brighter than the other.
            doppler = 0.40 + 0.60 * (0.5 + 0.5 * math.cos(a - 0.8)) ** 1.8
            inner_glow = clamp((OUTER_RADIUS - r) / 4.4)
            alpha = (0.32 + 0.62 * inner_glow) * doppler
            glColor4f(cr * doppler, cg * doppler, cb * doppler, alpha)
            glVertex3f(x, y, z)
        glEnd()

    # Fine glowing rings give the disk a luminous layered structure.
    glLineWidth(1.4)
    for radius, color, alpha in [
        (1.58, (1.0, 0.86, 0.64), 0.72),
        (1.72, (1.0, 0.52, 0.16), 0.52),
        (2.05, (1.0, 0.28, 0.07), 0.28),
        (3.0, (0.22, 0.46, 1.0), 0.15),
        (4.4, (0.24, 0.46, 1.0), 0.11),
        (5.6, (0.20, 0.40, 1.0), 0.08),
    ]:
        glColor4f(*color, alpha)
        glBegin(GL_LINE_LOOP)
        for i in range(240):
            a = math.tau * i / 240
            wobble = 1.0 + 0.009 * math.sin(a * 5 + t * 0.7)
            glVertex3f(radius * wobble * math.cos(a), 0.0,
                       radius * wobble * math.sin(a))
        glEnd()

def draw_black_hole():
    # Event horizon: a perfectly dark sphere.
    glPushMatrix()
    glDisable(GL_BLEND)
    glColor4f(0.0, 0.0, 0.0, 1.0)
    quad = gluNewQuadric()
    gluQuadricNormals(quad, GLU_SMOOTH)
    gluSphere(quad, 1.42, 64, 48)
    gluDeleteQuadric(quad)
    glEnable(GL_BLEND)
    glPopMatrix()

    # Thin blue-white photon glow around the silhouette.
    glLineWidth(2.0)
    for radius, alpha in [(1.47, 0.38), (1.51, 0.18), (1.56, 0.08)]:
        glColor4f(0.36, 0.66, 1.0, alpha)
        glBegin(GL_LINE_LOOP)
        for i in range(180):
            a = math.tau * i / 180
            glVertex3f(radius * math.cos(a), 0.0, radius * math.sin(a))
        glEnd()

def draw_lensing_arcs(t):
    # Stylized arcs above/below the disk suggest light bending around the hole.
    glLineWidth(2.0)
    for k in range(2):
        glBegin(GL_LINE_STRIP)
        for i in range(181):
            a = math.pi * (i / 180.0)
            x = 1.52 * math.cos(a)
            z = (1 if k == 0 else -1) * 1.52 * math.sin(a)
            y = (0.42 if k == 0 else -0.42) + 0.035 * math.sin(a * 4 + t)
            glColor4f(0.36, 0.66, 1.0, 0.16 + 0.13 * math.sin(a))
            glVertex3f(x, y, z)
        glEnd()

def main():
    pygame.init()
    pygame.display.set_caption("3D Black Hole — OpenGL")
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL | RESIZABLE)
    setup_lighting()

    glClearColor(0.002, 0.003, 0.012, 1.0)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(42.0, WIDTH / HEIGHT, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

    clock = pygame.time.Clock()
    running = True
    paused = False
    dragging = False
    last_mouse = (0, 0)
    yaw, pitch = -22.0, 23.0
    distance = 13.2
    t = 0.0

    while running:
        dt = min(clock.tick(60) / 1000.0, 0.04)
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_SPACE:
                    paused = not paused
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    dragging = True
                    last_mouse = event.pos
                elif event.button == 4:
                    distance = max(7.0, distance - 0.7)
                elif event.button == 5:
                    distance = min(24.0, distance + 0.7)
            elif event.type == MOUSEBUTTONUP and event.button == 1:
                dragging = False
            elif event.type == MOUSEMOTION and dragging:
                dx = event.pos[0] - last_mouse[0]
                dy = event.pos[1] - last_mouse[1]
                yaw += dx * 0.35
                pitch = max(-5, min(68, pitch + dy * 0.30))
                last_mouse = event.pos
            elif event.type == VIDEORESIZE:
                glViewport(0, 0, event.w, event.h)
                glMatrixMode(GL_PROJECTION)
                glLoadIdentity()
                gluPerspective(42.0, max(0.1, event.w / max(1, event.h)), 0.1, 100.0)
                glMatrixMode(GL_MODELVIEW)

        if not paused:
            t += dt

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -distance)
        glRotatef(pitch, 1, 0, 0)
        glRotatef(yaw, 0, 1, 0)

        draw_stars(t)
        draw_disk(t)
        draw_lensing_arcs(t)
        draw_black_hole()

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
