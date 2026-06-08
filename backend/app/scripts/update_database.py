from app.scripts.bootstrap_db import run_migrations
from app.scripts.seed_all import main as seed_all


def main(include_sample_staff: bool = True) -> None:
    run_migrations()
    seed_all(include_sample_staff=include_sample_staff)
    print("Database updated with migrations and seed scripts.")


if __name__ == "__main__":
    main()
