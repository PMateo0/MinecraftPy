from settings import *
import moderngl as mgl
import pygame as pg
import sys
from shader_program import ShaderProgram
from scene import Scene
from player import Player
from textures import Textures
import socket
import threading
import pickle
import time

# Importar la clase NetworkManager (asumiendo que se encuentra en network_manager.py)
from network_manager import NetworkManager

HOST = '0.0.0.0'
PORT = 12345
FPS = 30

WIDTH, HEIGHT = 600, 400
PLAYER_SIZE = 20

COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

# --- Definición de DummySocket para el servidor ---
class DummySocket:
    def recv(self, bufsize):
        return b''
    def sendall(self, data):
        pass
    def close(self):
        pass

# ==================== CLASE SERVIDOR ====================
class Server:
    def __init__(self):
        self.players = {}
        self.connections = []
        self.lock = threading.Lock()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((HOST, PORT))
        self.server.listen()
        print(f"[SERVIDOR] Escuchando en {HOST}:{PORT}")

    def broadcast_positions(self):
        with self.lock:
            data = pickle.dumps(self.players)
            for conn in self.connections:
                try:
                    conn.sendall(data)
                except Exception as e:
                    print(f"[ERROR] Al enviar posiciones: {e}")

    def handle_client(self, conn, addr):
        with self.lock:
            self.players[addr] = [WIDTH // 2, HEIGHT // 2]
            self.connections.append(conn)
        
        self.broadcast_positions()

        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break

                direction = pickle.loads(data)
                with self.lock:
                    if direction == 'UP':
                        self.players[addr][1] = max(0, self.players[addr][1] - 5)
                    elif direction == 'DOWN':
                        self.players[addr][1] = min(HEIGHT, self.players[addr][1] + 5)
                    elif direction == 'LEFT':
                        self.players[addr][0] = max(0, self.players[addr][0] - 5)
                    elif direction == 'RIGHT':
                        self.players[addr][0] = min(WIDTH, self.players[addr][0] + 5)
                
                self.broadcast_positions()

        except Exception as e:
            print(f"[ERROR] Cliente {addr} desconectado inesperadamente: {e}")
        finally:
            with self.lock:
                print(f"[DESCONECTADO] {addr} se ha desconectado.")
                if addr in self.players:
                    del self.players[addr]
                if conn in self.connections:
                    self.connections.remove(conn)
            self.broadcast_positions()
            conn.close()

    def start(self):
        print("[SERVIDOR] Esperando conexiones...")
        while True:
            try:
                conn, addr = self.server.accept()
                print(f"[NUEVA CONEXIÓN] {addr} conectado.")
                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
            except Exception as e:
                print(f"[ERROR] Al aceptar conexión: {e}")

# ==================== CLASE CLIENTE ====================
class Client:
    def __init__(self, host):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            resolved_host = socket.gethostbyname(host)
            self.client.connect((resolved_host, PORT))
            print(f"[CLIENTE] Conectado al servidor {resolved_host}:{PORT}")
        except Exception as e:
            print(f"[ERROR] No se pudo conectar al servidor: {e}")
            exit()

        pg.init()
        info = pg.display.Info()
        self.screen = pg.display.set_mode((info.current_w, info.current_h), pg.FULLSCREEN)
        pg.display.set_caption("Juego Multijugador")
        self.clock = pg.time.Clock()

    def send_direction(self, direction):
        try:
            self.client.sendall(pickle.dumps(direction))
        except Exception as e:
            print(f"[ERROR] No se pudo enviar la dirección: {e}")

    def receive_positions(self):
        try:
            self.client.settimeout(0.1)
            data = self.client.recv(4096)
            return pickle.loads(data) if data else {}
        except socket.timeout:
            return {}
        except Exception as e:
            print(f"[ERROR] Al recibir posiciones: {e}")
            return {}

    def runVoxelEngine(self):
        app = VoxelEngine()
        # Instanciar NetworkManager en modo cliente usando la instancia del mundo en app.scene.world
        net_manager = NetworkManager(is_server=False, sock=self.client, world=app.scene.world)
        app.net_manager = net_manager  # Guardar la referencia para que otras partes (p.ej., VoxelHandler) puedan usarla
        app.run()

# ==================== CLASE VOXELENGINE ====================
class VoxelEngine:
    def __init__(self):
        pg.init()
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, MAJOR_VER)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, MINOR_VER)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.gl_set_attribute(pg.GL_DEPTH_SIZE, DEPTH_SIZE)
        pg.display.gl_set_attribute(pg.GL_MULTISAMPLESAMPLES, NUM_SAMPLES)

        # Nota: Asumimos que WIN_RES es convertible o se usa directamente aquí
        pg.display.set_mode(WIN_RES, flags=pg.OPENGL | pg.DOUBLEBUF)
        self.ctx = mgl.create_context()

        self.ctx.enable(flags=mgl.DEPTH_TEST | mgl.CULL_FACE | mgl.BLEND)
        self.ctx.gc_mode = 'auto'

        self.clock = pg.time.Clock()
        self.delta_time = 0
        self.time = 0

        pg.event.set_grab(True)
        pg.mouse.set_visible(False)

        self.is_running = True
        self.on_init()

    def on_init(self):
        self.textures = Textures(self)
        self.player = Player(self)
        self.shader_program = ShaderProgram(self)
        self.scene = Scene(self)

    def update(self):
        self.player.update()
        self.shader_program.update()
        self.scene.update()

        self.delta_time = self.clock.tick()
        self.time = pg.time.get_ticks() * 0.001
        pg.display.set_caption(f'{self.clock.get_fps() :.0f}')

    def render(self):
        self.ctx.clear(color=BG_COLOR)
        self.scene.render()
        pg.display.flip()

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                self.is_running = False
            self.player.handle_event(event=event)

    def run(self):
        while self.is_running:
            self.handle_events()
            self.update()
            self.render()
        pg.quit()
        sys.exit()

# ==================== EJECUCIÓN PRINCIPAL ====================
if __name__ == "__main__":
    choice = input("¿Quieres iniciar como servidor (s) o cliente (c)? ").strip().lower()

    if choice == 's':
        # Modo servidor: crear el mundo autoritativo y arrancar el servidor de red.
        engine = VoxelEngine()
        server = Server()
        dummy_sock = DummySocket()
        # Usamos engine.scene.world, ya que el mundo se crea en Scene.on_init()
        net_manager = NetworkManager(is_server=True, sock=dummy_sock, world=engine.scene.world, connections=server.connections)
        engine.net_manager = net_manager
        threading.Thread(target=server.start, daemon=True).start()
        def broadcast_loop():
            while True:
                net_manager.send_world_update()
                time.sleep(0.1)  # Actualiza 10 veces por segundo
        threading.Thread(target=broadcast_loop, daemon=True).start()
        engine.run()

    elif choice == 'c':
        host = input("Introduce la IP del servidor (ej: 192.168.1.10): ").strip()
        client_obj = Client(host)
        client_obj.runVoxelEngine()

    else:
        print("S o c te he dicho...!. Ejecuta nuevamente e ingresa 's' para servidor o 'c' para cliente.")
