"""
Courier Quest - Primer Proyecto Programado
EIF-207 Estructuras de Datos
II Ciclo 2025
"""

from src.logic.game import Game


def main():
    """Punto de entrada del juego."""
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
    
    try:
        game = Game()
        game.run()
    except KeyboardInterrupt:
        print("\n\nJuego interrumpido. ¡Hasta pronto!")
    except Exception as e:
        print(f"\nError al ejecutar el juego: {e}")
        raise


if __name__ == "__main__":
    main()