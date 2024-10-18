import sys

from itakello_logging import ItakelloLogging

from src.managers import ConfigManager, SimulationManager

logger = ItakelloLogging(debug=True).get_logger(__name__)


def main(config_filename: str) -> None:
    config_data = ConfigManager().load_config(config_filename)
    simulation_manager = SimulationManager(config_data, config_filename)
    simulation_manager.setup()
    simulation_manager.create_shapes()
    simulation_manager.run()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("Usage: python main.py <config_filename>")
        sys.exit(1)
    main(sys.argv[1])
