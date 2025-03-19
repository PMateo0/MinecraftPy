import pickle
import threading
import time
import numpy as np

class NetworkManager:
    """
    Clase para gestionar la sincronización del estado del mundo entre el servidor y los clientes.
    
    En modo servidor, se encarga de recibir actualizaciones locales (por ejemplo, cambios en los voxeles)
    y reenvía los cambios a todos los clientes conectados.
    
    En modo cliente, se conecta al servidor y recibe actualizaciones para aplicarlas a la instancia local del World.
    """
    def __init__(self, is_server, sock, world, connections=None):
        """
        Los parametros que estamos recibiendo en el init son:
        :param is_server: True si la instancia es del lado del servidor.
        :param sock: 
            - En modo cliente, es el socket conectado al servidor.
            - En modo servidor, se puede pasar un socket "dummy" (no se usa para enviar, se usará la lista de conexiones).
        :param world: Instancia del mundo (World) que se va a sincronizar.
        :param connections: En modo servidor, una lista de sockets de clientes a los que se enviarán actualizaciones.
        """
        self.is_server = is_server
        self.sock = sock
        self.world = world
        self.connections = connections if connections is not None else []
        self.running = True

        # Iniciar el hilo de recepción de mensajes
        self.thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.thread.start()

    def receive_loop(self):
        """Bucle que recibe mensajes del socket y los procesa."""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if data:
                    message = pickle.loads(data)
                    self.process_message(message)
                else:
                    time.sleep(0.01)
            except Exception as e:
                # Puede producirse cuando se cierra la conexión
                print(f"[NetworkManager] Error recibiendo datos: {e}")
                break

    def process_message(self, message):
        """
        Procesa el mensaje recibido.
        Se esperan mensajes con la siguiente estructura:
            {"type": "world_update", "data": <matriz_voxeles>}
            {"type": "voxel_update", "data": (chunk_index, voxel_index, new_voxel_id)}
        """
        msg_type = message.get("type")
        if msg_type == "world_update":
            new_voxels = message.get("data")
            # Se espera que new_voxels sea un arreglo de NumPy con la misma forma que self.world.voxels
            if new_voxels.shape == self.world.voxels.shape:
                self.world.voxels[:] = new_voxels[:]
                self.world.build_chunk_mesh()  # Reconstruir mallas para reflejar la actualización
                print("[NetworkManager] Actualización completa del mundo aplicada.")
            else:
                print("[NetworkManager] La forma de los datos del mundo no coincide.")
        elif msg_type == "voxel_update":
            # Se espera un update individual: (chunk_index, voxel_index, new_voxel_id)
            voxel_data = message.get("data")
            if voxel_data:
                chunk_index, voxel_index, new_voxel_id = voxel_data
                self.world.voxels[chunk_index][voxel_index] = new_voxel_id
                self.world.chunks[chunk_index].mesh.rebuild()
                print("[NetworkManager] Actualización individual de voxel aplicada.")
        # Aquí se pueden agregar más tipos de mensajes según se requiera.

    def send_world_update(self):
        """
        Envía una actualización completa del estado del mundo.
        Este método se usará en el servidor para enviar la matriz de voxeles a todos los clientes.
        """
        message = {
            "type": "world_update",
            "data": self.world.voxels,
        }
        self.send(message)

    def send_voxel_update(self, chunk_index, voxel_index, new_voxel_id):
        """
        Envía una actualización individual de un voxel.
        
        :param chunk_index: Índice del chunk modificado.
        :param voxel_index: Índice del voxel dentro del chunk.
        :param new_voxel_id: Nuevo valor del voxel.
        """
        message = {
            "type": "voxel_update",
            "data": (chunk_index, voxel_index, new_voxel_id),
        }
        self.send(message)

    def send(self, message):
        """Serializa y envía el mensaje según el modo."""
        data = pickle.dumps(message)
        if self.is_server:
            # En el servidor, se hace broadcast a todas las conexiones
            for conn in self.connections:
                try:
                    conn.sendall(data)
                except Exception as e:
                    print(f"[NetworkManager] Error enviando datos a un cliente: {e}")
        else:
            # En modo cliente, se envía al servidor
            try:
                self.sock.sendall(data)
            except Exception as e:
                print(f"[NetworkManager] Error enviando datos: {e}")

    def stop(self):
        """Detiene el hilo de recepción y cierra la conexión."""
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        self.thread.join()

