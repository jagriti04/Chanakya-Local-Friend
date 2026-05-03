from chanakya.services.tool_loader import (
    get_cached_tools,
    get_tools_availability,
    initialize_all_tools,
)


def main() -> None:
    initialize_all_tools()
    print("Tools loaded:", len(get_cached_tools()))
    print("Status:", get_tools_availability())


if __name__ == "__main__":
    main()
