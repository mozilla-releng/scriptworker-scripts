use serde::de::DeserializeOwned;
use serde_derive::Deserialize;
use std::path::{Path, PathBuf};

use clap::{App, Arg};

#[derive(Deserialize, Debug)]
pub struct Empty {}

#[derive(Deserialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct TaskArtifacts<A> {
    pub task_type: String,
    pub task_id: String,
    // TODO: Path
    pub paths: Vec<PathBuf>,
    #[serde(flatten)]
    pub attributes: A,
}

#[derive(Deserialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct TaskPayload<A, E> {
    pub upstream_artifacts: Vec<TaskArtifacts<A>>,
    #[serde(flatten)]
    pub extra: E,
}

#[derive(Deserialize, Debug)]
pub struct Task<A = Empty, E = Empty> {
    pub dependencies: Option<Vec<String>>,
    pub scopes: Vec<String>,
    pub payload: TaskPayload<A, E>,
}

fn init_config<T>() -> Result<(T, PathBuf), Box<dyn std::error::Error>>
where
    T: DeserializeOwned,
{
    let matches = App::new("scriptworker")
        .arg(Arg::with_name("CONFIG_FILE").index(1).required(true))
        .arg(Arg::with_name("WORK_DIR").index(2).required(true))
        .get_matches();

    let config_file = matches.value_of_os("CONFIG_FILE").unwrap();
    let work_dir = Path::new(matches.value_of_os("WORK_DIR").unwrap());
    Ok((
        serde_yaml::from_reader(std::fs::File::open(config_file)?)?,
        work_dir.into(),
    ))
}

fn get_task<A, E>(work_dir: &Path) -> Result<Task<A, E>, Box<dyn std::error::Error>>
where
    A: DeserializeOwned,
    E: DeserializeOwned,
{
    let task_file = work_dir.join("task.json");
    Ok(serde_json::from_reader(std::fs::File::open(task_file)?)?)
}

pub fn main<Config, A, E>(
    do_work: impl FnOnce(Config, &Path, Task<A, E>) -> Result<(), Box<dyn std::error::Error>>,
) -> Result<(), Box<dyn std::error::Error>>
where
    Config: DeserializeOwned,
    A: DeserializeOwned,
    E: DeserializeOwned,
{
    let (config, work_dir) = init_config::<Config>()?;
    // TODO: logging
    let task = get_task(&work_dir)?;

    do_work(config, &work_dir, task)

    // TODO: Statuses
}

// TODO: Turn into method and don't pass around work_dir
pub fn get_artifact_path(task_id: &String, path: &Path, work_dir: &Path) -> PathBuf {
    // TODO: .. traversal
    if path.is_absolute() {
        panic!("Can't get artifact at absolute path.")
    }
    work_dir.join("cot").join(task_id).join(path)
}
