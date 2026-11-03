from threepounds_training.server import build_server


def main() -> None:
    build_server().run(transport="stdio")
