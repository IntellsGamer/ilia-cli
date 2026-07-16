use actix_web::{get, web, App, HttpResponse, HttpServer, Responder};
use serde::Serialize;

#[derive(Serialize)]
struct Info {
    project: &'static str,
    version: &'static str,
}

#[derive(Serialize)]
struct Health {
    status: &'static str,
}

#[get("/")]
async fn index() -> impl Responder {
    HttpResponse::Ok().json(Info {
        project: "{{ project_name }}",
        version: "{{ version }}",
    })
}

#[get("/health")]
async fn health() -> impl Responder {
    HttpResponse::Ok().json(Health { status: "ok" })
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    println!("{{ project_name }} running on http://localhost:{{ port }}");
    HttpServer::new(|| App::new().service(index).service(health))
        .bind(("0.0.0.0", {{ port }}))?
        .run()
        .await
}
