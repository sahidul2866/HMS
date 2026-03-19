from app.scripts.seed_access_control import main as seed_access_control


def seed() -> None:
    seed_access_control()


if __name__ == "__main__":
    seed()
