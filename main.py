import pygame
import cv2
import mediapipe as mp
import random
import math
import sys
from pathlib import Path

# ============================================================
# GESTURE HERO - SUPERMAN
# ============================================================
# OPEN HAND -> Move Superman
# FIST      -> Eye Laser
# R         -> Restart
# ESC       -> Quit
#
# IMPORTANT:
# The complete Superman image is used as ONE sprite.
# No cape separation.
# No image flipping.
# No repeated image scaling.
# ============================================================


# ============================================================
# INITIALIZE PYGAME
# ============================================================

pygame.init()
pygame.mixer.init()
WIDTH = 1000
HEIGHT = 600
FPS = 60

screen = pygame.display.set_mode(
    (WIDTH, HEIGHT)
)

pygame.display.set_caption(
    "GESTURE HERO - Superman"
)

clock = pygame.time.Clock()


# ============================================================
# COLORS
# ============================================================

BLACK = (8, 10, 22)
WHITE = (255, 255, 255)

RED = (255, 60, 60)
GREEN = (0, 240, 110)
BLUE = (50, 150, 255)
YELLOW = (255, 225, 20)

DARK_GRAY = (25, 28, 40)


# ============================================================
# FONTS
# ============================================================

font = pygame.font.SysFont(
    "Arial",
    28,
    bold=True
)

small_font = pygame.font.SysFont(
    "Arial",
    18,
    bold=True
)

big_font = pygame.font.SysFont(
    "Arial",
    55,
    bold=True
)


# ============================================================
# LOAD SUPERMAN IMAGE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

IMAGE_PATH = (
    BASE_DIR /
    "assets" /
    "superman.png"
)
KRYPTONITE_PATH = BASE_DIR / "assets" / "kryptonite.png"

LASER_SOUND_PATH = BASE_DIR / "assets" / "laser_sound.wav"
laser_sound = pygame.mixer.Sound(str(LASER_SOUND_PATH))
laser_sound.set_volume(0.8)
if not IMAGE_PATH.exists():

    print()
    print("ERROR: Superman image was not found.")
    print()
    print("Please put your image here:")
    print(IMAGE_PATH)
    print()

    pygame.quit()
    sys.exit()


try:

    source = pygame.image.load(
        str(IMAGE_PATH)
    ).convert_alpha()

except pygame.error as error:

    print(
        "Could not load Superman image:",
        error
    )

    pygame.quit()
    sys.exit()


# ============================================================
# IMPORTANT:
# DO NOT FLIP THE IMAGE
# ============================================================
#
# The uploaded Superman image already faces RIGHT.
#
# The old code used:
#
# source = pygame.transform.flip(
#     source,
#     True,
#     False
# )
#
# That is removed.
# ============================================================


# ============================================================
# CROP ONLY TRANSPARENT BORDER
# ============================================================

def crop_transparent(surface):

    rect = surface.get_bounding_rect(
        min_alpha=10
    )

    if rect.width <= 0 or rect.height <= 0:

        return surface.copy()

    return surface.subsurface(
        rect
    ).copy()


source = crop_transparent(
    source
)
kryptonite_source = pygame.image.load(
    str(KRYPTONITE_PATH)
).convert_alpha()

kryptonite_source = crop_transparent(
    kryptonite_source
)

kryptonite_sprite = pygame.transform.smoothscale(
    kryptonite_source,
    (60, 60)
)

# ============================================================
# SUPERMAN SIZE
# ============================================================

# The original image is 1275 x 816.
#
# We keep its aspect ratio.
#
# 190 / 122 ≈ 1.557
# Original ratio ≈ 1.562
#
# So the image is not stretched.
# ============================================================

PLAYER_WIDTH = 130
PLAYER_HEIGHT = 83


# Collision area
PLAYER_COLLISION_W = 125
PLAYER_COLLISION_H = 75


# Superman starting position
player_x = 145.0
player_y = HEIGHT / 2


# ============================================================
# CREATE SUPERMAN SPRITE
# ============================================================

# Scale the image ONLY ONCE.

body_sprite = pygame.transform.smoothscale(
    source,
    (
        PLAYER_WIDTH,
        PLAYER_HEIGHT
    )
)


# ============================================================
# OPTIONAL SHARP VERSION
# ============================================================
#
# body_sprite is created once and then reused.
# This prevents the sprite from being resized every frame.
# ============================================================


# ============================================================
# PILLARS
# ============================================================

obstacles = []

OBSTACLE_WIDTH = 70

MIN_GAP = 200
MAX_GAP = 260

score = 0
game_over = False


def create_obstacle(x_position):

    current_gap = max(
        MIN_GAP,
        MAX_GAP -
        (score // 5) * 5
    )

    gap_y = random.randint(
        50,
        HEIGHT - 50 - current_gap
    )

    return {
        "x": float(x_position),
        "gap_y": gap_y,
        "gap_size": current_gap,
        "passed": False
    }


# Create initial pillars

for i in range(4):

    obstacles.append(
        create_obstacle(
            WIDTH + i * 500
        )
    )


# ============================================================
# FLYING ENEMIES
# ============================================================

flying_enemies = []

FLYING_ENEMY_SIZE = 35


def create_flying_enemy():

    return {
        "x": WIDTH + 50,

        "y": random.randint(
            60,
            HEIGHT - 60
        ),

        "size": FLYING_ENEMY_SIZE,

        "phase": (
            random.random() *
            math.pi *
            2
        )
    }


# ============================================================
# PARTICLES
# ============================================================

particles = []


def spawn_explosion(x, y):

    for _ in range(20):

        angle = random.uniform(
            0,
            math.pi * 2
        )

        speed = random.uniform(
            2,
            7
        )

        particles.append({

            "x": x,
            "y": y,

            "vx":
                math.cos(angle) *
                speed,

            "vy":
                math.sin(angle) *
                speed,

            "life":
                random.uniform(
                    0.25,
                    0.65
                ),

            "max_life":
                0.65
        })


def update_particles(dt):

    for p in particles[:]:

        p["x"] += (
            p["vx"] *
            60 *
            dt
        )

        p["y"] += (
            p["vy"] *
            60 *
            dt
        )

        p["vy"] += (
            5 *
            dt
        )

        p["life"] -= dt

        if p["life"] <= 0:

            particles.remove(
                p
            )


def draw_particles():

    for p in particles:

        radius = max(
            1,
            int(
                4 *
                p["life"] /
                p["max_life"]
            )
        )

        pygame.draw.circle(
            screen,
            YELLOW,
            (
                int(p["x"]),
                int(p["y"])
            ),
            radius
        )


# ============================================================
# LASER
# ============================================================

laser_active = False
laser_time = 0.0
laser_sound_playing = False


# ============================================================
# SUPERMAN EYE POSITION
# ============================================================
#
# Your uploaded image faces RIGHT.
#
# The eye is approximately around:
#
# Original image:
# X ≈ 925
# Y ≈ 150
#
# After scaling to 190 x 122:
#
# X ≈ 138
# Y ≈ 22
#
# ============================================================

EYE_X_OFFSET = 138
EYE_Y_OFFSET = 23


def draw_laser():

    if not laser_active:
        return

    if game_over:
        return

    eye_x = int(
        player_x +
        EYE_X_OFFSET
    )

    eye_y = int(
        player_y +
        EYE_Y_OFFSET
    )

    pulse = (
        math.sin(
            laser_time * 25
        ) + 1
    ) / 2

    outer_width = (
        18 +
        int(pulse * 8)
    )

    # Outer laser glow

    pygame.draw.line(
        screen,
        (180, 20, 25),

        (
            eye_x,
            eye_y
        ),

        (
            WIDTH,
            eye_y
        ),

        outer_width
    )

    # Main laser

    pygame.draw.line(
        screen,
        RED,

        (
            eye_x,
            eye_y
        ),

        (
            WIDTH,
            eye_y
        ),

        9
    )

    # White center

    pygame.draw.line(
        screen,
        WHITE,

        (
            eye_x,
            eye_y
        ),

        (
            WIDTH,
            eye_y
        ),

        3
    )

    # Eye glow

    pygame.draw.circle(
        screen,
        WHITE,

        (
            eye_x,
            eye_y
        ),

        8 +
        int(pulse * 3)
    )


# ============================================================
# MEDIAPIPE
# ============================================================

mp_hands = mp.solutions.hands

mp_drawing = (
    mp.solutions.drawing_utils
)


hands = mp_hands.Hands(

    static_image_mode=False,

    max_num_hands=1,

    min_detection_confidence=0.6,

    min_tracking_confidence=0.6
)


# ============================================================
# CAMERA
# ============================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print(
        "Camera could not be opened."
    )

    pygame.quit()
    sys.exit()


CAMERA_WIDTH = 240
CAMERA_HEIGHT = 180

CAMERA_X = (
    WIDTH -
    CAMERA_WIDTH -
    20
)

CAMERA_Y = 20


# ============================================================
# FIST DETECTION
# ============================================================

def is_fist(hand_landmarks):

    fingers = [

        (
            mp_hands.HandLandmark.INDEX_FINGER_TIP,
            mp_hands.HandLandmark.INDEX_FINGER_PIP
        ),

        (
            mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
            mp_hands.HandLandmark.MIDDLE_FINGER_PIP
        ),

        (
            mp_hands.HandLandmark.RING_FINGER_TIP,
            mp_hands.HandLandmark.RING_FINGER_PIP
        ),

        (
            mp_hands.HandLandmark.PINKY_TIP,
            mp_hands.HandLandmark.PINKY_PIP
        )
    ]

    folded = 0

    for tip_id, pip_id in fingers:

        tip = hand_landmarks.landmark[
            tip_id
        ]

        pip = hand_landmarks.landmark[
            pip_id
        ]

        if tip.y > pip.y:

            folded += 1

    return folded >= 3


# ============================================================
# BACKGROUND
# ============================================================

def draw_background():

    screen.fill(
        BLACK
    )

    # Horizontal lines

    for y in range(
        0,
        HEIGHT,
        60
    ):

        pygame.draw.line(
            screen,

            (15, 18, 32),

            (
                0,
                y
            ),

            (
                WIDTH,
                y
            ),

            1
        )

    # Stars

    for i in range(55):

        x = (
            i * 173
        ) % WIDTH

        y = (
            i * 97
        ) % HEIGHT

        pygame.draw.circle(

            screen,

            WHITE,

            (
                x,
                y
            ),

            1 if i % 4
            else 2
        )


# ============================================================
# DRAW SUPERMAN
# ============================================================

def draw_player():

    # Small flying movement

    bob = (
        math.sin(
            pygame.time.get_ticks()
            * 0.008
        ) * 2
    )

    body_x = int(
        player_x
    )

    body_y = int(
        player_y +
        bob
    )

    # Draw complete Superman image

    screen.blit(
        body_sprite,

        (
            body_x,
            body_y
        )
    )

    # Small flight trails

    if not game_over:

        for i in range(3):

            y = int(
                player_y +
                45 +
                i * 9
            )

            pygame.draw.line(

                screen,

                (70, 100, 180),

                (
                    int(
                        player_x -
                        5
                    ),
                    y
                ),

                (
                    int(
                        player_x -
                        35 -
                        i * 12
                    ),
                    y
                ),

                2
            )


# ============================================================
# DRAW PILLAR
# ============================================================

def draw_obstacle(obstacle):

    x = int(
        obstacle["x"]
    )

    gap_y = obstacle[
        "gap_y"
    ]

    gap = obstacle[
        "gap_size"
    ]

    top = pygame.Rect(

        x,
        0,

        OBSTACLE_WIDTH,
        gap_y
    )

    bottom = pygame.Rect(

        x,

        gap_y + gap,

        OBSTACLE_WIDTH,

        HEIGHT -
        gap_y -
        gap
    )

    pygame.draw.rect(
        screen,
        GREEN,
        top
   )

    pygame.draw.rect(
        screen,
        GREEN,
        bottom
    )

    pygame.draw.rect(
        screen,
        BLACK,
        top,
        3
    )

    pygame.draw.rect(
        screen,
        BLACK,
        bottom,
        3
    )


# ============================================================
# DRAW FLYING ENEMY
# ============================================================

def draw_flying_enemy(enemy):

    x = int(enemy["x"])
    y = int(enemy["y"])

    screen.blit(
        kryptonite_sprite,
        (
            x - kryptonite_sprite.get_width() // 2,
            y - kryptonite_sprite.get_height() // 2
        )
    )
# ============================================================
# PLAYER COLLISION
# ============================================================

def check_player_collision():

    global game_over

    player_rect = pygame.Rect(

        int(
            player_x + 25
        ),

        int(
            player_y + 20
        ),

        PLAYER_COLLISION_W,

        PLAYER_COLLISION_H
    )

    # Top / bottom boundaries

    if player_y <= -10:

        game_over = True

    if (
        player_y +
        PLAYER_COLLISION_H
        >=
        HEIGHT + 10
    ):

        game_over = True

    # Pillars

    for obstacle in obstacles:

        x = int(
            obstacle["x"]
        )

        gap_y = obstacle[
            "gap_y"
        ]

        gap = obstacle[
            "gap_size"
        ]

        top = pygame.Rect(

            x,
            0,

            OBSTACLE_WIDTH,
            gap_y
        )

        bottom = pygame.Rect(

            x,

            gap_y + gap,

            OBSTACLE_WIDTH,

            HEIGHT
        )

        if player_rect.colliderect(
            top
        ):

            game_over = True

            spawn_explosion(

                int(
                    player_x + 70
                ),

                int(
                    player_y + 35
                )
            )

        if player_rect.colliderect(
            bottom
        ):

            game_over = True

            spawn_explosion(

                int(
                    player_x + 70
                ),

                int(
                    player_y + 35
                )
            )

    # Flying enemies

    for enemy in flying_enemies:

        distance = math.hypot(

            player_x +
            PLAYER_COLLISION_W / 2 -
            enemy["x"],

            player_y +
            PLAYER_COLLISION_H / 2 -
            enemy["y"]
        )

        if distance < 50:

            game_over = True

            spawn_explosion(

                int(
                    enemy["x"]
                ),

                int(
                    enemy["y"]
                )
            )


# ============================================================
# LASER COLLISION
# ============================================================

def check_laser_collision():

    global score

    if not laser_active:

        return

    eye_x = (
        player_x +
        EYE_X_OFFSET
    )

    eye_y = (
        player_y +
        EYE_Y_OFFSET
    )

    laser_rect = pygame.Rect(

        int(
            eye_x
        ),

        int(
            eye_y - 12
        ),

        WIDTH,

        24
    )

    destroyed = []

    for enemy in flying_enemies:

        enemy_rect = pygame.Rect(

            int(
                enemy["x"] -
                enemy["size"] / 2
            ),

            int(
                enemy["y"] -
                enemy["size"] / 2
            ),

            enemy["size"],

            enemy["size"]
        )

        if laser_rect.colliderect(
            enemy_rect
        ):

            destroyed.append(
                enemy
            )

            score += 5

            spawn_explosion(

                int(
                    enemy["x"]
                ),

                int(
                    enemy["y"]
                )
            )

    for enemy in destroyed:

        if enemy in flying_enemies:

            flying_enemies.remove(
                enemy
            )


# ============================================================
# RESET GAME
# ============================================================

def reset_game():

    global player_y
    global score
    global game_over
    global laser_active
    global obstacles
    global flying_enemies
    global particles

    player_y = HEIGHT / 2

    score = 0

    game_over = False

    laser_active = False

    obstacles = []

    flying_enemies = []

    particles = []

    for i in range(4):

        obstacles.append(

            create_obstacle(

                WIDTH +
                i * 500
            )
        )


# ============================================================
# MAIN LOOP
# ============================================================

running = True

hand_detected = False
fist_detected = False


while running:

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    dt = (
        clock.tick(FPS)
        / 1000.0
    )


    # --------------------------------------------------------
    # EVENTS
    # --------------------------------------------------------

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:

                running = False

            if event.key == pygame.K_r:

                reset_game()


    # --------------------------------------------------------
    # CAMERA
    # --------------------------------------------------------

    ret, frame = cap.read()

    if not ret:

        continue

    # Mirror camera

    frame = cv2.flip(
        frame,
        1
    )

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    results = hands.process(
        rgb
    )


    # --------------------------------------------------------
    # RESET GESTURE STATUS
    # --------------------------------------------------------

    hand_detected = False
    fist_detected = False


    # --------------------------------------------------------
    # HAND DETECTION
    # --------------------------------------------------------

    if results.multi_hand_landmarks:

        hand_detected = True

        hand = (
            results.multi_hand_landmarks[0]
        )

        # Draw hand skeleton

        mp_drawing.draw_landmarks(

            frame,

            hand,

            mp_hands.HAND_CONNECTIONS
        )

        # Check fist

        fist_detected = is_fist(
            hand
        )

        # Wrist

        wrist = hand.landmark[
            mp_hands.HandLandmark.WRIST
        ]

        # Middle finger MCP

        middle_mcp = hand.landmark[

            mp_hands.HandLandmark
            .MIDDLE_FINGER_MCP
        ]

        # Palm position

        palm_y = (

            wrist.y +
            middle_mcp.y

        ) / 2


        # ----------------------------------------------------
        # OPEN HAND MOVEMENT
        # ----------------------------------------------------

        if not game_over:

            target_y = (

                palm_y *
                HEIGHT

                -
                PLAYER_COLLISION_H / 2
            )

            # Smooth movement

            player_y += (

                target_y -
                player_y

            ) * min(

                1.0,

                7.0 *
                dt
            )


            # Keep Superman inside screen

            player_y = max(

                0,

                min(

                    HEIGHT -
                    PLAYER_COLLISION_H,

                    player_y
                )
            )


    # --------------------------------------------------------
    # LASER STATUS
    # --------------------------------------------------------

    new_laser_active = (

        fist_detected
        and
        not game_over
    )
    if new_laser_active and not laser_active:
        laser_sound.play(-1)
    if not new_laser_active and laser_active:
        laser_sound.stop()
    laser_active = new_laser_active

    laser_time += dt


    # --------------------------------------------------------
    # GAME UPDATE
    # --------------------------------------------------------

    if not game_over:

        # Speed increases with score

        current_speed = min(

            10 +
            (score // 5) *
            1.5,

            17
        )


        # ----------------------------------------------------
        # MOVE PILLARS
        # ----------------------------------------------------

        for obstacle in obstacles:

            obstacle["x"] -= (
                current_speed
            )


        # ----------------------------------------------------
        # CREATE NEW PILLARS
        # ----------------------------------------------------

        if (

            len(obstacles) == 0

            or

            obstacles[-1]["x"]
            <
            WIDTH - 300
        ):

            last_x = (

                obstacles[-1]["x"]

                if obstacles

                else WIDTH
            )

            spacing = max(

                450,

                500 -
                (score // 5) * 5
            )

            obstacles.append(

                create_obstacle(

                    last_x +
                    spacing
                )
            )


        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        for obstacle in obstacles:

            if (

                not obstacle["passed"]

                and

                obstacle["x"] +
                OBSTACLE_WIDTH
                <
                player_x
            ):

                obstacle["passed"] = True

                score += 1


        # ----------------------------------------------------
        # REMOVE OLD PILLARS
        # ----------------------------------------------------

        obstacles = [

            o

            for o in obstacles

            if
            o["x"] >
            -OBSTACLE_WIDTH
        ]


        # ----------------------------------------------------
        # CREATE ENEMIES
        # ----------------------------------------------------

        enemy_chance = max(

            18,

            50 - score
        )

        if random.randint(

            1,
            enemy_chance

        ) == 1:

            flying_enemies.append(

                create_flying_enemy()
            )


        # ----------------------------------------------------
        # MOVE ENEMIES
        # ----------------------------------------------------

        enemy_speed = min(

            11 +
            score * 0.15,

            17
        )

        for enemy in flying_enemies:

            enemy["x"] -= (
                enemy_speed
            )

            enemy["phase"] += (
                dt * 7
            )

            enemy["y"] += (

                math.sin(
                    enemy["phase"]
                ) * 0.8
            )


        # ----------------------------------------------------
        # REMOVE OLD ENEMIES
        # ----------------------------------------------------

        flying_enemies = [

            e

            for e in flying_enemies

            if
            e["x"] > -60
        ]


        # ----------------------------------------------------
        # COLLISIONS
        # ----------------------------------------------------

        check_laser_collision()

        check_player_collision()


    # --------------------------------------------------------
    # PARTICLES
    # --------------------------------------------------------

    update_particles(
        dt
    )


    # ========================================================
    # DRAW EVERYTHING
    # ========================================================

    draw_background()


    # Pillars

    for obstacle in obstacles:

        draw_obstacle(
            obstacle
        )


    # Enemies

    for enemy in flying_enemies:

        draw_flying_enemy(
            enemy
        )


    # Laser

    draw_laser()


    # Explosions

    draw_particles()


    # Superman

    draw_player()


    # ========================================================
    # SCORE
    # ========================================================

    score_text = font.render(

        f"Score: {score}",

        True,

        WHITE
    )

    screen.blit(

        score_text,

        (
            20,
            20
        )
    )


    # ========================================================
    # HAND STATUS
    # ========================================================

    hand_status = small_font.render(

        "HAND DETECTED"
        if hand_detected
        else
        "NO HAND",

        True,

        GREEN
        if hand_detected
        else
        RED
    )

    screen.blit(

        hand_status,

        (
            20,
            55
        )
    )


    # ========================================================
    # GESTURE STATUS
    # ========================================================

    gesture_text = small_font.render(

        "FIST: EYE LASER"
        if fist_detected
        else
        "OPEN HAND: MOVE",

        True,

        YELLOW
        if fist_detected
        else
        GREEN
    )

    screen.blit(

        gesture_text,

        (
            20,
            82
        )
    )


    # ========================================================
    # CAMERA PREVIEW
    # ========================================================

    preview = cv2.resize(

        frame,

        (
            CAMERA_WIDTH,
            CAMERA_HEIGHT
        ),

        interpolation=cv2.INTER_AREA
    )

    preview = cv2.cvtColor(

        preview,

        cv2.COLOR_BGR2RGB
    )

    camera_surface = (
        pygame.surfarray.make_surface(
            preview.swapaxes(0, 1)
        )
    )


    # Camera background

    pygame.draw.rect(

        screen,

        DARK_GRAY,

        (

            CAMERA_X - 6,

            CAMERA_Y - 6,

            CAMERA_WIDTH + 12,

            CAMERA_HEIGHT + 38
        ),

        border_radius=5
    )


    # Camera image

    screen.blit(

        camera_surface,

        (
            CAMERA_X,
            CAMERA_Y
        )
    )


    # Camera border

    border = (

        YELLOW

        if fist_detected

        else GREEN

        if hand_detected

        else RED
    )


    pygame.draw.rect(

        screen,

        border,

        (

            CAMERA_X,

            CAMERA_Y,

            CAMERA_WIDTH,

            CAMERA_HEIGHT
        ),

        4
    )


    # ========================================================
    # HAND AREA GUIDE
    # ========================================================

    guide_margin = 25

    pygame.draw.rect(

        screen,

        GREEN,

        (

            CAMERA_X +
            guide_margin,

            CAMERA_Y +
            guide_margin,

            CAMERA_WIDTH -
            guide_margin * 2,

            CAMERA_HEIGHT -
            guide_margin * 2
        ),

        2
    )


    camera_text = small_font.render(

        "HAND AREA",

        True,

        WHITE
    )

    screen.blit(

        camera_text,

        (

            CAMERA_X + 75,

            CAMERA_Y +
            CAMERA_HEIGHT + 8
        )
    )


    # ========================================================
    # GAME OVER
    # ========================================================

    if game_over:

        overlay = pygame.Surface(

            (
                WIDTH,
                HEIGHT
            ),

            pygame.SRCALPHA
        )

        overlay.fill(

            (
                0,
                0,
                0,
                125
            )
        )

        screen.blit(

            overlay,

            (
                0,
                0
            )
        )


        game_over_text = big_font.render(

            "GAME OVER",

            True,

            RED
        )


        final_score = font.render(

            f"Final Score: {score}",

            True,

            WHITE
        )


        restart = font.render(

            "Press R to Restart",

            True,

            WHITE
        )


        screen.blit(

            game_over_text,

            (

                WIDTH // 2 -
                game_over_text.get_width() // 2,

                HEIGHT // 2 - 85
            )
        )


        screen.blit(

            final_score,

            (

                WIDTH // 2 -
                final_score.get_width() // 2,

                HEIGHT // 2 - 15
            )
        )


        screen.blit(

            restart,

            (

                WIDTH // 2 -
                restart.get_width() // 2,

                HEIGHT // 2 + 35
            )
        )


    # ========================================================
    # INSTRUCTIONS
    # ========================================================

    instruction = small_font.render(

        "OPEN HAND = MOVE   |   FIST = EYE LASER",

        True,

        WHITE
    )

    screen.blit(

        instruction,

        (

            WIDTH // 2 -
            instruction.get_width() // 2,

            HEIGHT - 30
        )
    )


    # ========================================================
    # UPDATE DISPLAY
    # ========================================================

    pygame.display.flip()


# ============================================================
# CLEANUP
# ============================================================

cap.release()

hands.close()

cv2.destroyAllWindows()

pygame.quit()

sys.exit()
