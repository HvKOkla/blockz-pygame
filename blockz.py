import pygame
import math
import time
import random
import sys, os
from pathlib import Path
from dataclasses import dataclass
pygame.init()
pygame.mixer.init()

SETTINGS = {
    "DISABLE_CULLING": False,
    "DISABLE_LEVEL_SELECTION": False,
    "FPS_MAX": 30,
    "MUSIC_VOLUME": 1 # 1 max
}

WIDTH,HEIGHT = 480,360
screen = pygame.display.set_mode((WIDTH,HEIGHT), pygame.SCALED | pygame.FULLSCREEN)
pygame.display.set_caption("Blockz")
clock = pygame.time.Clock()

scene = "playing" if SETTINGS["DISABLE_LEVEL_SELECTION"] else "level_selection"

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    base_dir = Path(sys._MEIPASS)
else:
    base_dir = Path(__file__).resolve().parent

songs = [
    base_dir / "assets/music1.wav",
    base_dir / "assets/music2.wav"
]
SONG_END = pygame.USEREVENT + 1
pygame.mixer.music.set_endevent(SONG_END)

def play_song():
    new_song = random.choice(songs)
    pygame.mixer.music.load(new_song)
    pygame.mixer.music.play()

play_song()

sounds = {
    "die": pygame.mixer.Sound(base_dir / "assets/die.wav"),
    "end": pygame.mixer.Sound(base_dir / "assets/end.wav"),
    "jump": pygame.mixer.Sound(base_dir / "assets/jump.wav"),
    "bouncy": pygame.mixer.Sound(base_dir / "assets/bouncy.wav")
}

alpha_overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

CameraRot = pygame.Vector2(math.radians(-20), 0)
CameraPos = pygame.Vector3(0,0,0)

mouse_sensitivity = math.radians(50)

FL = 300
nearZ = 0.3
x2 = 0

level = 1

playerSize = 0.8
playerVelY = 0
playerPos = pygame.Vector3(0,0,0)
playerSpeed = 4
playerJumpHeight = 6
playerStart = pygame.Vector3(0,0,0)
shadowY = 0

@dataclass
class Block:
    color: tuple
    size: pygame.Vector3
    pos: pygame.Vector3
    blocktype: str

    def __hash__(self):
        return hash(str(self.color) + str(self.size) + str(self.pos) + self.blocktype)

blocks: list[Block] = []
BlockTypes = {}
CollisionType = []

current_fps = 0
frame = 0

DRAW_SIZE = 0.075
DRAW_COLOR = (0,0,0)
DRAW_TRANSPARENCY = 153

font = pygame.font.Font(base_dir / "assets/RobotoMono-Regular.ttf")

class Game_Drawer:
    def __init__(self):
        self.cosX = 0
        self.cosY = 0
        self.p = 0
        self.sinX = 0
        self.sinY = 0
        self.x1,self.y1,self.z1 = 0,0,0
        self.x2,self.y2,self.z2 = 0,0,0
        self.getID = 0
        self.sort_High = 0
        self.sort_Low = 0
        self.sort_Mid = 0
        self.vx,self.vy,self.vz = 0,0,0
        self.z = 0
        self.collision = 0
        self.mouseOx = 0
        self.mouseOy = 0
        self.mouseRotation = 0
        self.getY = 0
        self.mag = 0
        self.LayerIDs = []
        self.LayerValues = []
        self.CollisionID = 0

        # variables that arent a part of the original game
        # and are used for different purposes
        self.used_circle_points = []
        self.fps_show = 0

    def block_order(self):
        self.LayerIDs.clear()
        self.LayerValues.clear()
        for idx, block in enumerate(blocks):
            self.vx = (block.pos.x+(block.size.x/2))-CameraPos.x
            self.vy = (block.pos.y+(block.size.y/2))-CameraPos.y
            self.vz = (block.pos.z+(block.size.z/2))-CameraPos.z
            self.z = math.hypot(self.vx, self.vy, self.vz)
            self.LayerValues.append(self.z)
            self.sort_Low = 1
            self.sort_High = len(self.LayerValues)
            while self.sort_Low < self.sort_High:
                self.sort_Mid = (self.sort_Low+self.sort_High)//2
                if self.z < self.LayerValues[self.LayerIDs[self.sort_Mid-1]-1]:
                    self.sort_Low = self.sort_Mid + 1
                else:
                    self.sort_High = self.sort_Mid
            self.LayerIDs.insert(self.sort_Low-1, idx+1)

    def init_trigonometry(self):
        self.sinX = math.sin(CameraRot.x)
        self.cosX = math.cos(CameraRot.x)
        self.sinY = math.sin(CameraRot.y)
        self.cosY = math.cos(CameraRot.y)

    def set_point1(self,x,y,z):
        self.x1,self.y1,self.z1 = x,y,z
    def set_point2(self,x,y,z):
        self.x2,self.y2,self.z2 = x,y,z

    def z_clipping(self):
        if self.z1 < nearZ or self.z2 < nearZ:
            self.p = (nearZ - self.z1) / (self.z2-self.z1)
            if self.z1 < nearZ:
                self.set_point1(
                    self.x1 + ((self.x2-self.x1)*self.p),
                    self.y1 + ((self.y2-self.y1)*self.p),
                    nearZ
                )
            else:
                self.set_point2(
                    self.x1 + ((self.x2-self.x1)*self.p),
                    self.y1 + ((self.y2-self.y1)*self.p),
                    nearZ
                )

    @staticmethod
    def _check_line_visibility(drawing_points):
        rect = pygame.Rect(
            min(drawing_points[0][0], drawing_points[1][0]),
            min(drawing_points[0][1], drawing_points[1][1]),
            abs(drawing_points[1][0] - drawing_points[0][0])+1,
            abs(drawing_points[1][1] - drawing_points[0][1])+1,
        )
        return screen.get_rect().colliderect(rect)

    def draw_3d_line(self,x1,y1,z1,x2,y2,z2,size,overlay=None,edge_overlay=None):
        #screen_x = int(self.x1 / self.z1 * FL) + WIDTH // 2
        #screen_y = HEIGHT // 2 - int(self.y1 / self.z1 * FL)
        self.set_point1(
            x1-CameraPos.x,
            y1-CameraPos.y,
            z1-CameraPos.z
        )
        self.set_point2(
            x2-CameraPos.x,
            y2-CameraPos.y,
            z2-CameraPos.z
        )
        self.set_point1(
            ((self.z1*self.sinY)+(self.x1*self.cosY)),
            self.y1,
            ((self.z1*self.cosY)-(self.x1*self.sinY))
        )
        self.set_point2(
            ((self.z2*self.sinY)+(self.x2*self.cosY)),
            self.y2,
            ((self.z2*self.cosY)-(self.x2*self.sinY))
        )
        self.set_point1(
            self.x1,
            ((self.y1*self.cosX)-(self.z1*self.sinX)),
            ((self.y1*self.sinX)+(self.z1*self.cosX))
        )
        self.set_point2(
            self.x2,
            ((self.y2*self.cosX)-(self.z2*self.sinX)),
            ((self.y2*self.sinX)+(self.z2*self.cosX))
        )
        if (self.z1 > nearZ) or (self.z2 > nearZ):
            self.z_clipping()
            DRAW_SIZE = max(1, int(size / ((self.z1 + self.z2) / 2) * FL))

            drawing_points = [
                (round(self.x1/self.z1*FL)+WIDTH//2,HEIGHT-(round(self.y1/self.z1*FL)+HEIGHT//2)),
                (round(self.x2/self.z2*FL)+WIDTH//2,HEIGHT-(round(self.y2/self.z2*FL)+HEIGHT//2))
            ]
            if not SETTINGS["DISABLE_CULLING"]:
                if not self._check_line_visibility(drawing_points):
                    return
            pygame.draw.aaline(
                overlay if overlay else alpha_overlay,
                DRAW_COLOR,
                drawing_points[0],
                drawing_points[1],
                DRAW_SIZE*2
            )
            if drawing_points[0] not in self.used_circle_points:
                pygame.draw.aacircle(
                    edge_overlay if edge_overlay else alpha_overlay,
                    DRAW_COLOR,
                    drawing_points[0],
                    DRAW_SIZE
                )
                self.used_circle_points.append(drawing_points[0])
            if drawing_points[1] not in self.used_circle_points:
                pygame.draw.aacircle(
                    edge_overlay if edge_overlay else alpha_overlay,
                    DRAW_COLOR,
                    drawing_points[1],
                    DRAW_SIZE
                )
                self.used_circle_points.append(drawing_points[1])

    def draw_block(self,x,y,z,sizeX,sizeY,sizeZ):
        temp = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
        temp_edge = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
        self.draw_3d_line(x, y, z, x + sizeX, y, z, DRAW_SIZE, temp, temp_edge)
        self.draw_3d_line(x+sizeX, y, z, x+sizeX, y+sizeY, z, DRAW_SIZE, temp, temp_edge)
        self.draw_3d_line(x+sizeX, y+sizeY, z, x, y+sizeY, z, DRAW_SIZE, temp, temp_edge)
        self.draw_3d_line(x, y+sizeY, z, x, y, z, DRAW_SIZE, temp, temp_edge)
        self.draw_3d_line(x, y, z+sizeZ, x+sizeX, y, z+sizeZ, DRAW_SIZE, temp, temp_edge)
        self.draw_3d_line(x+sizeX, y, z+sizeZ, x+sizeX, y+sizeY, z+sizeZ, DRAW_SIZE, temp, temp_edge)
        self.draw_3d_line(x+sizeX, y+sizeY, z+sizeZ, x, y+sizeY, z+sizeZ, DRAW_SIZE, temp, temp_edge)
        self.draw_3d_line(x, y+sizeY, z+sizeZ, x, y, z+sizeZ, DRAW_SIZE, temp, temp_edge)
        self.draw_3d_line(x, y, z, x, y, z+sizeZ, DRAW_SIZE, temp, temp_edge)
        self.draw_3d_line(x+sizeX, y, z, x+sizeX, y, z+sizeZ, DRAW_SIZE, temp, temp_edge)
        self.draw_3d_line(x, y+sizeY, z, x, y+sizeY, z+sizeZ, DRAW_SIZE, temp, temp_edge)
        self.draw_3d_line(x+sizeX, y+sizeY, z, x+sizeX, y+sizeY, z+sizeZ, DRAW_SIZE, temp, temp_edge)
        alpha_overlay.blit(temp)
        alpha_overlay.blit(temp_edge)

    def draw_all_blocks(self):
        global DRAW_COLOR
        self.used_circle_points.clear()
        for i in range(1,len(self.LayerIDs)+1):
            self.getID = self.LayerIDs[i-1]
            block = blocks[self.getID-1]
            DRAW_COLOR = block.color
            self.draw_block(
                *block.pos,
                *block.size
            )

    def draw(self):
        self.init_trigonometry()
        self.block_order()
        self.draw_all_blocks()

class Game_Updater:
    def __init__(self):
        self.collision = 0
        self.mouseOx = 0
        self.mouseOy = 0
        self.mouseRotation = 0
        self.getY = 0
        self.mag = 0
        self.moveX = 0
        self.moveZ = 0
        self.cosX, self.cosY = 0,0
        self.sinX, self.sinY = 0,0
        self.p = 0
        self.x1, self.y1 = 0,0
        self.y2 = 0
        self.z1, self.z2 = 0,0
        self.i = 0
        self.getID = 0
        self.sort_High = 0
        self.sort_Low = 0
        self.sort_Mid = 0
        self.z = 0
        self.CollisionID = []
        self.LayerIDs = []
        self.LayerValues = []

        # variables that arent a part of the original game
        # and are used for different purposes
        self.fps_show = 0
        self.time_show = 0

    def init_level(self):
        global playerVelY
        self.collision = 0
        playerVelY = 0

    def show_fps(self):
        alpha_overlay.blit(font.render(str(round(current_fps)), True, (255,255,255)))
    def show_time(self):
        current_timer = int(time.time()-timer_start)
        minutes, seconds = divmod(current_timer, 60)
        hours, minutes = divmod(minutes, 60)

        rendered_timer = font.render(f"{hours:02d}:{minutes:02d}:{seconds:02d}", True, (255,255,255))
        
        alpha_overlay.blit(rendered_timer, (WIDTH//2 - rendered_timer.width//2, 0))

    def update_camera_position(self):
        global CameraPos
        CameraPos.xyz = (
            (playerPos.x+(playerSize/2)) + (8 * (math.sin(CameraRot.y)*math.cos(CameraRot.x))),
            (playerPos.y+(playerSize/2)) + (-8 * math.sin(CameraRot.x)),
            (playerPos.z+(playerSize/2)) + (-8 * (math.cos(CameraRot.y)*math.cos(CameraRot.x)))
        )

    def update_camera_rotation(self, pressed):
        global deltatime, CameraRot
        pressed = pygame.key.get_pressed()
        CameraRot.x += (pressed[pygame.K_UP] - pressed[pygame.K_DOWN]) * math.pi * deltatime
        CameraRot.y += (pressed[pygame.K_RIGHT] - pressed[pygame.K_LEFT]) * -math.pi * deltatime
        if any(pygame.mouse.get_pressed()):
            mouse_pos = list(pygame.mouse.get_pos())

            mouse_pos[0] /= -100
            mouse_pos[1] /= -100
            if self.mouseRotation == 0:
                self.mouseRotation = 1
                self.mouseOx, self.mouseOy = mouse_pos
            else:
                CameraRot.x += (mouse_pos[1]-self.mouseOy) * mouse_sensitivity
                CameraRot.y += (mouse_pos[0]-self.mouseOx) * mouse_sensitivity
                self.mouseOx, self.mouseOy = mouse_pos
        else:
            self.mouseRotation = 0
        CameraRot.x = max(math.radians(-90), min(CameraRot.x, math.radians(30)))

    def check_player_collision(self):
        global playerPos, playerVelY, CameraRot
        if self.collision == "end":
            return
        self.CollisionID.clear()
        CollisionType.clear()
        self.collision = 0
        for c in range(3,len(blocks)+1):
            block = blocks[c-1]
            if playerPos.x < (block.pos.x + block.size.x) and (playerPos.x + playerSize) > block.pos.x:
                if playerPos.y < (block.pos.y + block.size.y) and (playerPos.y + playerSize) > block.pos.y:
                    if playerPos.z < (block.pos.z + block.size.z) and (playerPos.z + playerSize) > block.pos.z:
                        self.collision = 1
                        self.CollisionID.append(c)
                        CollisionType.append(block.blocktype)
        if "end" in CollisionType:
            global level
            sounds["end"].play()
            self.collision = "end"
            level += 1
            self.init_level()
            game_levels.init_level()
        if ("lava" in CollisionType) or playerPos.y < -10:
            sounds["die"].play()
            playerPos.xyz = playerStart.xyz
            playerVelY = 0
            CameraRot.xy = (math.radians(-20), 0)
            self.collision = 0

    def player_y_movement(self, pressed, yDir: bool):
        global playerPos, playerVelY, deltatime, BlockY, playerSize
        playerPos.y += playerVelY * deltatime
        playerVelY = max(-8, playerVelY + -15 * deltatime)

        playerPos.y += (yDir * 2 - 1) / 1000
        self.check_player_collision()

        if self.collision == 1:
            playerVelY = 0
            if yDir:
                for c in range(len(self.CollisionID)):
                    self.getY = (blocks[self.CollisionID[c]-1].pos.y) - playerSize
                    if self.getY < playerPos.y:
                        playerPos.y = self.getY
            else:
                for c in range(len(self.CollisionID)):
                    self.getY = (blocks[self.CollisionID[c]-1].pos.y) + blocks[self.CollisionID[c]-1].size.y
                    if self.getY > playerPos.y:
                        playerPos.y = self.getY
                if pressed[pygame.K_SPACE]:
                    playerVelY = playerJumpHeight
                    sounds["jump"].play()
                if "bouncy" in CollisionType:
                    playerVelY = 8
                    sounds["bouncy"].play()
                if ("bouncy" in CollisionType) and (level in (6,7)):
                    playerVelY = 15
                    sounds["bouncy"].play()
                if ("bouncy" in CollisionType) and level == 8:
                    playerVelY = 13
                    sounds["bouncy"].play()
                if "small" in CollisionType:
                    playerSize = 2
        else:
            playerPos.y += (yDir*2-1)/1000

    def player_xz_movement(self, x, z):
        global playerPos
        playerPos.x += x
        self.check_player_collision()
        if self.collision == 1:
            playerPos.x -= x
        playerPos.z += z
        self.check_player_collision()
        if self.collision == 1:
            playerPos.z -= z

    def update_player(self, pressed):
        self.player_y_movement(pressed, playerVelY > 0)
        self.moveX = pressed[pygame.K_d] - pressed[pygame.K_a]
        self.moveZ = pressed[pygame.K_w] - pressed[pygame.K_s]
        self.mag = math.hypot(self.moveX, self.moveZ)
        if self.mag > 0:
            self.moveX = (self.moveX / self.mag) * deltatime * playerSpeed
            self.moveZ = (self.moveZ / self.mag) * deltatime * playerSpeed
            self.player_xz_movement(
                (self.moveX * math.cos(CameraRot.y)) - (self.moveZ * math.sin(CameraRot.y)),
                (self.moveX * math.sin(CameraRot.y)) + (self.moveZ * math.cos(CameraRot.y))
            )

    def player_shadow(self):
        global shadowY
        shadowY = -999
        for c in range(2, len(blocks)):
            block = blocks[c]
            if playerPos.x < (block.pos.x + block.size.x) and (playerPos.x + playerSize) > block.pos.x:
                if playerPos.z < (block.pos.z + block.size.z) and (playerPos.z + playerSize) > block.pos.z:
                    self.getY = block.pos.y + block.size.y
                    if shadowY < self.getY <= playerPos.y:
                        shadowY = self.getY

    def update(self):
        pressed = pygame.key.get_pressed()
        self.update_camera_rotation(pressed)
        self.update_player(pressed)
        self.player_shadow()
        self.update_camera_position()

        blocks[0].pos.xyz = playerPos.xyz
        blocks[1].pos.xyz = (playerPos.x, shadowY, playerPos.z)
        if self.fps_show:
            self.show_fps()
        if self.time_show:
            self.show_time()

class Game_Levels:
    def __init__(self):
        global playerSize
        playerSize = 0.8
        BlockTypes.clear()
        self.init_block_types()
        self.init_level()

    def add_block_type(self, name: str, color: tuple):
        BlockTypes[name] = color

    def init_block_types(self):
        self.add_block_type("player", (100,255,255,DRAW_TRANSPARENCY))
        self.add_block_type("shadow", (100,100,255,DRAW_TRANSPARENCY))
        self.add_block_type("ground", (255,255,255,DRAW_TRANSPARENCY))
        self.add_block_type("end", (0,255,0,DRAW_TRANSPARENCY))
        self.add_block_type("lava", (255,0,0,DRAW_TRANSPARENCY))
        self.add_block_type("bouncy", (255,255,0,DRAW_TRANSPARENCY))
        self.add_block_type("ice", (161,231,247,DRAW_TRANSPARENCY))
        self.add_block_type("black", (0,0,0,DRAW_TRANSPARENCY))

    def init_level(self):
        global CameraRot, playerPos
        blocks.clear()
        # CameraRotX = -20
        # CameraRotY = 0
        match level:
            case 1:
                self.level1()
            case 2:
                self.level2()
            case 3:
                self.level3()
            case 4:
                self.level4()
            case 5:
                self.level5()
            case 6:
                self.level6()
            case 7:
                self.level7()
            case 8:
                self.level8()
            case 9:
                self.level9()
            case 10:
                self.level10()
        playerPos.xyz = playerStart.xyz

    def add_block(self, x, y, z, sizeX, sizeY, sizeZ, block_type):
        blocks.append(Block(
            color=BlockTypes[block_type],
            size=pygame.Vector3(sizeX,sizeY,sizeZ),
            pos=pygame.Vector3(x,y,z),
            blocktype=block_type
        ))

    def add_player(self, x, y, z):
        global playerStart
        playerPos.xyz = (x,y,z)
        playerStart.xyz = (x,y,z)
        self.add_block(
            *playerPos.xyz,
            playerSize,playerSize,playerSize,
            "player"
        )
        self.add_block(0,0,0,playerSize,0,playerSize,"shadow")

    def level1(self):
        self.add_player(0,0,0)
        self.add_block(-2,0,-2,5,1,5,"ground")
        self.add_block(0,0,4,1,1,1,"bouncy")
        self.add_block(0,0,6,1,1,1,"lava")
        self.add_block(0,0,8,1,1,1,"bouncy")
        self.add_block(-1,0,10,3,1,3,"ground")
        self.add_block(0,1,11,1,1,1,"end")
    def level2(self):
        self.add_player(-9,-3,3)
        self.add_block(-0.5,0,-0.5,2,1,8,"ground")
        self.add_block(-0.5,0,9,2,1,2,"bouncy")
        self.add_block(-7.5,1.5,9,6,1,2,"ground")
        self.add_block(-7,2.5,9.5,1,0.5,1,"end")
        self.add_block(0.5,1,1.5,1,0.5,2,"lava")
        self.add_block(-0.5,1,5,1,0.5,2.5,"lava")
        self.add_block(-1.9,2.5,9,0.1,2,0.1,"lava")
        self.add_block(-3,2.5,11,0.1,2,0.1,"lava")
        self.add_block(-3.5,2.5,10,0.1,2,0.1,"lava")
        self.add_block(-5,2.5,9,0.1,2,0.1,"lava")
        self.add_block(-5,2.5,10.8,0.1,2,0.1,"lava")
        self.add_block(-3.5,-1,-0.5,2,1,2,"bouncy")
        self.add_block(-6.5,-2,-0.5,2,1,2,"bouncy")
        self.add_block(-6.5,-3,2.5,2,1,2,"bouncy")
        self.add_block(-9.5,-4,2.5,2,1,2,"ground")
    def level3(self):
        self.add_player(0,0,0)
        self.add_block(0,0,0,5,1,5,"ground")
        self.add_block(2,1,2,1,11,1,"ground")
        self.add_block(0,1,2,1,1,1,"bouncy")
        self.add_block(0,2,4,1,1,1,"bouncy")
        self.add_block(2,3,4,1,1,1,"bouncy")
        self.add_block(4,4,4,1,1,1,"bouncy")
        self.add_block(4,5,2,1,1,1,"bouncy")
        self.add_block(4,6,0,1,1,1,"bouncy")
        self.add_block(2,7,0,1,1,1,"bouncy")
        self.add_block(0,8,0,1,1,1,"bouncy")
        self.add_block(0,9,2,1,1,1,"bouncy")
        self.add_block(2,12,2,1,1,1,"end")
    def level4(self):
        self.add_player(0.5,0,-1.5)
        self.add_block(-1,0,-2,4,1,4,"ground")
        self.add_block(2,1,2,1,1,1,"bouncy")
        self.add_block(-1,3,2,1,1,1,"bouncy")
        self.add_block(2,5,2,1,1,1,"bouncy")
        self.add_block(-1,7,2,1,1,1,"bouncy")
        self.add_block(2,9,2,1,1,1,"bouncy")
        self.add_block(-1,11,2,1,1,1,"bouncy")
        self.add_block(2,13,2,1,1,1,"bouncy")
        self.add_block(2,13,4,1,1,6,"ground")
        self.add_block(2,14,5,1,0.5,1,"lava")
        self.add_block(2,14,6,1,1,1,"bouncy")
        self.add_block(2,14,7,1,2,1,"lava")
        self.add_block(2,14,8,1,3,1,"bouncy")
        self.add_block(2,14,9,1,4,1,"lava")
        self.add_block(1.5,14,12,2,1,4,"ground")
        self.add_block(1.5,14,17,2,1,2,"bouncy")
        self.add_block(-0.5,16,17,2,1,2,"bouncy")
        self.add_block(-0.5,17,14,2,1,2,"ground")
        self.add_block(0,18,14.5,1,1,1,"end")
    def level5(self):
        self.add_player(0,0,0)
        self.add_block(-1,0,-1,3,1,3,"ground")
        self.add_block(-5,0,0,4,1,1,"ground")
        self.add_block(-3,1,0,1,0.25,1,"lava")
        self.add_block(-5,1,0,1,0.25,1,"bouncy")
        self.add_block(-5,0,0,1,1,5,"ground")
        self.add_block(-5,1,2,1,0.25,1,"lava")
        self.add_block(-4,1,4,1,1,1,"bouncy")
        self.add_block(-2,3,4,1,1,1,"bouncy")
        self.add_block(0,5,4,1,1,1,"bouncy")
        self.add_block(2,7,4,1,1,1,"bouncy")
        self.add_block(2,9,2,1,1,1,"bouncy")
        self.add_block(2,11,0,1,1,1,"bouncy")
        self.add_block(0,13,0,1,1,1,"bouncy")
        self.add_block(-2,15,0,1,1,1,"bouncy")
        self.add_block(-2,17,2,1,1,1,"bouncy")
        self.add_block(-2,19,4,1,1,1,"bouncy")
        self.add_block(-2,21,6,1,1,1,"bouncy")
        self.add_block(-3.5,21,8,0.75,1,4,"ground")
        self.add_block(-0.25,21,8,0.75,1,4,"ground")
        self.add_block(-3.5,21,8,4,1,0.75,"ground")
        self.add_block(-3.5,21,11.25,4,1,0.75,"ground")
        self.add_block(-3.5,6,8,0.25,15,4,"lava")
        self.add_block(0.25,6,8,0.25,15,4,"lava")
        self.add_block(-3.5,6,8,4,15,0.25,"lava")
        self.add_block(-3.5,6,11.75,4,15,0.25,"lava")
        self.add_block(-2,6,9.5,1,0.5,1,"end")
    def level6(self):
       self.add_player(0,0,0)
       self.add_block(-1,0.5,4,0.25,4,7,"lava")
       self.add_block(1.8,0.5,4,0.25,4,7,"lava")
       self.add_block(-1,0,-1,3,1,3,"ground")
       self.add_block(0,0,4,1,1,1,"ground")
       self.add_block(0,0,7,1,1,1,"ground")
       self.add_block(0,0,10,1,1,1,"ground")
       self.add_block(-0.5,-3,15,2,1,2,"bouncy")
       self.add_block(-0.5,-3,25,2,1,2,"bouncy")
       self.add_block(-2,-3,35,5,1,5,"ground")
       self.add_block(-0.5,-3,40,2,1,2,"bouncy")
       self.add_block(3,4,36.5,2,1,2,"bouncy")
       self.add_block(-0.5,11,33,2,1,2,"bouncy")
       self.add_block(-4,18,36.5,2,1,2,"bouncy")
       self.add_block(-0.5,25,40,2,1,2,"bouncy")
       self.add_block(-1,32,42,3,1,3,"ground")
       self.add_block(-1,32,47,3,1,3,"ground")
       self.add_block(-1,32,52,3,1,3,"ground")
       self.add_block(0,33,53,1,0.5,1,"end")
    def level7(self):
        self.add_player(1,0,1)
        self.add_block(0,0,0,3,1,11,"ground")
        self.add_block(0,1,3.5,2,2.5,1,"lava")
        self.add_block(1,1,6.5,2,2.5,1,"lava")
        self.add_block(1,1,9,1,0.5,1,"bouncy")
        self.add_block(3,7,8,3,1,3,"ground")
        self.add_block(6,7,11,5,6,1,"lava")
        self.add_block(6,7,7,5,6,1,"lava")
        self.add_block(8,1,9,1,0.5,1,"bouncy")
        self.add_block(11,7,8,3,1,3,"ground")
        self.add_block(12,8,9,1,0.5,1,"bouncy")
        self.add_block(11,14,6,3,1,2,"ground")
        self.add_block(11,14,0,3,1,6,"lava")
        self.add_block(11.5,15,5,0.25,1.2,0.25,"ground")
        self.add_block(13.25,15,4,0.25,2.4,0.25,"ground")
        self.add_block(11.5,15,3,0.25,3.6,0.25,"ground")
        self.add_block(13.5,15,2,0.25,4.8,0.25,"ground")
        self.add_block(11.5,15,1,0.25,6,0.25,"ground")
        self.add_block(11.5,21,1,0.25,0.01,0.25,"bouncy")
        self.add_block(11,21.5,-3,3,1,3,"ground")
        self.add_block(3,21.5,-3,8,1,3,"bouncy")
        self.add_block(0,21.5,-3,3,1,3,"ground")
        self.add_block(1,22.5,-2,1,1,1,"end")
        self.add_block(9,21.5,-2,0.25,10,0.25,"lava")
        self.add_block(7,21.5,-1,0.25,10,0.25,"lava")
        self.add_block(5,21.5,-2.5,0.25,10,0.25,"lava")
        self.add_block(3,21.5,-1,0.25,10,0.25,"lava")
    def level8(self):
        self.add_player(2,1,2)
        self.add_block(0,-9,19,5,14,1,"ground")
        self.add_block(0,-9,0,5,1,20,"ground")
        self.add_block(0,4,0,5,1,20,"ground")
        self.add_block(4,-9,0,1,14,20,"ground")
        self.add_block(0,-9,0,1,14,20,"ground")
        self.add_block(0,-9,0,5,14,1,"ground")
        self.add_block(1,0,1,3,1,3,"ground")
        self.add_block(1,-5,3,3,6,1,"ground")
        self.add_block(1,-1,7,3,6,1,"ground")
        self.add_block(1,-5,3,3,1,5,"ground")
        self.add_block(1,-1,7,3,1,5,"ground")
        self.add_block(1,-5,8,3,0.5,3,"lava")
        self.add_block(1,-5,11,3,1,5,"ground")
        self.add_block(1,-5,15,3,6,1,"lava")
        self.add_block(2,-4,13.5,1,0.5,1,"bouncy")
        self.add_block(1,-1,11,3,6,1,"ground")
        self.add_block(1,-8,10.5,1.5,3,5.5,"lava")
        self.add_block(2.5,-8,3,1.5,3,5.5,"lava")
        self.add_block(2.5,-8,1.5,1,0.5,1,"bouncy")
        self.add_block(2,-1,1.5,1,1,1,"end")
    def level9(self):
        self.add_player(0,0,0)
        self.add_block(-1,0,-1,3,1,3,"ground")
        self.add_block(-4,0,2,9,13,9,"ground")
        self.add_block(-1,13,5,3,10,3,"ground")
        self.add_block(-2,1,0,1,1,1,"bouncy")
        self.add_block(-4,2,0,1,1,1,"bouncy")
        self.add_block(-6,3,0,1,1,1,"bouncy")
        self.add_block(-7,4,2,3,1,3,"ground")
        self.add_block(-7,4,8,3,1,2,"ground")
        self.add_block(-6,5,10,1,1,1,"bouncy")
        self.add_block(-6,6,12,1,1,1,"ground")
        self.add_block(-4,7,12,1,1,1,"bouncy")
        self.add_block(-2,8,12,1,1,1,"bouncy")
        self.add_block(0,9,12,1,1,1,"bouncy")
        self.add_block(2,10,12,1,1,1,"bouncy")
        self.add_block(4,11,12,1,1,1,"bouncy")
        self.add_block(2,13,8,3,3,1,"ground")
        self.add_block(6,14,9,0.5,0,0.5,"black") # superliminal ahh easter egg
        self.add_block(0.5,13,9.25,0,3,1.75,"lava")
        self.add_block(-3.5,13,5,2.5,3,4.25,"ground")
        self.add_block(-2.5,13,2,4.5,0.25,3,"lava")
        self.add_block(-0.5,13.25,3,1,0.25,1,"bouncy")
        self.add_block(3,13,6,1,1,1,"bouncy")
        self.add_block(-2.75,16,5.75,1,1,1,"bouncy")
        self.add_block(-2.75,17,3.25,1,1,1,"bouncy")
        self.add_block(0,18,3.25,1,1,1,"bouncy")
        self.add_block(2.75,19,3.25,1,1,1,"bouncy")
        self.add_block(2.75,20,6.25,1,1,1,"bouncy")
        self.add_block(0,23,6,1,1,1,"end")
    def level10(self):
        self.add_player(6,1,-7)
        self.add_block(0,0,0,13,1,5,"ground")
        self.add_block(1,3,3,5,1,1,"lava")
        self.add_block(2,2,3,1,3,1,"lava")
        self.add_block(3,1,3,1,3,1,"lava")
        self.add_block(4,2,3,1,3,1,"lava")
        self.add_block(7,3,3,5,1,1,"bouncy")
        self.add_block(8,1,3,1,3,1,"bouncy")
        self.add_block(9,2,3,1,3,1,"bouncy")
        self.add_block(10,1,3,1,3,1,"bouncy")
        self.add_block(5,0,-4,3,1,3,"ground")
        self.add_block(5,0,-8,3,1,3,"ground")

class Button(pygame.sprite.Sprite):
    def __init__(self, *groups, x: float, y: float, w: float, h: float, action: function, color, text: str):
        super().__init__(*groups)
        self.rect = pygame.Rect(x, y, w, h)
        self.bigger_rect = pygame.Rect(x-2, y-2, w+4, h+4)
        self.color = color
        self.action = action
        self.text = text

    def update(self):
        cursor_touching = self.rect.collidepoint(pygame.mouse.get_pos())
        if not cursor_touching:
            pygame.draw.rect(screen, self.color, self.rect, width=3)
        else:
            pygame.draw.rect(screen, self.color, self.bigger_rect, width=3)

        text_render = font.render(self.text, True, self.color)
        screen.blit(text_render, (
            self.rect.centerx - text_render.width // 2,
            self.rect.centery - text_render.height // 2
        ))

        if cursor_touching and any(pygame.mouse.get_pressed(3)):
            self.action()

game_drawer = Game_Drawer()
game_updater = Game_Updater()
game_levels = Game_Levels()
timer_start = time.time()

buttons = pygame.sprite.Group()

ROWS, COLS = 2,5
CELL = 50
GAP = 6

grid_width = COLS * CELL + (COLS - 1) * GAP
grid_height = ROWS * CELL + (ROWS - 1) * GAP
grid_x = (WIDTH - grid_width) // 2
grid_y = (HEIGHT - grid_height) // 2

for row in range(ROWS):
    for col in range(COLS):
        x = grid_x + col * (CELL + GAP)
        y = grid_y + row * (CELL + GAP)

        idx = row * COLS + col

        if idx <= 10-1:
            color = "blue"
            def action(idx=idx):
                global level, scene
                scene = "playing"
                level = idx + 1
                #print(level)
                game_levels.init_level()
                game_updater.init_level()
        else:
            color = "grey"
            def action():
                return

        Button(buttons, x=x, y=y, w=CELL, h=CELL, color=color, text=str(idx+1), action=action)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if scene == "playing":
                if event.key == pygame.K_r:
                    game_updater.init_level()
                    game_levels.init_level()
            if event.key == pygame.K_f:
                game_updater.fps_show ^= 1
            if event.key == pygame.K_t:
                game_updater.time_show ^= 1
            if event.key == pygame.K_ESCAPE:
                if not SETTINGS["DISABLE_LEVEL_SELECTION"]:
                    scene = "level_selection"
        if event.type == SONG_END:
            play_song()

    deltatime = clock.tick(SETTINGS["FPS_MAX"])/1000
    current_fps = clock.get_fps()

    if pygame.mixer.music.get_volume() != SETTINGS["MUSIC_VOLUME"]:
        pygame.mixer.music.set_volume(SETTINGS["MUSIC_VOLUME"])

    screen.fill((0,0,0))
    if scene == "playing":
        alpha_overlay.fill((0,0,0,0))
        game_updater.update()
        game_drawer.draw()
        screen.blit(alpha_overlay)
    elif scene == "level_selection":
        buttons.update()
    pygame.display.flip()