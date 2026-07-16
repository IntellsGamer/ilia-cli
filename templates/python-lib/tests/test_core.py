from {{ project_name }}.core import hello

def test_hello():
    assert hello("World") == "Hello, World!"
    assert hello() == "Hello, world!"
