use serde::de::DeserializeOwned;
use std::path::{Path, PathBuf};

use clap::{App, Arg};

mod error;
pub use error::Error;

pub mod task;
pub use task::Task;

pub struct Context {
    work_dir: PathBuf,
}

fn init_config<T>() -> Result<(T, PathBuf), Error>
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

pub fn load_secrets<'de, D, T>(deserializer: D) -> Result<T, D::Error>
where
    D: serde::Deserializer<'de>,
    T: DeserializeOwned,
{
    let secret_file_path: String = serde::Deserialize::deserialize(deserializer)?;
    let secret_file = std::fs::File::open(secret_file_path)
        .map_err(|_| serde::de::Error::custom("Could not open secret file."))?;
    Ok(serde_yaml::from_reader(secret_file)
        .map_err(|_| serde::de::Error::custom("Could not parse secrets file."))?)
}

pub fn scriptworker_main<Config, A, E>(
    do_work: impl FnOnce(Config, &Context, Task<A, E>) -> Result<(), Error>,
) where
    Config: DeserializeOwned,
    A: DeserializeOwned,
    E: DeserializeOwned,
{
    let result = (|| {
        let (config, work_dir) = init_config::<Config>()?;
        // TODO: Setup rust logging
        let task_filename = work_dir.join("task.json");
        let task = Task::<A, E>::load(&task_filename)?;

        do_work(config, &Context { work_dir }, task)
    })();
    match result {
        Ok(()) => std::process::exit(0),
        Err(err) => {
            if let Error::MalformedPayload(message) = &err {
                std::println!("{}", &message)
            }
            if let Error::InternalError(message) = &err {
                std::println!("{}", &message)
            }
            std::process::exit(err.exit_code())
        }
    }
}

#[cfg(not(test))]
// Work around for rust-lang/rust#62127
pub use scriptworker_script_macros::main;
