from src.core.repository.code_table_repository import code_repo

def test_resolve():
    code_repo.preload()
    addr_info = code_repo.get_address_info("LA143")
    shop_name = code_repo.get_shop_code_name("SC01")
    print(f"Address: {addr_info['name']}")
    print(f"Shop: {shop_name}")
    print(f"Query: {addr_info['name']} {shop_name}")

if __name__ == "__main__":
    test_resolve()
