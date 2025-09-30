import pygame
import random
from datetime import datetime, timedelta
from src.logic.proxy import Proxy
from src.logic.city import City, OrderManager
from src.logic.player import Player
from src.logic.order import Order
from src.logic.game_state import GameState
from src.logic.ui import UIManager
from src.config.config import WEATHER_MULTIPLIERS


class Game:
    """Bucle principal del juego."""
    
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1200, 800))
        pygame.display.set_caption("Courier Quest")
        self.clock = pygame.time.Clock()
        
        # Cargar datos del API
        proxy = Proxy()
        map_data = proxy.get_map()
        jobs_data = proxy.get_jobs()
        self.weather = proxy.get_weather()
        
        # Inicializar componentes
        self.city = City(map_data)
        self.order_manager = OrderManager(jobs_data)
        self.player = Player(1, 1, self.city.goal)
        self.game_state = GameState()
        self.ui = UIManager(1200, 800)
        
        # Variables de tiempo
        self.game_duration = 600  # 10 minutos
        self.start_time = datetime.now()
        self.elapsed_time = 0
        self.running = True
        self.game_over = False
        self.victory = False
        
        # Sistema de clima
        self.current_weather = self.weather.state
        self.next_weather = self.weather.state
        self.weather_timer = random.uniform(45, 60)
        self.weather_transition_time = 0
        self.in_transition = False
        
        # Mensajes
        self.message = ""
        self.message_timer = 0

    def show_message(self, text, duration=2.0):
        """Muestra un mensaje temporal."""
        self.message = text
        self.message_timer = duration

    def handle_input(self):
        """Maneja input del jugador."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.KEYDOWN and not self.game_over:
                # Movimiento
                dx, dy = 0, 0
                if event.key == pygame.K_UP:
                    dy = -1
                elif event.key == pygame.K_DOWN:
                    dy = 1
                elif event.key == pygame.K_LEFT:
                    dx = -1
                elif event.key == pygame.K_RIGHT:
                    dx = 1
                
                # Ejecutar movimiento
                if dx != 0 or dy != 0:
                    new_x = self.player.x + dx
                    new_y = self.player.y + dy
                    
                    if not self.city.is_blocked(new_x, new_y):
                        surface_weight = self.city.get_surface_weight(new_x, new_y)
                        
                        if self.player.move(dx, dy, self.current_weather, surface_weight):
                            self.game_state.save_state(
                                self.player, 
                                self.player.inventory,
                                self.elapsed_time,
                                self.current_weather
                            )
                            self.check_delivery_points()
                        else:
                            self.show_message("¡Exhausto! Descansa para recuperarte")
                    else:
                        self.show_message("No puedes moverte ahí")
                
                # Inventario
                if event.key == pygame.K_n:
                    self.player.inventory.view_next_order()
                    self.show_message("Siguiente pedido")
                elif event.key == pygame.K_p:
                    self.player.inventory.view_prev_order()
                    self.show_message("Pedido anterior")
                elif event.key == pygame.K_s:
                    self.player.inventory.sort_inventory(lambda o: o.priority)
                    self.show_message("Ordenado por prioridad")
                elif event.key == pygame.K_d:
                    self.player.inventory.sort_inventory(lambda o: o.deadline)
                    self.show_message("Ordenado por deadline")
                
                # Aceptar pedido
                if event.key == pygame.K_a:
                    self.accept_order_at_location()
                
                # Completar entrega
                if event.key == pygame.K_RETURN:
                    self.complete_delivery()
                
                # Cancelar pedido
                if event.key == pygame.K_c:
                    if self.player.cancel_order():
                        self.show_message("Pedido cancelado (-4 reputación)")
                
                # Guardar/Cargar
                if event.key == pygame.K_F5:
                    self.save_game(1)
                    self.show_message("Juego guardado")
                elif event.key == pygame.K_F9:
                    if self.load_game(1):
                        self.show_message("Juego cargado")
                
                # Deshacer
                if event.key == pygame.K_u:
                    state = self.game_state.undo(1)
                    if state:
                        self.restore_state(state)
                        self.show_message("Deshacer último movimiento")

    def accept_order_at_location(self):
        """Acepta un pedido si el jugador está en el punto de recogida."""
        available = self.order_manager.get_available()
        
        for order_data in available:
            pickup = order_data['pickup']
            if [self.player.x, self.player.y] == pickup:
                order = Order(
                    order_data['id'],
                    order_data['pickup'],
                    order_data['dropoff'],
                    order_data['payout'],
                    order_data['deadline'],
                    order_data['weight'],
                    order_data['priority'],
                    order_data['release_time']
                )
                
                if self.player.accept_order(order):
                    self.order_manager.remove_order(order_data['id'])
                    self.show_message(f"Pedido {order.id} aceptado!")
                    return
                else:
                    self.show_message("Inventario lleno")
                    return
        
        self.show_message("No hay pedidos en esta ubicación")

    def check_delivery_points(self):
        """Verifica si el jugador está en un punto de entrega."""
        if self.player.inventory.current_order:
            dropoff = self.player.inventory.current_order.order.dropoff
            if [self.player.x, self.player.y] == dropoff:
                self.show_message("¡Punto de entrega! Presiona ENTER")

    def complete_delivery(self):
        """Completa entrega actual."""
        if self.player.inventory.current_order is None:
            self.show_message("No hay pedido para entregar")
            return
        
        dropoff = self.player.inventory.current_order.order.dropoff
        if [self.player.x, self.player.y] != dropoff:
            self.show_message("Debes estar en el punto de entrega")
            return
        
        result = self.player.complete_delivery(
            self.start_time + timedelta(seconds=self.elapsed_time)
        )
        
        if result:
            msg = f"¡Entregado! +${int(result['payout'])} | Rep: {result['rep_change']:+d}"
            self.show_message(msg, 3.0)

    def update_weather(self, dt):
        """Actualiza sistema de clima con transición suave."""
        self.weather_timer -= dt
        
        if self.in_transition:
            self.weather_transition_time += dt
            if self.weather_transition_time >= 4:
                self.current_weather = self.next_weather
                self.in_transition = False
        
        if self.weather_timer <= 0 and not self.in_transition:
            self.next_weather = self.weather.next_state()
            self.weather_timer = random.uniform(45, 60)
            self.weather_transition_time = 0
            self.in_transition = True

    def get_current_weather_multiplier(self):
        """Obtiene multiplicador de clima con interpolación."""
        if not self.in_transition:
            return WEATHER_MULTIPLIERS.get(self.current_weather, 1.0)
        
        progress = self.weather_transition_time / 4.0
        current_mult = WEATHER_MULTIPLIERS.get(self.current_weather, 1.0)
        next_mult = WEATHER_MULTIPLIERS.get(self.next_weather, 1.0)
        
        return current_mult + (next_mult - current_mult) * progress

    def update(self, dt):
        """Actualiza lógica del juego."""
        if self.game_over:
            return
        
        self.elapsed_time += dt
        
        # Actualizar clima
        self.update_weather(dt)
        
        # Actualizar pedidos disponibles
        self.order_manager.update_available(self.elapsed_time)
        
        # Recuperar resistencia si está quieto
        if (self.player.x, self.player.y) == self.player.last_position:
            self.player.recover_stamina()
        self.player.last_position = (self.player.x, self.player.y)
        
        # Actualizar mensaje
        if self.message_timer > 0:
            self.message_timer -= dt
        
        # Verificar condiciones de victoria/derrota
        if self.player.is_defeated():
            self.end_game(False)
        
        if self.elapsed_time >= self.game_duration:
            if self.player.has_won():
                self.end_game(True)
            else:
                self.end_game(False)

    def draw(self):
        """Dibuja el juego."""
        self.screen.fill((20, 20, 30))
        
        # Dibujar mapa
        self.ui.draw_map(self.screen, self.city, self.player.x, self.player.y)
        
        # Dibujar HUD
        self.ui.draw_hud(self.screen, self.player, self.game_duration, 
                        self.current_weather, self.elapsed_time)
        
        # Dibujar pedido actual
        self.ui.draw_current_order(self.screen, self.player.inventory, self.city)
        
        # Dibujar pedidos disponibles
        available = self.order_manager.get_available()
        self.ui.draw_available_orders(self.screen, available)
        
        # Mensaje temporal
        if self.message_timer > 0:
            font = pygame.font.Font(None, 32)
            text = font.render(self.message, True, (255, 255, 100))
            rect = text.get_rect(center=(600, 400))
            
            # Fondo semi-transparente
            bg = pygame.Surface((rect.width + 40, rect.height + 20))
            bg.set_alpha(200)
            bg.fill((0, 0, 0))
            bg_rect = bg.get_rect(center=(600, 400))
            self.screen.blit(bg, bg_rect)
            self.screen.blit(text, rect)
        
        # Pantalla de fin de juego
        if self.game_over:
            score = self.calculate_score()
            self.ui.draw_game_over(self.screen, self.victory, score)
        
        pygame.display.flip()

    def run(self):
        """Ejecuta el bucle principal."""
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            
            self.handle_input()
            self.update(dt)
            self.draw()
        
        pygame.quit()

    def save_game(self, slot):
        """Guarda la partida."""
        game_data = {
            'elapsed_time': self.elapsed_time,
            'weather_state': self.current_weather,
            'weather_timer': self.weather_timer
        }
        self.game_state.save_game(slot, self.player, self.player.inventory, game_data)

    def load_game(self, slot):
        """Carga una partida."""
        data = self.game_state.load_game(slot)
        if data:
            # Restaurar player
            p = data['player']
            self.player.x = p['x']
            self.player.y = p['y']
            self.player.stamina = p['stamina']
            self.player.reputation = p['reputation']
            self.player.total_income = p['total_income']
            
            # Restaurar inventario
            from src.logic.inventory import Inventory
            self.player.inventory = Inventory()
            for order_data in data['inventory']:
                order = Order(**order_data)
                self.player.inventory.add_order(order)
            
            # Restaurar datos de juego
            gd = data['game_data']
            self.elapsed_time = gd['elapsed_time']
            self.current_weather = gd['weather_state']
            self.weather_timer = gd['weather_timer']
            
            return True
        return False

    def restore_state(self, state):
        """Restaura estado anterior (deshacer)."""
        self.player.x, self.player.y = state['player_pos']
        self.player.stamina = state['stamina']
        self.player.reputation = state['reputation']
        self.player.total_income = state['income']
        self.elapsed_time = state['time']
        self.current_weather = state['weather']

    def calculate_score(self):
        """Calcula puntaje final."""
        bonus = 0
        if self.victory and self.elapsed_time < self.game_duration * 0.8:
            bonus = 500
        
        return int(self.player.total_income + bonus)

    def end_game(self, victory):
        """Finaliza el juego y calcula puntaje."""
        self.game_over = True
        self.victory = victory
        
        score = self.calculate_score()
        
        GameState.save_score(
            "Player",
            score,
            self.player.total_income,
            self.player.reputation
        )
        
        print(f"\n{'='*50}")
        print(f"{'VICTORIA' if victory else 'DERROTA'}")
        print(f"Puntaje final: {score}")
        print(f"Ingresos: ${self.player.total_income}")
        print(f"Reputación: {self.player.reputation}")
        print(f"{'='*50}\n")


if __name__ == "__main__":
    game = Game()
    game.run()