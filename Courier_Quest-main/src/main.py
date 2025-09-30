"""
Courier Quest - Primer Proyecto Programado
EIF-207 Estructuras de Datos
II Ciclo 2025
"""

import pygame
from src.logic.game import Game
from src.logic.main_menu import MainMenu


def main():
    """Punto de entrada del juego."""
    pygame.init()
    screen = pygame.display.set_mode((1200, 800))
    pygame.display.set_caption("Courier Quest")
    clock = pygame.time.Clock()

    # Bucle principal que controla el estado (menú o juego)
    while True:
        # Iniciar y correr el menú principal
        menu = MainMenu(screen, 1200, 800)
        action = run_menu_loop(menu, clock)

        # Si el usuario elige "NUEVA PARTIDA"
        if action == "start_game":
            print_game_intro()
            try:
                game = Game()
                # El método game.run() contiene su propio bucle y finaliza pygame
                game.run()
            except Exception as e:
                print(f"\nError al ejecutar el juego: {e}")
                raise
            # Una vez que el juego termina, salimos del bucle principal
            break

        # Si el usuario elige "SALIR" o cierra la ventana del menú
        elif action == "exit":
            break

        # Aquí se podrían manejar otras acciones como "load_game" o "high_scores"
        else:
            print(f"Acción '{action}' no implementada. Saliendo.")
            break

    pygame.quit()


def run_menu_loop(menu, clock):
    """Maneja el bucle de eventos y dibujado del menú principal."""
    while True:
        # Delta time para animaciones consistentes
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "exit"

            # El menú maneja sus propios eventos y devuelve una acción si se presiona un botón
            action = menu.handle_event(event)
            if action:
                return action  # Devuelve la acción (ej: "start_game", "exit")

        menu.update(dt)
        menu.draw()


def print_game_intro():
    """Imprime los controles e información del juego en la consola."""
    print("=" * 50)
    print("COURIER QUEST")
    print("=" * 50)
    print("\nControles:")
    print("  Flechas: Moverse")
    print("  N/P: Siguiente/Anterior pedido")
    print("  S: Ordenar por prioridad")
    print("  D: Ordenar por deadline")
    print("  Enter: Completar entrega")
    print("  U: Deshacer")
    print("  F5: Guardar | F9: Cargar")
    print("\n¡Alcanza tu meta de ingresos antes del tiempo!")
    print("=" * 50)


if __name__ == "__main__":
    main()