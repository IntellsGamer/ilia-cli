#[macro_use] extern crate rocket;
use rocket::serde::json::Json;
use serde::Serialize;

#[derive(Serialize)]
struct Info {
    project: &'static str,
    version: &'static str,
}

#[get("/")]
fn index() -> Json<Info> {
    Json(Info { project: "{{ project_name }}", version: "{{ version }}" })
}

#[get("/health")]
fn health() -> Json<&'static str> {
    Json("ok")
}

#[launch]
fn rocket() -> _ {
    rocket::build().mount("/", routes![index, health])
}
