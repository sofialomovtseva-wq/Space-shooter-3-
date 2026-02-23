import arcade
import random
import wave
import array
import math
import os

SCREEN_WIDTH = 600
SCREEN_HEIGHT = 800
SCREEN_TITLE = "Космический штурм: Битва за Галактику"
PLAYER_SPEED = 5
BULLET_SPEED = 10
BASE_ENEMY_SPEED = 2
COMBO_TIME = 120

MENU = 0
PLAYING = 1
STORY = 2
GAME_OVER = 3

def generate_tone(filename, freq=440, duration=0.1, volume=0.5, sample_rate=44100):
    n_samples = int(sample_rate * duration)
    amplitude = int(32767 * volume)
    buf = array.array('h')
    for i in range(n_samples):
        sample = amplitude * math.sin(2 * math.pi * freq * i / sample_rate)
        buf.append(int(sample))
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(buf.tobytes())

class Player(arcade.SpriteSolidColor):
    def __init__(self):
        super().__init__(40, 40, arcade.color.BLUE)
        self.center_x = SCREEN_WIDTH // 2
        self.center_y = 50
        self.health = 100
        self.lives = 3
        self.invulnerable_timer = 0
        self.weapon_level = 1
        self.weapon_timer = 0
        self.shield_timer = 0

class Bullet(arcade.SpriteSolidColor):
    def __init__(self, x, y, dx=0):
        super().__init__(5, 15, arcade.color.YELLOW)
        self.center_x = x
        self.center_y = y
        self.change_x = dx

    def update(self, delta_time: float = 1 / 60):
        self.center_x += self.change_x
        self.center_y += BULLET_SPEED
        if self.top > SCREEN_HEIGHT or self.right < 0 or self.left > SCREEN_WIDTH:
            self.kill()

class Enemy(arcade.SpriteSolidColor):
    ENEMY_TYPES = [
        {"name": "Scout", "size": 20, "health": 1, "score": 10, "color": arcade.color.RED, "speed": 2},
        {"name": "Fighter", "size": 30, "health": 1, "score": 15, "color": arcade.color.PURPLE, "speed": 2},
        {"name": "Bomber", "size": 50, "health": 2, "score": 25, "color": arcade.color.ORANGE, "speed": 1.5},
        {"name": "Elite", "size": 35, "health": 2, "score": 30, "color": arcade.color.TEAL, "speed": 1.8},
        {"name": "MiniBoss", "size": 80, "health": 8, "score": 150, "color": arcade.color.PINK, "speed": 1.2}
    ]

    def __init__(self, window, enemy_type=None):
        self.window = window
        if enemy_type is None:
            enemy_type = random.choice(self.ENEMY_TYPES[:-1])
        super().__init__(enemy_type["size"], enemy_type["size"], enemy_type["color"])
        self.center_x = random.randint(20, SCREEN_WIDTH - 20)
        self.center_y = SCREEN_HEIGHT + 20
        self.health = enemy_type["health"]
        self.score = enemy_type["score"]
        self.type_name = enemy_type["name"]
        self.speed = enemy_type.get("speed", BASE_ENEMY_SPEED)
        self.color = enemy_type["color"]

    def update(self, delta_time: float = 1 / 60):
        dx = self.window.player.center_x - self.center_x
        dy = self.window.player.center_y - self.center_y
        distance = (dx ** 2 + dy ** 2) ** 0.5
        if distance != 0:
            self.center_x += dx / distance * self.speed
            self.center_y += dy / distance * self.speed
        if self.bottom < 0:
            self.kill()

    def draw(self):
        arcade.draw_rectangle_filled(self.center_x, self.center_y, self.width, self.height, self.color)
        arcade.draw_rectangle_outline(self.center_x, self.center_y, self.width, self.height, arcade.color.WHITE, 2)

class DropItem(arcade.SpriteSolidColor):
    TYPES = ["Health", "Weapon", "Shield", "Life", "Points", "Bomb"]
    COLORS = {"Health": arcade.color.GREEN, "Weapon": arcade.color.YELLOW, "Shield": arcade.color.LIGHT_BLUE,
              "Life": arcade.color.PINK, "Points": arcade.color.ORANGE, "Bomb": arcade.color.RED}

    def __init__(self, x, y, item_type=None):
        if item_type is None:
            item_type = random.choice(self.TYPES)
        super().__init__(20, 20, self.COLORS[item_type])
        self.center_x = x
        self.center_y = y
        self.type = item_type
        self.speed = random.uniform(1, 3)

    def update(self, delta_time: float = 1 / 60):
        self.center_y -= self.speed
        if self.bottom < 0:
            self.kill()

    def draw(self):
        arcade.draw_circle_filled(self.center_x, self.center_y, self.width//2, self.COLORS[self.type])
        arcade.draw_circle_outline(self.center_x, self.center_y, self.width//2, arcade.color.BLACK, 2)

class GameWindow(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.BLACK)
        self.state = MENU
        self.selected_option = 0
        self.menu_options = ["Start Game", "Story", "Exit"]
        self.player_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList(use_spatial_hash=True)
        self.drop_list = arcade.SpriteList()
        self.player = Player()
        self.player_list.append(self.player)
        self.keys = {"up": False, "down": False, "left": False, "right": False, "shoot": False, "bomb": False}
        self.spawn_timer = 0
        self.score = 0
        self.wave = 1
        self.wave_timer = 0
        self.combo = 0
        self.combo_timer = 0
        self.stars = [(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT)) for _ in range(50)]
        self.shoot_cooldown = 0
        self.bomb_count = 1
        if not os.path.exists("sounds"):
            os.mkdir("sounds")
        generate_tone("sounds/shoot.wav", freq=800, duration=0.05)
        generate_tone("sounds/explosion.wav", freq=200, duration=0.2)
        generate_tone("sounds/pickup.wav", freq=1200, duration=0.1)
        generate_tone("sounds/hurt.wav", freq=300, duration=0.15)
        generate_tone("sounds/wave_start.wav", freq=600, duration=0.3)
        self.shoot_sound = arcade.load_sound("sounds/shoot.wav")
        self.explosion_sound = arcade.load_sound("sounds/explosion.wav")
        self.pickup_sound = arcade.load_sound("sounds/pickup.wav")
        self.hurt_sound = arcade.load_sound("sounds/hurt.wav")
        self.wave_start_sound = arcade.load_sound("sounds/wave_start.wav")

    def on_draw(self):
        self.clear()
        if self.state == MENU:
            self.draw_menu()
        elif self.state == STORY:
            self.draw_story()
        elif self.state in (PLAYING, GAME_OVER):
            self.draw_game()

    def draw_menu(self):
        arcade.draw_text("Main Menu", SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100,
                         arcade.color.YELLOW, 48, anchor_x="center")
        for i, option in enumerate(self.menu_options):
            color = arcade.color.WHITE
            if i == self.selected_option:
                color = arcade.color.GREEN
            arcade.draw_text(option, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 200 - i * 60,
                             color, 36, anchor_x="center")

    def draw_story(self):
        arcade.draw_text("Здесь будет история игры", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2,
                         arcade.color.WHITE, 24, anchor_x="center")
        arcade.draw_text("Нажмите ESC для возврата в меню", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50,
                         arcade.color.GRAY, 16, anchor_x="center")

    def draw_game(self):
        for star in self.stars:
            arcade.draw_circle_filled(star[0], star[1], 2, arcade.color.WHITE)
        if self.player.invulnerable_timer > 0 or self.player.shield_timer > 0:
            if self.player.invulnerable_timer % 10 < 5:
                self.player.alpha = 128
            else:
                self.player.alpha = 255
        else:
            self.player.alpha = 255
        self.player_list.draw()
        self.bullet_list.draw()
        self.enemy_list.draw()
        self.drop_list.draw()
        arcade.draw_text(f"HP: {self.player.health}", 10, SCREEN_HEIGHT - 30, arcade.color.WHITE, 16)
        arcade.draw_text(f"Lives: {self.player.lives}", 10, SCREEN_HEIGHT - 60, arcade.color.WHITE, 16)
        arcade.draw_text(f"Score: {self.score}", SCREEN_WIDTH - 150, SCREEN_HEIGHT - 30, arcade.color.WHITE, 16)
        arcade.draw_text(f"Wave: {self.wave}", SCREEN_WIDTH - 150, SCREEN_HEIGHT - 60, arcade.color.WHITE, 16)
        arcade.draw_text(f"Bombs: {self.bomb_count}", 10, 10, arcade.color.RED, 16)
        if self.combo > 1:
            arcade.draw_text(f"Combo x{self.combo}", SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT - 50, arcade.color.YELLOW, 16)
        if self.state == GAME_OVER:
            arcade.draw_text("GAME OVER", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, arcade.color.RED, 48,
                             anchor_x="center")
            arcade.draw_text("ESC для возврата в меню", SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50,
                             arcade.color.WHITE, 24, anchor_x="center")

    def on_update(self, delta_time):
        if self.state != PLAYING:
            return
        if self.player.invulnerable_timer > 0:
            self.player.invulnerable_timer -= 1
        if self.player.shield_timer > 0:
            self.player.shield_timer -= 1
        if self.player.weapon_timer > 0:
            self.player.weapon_timer -= 1
        else:
            self.player.weapon_level = max(1, self.player.weapon_level)
        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo = 0
        if self.keys["up"] and self.player.top < SCREEN_HEIGHT:
            self.player.center_y += PLAYER_SPEED
        if self.keys["down"] and self.player.bottom > 0:
            self.player.center_y -= PLAYER_SPEED
        if self.keys["left"] and self.player.left > 0:
            self.player.center_x -= PLAYER_SPEED
        if self.keys["right"] and self.player.right < SCREEN_WIDTH:
            self.player.center_x += PLAYER_SPEED
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.keys["shoot"] and self.shoot_cooldown == 0:
            self.shoot_cooldown = 10
            self.shoot_bullets()
            arcade.play_sound(self.shoot_sound)
        if self.keys["bomb"] and self.bomb_count > 0:
            for enemy in self.enemy_list:
                self.score += enemy.score
                enemy.kill()
            self.bomb_count -= 1
            self.keys["bomb"] = False
            arcade.play_sound(self.explosion_sound)
        self.bullet_list.update()
        self.enemy_list.update()
        self.drop_list.update()
        self.spawn_timer += 1
        if self.spawn_timer > 60:
            self.spawn_timer = 0
            if self.wave % 5 == 0 and len(self.enemy_list) == 0:
                self.enemy_list.append(Enemy(self, Enemy.ENEMY_TYPES[-1]))
                arcade.play_sound(self.wave_start_sound)
            else:
                self.enemy_list.append(Enemy(self))
        for bullet in self.bullet_list:
            hit_list = arcade.check_for_collision_with_list(bullet, self.enemy_list)
            for enemy in hit_list:
                enemy.health -= 1
                bullet.kill()
                if enemy.health <= 0:
                    self.score += enemy.score
                    self.combo += 1
                    self.combo_timer = COMBO_TIME
                    enemy.kill()
                    arcade.play_sound(self.explosion_sound)
                    chance = {"Scout": 0.1, "Fighter": 0.2, "Bomber": 0.3, "Elite": 0.4, "MiniBoss": 1.0}
                    if random.random() < chance[enemy.type_name]:
                        self.drop_list.append(DropItem(enemy.center_x, enemy.center_y))
        if self.player.invulnerable_timer <= 0 and self.player.shield_timer <= 0:
            hit_list = arcade.check_for_collision_with_list(self.player, self.enemy_list)
            for enemy in hit_list:
                self.player.health -= 20
                self.player.invulnerable_timer = 60
                arcade.play_sound(self.hurt_sound)
                if self.player.health <= 0:
                    self.player.lives -= 1
                    self.player.health = 100
                    if self.player.lives <= 0:
                        self.state = GAME_OVER
        for drop in self.drop_list:
            if arcade.check_for_collision(self.player, drop):
                if drop.type == "Health":
                    self.player.health = min(100, self.player.health + 20)
                elif drop.type == "Weapon":
                    self.player.weapon_level = min(4, self.player.weapon_level + 1)
                    self.player.weapon_timer = 600
                elif drop.type == "Shield":
                    self.player.shield_timer = 180
                elif drop.type == "Life":
                    self.player.lives += 1
                elif drop.type == "Points":
                    self.score += 75 * self.wave
                elif drop.type == "Bomb":
                    self.bomb_count += 1
                arcade.play_sound(self.pickup_sound)
                drop.kill()
        self.wave_timer += 1
        if self.wave_timer > 1800:
            self.wave_timer = 0
            self.wave += 1
            arcade.play_sound(self.wave_start_sound)
        self.stars = [(x, (y - 2) % SCREEN_HEIGHT) for (x, y) in self.stars]

    def shoot_bullets(self):
        self.bullet_list.append(Bullet(self.player.center_x, self.player.top + 5))
        if self.player.weapon_level >= 2:
            self.bullet_list.append(Bullet(self.player.center_x - 10, self.player.top + 5))
            self.bullet_list.append(Bullet(self.player.center_x + 10, self.player.top + 5))
        if self.player.weapon_level >= 3:
            self.bullet_list.append(Bullet(self.player.center_x - 20, self.player.top + 5, dx=-1))
            self.bullet_list.append(Bullet(self.player.center_x + 20, self.player.top + 5, dx=1))
        if self.player.weapon_level >= 4:
            self.bullet_list.append(Bullet(self.player.center_x - 25, self.player.top + 5, dx=-1.5))
            self.bullet_list.append(Bullet(self.player.center_x + 25, self.player.top + 5, dx=1.5))

    def on_key_press(self, key, modifiers):
        if self.state == MENU:
            if key == arcade.key.UP:
                self.selected_option = (self.selected_option - 1) % len(self.menu_options)
            elif key == arcade.key.DOWN:
                self.selected_option = (self.selected_option + 1) % len(self.menu_options)
            elif key == arcade.key.ENTER or key == arcade.key.RETURN:
                self.activate_option()
        elif self.state in (PLAYING, GAME_OVER):
            if key == arcade.key.W or key == arcade.key.UP:
                self.keys["up"] = True
            if key == arcade.key.S or key == arcade.key.DOWN:
                self.keys["down"] = True
            if key == arcade.key.A or key == arcade.key.LEFT:
                self.keys["left"] = True
            if key == arcade.key.D or key == arcade.key.RIGHT:
                self.keys["right"] = True
            if key == arcade.key.SPACE:
                self.keys["shoot"] = True
            if key == arcade.key.B:
                self.keys["bomb"] = True
            if key == arcade.key.ESCAPE:
                self.state = MENU
        elif self.state == STORY:
            if key == arcade.key.ESCAPE:
                self.state = MENU

    def on_key_release(self, key, modifiers):
        if self.state in (PLAYING, GAME_OVER):
            if key == arcade.key.W or key == arcade.key.UP:
                self.keys["up"] = False
            if key == arcade.key.S or key == arcade.key.DOWN:
                self.keys["down"] = False
            if key == arcade.key.A or key == arcade.key.LEFT:
                self.keys["left"] = False
            if key == arcade.key.D or key == arcade.key.RIGHT:
                self.keys["right"] = False
            if key == arcade.key.SPACE:
                self.keys["shoot"] = False
            if key == arcade.key.B:
                self.keys["bomb"] = False

    def on_mouse_motion(self, x, y, dx, dy):
        if self.state == MENU:
            for i, option in enumerate(self.menu_options):
                text_x = SCREEN_WIDTH // 2
                text_y = SCREEN_HEIGHT - 200 - i * 60
                width = 200
                height = 40
                if text_x - width // 2 < x < text_x + width // 2 and text_y - height // 2 < y < text_y + height // 2:
                    self.selected_option = i

    def on_mouse_press(self, x, y, button, modifiers):
        if self.state == MENU:
            self.activate_option()

    def activate_option(self):
        option = self.menu_options[self.selected_option]
        if option == "Start Game":
            self.reset_game()
            self.state = PLAYING
        elif option == "Story":
            self.state = STORY
        elif option == "Exit":
            arcade.close_window()

    def reset_game(self):
        self.player_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList(use_spatial_hash=True)
        self.drop_list = arcade.SpriteList()
        self.player = Player()
        self.player_list.append(self.player)
        self.keys = {"up": False, "down": False, "left": False, "right": False, "shoot": False, "bomb": False}
        self.spawn_timer = 0
        self.score = 0
        self.wave = 1
        self.wave_timer = 0
        self.combo = 0
        self.combo_timer = 0
        self.stars = [(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT)) for _ in range(50)]
        self.shoot_cooldown = 0
        self.bomb_count = 1

if __name__ == "__main__":
    window = GameWindow()
    arcade.run()