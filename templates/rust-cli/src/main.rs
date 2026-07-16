use clap::Parser;

#[derive(Parser)]
#[command(name = "{{ project_name }}")]
#[command(version = "{{ version }}")]
#[command(about = "{{ description }}")]
struct Cli {
    name: Option<String>,

    #[arg(short, long)]
    verbose: bool,
}

fn main() {
    let cli = Cli::parse();
    let name = cli.name.unwrap_or_else(|| "world".to_string());
    if cli.verbose {
        println!("{{ project_name }} v{{ version }}");
    }
    println!("Hello, {name}!");
}
