import strawberry

@strawberry.type
class Query:
    @strawberry.field
    def hello(self, name: str = "world") -> str:
        return f"Hello, {name}!"

    @strawberry.field
    def version(self) -> str:
        return "{{ version }}"

schema = strawberry.Schema(query=Query)
