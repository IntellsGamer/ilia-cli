from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from schema import schema

app = FastAPI(title="{{ project_name }}", description="{{ description }}")
app.include_router(GraphQLRouter(schema), prefix="/graphql")

@app.get("/")
async def root():
    return {"project": "{{ project_name }}", "graphql": "/graphql"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port={{ port }}, reload=True)
