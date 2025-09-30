from datetime import datetime
from src.config.config import WEATHER_MULTIPLIERS
from .inventory import Inventory


class Player:
    """Representa al repartidor (jugador)."""
    
    def __init__(self, x, y, income_goal):
        self.x = x
        self.y = y
        self.income_goal = income_goal
        
        self.inventory = Inventory(max_weight=10)
        self.stamina = 100
        self.reputation = 70
        self.total_income = 0
        self.is_exhausted = False
        
        self.base_speed = 3
        self.stamina_consumption_base = 0.5
        self.last_position = (x, y)
        
        # Estadísticas para reputación
        self.deliveries_streak = 0
        self.first_late_today = True

    def get_total_weight(self):
        """Calcula peso total del inventario."""
        return self.inventory.current_weight

    def get_weather_multiplier(self, weather_condition):
        """Obtiene multiplicador de clima."""
        return WEATHER_MULTIPLIERS.get(weather_condition, 1.0)
        
    def calculate_speed(self, weather_condition, surface_weight_tile):
        """Calcula velocidad actual del jugador."""
        total_weight = self.get_total_weight()
        m_weather = self.get_weather_multiplier(weather_condition)
        m_weight = max(0.8, 1 - 0.03 * total_weight)
        m_rep = 1.03 if self.reputation >= 90 else 1.0
        
        if self.stamina <= 0:
            m_stamina = 0.0
        elif self.stamina < 30:
            m_stamina = 0.8
        else:
            m_stamina = 1.0

        speed = (self.base_speed * m_weather * m_weight * 
                m_rep * m_stamina * surface_weight_tile)
        return speed

    def consume_stamina(self, weather_condition):
        """Calcula y consume resistencia por movimiento."""
        total_weight = self.get_total_weight()
        consumption = self.stamina_consumption_base
        
        if total_weight > 3:
            consumption += 0.2 * (total_weight - 3)
        
        if weather_condition in ["rain", "wind"]:
            consumption += 0.1
        elif weather_condition == "storm":
            consumption += 0.3
        elif weather_condition == "heat":
            consumption += 0.2
        
        self.stamina = max(0, self.stamina - consumption)
        
        if self.stamina <= 0:
            self.is_exhausted = True
            
    def recover_stamina(self, in_rest_point=False):
        """Recupera resistencia."""
        recovery = 10 if in_rest_point else 5
        self.stamina = min(100, self.stamina + recovery)
        
        if self.stamina >= 30 and self.is_exhausted:
            self.is_exhausted = False
    
    def move(self, dx, dy, weather_condition, surface_weight_tile):
        """Mueve al jugador y consume resistencia."""
        if not self.is_exhausted:
            self.x += dx
            self.y += dy
            self.consume_stamina(weather_condition)
            return True
        return False
            
    def accept_order(self, order):
        """Acepta un pedido y lo añade al inventario."""
        try:
            self.inventory.add_order(order)
            return True
        except ValueError as e:
            print(f"No se puede aceptar: {e}")
            return False
        
    def complete_delivery(self, current_time):
        """Completa entrega actual y actualiza reputación/ingresos."""
        if self.inventory.current_order is None:
            return None
        
        order = self.inventory.current_order.order
        deadline = datetime.fromisoformat(order.deadline)
        time_diff = (deadline - current_time).total_seconds()
        
        # Calcular cambio de reputación
        rep_change = 0
        if time_diff >= 0:
            total_time = 600  # Asumiendo 10 min por pedido
            if time_diff >= 0.20 * total_time:
                rep_change = 5  # Entrega temprana
            else:
                rep_change = 3  # A tiempo
            self.deliveries_streak += 1
        else:
            time_late = abs(time_diff)
            if time_late <= 30:
                rep_change = -2
            elif time_late <= 120:
                rep_change = -5
            else:
                rep_change = -10
            
            # Primera tardanza del día con reputación alta
            if self.first_late_today and self.reputation >= 85:
                rep_change //= 2
                self.first_late_today = False
            
            self.deliveries_streak = 0
        
        # Bonus por racha
        if self.deliveries_streak >= 3:
            rep_change += 2
            self.deliveries_streak = 0
        
        self.reputation = max(0, min(100, self.reputation + rep_change))
        
        # Calcular pago
        payout = order.payout
        if self.reputation >= 90:
            payout *= 1.05
        
        self.total_income += payout
        
        # Completar orden en inventario
        completed = self.inventory.complete_current_order()
        
        return {
            'order': completed,
            'payout': payout,
            'rep_change': rep_change
        }
    
    def cancel_order(self):
        """Cancela pedido actual."""
        if self.inventory.current_order:
            self.reputation = max(0, self.reputation - 4)
            self.inventory.complete_current_order()
            self.deliveries_streak = 0
            return True
        return False
    
    def is_defeated(self):
        """Verifica si el jugador ha perdido."""
        return self.reputation < 20
    
    def has_won(self):
        """Verifica si el jugador ha ganado."""
        return self.total_income >= self.income_goal